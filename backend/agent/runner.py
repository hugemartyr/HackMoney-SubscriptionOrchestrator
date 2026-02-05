from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict

from agent.graph import app_graph
from services.pending_diff_service import set_pending_diff


async def run_agent(runId: str, prompt: str) -> AsyncIterator[Dict[str, Any]]:
    """
    Minimal runner that emits frontend-compatible SSE events.
    Backed by a simple LangGraph workflow (scan -> read -> plan/diff).
    """
    yield {"type": "run_started", "runId": runId, "prompt": prompt}
    yield {"type": "thought", "runId": runId, "content": "Starting Yellow agent..."}

    # Stream node lifecycle + state deltas from LangGraph.
    # We translate those into the SSEEvent schema the frontend understands.
    proposed_files: list[str] = []
    graph_completed = False

    try:
        async for ev in app_graph.astream_events({"prompt": prompt}, version="v2"):
            name = ev.get("name")
            event_type = ev.get("event")
            data = ev.get("data") or {}

            # Check for graph completion
            if event_type == "on_chain_end" and name == "LangGraph":
                graph_completed = True

            # Node lifecycle => tool events
            if event_type == "on_chain_start" and name not in (None, "LangGraph"):
                yield {"type": "tool_start", "runId": runId, "name": name}
                if name == "scan":
                    yield {"type": "thought", "runId": runId, "content": "Scanning sandbox..."}
                elif name == "read_files":
                    yield {"type": "thought", "runId": runId, "content": "Reading files for context..."}
                elif name == "plan":
                    yield {"type": "thought", "runId": runId, "content": "Planning changes..."}
                elif name == "propose_changes":
                    yield {"type": "thought", "runId": runId, "content": "Generating proposed file changes..."}
                elif name == "validate":
                    yield {"type": "thought", "runId": runId, "content": "Validating changes..."}

            if event_type == "on_chain_end" and name not in (None, "LangGraph"):
                yield {"type": "tool_end", "runId": runId, "name": name, "status": "success"}

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
    except Exception as e:
        yield {"type": "thought", "runId": runId, "content": f"Error during agent execution: {str(e)}"}
        yield {"type": "run_finished", "runId": runId}
        return

    # Optional build placeholder to exercise UI.
    yield {"type": "build", "runId": runId, "status": "start"}
    await asyncio.sleep(0.05)
    yield {"type": "build", "runId": runId, "status": "output", "data": "Build step placeholder (no-op)\n"}
    await asyncio.sleep(0.05)
    yield {"type": "build", "runId": runId, "status": "success", "data": "No build executed (placeholder)\n"}

    yield {"type": "awaiting_user_review", "runId": runId, "files": proposed_files}
    yield {"type": "thought", "runId": runId, "content": "Agent stream complete."}
    yield {"type": "run_finished", "runId": runId}
