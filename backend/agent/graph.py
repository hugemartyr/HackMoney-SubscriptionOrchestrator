from __future__ import annotations

from typing import Literal

from langgraph.graph import END, StateGraph

from agent.state import AgentState

# Import nodes from the new package
from agent.nodes import (
    context_check_node,
    read_code_node,
    analyze_imports_node,
    retrieve_docs_node,
    research_node,
    update_memory_node,
    architect_node,
    write_code_node,
    await_approval_node,
    coding_node,
    build_node,
    error_analysis_node,
    memory_check_node,
    fix_plan_node,
    escalation_node,
    summary_node
)

# Routing functions
def route_context_decision(state: AgentState) -> Literal["read_code", "retrieve_docs", "research", "ready"]:
    # Safety: Break loop if count > 4
    if state.get("context_loop_count", 0) > 4:
        return "ready" # Force proceed to architect

    if not state.get("context_ready"):
        # Check files_to_read FIRST
        if state.get("files_to_read"):
            return "read_code"

        status = "ready" # Default fallback
        # Check explicit status from analysis if available
        # Note: logic relies on flags set by context_check_node logic. 
        # But context_check_node returns 'context_ready' boolean.
        
        # Re-eval based on priority:
        # 1. If no files, read code.
        if not state.get("file_contents"):
            return "read_code"
            
        # 2. If flags indicate missing info (managed by node logic setting 'context_ready')
        # If context_ready is False, we check other flags or defaults.
        # But wait, context_check_node sets context_ready=False if status != 'ready'.
        # We need to know WHICH path to take.
        # The state doesn't store 'status' string directly, just flags.
        # We can infer from missing_info or flags.
        
        # IMPROVEMENT: The previous logic relied on analysis.py return value mapping to next step.
        # But here we only have state.
        # Let's check 'missing_info'.
        missing = state.get("missing_info", [])
        
        # Heuristic:
        # If any missing info looks like file path -> read_code
        if any(("." in m or "/" in m) for m in missing):
             return "read_code"
        
        # If docs not retrieved -> retrieve_docs
        if not state.get("docs_retrieved"):
            return "retrieve_docs"
            
        # Else -> research
        return "research"
        
    return "ready"

def check_approval_status(state: AgentState) -> Literal["approved", "pending"]:
    if state.get("awaiting_approval"):
        return "pending"
    return "approved"

def check_build_result(state: AgentState) -> Literal["success", "failure"]:
    if state.get("build_success"):
        return "success"
    return "failure"

def check_memory(state: AgentState) -> Literal["retry", "escalate"]:
    if state.get("error_count", 0) > 3:
        return "escalate"
    return "retry"


# Build the graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("context_check", context_check_node)
workflow.add_node("read_code", read_code_node)
workflow.add_node("analyze_imports", analyze_imports_node)
workflow.add_node("retrieve_docs", retrieve_docs_node)
workflow.add_node("research", research_node)
workflow.add_node("update_memory", update_memory_node)
workflow.add_node("architect", architect_node)
workflow.add_node("write_code", write_code_node)
workflow.add_node("await_approval", await_approval_node)
workflow.add_node("coding", coding_node)
workflow.add_node("build", build_node)
workflow.add_node("error_analysis", error_analysis_node)
workflow.add_node("memory_check", memory_check_node)
workflow.add_node("fix_plan", fix_plan_node)
workflow.add_node("escalation", escalation_node)
workflow.add_node("summary", summary_node)

# Set entry point
workflow.set_entry_point("context_check")

# Conditional edges from context_check
workflow.add_conditional_edges(
    "context_check",
    route_context_decision,
    {
        "read_code": "read_code",
        "retrieve_docs": "retrieve_docs",
        "research": "research",
        "ready": "architect"
    }
)

# Research loops
workflow.add_edge("read_code", "analyze_imports")
workflow.add_edge("analyze_imports", "update_memory")
workflow.add_edge("retrieve_docs", "update_memory")
workflow.add_edge("research", "update_memory")
workflow.add_edge("update_memory", "context_check")

# Main flow
workflow.add_edge("architect", "write_code")
workflow.add_edge("write_code", "await_approval")

# HITL approval loop
workflow.add_conditional_edges(
    "await_approval",
    check_approval_status,
    {
        "approved": "coding",
        "pending": "await_approval"
    }
)

workflow.add_edge("coding", "build")

# Build result routing
workflow.add_conditional_edges(
    "build",
    check_build_result,
    {
        "success": "summary",
        "failure": "error_analysis"
    }
)

# Error handling loop
workflow.add_edge("error_analysis", "memory_check")
workflow.add_conditional_edges(
    "memory_check",
    check_memory,
    {
        "retry": "fix_plan",
        "escalate": "escalation"
    }
)

workflow.add_edge("fix_plan", "coding")  # Loop back to verify fix
workflow.add_edge("escalation", "summary")
workflow.add_edge("summary", END)

app_graph = workflow.compile()
