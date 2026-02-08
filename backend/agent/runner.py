from __future__ import annotations
from typing import Any, AsyncIterator, Dict, List
import json
import hashlib

from langgraph.types import Command

from agent.graph import app_graph
from services.pending_diff_service import set_pending_diff
from services.sandbox_fs_service import get_file_tree, require_root
from utils.logger import get_logger


logger = get_logger(__name__)

# Nodes that only read files, not write them
READ_ONLY_NODES = {
    "start_agent",
    "context_check",
    "read_code",
    "analyze_imports",
    "retrieve_docs",
    "research",
    "update_memory",
    "architect",
    "plan_review_and_doc_checklist",
    "retrieve_targeted_docs",
    "plan_correction",
    "yellow_init",
    "yellow_workflow",
    "yellow_versioned",
    "yellow_multiparty",
    "yellow_tip",
    "yellow_deposit",
}

# Last run id passed to run_agent (so apply/resume can use it when client omits runId)
_LAST_AGENT_RUN_ID: str | None = None


def get_last_agent_run_id() -> str | None:
    """Return the run id of the most recent agent stream (for apply/resume when client omits runId)."""
    return _LAST_AGENT_RUN_ID


async def run_agent(runId: str, prompt: str) -> AsyncIterator[Dict[str, Any]]:
    """
    Minimal runner that emits frontend-compatible SSE events.
    Backed by LangGraph workflow.
    """
    global _LAST_AGENT_RUN_ID
    _LAST_AGENT_RUN_ID = runId
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
    
    # Track which files have been sent and tree state to avoid duplicate events
    sent_file_contents: dict[str, str] = {}
    last_tree_hash: str | None = None

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
                    yield {"type": "thought", "runId": runId, "content": "Designing integration plan and detecting Yellow requirements..."}
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
                elif name == "yellow_deposit":
                    yield {"type": "thought", "runId": runId, "content": "Injecting deposit utility..."}
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
                
                # Print state to terminal after each node completes
                try:
                    snapshot = app_graph.get_state(config)
                    state_values = snapshot.values or {}
                    
                    # Format state for terminal output
                    print("\n" + "="*80)
                    print(f"STATE AFTER NODE: {name}")
                    print("="*80)
                    print(json.dumps(state_values, indent=2, default=str))
                    print("="*80 + "\n")
                except Exception as e:
                    logger.exception("Failed to print state after node", extra={"run_id": runId, "node": name})
                    print(f"\n[ERROR] Failed to print state after node {name}: {str(e)}\n")

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

                # Print state update to terminal after each state change
                try:
                    snapshot = app_graph.get_state(config)
                    state_values = snapshot.values or {}
                    
                    # Format state for terminal output
                    print("\n" + "="*80)
                    print(f"STATE UPDATE AFTER NODE: {name}")
                    print("="*80)
                    print(json.dumps(state_values, indent=2, default=str))
                    print("="*80 + "\n")
                except Exception as e:
                    logger.exception("Failed to print state update", extra={"run_id": runId, "node": name})
                    print(f"\n[ERROR] Failed to print state update for node {name}: {str(e)}\n")

                # Only emit file_tree if it actually changed
                if "tree" in chunk:
                    tree_str = json.dumps(chunk["tree"], sort_keys=True)
                    tree_hash = hashlib.md5(tree_str.encode()).hexdigest()
                    if tree_hash != last_tree_hash:
                        logger.debug("State update: tree (changed)", extra={"run_id": runId})
                        yield {"type": "file_tree", "runId": runId, "tree": chunk["tree"]}
                        last_tree_hash = tree_hash

                # Only emit file_content events when NOT in read-only nodes
                # Files are only written when diffs are approved (outside graph), not during read phase
                if "file_contents" in chunk and isinstance(chunk["file_contents"], dict):
                    # Suppress file_content events for read-only nodes (files are only being read, not written)
                    if name not in READ_ONLY_NODES:
                        # Only emit for files that are new or changed
                        new_or_changed = []
                        for path, content in chunk["file_contents"].items():
                            if isinstance(path, str) and isinstance(content, str):
                                # Only emit if this is a new file or content changed
                                if path not in sent_file_contents or sent_file_contents[path] != content:
                                    yield {"type": "file_content", "runId": runId, "path": path, "content": content}
                                    sent_file_contents[path] = content
                                    new_or_changed.append(path)
                        
                        if new_or_changed:
                            logger.debug(
                                "State update: file_contents (new/changed)",
                                extra={"run_id": runId, "file_count": len(new_or_changed), "files": new_or_changed},
                            )
                    else:
                        # For read-only nodes, just track the files internally without emitting events
                        for path, content in chunk["file_contents"].items():
                            if isinstance(path, str) and isinstance(content, str):
                                sent_file_contents[path] = content

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
    Resume the graph after HITL approval. Uses checkpoint state + resume_from_approval
    so the entry router sends the run to coding → build → ... (no interrupt resume).
    """
    logger.debug(
        "resume_agent started",
        extra={"run_id": runId, "approved": approved, "approved_files_count": len(approved_files)},
    )
    yield {"type": "thought", "runId": runId, "content": "Resuming after user approval..."}

    config = {"configurable": {"thread_id": runId}}
    
    # Track tree and file contents to avoid duplicate events
    last_tree_hash: str | None = None
    sent_file_contents: dict[str, str] = {}

    try:
        # Load checkpoint state from the interrupted run, then continue from coding
        snapshot = app_graph.get_state(config)
        if not snapshot or not snapshot.values:
            logger.warning("No checkpoint state for run_id=%s, trying Command(resume=...)", runId)
            resume_value = {"approved": approved, "approved_files": approved_files}
            stream_input = Command(resume=resume_value)
        else:
            # Merge approval into checkpoint state and run from entry (resume_router → coding)
            values = dict(snapshot.values)
            values["resume_from_approval"] = True
            values["approved"] = approved
            values["approved_files"] = approved_files
            values["awaiting_approval"] = False
            values["pending_approval_files"] = []
            stream_input = values

        async for ev in app_graph.astream_events(
            stream_input, config=config, version="v2"
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
                
                # Print state to terminal after each node completes
                try:
                    snapshot = app_graph.get_state(config)
                    state_values = snapshot.values or {}
                    
                    # Format state for terminal output
                    print("\n" + "="*80)
                    print(f"STATE AFTER NODE: {name}")
                    print("="*80)
                    print(json.dumps(state_values, indent=2, default=str))
                    print("="*80 + "\n")
                except Exception as e:
                    logger.exception("Failed to print state after node", extra={"run_id": runId, "node": name})
                    print(f"\n[ERROR] Failed to print state after node {name}: {str(e)}\n")

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

                # Print state update to terminal after each state change
                try:
                    snapshot = app_graph.get_state(config)
                    state_values = snapshot.values or {}
                    
                    # Format state for terminal output
                    print("\n" + "="*80)
                    print(f"STATE UPDATE AFTER NODE: {name}")
                    print("="*80)
                    print(json.dumps(state_values, indent=2, default=str))
                    print("="*80 + "\n")
                except Exception as e:
                    logger.exception("Failed to print state update", extra={"run_id": runId, "node": name})
                    print(f"\n[ERROR] Failed to print state update for node {name}: {str(e)}\n")

                # Only emit file_tree if it actually changed
                if "tree" in chunk:
                    tree_str = json.dumps(chunk["tree"], sort_keys=True)
                    tree_hash = hashlib.md5(tree_str.encode()).hexdigest()
                    if tree_hash != last_tree_hash:
                        yield {"type": "file_tree", "runId": runId, "tree": chunk["tree"]}
                        last_tree_hash = tree_hash
                
                # Only emit file_content for files that are new or changed
                # After resume, we're past the read-only phase, but still track changes
                if "file_contents" in chunk and isinstance(chunk["file_contents"], dict):
                    new_or_changed = []
                    for path, content in chunk["file_contents"].items():
                        if isinstance(path, str) and isinstance(content, str):
                            # Only emit if this is a new file or content changed
                            if path not in sent_file_contents or sent_file_contents[path] != content:
                                yield {"type": "file_content", "runId": runId, "path": path, "content": content}
                                sent_file_contents[path] = content
                                new_or_changed.append(path)
                    
                    if new_or_changed:
                        logger.debug(
                            "State update: file_contents (new/changed)",
                            extra={"run_id": runId, "file_count": len(new_or_changed), "files": new_or_changed},
                        )
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
