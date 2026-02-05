from agent.state import AgentState
from agent.llm import generate_plan

async def plan_node(state: AgentState) -> AgentState:
    prompt = state.get("prompt", "")
    files = state.get("file_contents", {}) or {}

    llm_out = await generate_plan(prompt, files)
    plan_notes = llm_out["notes_markdown"].rstrip() + "\n"
    sdk_version = llm_out["yellow_sdk_version"].strip() or "latest"

    return {"plan_notes": plan_notes, "sdk_version": sdk_version}
