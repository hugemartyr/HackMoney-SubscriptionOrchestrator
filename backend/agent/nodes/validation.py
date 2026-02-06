from __future__ import annotations
from agent.state import AgentState
from agent.tools.command_executor import execute_command
from langgraph.types import interrupt


async def await_approval_node(state: AgentState) -> AgentState:
    """
    Pause execution and wait for user approval using interrupt().
    On resume, interrupt() returns the value passed to Command(resume=...).
    """
    diffs = state.get("diffs", [])
    files = [d.get("file", "") for d in diffs if d.get("file")]

    # No diffs: skip interrupt, proceed to coding
    if not files:
        return {
            "awaiting_approval": False,
            "approved_files": [],
            "pending_approval_files": [],
            "thinking_log": state.get("thinking_log", []) + [
                "No files to approve, proceeding...",
                "Yellow tool workflow preferred; skipping generic codegen approvals."
            ] if state.get("needs_yellow") else state.get("thinking_log", []) + ["No files to approve, proceeding..."],
        }

    # interrupt() PAUSES the graph; on resume it returns the Command(resume=...) value
    result = interrupt({"files": files, "message": "Review and approve changes"})

    approved = result.get("approved", False) if isinstance(result, dict) else False
    approved_files = result.get("approved_files", []) if isinstance(result, dict) else []

    return {
        "awaiting_approval": False,
        "approved_files": approved_files,
        "pending_approval_files": [],
        "thinking_log": state.get("thinking_log", []) + [
            f"User {'approved' if approved else 'rejected'} {len(files)} files"
        ],
    }

async def coding_node(state: AgentState) -> AgentState:
    """
    Verify code syntax/logic before build.
    """
    # Placeholder for syntax verification
    state["awaiting_approval"] = False # Clear flag once we proceed
    state["thinking_log"] = state.get("thinking_log", []) + ["Verifying code..."]
    return state

async def build_node(state: AgentState) -> AgentState:
    """
    Run build/test commands.
    """
    # 1. Determine build command (simple heuristic for now)
    files = state.get("file_contents", {})
    build_cmd = "echo 'No build command detected'"
    
    if "package.json" in files:
        build_cmd = "npm install && npm run build"
    elif "requirements.txt" in files:
        build_cmd = "pip install -r requirements.txt && python main.py --dry-run" # Example
    
    # 2. Execute command
    output_lines = []
    terminal_output = []  # For incremental streaming
    success = False
    
    try:
        # Stream output
        async for event in execute_command(build_cmd, timeout=300):
            if event["type"] == "output":
                line = event["data"]
                output_lines.append(line)
                terminal_output.append(line)  # Store for runner
            elif event["type"] == "exit":
                success = (event["code"] == 0)
            elif event["type"] == "error":
                error_msg = f"Error: {event['message']}"
                output_lines.append(error_msg)
                terminal_output.append(error_msg)
                success = False
    except Exception as e:
        error_msg = f"Execution failed: {e}"
        output_lines.append(error_msg)
        terminal_output.append(error_msg)
        success = False
    state["build_success"] = success
    state["build_output"] = "".join(output_lines)
    state["build_command"] = build_cmd
    state["terminal_output"] = terminal_output
    state["thinking_log"] = state.get("thinking_log", []) + [f"Build finished: {'Success' if success else 'Failed'}"]
    return state
