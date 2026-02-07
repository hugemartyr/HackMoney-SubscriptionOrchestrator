from __future__ import annotations
from typing import Any, AsyncIterator, Dict, List

from langgraph.types import Command

from agent.graph import app_graph
from services.pending_diff_service import set_pending_diff
from services.sandbox_fs_service import get_file_tree, require_root
from utils.logger import get_logger


logger = get_logger(__name__)


async def run_agent(runId: str, prompt: str) -> AsyncIterator[Dict[str, Any]]:
    """
    Minimal runner that emits frontend-compatible SSE events.
    Backed by LangGraph workflow.
    """
    logger.debug(
        "run_agent started",
        extra={"run_id": runId, "prompt_length": len(prompt), "prompt_preview": prompt[:200]},
    )
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
            logger.debug("Requesting initial file tree", extra={"run_id": runId})
            tree = await get_file_tree()
            logger.debug(
                "Initial file tree loaded",
                extra={"run_id": runId, "has_tree": bool(tree)},
            )
            yield {"type": "file_tree", "runId": runId, "tree": tree}
        except Exception:
            logger.exception("Failed to load initial file tree", extra={"run_id": runId})
            tree = None  # Set to None if FS not ready

        # Pass tree in initial state
        initial_state = {"prompt": prompt}
        if tree:
            initial_state["tree"] = tree  # type: ignore[arg-type]
        try:
            initial_state["repo_path"] = str(require_root())
        except Exception:
            initial_state["repo_path"] = ""

        config = {"configurable": {"thread_id": runId}}
        async for ev in app_graph.astream_events(
            initial_state, config=config, version="v2"
        ):
            name = ev.get("name")
            event_type = ev.get("event")
            data = ev.get("data") or {}

            logger.debug(
                "LangGraph event received",
                extra={"run_id": runId, "event_type": event_type, "node_name": name},
            )

            # Check for graph completion
            if event_type == "on_chain_end" and name == "LangGraph":
                graph_completed = True
                logger.debug("LangGraph chain completed", extra={"run_id": runId})

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
                elif name == "parse_yellow":
                    yield {"type": "thought", "runId": runId, "content": "Parsing prompt for Yellow SDK requirements..."}
                elif name == "yellow_init":
                    yield {"type": "thought", "runId": runId, "content": "Initializing Yellow SDK in project..."}
                elif name == "yellow_workflow":
                    yield {"type": "thought", "runId": runId, "content": "Running Yellow network workflow..."}
                elif name == "yellow_multiparty":
                    yield {"type": "thought", "runId": runId, "content": "Setting up multiparty Yellow workflow..."}
                elif name == "yellow_versioned":
                    yield {"type": "thought", "runId": runId, "content": "Creating versioned integration layer..."}
                elif name == "yellow_tip":
                    yield {"type": "thought", "runId": runId, "content": "Injecting tipping utility..."}
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
                logger.debug(
                    "Tool finished",
                    extra={"run_id": runId, "name": name},
                )
                yield {"type": "tool_end", "runId": runId, "name": name, "status": "success"}

            # Handle custom events emitted by nodes (e.g. build output, awaiting approval)
            if event_type == "on_custom_event":
                event_name = ev.get("name")
                event_data = data

                logger.debug(
                    "Custom event received",
                    extra={"run_id": runId, "event_name": event_name},
                )

                if event_name == "terminal_output":
                    # Stream terminal output
                    yield {"type": "terminal", "runId": runId, "line": event_data.get("data", "")}

                elif event_name == "build_status":
                    # Stream build lifecycle
                    yield {
                        "type": "build",
                        "runId": runId,
                        "status": event_data.get("status"),
                        "data": event_data.get("data"),
                    }

                elif event_name == "awaiting_approval":
                    # HITL pause
                    files = event_data.get("files", [])
                    logger.debug(
                        "Awaiting user approval for files",
                        extra={"run_id": runId, "files": files},
                    )
                    yield {"type": "awaiting_user_review", "runId": runId, "files": files}
                    yield {"type": "thought", "runId": runId, "content": "Waiting for user approval..."}

            # Streamed state chunks
            if event_type == "on_chain_stream" and name not in (None, "LangGraph"):
                chunk = data.get("chunk") or {}
                if not isinstance(chunk, dict):
                    continue

                if "tree" in chunk:
                    logger.debug("State update: tree", extra={"run_id": runId})
                    yield {"type": "file_tree", "runId": runId, "tree": chunk["tree"]}

                if "file_contents" in chunk and isinstance(chunk["file_contents"], dict):
                    logger.debug(
                        "State update: file_contents",
                        extra={"run_id": runId, "file_count": len(chunk["file_contents"])},
                    )
                    for path, content in chunk["file_contents"].items():
                        if isinstance(path, str) and isinstance(content, str):
                            yield {"type": "file_content", "runId": runId, "path": path, "content": content}

                # Handle diffs
                if "diffs" in chunk and isinstance(chunk["diffs"], list):
                    logger.debug(
                        "State update: diffs",
                        extra={"run_id": runId, "diff_count": len(chunk["diffs"])},
                    )
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
                    logger.debug(
                        "State update: pending_approval_files",
                        extra={"run_id": runId, "files": files},
                    )
                    yield {"type": "awaiting_user_review", "runId": runId, "files": files}

                # Handle terminal output streaming
                if "terminal_output" in chunk and isinstance(chunk["terminal_output"], list):
                    logger.debug(
                        "State update: terminal_output",
                        extra={"run_id": runId, "line_count": len(chunk["terminal_output"])},
                    )
                    for line in chunk["terminal_output"]:
                        yield {"type": "terminal", "runId": runId, "line": line}

                # Handle build status from state
                if "build_success" in chunk and chunk.get("build_success") is not None:
                    success = chunk.get("build_success", False)
                    output = chunk.get("build_output", "")
                    logger.debug(
                        "State update: build status",
                        extra={"run_id": runId, "success": success},
                    )
                    yield {
                        "type": "build",
                        "runId": runId,
                        "status": "success" if success else "error",
                        "data": output,
                    }

                # Handle final summary
                if "final_summary" in chunk and chunk["final_summary"]:
                    logger.debug("State update: final_summary", extra={"run_id": runId})
                    yield {"type": "thought", "runId": runId, "content": chunk["final_summary"]}

    except Exception as e:
        logger.exception("Error during agent execution", extra={"run_id": runId})
        yield {"type": "thought", "runId": runId, "content": f"Error during agent execution: {str(e)}"}
        yield {"type": "run_finished", "runId": runId}
        return

    # If graph ended without completing, check for HITL interrupt at await_approval
    if not graph_completed:
        try:
            config = {"configurable": {"thread_id": runId}}
            snapshot = app_graph.get_state(config)
            next_nodes = getattr(snapshot, "next", ()) or ()
            if next_nodes and "await_approval" in next_nodes:
                values = snapshot.values or {}
                diffs = values.get("diffs", [])
                files = [d.get("file", "") for d in diffs if isinstance(d, dict) and d.get("file")]
                if files:
                    logger.debug(
                        "Graph interrupted at await_approval, emitting awaiting_user_review",
                        extra={"run_id": runId, "files": files},
                    )
                    yield {"type": "awaiting_user_review", "runId": runId, "files": files}
                    yield {"type": "thought", "runId": runId, "content": "Waiting for user approval..."}
                    # Signal paused for HITL so frontend keeps activeRunId for resume
                    yield {"type": "run_finished", "runId": runId, "interrupted": True}
                    return
        except Exception:
            logger.exception("Failed to check interrupt state", extra={"run_id": runId})

    logger.debug(
        "run_agent finished",
        extra={"run_id": runId, "graph_completed": graph_completed, "proposed_files": proposed_files},
    )
    yield {"type": "run_finished", "runId": runId}


async def resume_agent(
    runId: str, approved: bool, approved_files: List[str]
) -> AsyncIterator[Dict[str, Any]]:
    """
    Resume the graph after HITL approval. Applies Command(resume=...) to continue from interrupt.
    """
    logger.debug(
        "resume_agent started",
        extra={"run_id": runId, "approved": approved, "approved_files_count": len(approved_files)},
    )
    yield {"type": "thought", "runId": runId, "content": "Resuming after user approval..."}

    config = {"configurable": {"thread_id": runId}}
    resume_value = {"approved": approved, "approved_files": approved_files}

    try:
        async for ev in app_graph.astream_events(
            Command(resume=resume_value), config=config, version="v2"
        ):
            name = ev.get("name")
            event_type = ev.get("event")
            data = ev.get("data") or {}

            if event_type == "on_chain_start" and name not in (None, "LangGraph"):
                yield {"type": "tool_start", "runId": runId, "name": name}
                if name == "coding":
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

            if event_type == "on_custom_event":
                event_data = data
                if ev.get("name") == "terminal_output":
                    yield {"type": "terminal", "runId": runId, "line": event_data.get("data", "")}
                elif ev.get("name") == "build_status":
                    yield {
                        "type": "build",
                        "runId": runId,
                        "status": event_data.get("status"),
                        "data": event_data.get("data"),
                    }

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
                if "terminal_output" in chunk and isinstance(chunk["terminal_output"], list):
                    for line in chunk["terminal_output"]:
                        yield {"type": "terminal", "runId": runId, "line": line}
                if "build_success" in chunk and chunk.get("build_success") is not None:
                    success = chunk.get("build_success", False)
                    output = chunk.get("build_output", "")
                    yield {
                        "type": "build",
                        "runId": runId,
                        "status": "success" if success else "error",
                        "data": output,
                    }
                if "final_summary" in chunk and chunk.get("final_summary"):
                    yield {"type": "thought", "runId": runId, "content": chunk["final_summary"]}
    except Exception as e:
        logger.exception("Error during agent resume", extra={"run_id": runId})
        yield {"type": "thought", "runId": runId, "content": f"Error during resume: {str(e)}"}
    finally:
        yield {"type": "run_finished", "runId": runId}
