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
    needs_deposit: bool  # Whether deposit functionality is needed
    research_queries: List[str]  # Track research performed
    analyzed_imports: Dict[str, Any]  # Import analysis results
    doc_context: str  # Retrieved documentation context
    
    # Yellow routing flags (set by architect_node from LLM)
    needs_yellow: bool
    needs_simple_channel: bool
    needs_multiparty: bool
    needs_versioned: bool
    prefer_yellow_tools: bool
    needs_yellow_tools: bool
    needs_simple_channel_tools: bool
    needs_multiparty_tools: bool
    needs_versioned_tools: bool
    needs_tip_tools: bool
    needs_deposit_tools: bool
    # Yellow tool status (set by tools/nodes)
    yellow_init_status: str  # success | failed | skipped
    yellow_workflow_status: str
    yellow_versioned_status: str
    yellow_multiparty_status: str
    yellow_tip_status: str
    yellow_deposit_status: str

    yellow_initialized: bool  # Whether the Yellow SDK has been initialized
    yellow_framework: str  # The framework detected for the Yellow SDK
    yellow_version: str  # The version of the Yellow SDK
    yellow_dependencies: List[str]  # The dependencies of the Yellow SDK
    yellow_devDependencies: List[str]  # The devDependencies of the Yellow SDK
    yellow_scripts: Dict[str, str]  # The scripts of the Yellow SDK
    yellow_engines: Dict[str, str]  # The engines of the Yellow SDK
    yellow_author: str  # The author of the Yellow SDK
    yellow_license: str  # The license of the Yellow SDK
    yellow_repository: str  # The repository of the Yellow SDK
    yellow_bugs: str  # The bugs of the Yellow SDK

    # HITL & Thinking fields
    awaiting_approval: bool  # Graph is paused waiting for approval
    approved_files: List[str]  # Files that have been approved
    pending_approval_files: List[str]  # Files waiting for approval
    resume_from_approval: bool  # When True, entry router goes to coding (continue after user approve/discard)
    thinking_log: List[str]  # Agent's reasoning at each step
    final_summary: str  # Final explanation (Cursor-style)
    terminal_output: List[str]  # Terminal output lines for streaming
    error_analysis: Dict[str, Any]  # Error analysis results from error_analysis_node
    
    # Post-architect review fields
    doc_retrieval_checklist: List[str]  # Checklist of docs to retrieve
    doc_retrieval_reasoning: str  # Reasoning for checklist
    targeted_docs_retrieved: bool  # Whether targeted docs were retrieved
    plan_corrections: List[str]  # List of corrections made
    plan_correction_reasoning: str  # Reasoning for corrections