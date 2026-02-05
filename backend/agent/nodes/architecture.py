from __future__ import annotations
from agent.state import AgentState
from agent.llm.planning import generate_plan, generate_architecture
from agent.llm.coding import write_code

async def architect_node(state: AgentState) -> AgentState:
    """
    Generate the integration plan.
    """
    # Reuse generate_plan for now, can upgrade to generate_architecture later
    plan = await generate_plan(state.get("prompt", ""), state.get("file_contents", {}))
    
    return {
        "plan_notes": plan.get("notes_markdown", ""),
        "sdk_version": plan.get("yellow_sdk_version", "latest"),
        "thinking_log": state.get("thinking_log", []) + ["Architecture plan generated"]
    }

async def write_code_node(state: AgentState) -> AgentState:
    """
    Generate code changes.
    """
    diffs = await write_code(
        state.get("prompt", ""),
        state.get("file_contents", {}),
        state.get("plan_notes", ""),
        state.get("sdk_version", "latest"),
        state.get("doc_context", "")
    )
    
    return {
        "diffs": diffs,
        "thinking_log": state.get("thinking_log", []) + [f"Generated {len(diffs)} file changes"]
    }
