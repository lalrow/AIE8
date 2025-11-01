"""LangGraph Helpfulness Agent with post-response evaluation loop."""

from typing import Dict, Any, List, Optional
import os

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.tools.arxiv.tool import ArxivQueryRun
from langchain_core.tools import tool
from typing_extensions import TypedDict, Annotated
from langgraph.graph.message import add_messages

from .models import get_openai_model
from .rag import ProductionRAGChain


# ----------------------------
#   Agent State Definition
# ----------------------------

class AgentState(TypedDict):
    """State schema for agent graphs."""
    messages: Annotated[List[BaseMessage], add_messages]


# ----------------------------
#   RAG Tool Builder
# ----------------------------

def create_rag_tool(rag_chain: ProductionRAGChain):
    """Wrap a ProductionRAGChain as a LangChain tool."""
    @tool
    def retrieve_information(query: str) -> str:
        """Retrieve information from student-loan documents."""
        try:
            result = rag_chain.invoke(query)
            return result.content if hasattr(result, "content") else str(result)
        except Exception as e:
            return f"Error retrieving information: {e}"
    return retrieve_information


def get_default_tools(rag_chain: Optional[ProductionRAGChain] = None) -> list:
    """Return Tavily, Arxiv, and optional RAG tools."""
    tools = []
    if os.getenv("TAVILY_API_KEY"):
        tools.append(TavilySearchResults(max_results=5))
    tools.append(ArxivQueryRun())
    if rag_chain:
        tools.append(create_rag_tool(rag_chain))
    return tools


# ----------------------------
#   Core Nodes
# ----------------------------

def call_model(model_with_tools):
    """Return callable node for agent model."""
    def _inner(state: AgentState) -> Dict[str, Any]:
        messages = state["messages"]
        response = model_with_tools.invoke(messages)
        return {"messages": [response]}
    return _inner


def should_continue(state: AgentState):
    """Route to tools or to helpfulness check."""
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "action"
    return "helpfulness"


# ----------------------------
#   Helpfulness Evaluation
# ----------------------------

def helpfulness_node(state: AgentState) -> Dict[str, Any]:
    """Evaluate how helpful the latest response is."""
    if len(state["messages"]) > 10:
        return {"messages": [AIMessage(content="HELPFULNESS:END")]}

    initial_query = state["messages"][0].content
    final_response = state["messages"][-1].content

    template = """
    Given the initial user question and the model's final response,
    decide if the response is helpful ('Y') or unhelpful ('N').

    Question:
    {initial_query}

    Response:
    {final_response}
    """

    prompt = PromptTemplate.from_template(template)
    evaluator = get_openai_model(model_name="gpt-4.1-mini", temperature=0)
    chain = prompt | evaluator | StrOutputParser()
    decision = chain.invoke(
        {"initial_query": initial_query, "final_response": final_response}
    )

    flag = "Y" if "Y" in decision else "N"
    return {"messages": [AIMessage(content=f"HELPFULNESS:{flag}")]}


def helpfulness_decision(state: AgentState):
    """Decide whether to loop for refinement or end."""
    last = state["messages"][-1]
    text = getattr(last, "content", "")
    if "HELPFULNESS:Y" in text:
        return "end"
    if "HELPFULNESS:END" in text:
        return END
    return "continue"


# ----------------------------
#   Agent Builder
# ----------------------------

def create_helpfulness_agent(
    model_name: str = "gpt-4",
    temperature: float = 0.1,
    tools: Optional[List] = None,
    rag_chain: Optional[ProductionRAGChain] = None,
):
    """Create a LangGraph agent with a helpfulness-evaluation loop."""
    if tools is None:
        tools = get_default_tools(rag_chain)

    # Build model and bind tools
    model = get_openai_model(model_name=model_name, temperature=temperature)
    model_with_tools = model.bind_tools(tools)

    # Build graph
    graph = StateGraph(AgentState)
    tool_node = ToolNode(tools)

    # Add nodes
    graph.add_node("agent", call_model(model_with_tools))
    graph.add_node("action", tool_node)
    graph.add_node("helpfulness", helpfulness_node)

    # Set entry and edges
    graph.set_entry_point("agent")
    graph.add_conditional_edges(
        "agent", should_continue, {"action": "action", "helpfulness": "helpfulness"}
    )
    graph.add_edge("action", "agent")
    graph.add_conditional_edges(
        "helpfulness",
        helpfulness_decision,
        {"continue": "agent", "end": END, END: END},
    )

    return graph.compile()


# ----------------------------
#   Example Usage (optional)
# ----------------------------
# if __name__ == "__main__":
#     from .rag import ProductionRAGChain
#     rag_chain = ProductionRAGChain(file_path="./data/sample.pdf")
#     agent = create_helpfulness_agent(rag_chain=rag_chain)
#     response = agent.invoke({"messages": [AIMessage(content="Summarize this document.")]})
#     print(response)
