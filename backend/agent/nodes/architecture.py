from __future__ import annotations
import asyncio

from agent.state import AgentState
from agent.llm.planning import generate_plan, create_doc_retrieval_checklist, review_and_correct_plan
from agent.llm.coding import write_code

from agent.tools.yellow.yellow_initialiser import YellowInitializerTool
from agent.tools.yellow.yellow_network_workflow_tool import YellowNetworkWorkflowTool
from agent.tools.yellow.yellow_next_multi_party_full_lifecycle import YellowNextMultiPartyFullLifecycle
from agent.tools.yellow.yellow_versioned_integration_tool import YellowVersionedIntegrationTool
from agent.tools.yellow.yellow_tip_tool import YellowTipTool
from agent.tools.yellow.yellow_deposit_tool import YellowDepositTool

from typing import Any
from logging import getLogger

logger = getLogger(__name__)

yellow_initialiser_tool_instance = YellowInitializerTool()
yellow_network_workflow_tool_instance = YellowNetworkWorkflowTool()
yellow_multiparty_tool_instance = YellowNextMultiPartyFullLifecycle()
yellow_versioned_integration_tool_instance = YellowVersionedIntegrationTool()


async def architect_node(state: AgentState) -> AgentState:
    """
    Generate the integration plan and detect Yellow requirements via LLM.
    Sets plan_notes, sdk_version, and all needs_* / needs_*_tools from planner output.
    """
    plan = await generate_plan(
        state.get("prompt", ""), 
        state.get("file_contents", {}),
        state.get("doc_context", "")
    )

    state["plan_notes"] = plan.get("notes_markdown", "")
    state["sdk_version"] = plan.get("yellow_sdk_version", "latest")

    needs_yellow = plan.get("needs_yellow", False)
    needs_simple = plan.get("needs_simple_channel", False)
    needs_multiparty = plan.get("needs_multiparty", False)
    needs_versioned = plan.get("needs_versioned", False)
    needs_tip = plan.get("needs_tip", False)
    needs_deposit = plan.get("needs_deposit", False)

    state["needs_yellow"] = needs_yellow
    state["needs_simple_channel"] = needs_simple
    state["needs_multiparty"] = needs_multiparty
    state["needs_versioned"] = needs_versioned
    state["needs_tip"] = needs_tip
    state["needs_deposit"] = needs_deposit

    state["needs_yellow_tools"] = needs_yellow
    state["needs_simple_channel_tools"] = needs_simple
    state["needs_multiparty_tools"] = needs_multiparty
    state["needs_versioned_tools"] = needs_versioned
    state["needs_tip_tools"] = needs_tip
    state["needs_deposit_tools"] = needs_deposit

    logger.info(
        "Architect: plan + Yellow requirements: yellow=%s, simple=%s, multiparty=%s, versioned=%s, tip=%s, deposit=%s",
        needs_yellow, needs_simple, needs_multiparty, needs_versioned, needs_tip, needs_deposit,
    )
    state["thinking_log"] = state.get("thinking_log", []) + [
        "Architecture plan generated",
        f"Yellow requirements: yellow={needs_yellow}, simple_channel={needs_simple}, multiparty={needs_multiparty}, versioned={needs_versioned}, tip={needs_tip}, deposit={needs_deposit}",
    ]
    return state

async def yellow_init_node(state: AgentState) -> AgentState:
    """
    Initialize Yellow SDK in the target repository.
    """
    needs_yellow = state.get("needs_yellow")
    if not needs_yellow:
        state["yellow_init_status"] = "failed"
        state["thinking_log"] = state.get("thinking_log", []) + ["Yellow init failed: no repo_path"]
        return state

    try:
        await yellow_initialiser_tool_instance.invoke(state)
        return state
    except Exception as e:
        state["yellow_init_status"] = "failed"
        state["thinking_log"] = state.get("thinking_log", []) + [f"Yellow init error: {str(e)}"]
        return state


async def yellow_workflow_node(state: AgentState) -> AgentState:
    """
    Run the Yellow network workflow after initialization.
    """
    repo_path = state.get("repo_path", "./sandbox")
    if not repo_path:
        state["yellow_workflow_status"] = "failed"
        state["thinking_log"] = state.get("thinking_log", []) + ["Yellow workflow failed: no repo_path"]
        # Fallback to non-Yellow flow if we can't run the workflow
        return state

    try:
        workflow_tool = YellowNetworkWorkflowTool()
        await workflow_tool.invoke(state)
        return state
    except Exception as e:
        state["yellow_workflow_status"] = "failed"
        state["thinking_log"] = state.get("thinking_log", []) + [f"Yellow workflow error: {str(e)}"]
        return state


async def yellow_multiparty_node(state: AgentState) -> AgentState:
    needs_multiparty = state.get("needs_multiparty")
    if not needs_multiparty:
        state["yellow_multiparty_status"] = "skipped"
        state["thinking_log"] = state.get("thinking_log", []) + ["Multiparty: no needs_multiparty"]
        return state

    try:
        multiparty_tool = YellowNextMultiPartyFullLifecycle()
        await multiparty_tool.invoke(state)
        return state
    except Exception as e:
        state["yellow_multiparty_status"] = "failed"
        state["thinking_log"] = state.get("thinking_log", []) + [f"Multiparty error: {str(e)}"]
        return state


async def yellow_versioned_node(state: AgentState) -> AgentState:
    needs_versioned = state.get("needs_versioned")
    if not needs_versioned:
            state["yellow_versioned_status"] = "skipped"
            state["thinking_log"] = state.get("thinking_log", []) + ["Versioned integration: no needs_versioned"]
            return state
    try:
        versioned_tool = YellowVersionedIntegrationTool()
        await versioned_tool.invoke(state)
        return state
    except Exception as e:
        state["yellow_versioned_status"] = "failed"
        state["thinking_log"] = state.get("thinking_log", []) + [f"Versioned integration error: {str(e)}"]
        return state


async def yellow_tip_node(state: AgentState) -> AgentState:
    needs_tip = state.get("needs_tip")
    if not needs_tip:
        state["yellow_tip_status"] = "skipped"
        state["thinking_log"] = state.get("thinking_log", []) + ["Yellow tip: no needs_tip"]
        return state

    try:
        tip_tool = YellowTipTool()
        await tip_tool.invoke(state)
        return state
    except Exception as e:
        state["yellow_tip_status"] = "failed"
        state["thinking_log"] = state.get("thinking_log", []) + [f"Yellow tip error: {str(e)}"]
        return state


async def yellow_deposit_node(state: AgentState) -> AgentState:
    needs_deposit = state.get("needs_deposit")
    if not needs_deposit:
        state["yellow_deposit_status"] = "skipped"
        state["thinking_log"] = state.get("thinking_log", []) + ["Yellow deposit: no needs_deposit"]
        return state

    try:
        deposit_tool = YellowDepositTool()
        await deposit_tool.invoke(state)
        return state
    except Exception as e:
        state["yellow_deposit_status"] = "failed"
        state["thinking_log"] = state.get("thinking_log", []) + [f"Yellow deposit error: {str(e)}"]
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
        state.get("doc_context", ""),
        state.get("tool_diffs", [])
    )

    diffs = state.get("diffs", []) or []
    diffs.extend(llm_diffs)

    logger.info(f"Generated {len(llm_diffs)} LLM file changes, merged to {len(diffs)} total changes")

    # Merge tool_diffs and llm_diffs, prefer llm_diffs where conflicts (same file) exist
    tool_diffs = state.get("tool_diffs", []) or []
    llm_paths = {d.get("file", "") for d in llm_diffs}
    # Filter out tool_diffs that conflict with llm_diffs
    merged = [d for d in tool_diffs if d.get("path") not in llm_paths]
    merged.extend(llm_diffs)
    state["diffs"] = merged
    
    logger.info(f"tool diffs: {tool_diffs}")
    logger.info(f"llm diffs: {llm_diffs}")
    logger.info(f"merged diffs: {merged}")
    state["thinking_log"] = state.get("thinking_log", []) + [f"Generated {len(diffs)} file changes"]
    return state

async def plan_review_and_doc_checklist_node(state: AgentState) -> AgentState:
    """
    Stage 1: Review architect's plan and create documentation retrieval checklist.
    Reads: prompt, plan_notes, yellow requirements, tree, doc_context (if any)
    Does NOT read: file_contents (code)
    """
    checklist_result = await create_doc_retrieval_checklist(
        state.get("prompt", ""),
        state.get("plan_notes", ""),
        {
            "needs_yellow": state.get("needs_yellow", False),
            "needs_simple_channel": state.get("needs_simple_channel", False),
            "needs_multiparty": state.get("needs_multiparty", False),
            "needs_versioned": state.get("needs_versioned", False),
            "needs_tip": state.get("needs_tip", False),
            "needs_deposit": state.get("needs_deposit", False),
        },
        state.get("sdk_version", "latest"),
        state.get("tree", {}),
        state.get("doc_context", "")  # Previously retrieved docs if any
    )
    
    state["doc_retrieval_checklist"] = checklist_result.get("checklist", [])
    state["doc_retrieval_reasoning"] = checklist_result.get("reasoning", "")
    state["thinking_log"] = state.get("thinking_log", []) + [
        f"Created documentation retrieval checklist with {len(checklist_result.get('checklist', []))} items"
    ]
    
    return state

async def retrieve_targeted_docs_node(state: AgentState) -> AgentState:
    """
    Stage 2: Retrieve documentation based on the checklist.
    """
    from utils.helper_functions import _search_docs_with_checklist
    
    checklist = state.get("doc_retrieval_checklist", [])
    
    if not checklist:
        state["thinking_log"] = state.get("thinking_log", []) + [
            "No checklist items, skipping targeted doc retrieval"
        ]
        return state
    
    try:
        # Retrieve docs based on checklist
        targeted_docs = await asyncio.to_thread(
            _search_docs_with_checklist,
            checklist
        )
        
        # Merge with existing doc_context if any
        existing_docs = state.get("doc_context", "")
        if existing_docs:
            state["doc_context"] = existing_docs + "\n\n=== Additional Targeted Documentation ===\n\n" + targeted_docs
        else:
            state["doc_context"] = targeted_docs
        
        state["targeted_docs_retrieved"] = True
        state["thinking_log"] = state.get("thinking_log", []) + [
            f"Retrieved targeted documentation for {len(checklist)} checklist items"
        ]
        
        return state
    except Exception as e:
        state["targeted_docs_retrieved"] = True  # Mark as done to avoid loop
        state["thinking_log"] = state.get("thinking_log", []) + [
            f"Error retrieving targeted docs: {e}"
        ]
        return state

async def plan_correction_node(state: AgentState) -> AgentState:
    """
    Stage 3: Review retrieved docs + architect's plan, identify issues, and correct.
    """
    correction_result = await review_and_correct_plan(
        state.get("prompt", ""),
        state.get("plan_notes", ""),
        {
            "needs_yellow": state.get("needs_yellow", False),
            "needs_simple_channel": state.get("needs_simple_channel", False),
            "needs_multiparty": state.get("needs_multiparty", False),
            "needs_versioned": state.get("needs_versioned", False),
            "needs_tip": state.get("needs_tip", False),
            "needs_deposit": state.get("needs_deposit", False),
        },
        state.get("sdk_version", "latest"),
        state.get("doc_context", ""),  # All retrieved docs (initial + targeted)
        state.get("tree", {})
    )
    
    # Update plan if corrections were made
    if correction_result.get("plan_corrected", False):
        state["plan_notes"] = correction_result.get("corrected_plan", state.get("plan_notes", ""))
        state["sdk_version"] = correction_result.get("corrected_sdk_version", state.get("sdk_version", "latest"))
        
        # Update yellow requirements if corrected
        corrected_requirements = correction_result.get("corrected_requirements", {})
        if corrected_requirements:
            state["needs_yellow"] = corrected_requirements.get("needs_yellow", state.get("needs_yellow", False))
            state["needs_simple_channel"] = corrected_requirements.get("needs_simple_channel", state.get("needs_simple_channel", False))
            state["needs_multiparty"] = corrected_requirements.get("needs_multiparty", state.get("needs_multiparty", False))
            state["needs_versioned"] = corrected_requirements.get("needs_versioned", state.get("needs_versioned", False))
            state["needs_tip"] = corrected_requirements.get("needs_tip", state.get("needs_tip", False))
            state["needs_deposit"] = corrected_requirements.get("needs_deposit", state.get("needs_deposit", False))
            
            # Update tool flags
            state["needs_yellow_tools"] = state["needs_yellow"]
            state["needs_simple_channel_tools"] = state["needs_simple_channel"]
            state["needs_multiparty_tools"] = state["needs_multiparty"]
            state["needs_versioned_tools"] = state["needs_versioned"]
            state["needs_tip_tools"] = state["needs_tip"]
            state["needs_deposit_tools"] = state["needs_deposit"]
    
    state["plan_corrections"] = correction_result.get("corrections", [])
    state["plan_correction_reasoning"] = correction_result.get("reasoning", "")
    state["thinking_log"] = state.get("thinking_log", []) + [
        f"Plan review completed: {len(correction_result.get('corrections', []))} corrections identified",
        "Plan corrected" if correction_result.get("plan_corrected", False) else "Plan validated"
    ]
    
    return state
     