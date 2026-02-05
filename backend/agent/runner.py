from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict

from agent.graph import app_graph
from services.pending_diff_service import set_pending_diff, get_pending_diff, list_pending_diffs


async def run_agent(runId: str, prompt: str) -> AsyncIterator[Dict[str, Any]]:
    """
    Minimal runner that emits frontend-compatible SSE events.
    Backed by LangGraph workflow.
    """
    yield {"type": "run_started", "runId": runId, "prompt": prompt}
    yield {"type": "thought", "runId": runId, "content": "Starting Yellow agent..."}

    # Stream node lifecycle + state deltas from LangGraph.
    # We translate those into the SSEEvent schema the frontend understands.
    proposed_files: list[str] = []
    graph_completed = False

    try:
        # Pass stream_mode="updates" to get state updates
        try:
            # Initial file tree loading
            from services.sandbox_fs_service import get_file_tree
            tree = await get_file_tree()
            yield {"type": "file_tree", "runId": runId, "tree": tree}
        except Exception:
            tree = None  # Set to None if FS not ready

        # Pass tree in initial state
        initial_state = {"prompt": prompt}
        if tree:
            initial_state["tree"] = tree
            
        async for ev in app_graph.astream_events(initial_state, version="v2"):
            name = ev.get("name")
            event_type = ev.get("event")
            data = ev.get("data") or {}

            # Check for graph completion
            if event_type == "on_chain_end" and name == "LangGraph":
                graph_completed = True

            # Node lifecycle => tool events
            if event_type == "on_chain_start" and name not in (None, "LangGraph"):
                yield {"type": "tool_start", "runId": runId, "name": name}
                
                # Context-aware thoughts
                if name == "context_check":
                    yield {"type": "thought", "runId": runId, "content": "Analyzing context and requirements..."}
                elif name == "read_code":
                    yield {"type": "thought", "runId": runId, "content": "Reading codebase files..."}
                elif name == "analyze_imports":
                    yield {"type": "thought", "runId": runId, "content": "Analyzing project dependencies..."}
                elif name == "retrieve_docs":
                    yield {"type": "thought", "runId": runId, "content": "Searching documentation..."}
                elif name == "research":
                    yield {"type": "thought", "runId": runId, "content": "Researching implementation details..."}
                elif name == "architect":
                    yield {"type": "thought", "runId": runId, "content": "Designing integration plan..."}
                elif name == "write_code":
                    yield {"type": "thought", "runId": runId, "content": "Generating code changes..."}
                elif name == "coding":
                    yield {"type": "thought", "runId": runId, "content": "Verifying code syntax and logic..."}
                elif name == "build":
                    yield {"type": "thought", "runId": runId, "content": "Running build and tests..."}
                elif name == "error_analysis":
                    yield {"type": "thought", "runId": runId, "content": "Analyzing build errors..."}
                elif name == "fix_plan":
                    yield {"type": "thought", "runId": runId, "content": "Planning fixes for errors..."}
                elif name == "summary":
                    yield {"type": "thought", "runId": runId, "content": "Generating final summary..."}

            if event_type == "on_chain_end" and name not in (None, "LangGraph"):
                yield {"type": "tool_end", "runId": runId, "name": name, "status": "success"}

            # Handle custom events emitted by nodes (e.g. build output, awaiting approval)
            if event_type == "on_custom_event":
                event_name = ev.get("name")
                event_data = data
                
                if event_name == "terminal_output":
                    # Stream terminal output
                    yield {"type": "terminal", "runId": runId, "line": event_data.get("data", "")}
                
                elif event_name == "build_status":
                    # Stream build lifecycle
                    yield {
                        "type": "build", 
                        "runId": runId, 
                        "status": event_data.get("status"),
                        "data": event_data.get("data")
                    }
                
                elif event_name == "awaiting_approval":
                    # HITL pause
                    files = event_data.get("files", [])
                    yield {"type": "awaiting_user_review", "runId": runId, "files": files}
                    yield {"type": "thought", "runId": runId, "content": "Waiting for user approval..."}

            # Streamed state chunks
            if event_type == "on_chain_stream" and name not in (None, "LangGraph"):
                chunk = data.get("chunk") or {}
                if not isinstance(chunk, dict):
                    continue

                if "tree" in chunk:
                    yield {"type": "file_tree", "runId": runId, "tree": chunk["tree"]}

                if "file_contents" in chunk and isinstance(chunk["file_contents"], dict):
                    for path, content in chunk["file_contents"].items():
                        if isinstance(path, str) and isinstance(content, str):
                            yield {"type": "file_content", "runId": runId, "path": path, "content": content}

                # Handle diffs
                if "diffs" in chunk and isinstance(chunk["diffs"], list):
                    for d in chunk["diffs"]:
                        if not isinstance(d, dict):
                            continue
                        file = d.get("file")
                        oldCode = d.get("oldCode", "")
                        newCode = d.get("newCode", "")
                        if not isinstance(file, str):
                            continue
                        if not isinstance(oldCode, str) or not isinstance(newCode, str):
                            continue

                        # Store for approval/apply endpoints
                        await set_pending_diff(runId, file, oldCode, newCode)
                        proposed_files.append(file)
                        yield {"type": "proposed_file", "runId": runId, "path": file, "content": newCode}
                        # Back-compat: emit the old diff payload too.
                        yield {"type": "diff", "runId": runId, "file": file, "oldCode": oldCode, "newCode": newCode}
                
                # Handle pending approval files
                if "pending_approval_files" in chunk and chunk.get("awaiting_approval"):
                    files = chunk.get("pending_approval_files", [])
                    yield {"type": "awaiting_user_review", "runId": runId, "files": files}

                # Handle terminal output streaming
                if "terminal_output" in chunk and isinstance(chunk["terminal_output"], list):
                    for line in chunk["terminal_output"]:
                        yield {"type": "terminal", "runId": runId, "line": line}
                
                # Handle build status from state
                if "build_success" in chunk and chunk.get("build_success") is not None:
                    success = chunk.get("build_success", False)
                    output = chunk.get("build_output", "")
                    yield {
                        "type": "build",
                        "runId": runId,
                        "status": "success" if success else "error",
                        "data": output
                    }
                
                # Handle final summary
                if "final_summary" in chunk and chunk["final_summary"]:
                    yield {"type": "thought", "runId": runId, "content": chunk["final_summary"]}

    except Exception as e:
        yield {"type": "thought", "runId": runId, "content": f"Error during agent execution: {str(e)}"}
        yield {"type": "run_finished", "runId": runId}
        return

    yield {"type": "run_finished", "runId": runId}
