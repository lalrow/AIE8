import os
import asyncio
import logging
from typing import Any, Optional, TypedDict, List, Dict
from uuid import uuid4

import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    MessageSendParams,
    SendMessageRequest,
    SendStreamingMessageRequest,
)
from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
    EXTENDED_AGENT_CARD_PATH,
)

from langgraph.graph import StateGraph, START, END


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


DEFAULT_BASE_URL = os.environ.get("A2A_BASE_URL", "http://localhost:10000")


class A2AState(TypedDict):
    messages: List[Dict[str, str]]
    query: str
    a2a_task_id: Optional[str]
    a2a_context_id: Optional[str]
    a2a_last_event: Optional[Dict[str, Any]]
    is_task_complete: bool
    require_user_input: bool


class A2AClientWrapper:
    """Lazy-initialized A2A client wrapper with normalized send APIs."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout_s: float = 60.0):
        self._base_url = base_url
        self._timeout_s = timeout_s
        self._httpx_client: Optional[httpx.AsyncClient] = None
        self._resolver: Optional[A2ACardResolver] = None
        self._agent_card: Optional[AgentCard] = None
        self._client: Optional[A2AClient] = None

    async def _ensure_client(self) -> None:
        if self._client is not None:
            return

        self._httpx_client = httpx.AsyncClient(timeout=httpx.Timeout(self._timeout_s))
        self._resolver = A2ACardResolver(
            httpx_client=self._httpx_client, base_url=self._base_url
        )

        # Try public card, optionally extended
        agent_card: Optional[AgentCard] = None
        try:
            agent_card = await self._resolver.get_agent_card()
            logger.info("Fetched public agent card from %s%s", self._base_url, AGENT_CARD_WELL_KNOWN_PATH)
            if getattr(agent_card, "supports_authenticated_extended_card", False):
                try:
                    _extended = await self._resolver.get_agent_card(
                        relative_card_path=EXTENDED_AGENT_CARD_PATH,
                        http_kwargs={"headers": {"Authorization": "Bearer dummy-token"}},
                    )
                    agent_card = _extended
                    logger.info("Fetched authenticated extended agent card")
                except Exception as e:
                    logger.warning("Extended agent card fetch failed: %s", e)
        except Exception as e:
            logger.error("Failed to fetch agent card: %s", e)
            raise

        self._agent_card = agent_card
        self._client = A2AClient(httpx_client=self._httpx_client, agent_card=agent_card)

    async def send_message(self, query: str, *, task_id: Optional[str] = None, context_id: Optional[str] = None) -> Dict[str, Any]:
        await self._ensure_client()
        assert self._client is not None

        payload: Dict[str, Any] = {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": query}],
                "message_id": uuid4().hex,
            }
        }
        if task_id is not None:
            payload["message"]["task_id"] = task_id
        if context_id is not None:
            payload["message"]["context_id"] = context_id

        request = SendMessageRequest(id=str(uuid4()), params=MessageSendParams(**payload))
        response = await self._client.send_message(request)

        # Normalize conservatively: include raw json and best-effort IDs
        raw_json = response.model_dump(mode="json", exclude_none=True)
        rid = None
        rcx = None
        try:
            rid = raw_json.get("root", {}).get("result", {}).get("id")
            rcx = raw_json.get("root", {}).get("result", {}).get("context_id")
        except Exception:
            pass

        return {
            "content": raw_json,  # Full response JSON for inspection
            "task_id": rid,
            "context_id": rcx,
            "is_task_complete": True,  # Non-stream: treat as completed for demo
            "require_user_input": False,
        }

    async def send_message_streaming(self, query: str, *, task_id: Optional[str] = None, context_id: Optional[str] = None) -> Dict[str, Any]:
        await self._ensure_client()
        assert self._client is not None

        payload: Dict[str, Any] = {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": query}],
                "message_id": uuid4().hex,
            }
        }
        if task_id is not None:
            payload["message"]["task_id"] = task_id
        if context_id is not None:
            payload["message"]["context_id"] = context_id

        request = SendStreamingMessageRequest(id=str(uuid4()), params=MessageSendParams(**payload))
        chunks: List[Dict[str, Any]] = []
        async for chunk in self._client.send_message_streaming(request):
            chunks.append(chunk.model_dump(mode="json", exclude_none=True))

        # Best-effort id/context extraction from last chunk that contains them
        rid = None
        rcx = None
        for c in reversed(chunks):
            rid = rid or c.get("root", {}).get("result", {}).get("id")
            rcx = rcx or c.get("root", {}).get("result", {}).get("context_id")
            if rid and rcx:
                break

        return {
            "content": {"stream": chunks},
            "task_id": rid,
            "context_id": rcx,
            "is_task_complete": True,
            "require_user_input": False,
        }

    async def iter_message_stream(self, query: str, *, task_id: Optional[str] = None, context_id: Optional[str] = None):
        """Yield streaming chunks in real-time, without buffering the entire stream."""
        await self._ensure_client()
        assert self._client is not None

        payload: Dict[str, Any] = {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": query}],
                "message_id": uuid4().hex,
            }
        }
        if task_id is not None:
            payload["message"]["task_id"] = task_id
        if context_id is not None:
            payload["message"]["context_id"] = context_id

        request = SendStreamingMessageRequest(id=str(uuid4()), params=MessageSendParams(**payload))
        async for chunk in self._client.send_message_streaming(request):
            yield chunk.model_dump(mode="json", exclude_none=True)


# Graph nodes
def prepare_payload(state: A2AState) -> Dict[str, Any]:
    return {
        "query": state["query"],
        "task_id": state.get("a2a_task_id"),
        "context_id": state.get("a2a_context_id"),
    }


def accumulate(state: A2AState, result: Dict[str, Any]) -> Dict[str, Any]:
    content = result.get("content")
    # Store assistant message as stringified JSON to be robust
    state["messages"].append({"role": "assistant", "content": str(content)})
    return {
        "a2a_last_event": result,
        "a2a_task_id": result.get("task_id") or state.get("a2a_task_id"),
        "a2a_context_id": result.get("context_id") or state.get("a2a_context_id"),
        "is_task_complete": bool(result.get("is_task_complete", False)),
        "require_user_input": bool(result.get("require_user_input", False)),
        "messages": state["messages"],
    }


def route(state: A2AState) -> str:
    if state.get("is_task_complete") or state.get("require_user_input"):
        return END
    return "prepare"


def build_a2a_graph(client: A2AClientWrapper):
    graph = StateGraph(A2AState)

    async def _call_a2a(state: A2AState) -> Dict[str, Any]:
        result = await client.send_message(
            state["query"],
            task_id=state.get("a2a_task_id"),
            context_id=state.get("a2a_context_id"),
        )
        return accumulate(state, result)

    # Register nodes
    graph.add_node("prepare", prepare_payload)  # prep node (kept for structure symmetry)
    graph.add_node("call", _call_a2a)

    # Entry and edges
    graph.add_edge(START, "prepare")
    graph.add_edge("prepare", "call")
    graph.add_conditional_edges("call", route, {END: END, "prepare": "prepare"})

    return graph.compile()


def build_a2a_graph_streaming(client: A2AClientWrapper):
    """Placeholder streaming graph; collects full stream then returns normalized state.

    Note: Node-level real-time streaming isn't emitted per-chunk; use CLI --mode stream for live output.
    """
    graph = StateGraph(A2AState)

    async def _call_a2a_stream(state: A2AState) -> Dict[str, Any]:
        result = await client.send_message_streaming(
            state["query"],
            task_id=state.get("a2a_task_id"),
            context_id=state.get("a2a_context_id"),
        )
        return accumulate(state, result)

    graph.add_node("prepare", prepare_payload)
    graph.add_node("call_stream", _call_a2a_stream)

    graph.add_edge(START, "prepare")
    graph.add_edge("prepare", "call_stream")
    graph.add_conditional_edges("call_stream", route, {END: END, "prepare": "prepare"})

    return graph.compile()


async def _run_single(query: str):
    client = A2AClientWrapper()
    graph = build_a2a_graph(client)
    init: A2AState = {
        "messages": [{"role": "user", "content": query}],
        "query": query,
        "a2a_task_id": None,
        "a2a_context_id": None,
        "a2a_last_event": None,
        "is_task_complete": False,
        "require_user_input": False,
    }
    result = await graph.ainvoke(init)
    print(result.get("a2a_last_event"))


async def _run_multi(first: str, second: str):
    client = A2AClientWrapper()
    graph = build_a2a_graph(client)

    init: A2AState = {
        "messages": [{"role": "user", "content": first}],
        "query": first,
        "a2a_task_id": None,
        "a2a_context_id": None,
        "a2a_last_event": None,
        "is_task_complete": False,
        "require_user_input": False,
    }
    r1 = await graph.ainvoke(init)
    print("FIRST:", r1.get("a2a_last_event"))

    init2: A2AState = {
        "messages": r1.get("messages", []),
        "query": second,
        "a2a_task_id": r1.get("a2a_task_id"),
        "a2a_context_id": r1.get("a2a_context_id"),
        "a2a_last_event": None,
        "is_task_complete": False,
        "require_user_input": False,
    }
    r2 = await graph.ainvoke(init2)
    print("SECOND:", r2.get("a2a_last_event"))


def main():
    import argparse

    parser = argparse.ArgumentParser(description="LangGraph A2A Client")
    parser.add_argument("--mode", choices=["single", "multi", "stream"], default="single")
    parser.add_argument("--query", required=True)
    parser.add_argument("--next", dest="next_query", default=None)
    args = parser.parse_args()

    if args.mode == "single":
        asyncio.run(_run_single(args.query))
    elif args.mode == "multi":
        if not args.next_query:
            raise SystemExit("--next is required for multi mode")
        asyncio.run(_run_multi(args.query, args.next_query))
    else:
        async def _run_stream(query: str):
            client = A2AClientWrapper()
            last_chunk = None
            async for chunk in client.iter_message_stream(query):
                last_chunk = chunk
                print(chunk)
            # Print a final normalized line for convenience
            if last_chunk is not None:
                rid = last_chunk.get("root", {}).get("result", {}).get("id")
                rcx = last_chunk.get("root", {}).get("result", {}).get("context_id")
                print({"done": True, "task_id": rid, "context_id": rcx})
        asyncio.run(_run_stream(args.query))


if __name__ == "__main__":
    main()


