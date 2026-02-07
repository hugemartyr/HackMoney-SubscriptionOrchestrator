from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class Diff(TypedDict):
    file: str
    oldCode: str
    newCode: str


class AgentState(TypedDict, total=False):
    # Existing fields
    prompt: str
    tree: Dict[str, Any]
    repo_path: str
    files_to_read: List[str]
    file_contents: Dict[str, str]
    plan_notes: str
    sdk_version: str
    diffs: List[Diff]
    tool_diffs: List[Diff]
    errors: List[str]
    
    # New fields for enhanced flow
    session_memory: List[str]  # Track attempted fixes and research
    context_ready: bool  # Whether we have enough code context
    context_loop_count: int # Count loops to prevent infinite cycles
    missing_info: List[str] # Specific files or info requested by context check
    docs_retrieved: bool  # Whether docs have been fetched
    imports_analyzed: bool  # Whether imports are understood
    build_command: str  # Command to run (e.g., "npm run build")
    build_output: str  # Combined stdout/stderr from build
    build_success: Optional[bool]  # Build result (None = not run yet)
    error_count: int  # Track retry attempts
    escalation_needed: bool  # Flag for human intervention
    needs_tip: bool  # Whether tipping functionality is needed
    research_queries: List[str]  # Track research performed
    analyzed_imports: Dict[str, Any]  # Import analysis results
    doc_context: str  # Retrieved documentation context
    
    # HITL & Thinking fields
    awaiting_approval: bool  # Graph is paused waiting for approval
    approved_files: List[str]  # Files that have been approved
    pending_approval_files: List[str]  # Files waiting for approval
    thinking_log: List[str]  # Agent's reasoning at each step
    final_summary: str  # Final explanation (Cursor-style)
    terminal_output: List[str]  # Terminal output lines for streaming
    error_analysis: Dict[str, Any]  # Error analysis results from error_analysis_node
