from __future__ import annotations

from typing import Literal

from langgraph.checkpoint.memory import InMemorySaver
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


def start_agent_node(state: AgentState) -> AgentState:
    """
    Start the agent.
    """
    return AgentState(
        prompt = state.get("prompt") or "",
        tree = state.get("tree") or {},
        files_to_read = state.get("files_to_read") or [],
        file_contents = state.get("file_contents") or {},
        plan_notes = state.get("plan_notes") or "",
        sdk_version = state.get("sdk_version") or "",
        diffs = state.get("diffs") or [],
        errors = state.get("errors") or [],
        build_command = state.get("build_command") or "",
        build_output = state.get("build_output") or "",
        build_success = state.get("build_success") or None,
        error_count = state.get("error_count") or 0,
        awaiting_approval = False,
        approved_files = state.get("approved_files") or [],
        pending_approval_files = state.get("pending_approval_files") or [],
        context_loop_count = state.get("context_loop_count") or 0,
        missing_info = state.get("missing_info") or [],
        docs_retrieved = state.get("docs_retrieved") or False,
        imports_analyzed = state.get("imports_analyzed") or False,
        analyzed_imports = state.get("analyzed_imports") or {},
        doc_context = state.get("doc_context") or "",
        thinking_log = state.get("thinking_log") or [],
        final_summary = state.get("final_summary") or "",
        terminal_output = state.get("terminal_output") or [],
        error_analysis = state.get("error_analysis") or {}
    )

# Routing functions
def route_context_decision(state: AgentState) -> Literal["read_code", "retrieve_docs", "research", "ready"]:
    """
    Decide the next step in the context-gathering loop.

    Priority (while context_ready is False):
    1. If we've looped too many times → stop looping and move to "ready".
    2. If we have explicit files_to_read or almost no code loaded → "read_code".
    3. If missing_info points at files/paths → "read_code".
    4. If we still haven't pulled docs and missing_info looks doc-ish → "retrieve_docs".
    5. Otherwise → "research".
    """
    loop_count = state.get("context_loop_count", 0)

    # Hard safety: don't let the loop run forever.
    if loop_count > 4:
        return "ready"  # Force proceed to architect

    # Fast path: if context_check_node already said we're ready, skip the loop.
    if state.get("context_ready"):
        return "ready"

    # At this point, context_ready is False: we need more information.

    files_to_read = state.get("files_to_read") or []
    file_contents = state.get("file_contents") or {}
    missing = state.get("missing_info") or []
    docs_retrieved = state.get("docs_retrieved", False)

    # 1) If the LLM explicitly told us which files to read, honor that first.
    if files_to_read:
        return "read_code"

    # 2) If we have essentially no code loaded yet, prefer reading code.
    if not file_contents:
        return "read_code"

    # 3) Classify missing_info into "file-like" vs "doc-like" vs "other".
    file_like: list[str] = []
    doc_like: list[str] = []

    for item in missing:
        text = (item or "").lower()
        # A path or filename
        if "." in item or "/" in item:
            file_like.append(item)
            continue
        # Mentions docs / guides / api etc.
        if any(keyword in text for keyword in ["doc", "readme", "guide", "api", "reference", "spec"]):
            doc_like.append(item)

    # If there are unresolved file-like gaps, try reading code again.
    if file_like:
        return "read_code"

    # 4) If docs haven't been retrieved yet and we have doc-like gaps, fetch docs.
    if not docs_retrieved and doc_like:
        return "retrieve_docs"

    # 5) If we still haven't retrieved docs at all, do one docs pass before generic research.
    if not docs_retrieved:
        return "retrieve_docs"

    # 6) Fallback: we have some code and docs, but context_ready is still False → do targeted research.
    return "research"

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
workflow.add_node("start_agent", start_agent_node)
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
workflow.set_entry_point("start_agent")

workflow.add_edge("start_agent", "context_check")

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

# HITL: await_approval uses interrupt() to pause; resume continues to coding
workflow.add_edge("await_approval", "coding")

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

app_graph = workflow.compile(checkpointer=InMemorySaver())
