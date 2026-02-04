from __future__ import annotations

from typing import Any, AsyncGenerator

from utils.schema import AgentRequest, AgentResponse
from utils.intent import detect_intent
from utils.tools import run_tool
from services.langgraph_agent import build_graph
from services.langgraph_stream import stream_response


async def handle_api_call(payload: AgentRequest) -> AgentResponse:
    if not payload.prompt.strip():
        raise ValueError("Prompt is required.")

    intent = payload.intent or detect_intent(payload.prompt)

    graph = build_graph()
    result = graph.invoke(
        {
            "prompt": payload.prompt,
            "intent": intent,
            "tool_args": payload.tool_args or {},
            "tool_results": [],
            "response": "",
        }
    )
    response_text = result.get("response", "")
    tool_results = result.get("tool_results", [])

    return AgentResponse(
        request_id=payload.request_id,
        response=response_text,
        tools=tool_results,
    )


async def stream_api_call(payload: AgentRequest) -> AsyncGenerator[str, None]:
    if not payload.prompt.strip():
        raise ValueError("Prompt is required.")

    tool_results: list[dict[str, Any]] = []
    intent = payload.intent or detect_intent(payload.prompt)
    if intent:
        tool_results.append(run_tool(intent, payload.tool_args or {}))

    async for chunk in stream_response(payload.prompt, tool_results):
        yield chunk
