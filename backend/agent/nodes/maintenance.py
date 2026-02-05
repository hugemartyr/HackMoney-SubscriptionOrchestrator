from __future__ import annotations
from agent.state import AgentState
from agent.llm.analysis import analyze_errors
from agent.llm.error_handling import escalate_issue

async def error_analysis_node(state: AgentState) -> AgentState:
    """
    Analyze build errors.
    """
    analysis = await analyze_errors(state.get("build_output", ""))
    return {
        "error_analysis": analysis,  # Store for fix_plan_node
        "thinking_log": state.get("thinking_log", []) + ["Analyzed build errors"]
    }

async def memory_check_node(state: AgentState) -> AgentState:
    """
    Check retry count to avoid loops.
    """
    count = state.get("error_count", 0) + 1
    return {
        "error_count": count,
        "thinking_log": state.get("thinking_log", []) + [f"Error retry attempt {count}"]
    }

async def fix_plan_node(state: AgentState) -> AgentState:
    """
    Generate a fix plan.
    """
    from agent.llm.error_handling import generate_fix_plan
    
    error_analysis = state.get("error_analysis", {})
    if not error_analysis:
        from agent.llm.analysis import analyze_errors
        error_analysis = await analyze_errors(state.get("build_output", ""))
    
    diffs = await generate_fix_plan(
        error_analysis,
        state.get("file_contents", {}),
        state.get("prompt", ""),
        state.get("doc_context", "")
    )
    
    return {
        "diffs": diffs,
        "error_analysis": error_analysis,
        "thinking_log": state.get("thinking_log", []) + [f"Generated fix plan with {len(diffs)} file changes"]
    }

async def escalation_node(state: AgentState) -> AgentState:
    """
    Escalate to human.
    """
    from agent.llm.error_handling import escalate_issue
    
    error_context = state.get("build_output", "")
    attempted_fixes = state.get("session_memory", [])
    
    msg = await escalate_issue(error_context, attempted_fixes, error_context)
    
    return {
        "escalation_needed": True,
        "final_summary": msg,
        "thinking_log": state.get("thinking_log", []) + ["Escalated to human review"]
    }
