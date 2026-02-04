from __future__ import annotations

from typing import Any, Callable

from utils.tools.yellow_payment import yellow_simple_payment
from utils.tools.create_kb_agent import create_kb_agent

ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]

TOOL_REGISTRY: dict[str, ToolHandler] = {
    "yellow_payment": yellow_simple_payment,
    "create_kb_agent": create_kb_agent,
}


def run_tool(intent: str, payload: dict[str, Any]) -> dict[str, Any]:
    if intent not in TOOL_REGISTRY:
        return {
            "tool": intent,
            "status": "unsupported",
            "note": "No tool registered for this intent.",
        }
    return TOOL_REGISTRY[intent](payload)
