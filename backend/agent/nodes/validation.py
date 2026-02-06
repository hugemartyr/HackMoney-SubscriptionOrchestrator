from __future__ import annotations
from agent.state import AgentState
from agent.tools.command_executor import execute_command

async def await_approval_node(state: AgentState) -> AgentState:
    """
    Pause execution and wait for user approval.
    """
    diffs = state.get("diffs", [])
    files = [diff.get("file", "") for diff in diffs if diff.get("file")]
    
    state["awaiting_approval"] = True
    state["pending_approval_files"] = files
    state["thinking_log"] = state.get("thinking_log", []) + [f"Waiting for approval on {len(files)} files..."]
    return state

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
