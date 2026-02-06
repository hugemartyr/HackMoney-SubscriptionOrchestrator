from __future__ import annotations

from agent.state import AgentState
from agent.llm.planning import generate_plan
from agent.llm.coding import write_code
from agent.tools.yellow import (
    YellowInitializerTool,
    YellowNetworkWorkflowTool,
    YellowNextMultiPartyFullLifecycle,
    YellowVersionedIntegrationTool,
    detect_yellow_requirement,
    detect_multiparty_requirement,
    detect_versioned_integration_requirement,
)
from typing import Any
from logging import getLogger

logger = getLogger(__name__)

def _merge_diffs(tool_diffs: list[dict[str, str]], llm_diffs: list[dict[str, str]]) -> list[dict[str, str]]:
    tool_files = {d.get("file") for d in tool_diffs if d.get("file")}
    merged = [d for d in tool_diffs if d.get("file")]
    merged.extend([d for d in llm_diffs if d.get("file") not in tool_files])
    return merged


def _append_tool_diffs(state: AgentState, new_diffs: list[dict]) -> None:
    if not new_diffs:
        return
    tool_diffs = state.get("tool_diffs", []) or []
    tool_diffs.extend(new_diffs)
    state["tool_diffs"] = tool_diffs


async def architect_node(state: AgentState) -> AgentState:
    """
    Generate the integration plan.
    """
    plan = await generate_plan(state.get("prompt", ""), state.get("file_contents", {}))

    state["plan_notes"] = plan.get("notes_markdown", "")
    state["sdk_version"] = plan.get("yellow_sdk_version", "latest")
    state["thinking_log"] = state.get("thinking_log", []) + ["Architecture plan generated"]
    return state


async def parse_yellow_node(state: AgentState) -> AgentState:
    """
    Parse prompt to determine which Yellow workflows are required.
    Sets flags on state: needs_yellow, needs_simple_channel, needs_multiparty, needs_versioned
    """
    prompt = state.get("prompt", "") or ""

    needs_yellow = state.get("needs_yellow")
    if needs_yellow is None:
        needs_yellow = detect_yellow_requirement(prompt)

    needs_simple = state.get("needs_simple_channel")
    if needs_simple is None:
        pl = prompt.lower()
        needs_simple = any(k in pl for k in ("channel", "nitrolite", "create channel", "open channel", "stateless", "simple channel"))

    needs_multiparty = state.get("needs_multiparty")
    if needs_multiparty is None:
        needs_multiparty = detect_multiparty_requirement(prompt)

    needs_versioned = state.get("needs_versioned")
    if needs_versioned is None:
        needs_versioned = detect_versioned_integration_requirement(prompt) or needs_multiparty

    state.update({
        "needs_yellow": needs_yellow,
        "needs_simple_channel": needs_simple,
        "needs_multiparty": needs_multiparty,
        "needs_versioned": needs_versioned,
        "prefer_yellow_tools": needs_yellow,
    })

    state["thinking_log"] = state.get("thinking_log", []) + [
        f"Parsed Yellow requirements: yellow={needs_yellow}, simple={needs_simple}, multiparty={needs_multiparty}, versioned={needs_versioned}"
    ]

    return state


async def write_code_node(state: AgentState) -> AgentState:
    """
    Generate code changes.
    """
    llm_diffs = await write_code(
        state.get("prompt", ""),
        state.get("file_contents", {}),
        state.get("plan_notes", ""),
        state.get("sdk_version", "latest"),
        state.get("doc_context", "")
    )

    tool_diffs = state.get("tool_diffs", []) or []
    diffs = _merge_diffs(tool_diffs, llm_diffs)

    logger.info(f"Generated {len(llm_diffs)} LLM file changes, merged to {len(diffs)} total changes")

    state["diffs"] = diffs
    state["thinking_log"] = state.get("thinking_log", []) + [f"Generated {len(diffs)} file changes"]
    return state


async def yellow_init_node(state: AgentState) -> AgentState:
    """
    Initialize Yellow SDK in the target repository.
    """
    repo_path = state.get("repo_path", "/home/user/app")
    if not repo_path:
        state["yellow_init_status"] = "failed"
        state["thinking_log"] = state.get("thinking_log", []) + ["Yellow init failed: no repo_path"]

        return state

    try:
        initializer = YellowInitializerTool()
        result = await initializer.invoke(state)

        

        state.update(result)
        _append_tool_diffs(state, result.get("yellow_tool_diffs", []))
        return state

    except Exception as e:
        state["yellow_init_status"] = "failed"
        state["thinking_log"] = state.get("thinking_log", []) + [f"Yellow init error: {str(e)}"]
        return state


async def yellow_workflow_node(state: AgentState) -> AgentState:
    """
    Run the Yellow network workflow after initialization.
    """
    repo_path = state.get("repo_path", "/home/user/app")
    if not repo_path:
        state["yellow_workflow_status"] = "failed"
        state["thinking_log"] = state.get("thinking_log", []) + ["Yellow workflow failed: no repo_path"]
        # Fallback to non-Yellow flow if we can't run the workflow
        return state

    try:
        workflow_tool = YellowNetworkWorkflowTool()
        result = await workflow_tool.invoke(state)

        state.update(result)
        _append_tool_diffs(state, result.get("yellow_tool_diffs", []))
        return state

    except Exception as e:
        state["yellow_workflow_status"] = "failed"
        state["thinking_log"] = state.get("thinking_log", []) + [f"Yellow workflow error: {str(e)}"]
        return state


async def yellow_multiparty_node(state: AgentState) -> AgentState:
    repo_path = state.get("repo_path", "/home/user/app")
    if not repo_path:
        state["yellow_multiparty_status"] = "skipped"
        state["thinking_log"] = state.get("thinking_log", []) + ["Multiparty: no repo_path provided"]
        return state

    try:
        multiparty_tool = YellowNextMultiPartyFullLifecycle()
        result = await multiparty_tool.invoke(state)
        state.update(result)
        _append_tool_diffs(state, result.get("yellow_tool_diffs", []))
        return state

    except Exception as e:
        state["yellow_multiparty_status"] = "failed"
        state["thinking_log"] = state.get("thinking_log", []) + [f"Multiparty error: {str(e)}"]
        return state


async def yellow_versioned_node(state: AgentState) -> AgentState:
    repo_path = state.get("repo_path", "/home/user/app")
    if not repo_path:
        state["yellow_versioned_status"] = "skipped"
        state["thinking_log"] = state.get("thinking_log", []) + ["Versioned integration: no repo_path provided"]
        return state

    try:
        versioned_tool = YellowVersionedIntegrationTool()
        result = await versioned_tool.invoke(state)
        state.update(result)
        _append_tool_diffs(state, result.get("yellow_tool_diffs", []))
        if state.get("needs_yellow"):
            tool_diffs = state.get("tool_diffs", []) or []
            state["diffs"] = _merge_diffs(tool_diffs, state.get("diffs", []) or [])
        return state

    except Exception as e:
        state["yellow_versioned_status"] = "failed"
        state["thinking_log"] = state.get("thinking_log", []) + [f"Versioned integration error: {str(e)}"]
        return state
