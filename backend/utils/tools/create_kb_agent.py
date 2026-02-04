from __future__ import annotations

from typing import Any


def create_kb_agent(payload: dict[str, Any]) -> dict[str, Any]:
    knowledge_base = payload.get("knowledge_base", "default-kb")
    agent_name = payload.get("agent_name", "KB Agent")
    return {
        "tool": "create_kb_agent",
        "status": "simulated",
        "agent_name": agent_name,
        "knowledge_base": knowledge_base,
        "note": "Demo tool execution only. Replace with real KB agent creation.",
    }
