from __future__ import annotations
from agent.state import AgentState
from agent.llm.summary import generate_summary

async def summary_node(state: AgentState) -> AgentState:
    """
    Generate final summary.
    """
    summary = await generate_summary(
        state.get("thinking_log", []),
        state.get("diffs", []),
        state.get("build_success", False),
        state.get("error_count", 0)
    )
    return {
        "final_summary": summary,
        "thinking_log": state.get("thinking_log", []) + ["Summary generated"]
    }
