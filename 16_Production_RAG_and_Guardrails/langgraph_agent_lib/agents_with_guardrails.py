"""Production-safe LangGraph agent with integrated guardrails."""

from typing import Dict, Any, List, Optional
import os
from urllib.parse import quote_plus

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage, HumanMessage
from typing_extensions import TypedDict, Annotated
from langgraph.graph.message import add_messages

from guardrails.hub import (
    RestrictToTopic,
    DetectJailbreak,
    GuardrailsPII,
    ProfanityFree,
    LlmRagEvaluator,
    HallucinationPrompt
)
from guardrails import Guard

from .models import get_openai_model
from .rag import ProductionRAGChain


# ----------------------------
#   Runnable Wrapper
# ----------------------------

class _SafeAgentRunner:
    """Lightweight wrapper to tag runs and print a LangSmith link after invoke.

    This does not guarantee a specific run URL (API differences across versions),
    but it prints a direct Project link using env vars so users can click through
    to their latest traces.
    """

    def __init__(self, runnable, tags: Optional[List[str]] = None):
        self._runnable = runnable.with_config(tags=tags or ["safe-guardrails-agent"])  # add helpful tag

    def _print_langsmith_link(self):
        base = os.environ.get("LANGSMITH_ENDPOINT", "https://smith.langchain.com")
        org = os.environ.get("LANGCHAIN_ORGANIZATION") or os.environ.get("LANGCHAIN_HOSTED_ORG") or ""
        project = os.environ.get("LANGCHAIN_PROJECT", "")
        if org and project:
            url = f"{base}/o/{quote_plus(org)}/projects?name={quote_plus(project)}"
        elif project:
            # Fallback: show projects list filtered by name (org-less may still resolve when logged in)
            url = f"{base}/projects?name={quote_plus(project)}"
        else:
            url = base
        print(f"🔗 LangSmith Project: {url}")

    def invoke(self, *args, **kwargs):
        result = self._runnable.invoke(*args, **kwargs)
        try:
            self._print_langsmith_link()
        except Exception:
            # Best-effort; do not block on telemetry link
            pass
        return result

    # Basic passthroughs for common interfaces
    async def ainvoke(self, *args, **kwargs):
        result = await self._runnable.ainvoke(*args, **kwargs)
        try:
            self._print_langsmith_link()
        except Exception:
            pass
        return result

    def stream(self, *args, **kwargs):
        for chunk in self._runnable.stream(*args, **kwargs):
            yield chunk
        try:
            self._print_langsmith_link()
        except Exception:
            pass

# ----------------------------
#   Extended Agent State
# ----------------------------

class GuardedAgentState(TypedDict):
    """State schema for guarded agent graphs."""
    messages: Annotated[List[BaseMessage], add_messages]
    guard_failures: List[str]  # Track which guards failed
    input_sanitized: bool


# ----------------------------
#   Guard Setup
# ----------------------------

def setup_guards():
    """Initialize all 5 guardrails with production settings."""
    return {
        "topic": Guard().use(RestrictToTopic(
            valid_topics=["student loans", "financial aid", "education financing", "loan repayment"],
            invalid_topics=["investment advice", "crypto", "gambling", "politics"],
            disable_classifier=True,
            disable_llm=False,
            on_fail="exception"
        )),
        "jailbreak": Guard().use(DetectJailbreak()),
        "pii_input": Guard().use(GuardrailsPII(
            entities=["CREDIT_CARD", "SSN", "PHONE_NUMBER", "EMAIL_ADDRESS"],
            on_fail="fix"
        )),
        "profanity": Guard().use(ProfanityFree(
            threshold=0.8,
            validation_method="sentence",
            on_fail="exception"
        )),
        "factuality": Guard().use(LlmRagEvaluator(
            eval_llm_prompt_generator=HallucinationPrompt(prompt_name="hallucination_judge_llm"),
            llm_evaluator_fail_response="hallucinated",
            llm_evaluator_pass_response="factual",
            llm_callable="gpt-4.1-mini",
            on_fail="exception",
            on="prompt"
        ))
    }


# ----------------------------
#   Input Guard Node
# ----------------------------

def input_guard_node(guards):
    """Validate user input with jailbreak, topic, and PII guards."""
    def _validate(state: GuardedAgentState) -> Dict[str, Any]:
        user_msg = state["messages"][-1].content
        failures = []
        
        # 1. Jailbreak detection
        try:
            result = guards["jailbreak"].validate(user_msg)
            if not result.validation_passed:
                return {
                    "messages": [AIMessage(content="I cannot process this request as it appears to be an adversarial prompt.")],
                    "guard_failures": ["jailbreak"]
                }
        except Exception as e:
            return {
                "messages": [AIMessage(content="I cannot process this request for safety reasons.")],
                "guard_failures": ["jailbreak"]
            }
        
        # 2. Topic restriction
        try:
            guards["topic"].validate(user_msg)
        except Exception as e:
            return {
                "messages": [AIMessage(content="I can only help with student loans and financial aid topics. Please ask about those subjects.")],
                "guard_failures": ["topic"]
            }
        
        # 3. PII sanitization (fixes instead of fails)
        try:
            pii_result = guards["pii_input"].validate(user_msg)
            if pii_result.validated_output != user_msg:
                # Replace user message with sanitized version
                state["messages"][-1].content = pii_result.validated_output
                return {"input_sanitized": True}
        except:
            pass  # Continue if PII check fails
        
        return {}  # All guards passed
    return _validate


# ----------------------------
#   Output Guard Node
# ----------------------------

def output_guard_node(guards):
    """Validate agent output with profanity, factuality, and PII guards."""
    def _validate(state: GuardedAgentState) -> Dict[str, Any]:
        agent_response = state["messages"][-1].content
        
        # 1. Profanity check
        try:
            guards["profanity"].validate(agent_response)
        except:
            return {
                "messages": [AIMessage(content="I apologize, but I need to rephrase my response to maintain professionalism.")],
                "guard_failures": state.get("guard_failures", []) + ["profanity"]
            }
        
        # 2. PII redaction in output
        try:
            pii_result = guards["pii_input"].validate(agent_response)
            if pii_result.validated_output != agent_response:
                state["messages"][-1].content = pii_result.validated_output
        except:
            pass
        
        # 3. Factuality check (optional - expensive)
        # Skip for now to avoid latency, can be enabled per use case
        
        return {}
    return _validate


# ----------------------------
#   Guard Routing Logic
# ----------------------------

def should_continue_after_input_guard(state: GuardedAgentState):
    """Route to agent if guards passed, otherwise end."""
    if state.get("guard_failures"):
        return END
    return "agent"


def should_continue_after_output_guard(state: GuardedAgentState):
    """Route based on output validation."""
    if state.get("guard_failures") and len(state.get("guard_failures", [])) > 1:
        return END  # Too many failures, stop
    return END  # Normal completion


# ----------------------------
#   Main Agent Builder
# ----------------------------

def create_safe_guardrails_agent(
    model_name: str = "gpt-4.1-mini",
    temperature: float = 0.1,
    tools: Optional[List] = None,
    rag_chain: Optional[ProductionRAGChain] = None,
):
    """Create a production-safe agent with integrated guardrails.
    
    Guards applied:
    - Input: jailbreak, topic restriction, PII sanitization
    - Output: profanity filter, PII redaction
    
    Args:
        model_name: OpenAI model
        temperature: Model temperature
        tools: Optional tools list
        rag_chain: Optional RAG chain for retrieval
    
    Returns:
        Compiled guarded LangGraph agent
    """
    # Import base tools from agents.py
    from .agents import get_default_tools
    
    if tools is None:
        tools = get_default_tools(rag_chain)
    
    # Setup guards
    guards = setup_guards()
    
    # Setup model
    model = get_openai_model(model_name=model_name, temperature=temperature)
    model_with_tools = model.bind_tools(tools)
    
    # Build graph
    graph = StateGraph(GuardedAgentState)
    tool_node = ToolNode(tools)
    
    # Nodes
    graph.add_node("input_guard", input_guard_node(guards))
    graph.add_node("agent", lambda state: {
        "messages": [model_with_tools.invoke(state["messages"])]
    })
    graph.add_node("action", tool_node)
    graph.add_node("output_guard", output_guard_node(guards))
    
    # Edges
    graph.set_entry_point("input_guard")
    graph.add_conditional_edges(
        "input_guard",
        should_continue_after_input_guard,
        {"agent": "agent", END: END}
    )
    graph.add_conditional_edges(
        "agent",
        lambda s: "action" if getattr(s["messages"][-1], "tool_calls", None) else "output_guard",
        {"action": "action", "output_guard": "output_guard"}
    )
    graph.add_edge("action", "agent")
    graph.add_conditional_edges(
        "output_guard",
        should_continue_after_output_guard,
        {END: END}
    )
    
    compiled = graph.compile()
    # Wrap compiled graph so each invoke prints a LangSmith link users can click
    return _SafeAgentRunner(compiled, tags=["safe-guardrails-agent"])  # type: ignore[return-value]

