from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator, Dict

from agent.graph import app_graph
from services.pending_diff_service import set_pending_diff


async def run_agent(prompt: str) -> AsyncIterator[Dict[str, Any]]:
    """
    Minimal runner that emits frontend-compatible SSE events.
    Backed by a simple LangGraph workflow (scan -> read -> plan/diff).
    """
    yield {"type": "thought", "content": "Starting Yellow agent..."}
    yield {"type": "thought", "content": f"Received prompt: {prompt}"}

    # Stream node lifecycle + state deltas from LangGraph.
    # We translate those into the SSEEvent schema the frontend understands.
    async for ev in app_graph.astream_events({"prompt": prompt}, version="v2"):
        name = ev.get("name")
        event_type = ev.get("event")
        data = ev.get("data") or {}

        # Node lifecycle => tool events
        if event_type == "on_chain_start" and name not in (None, "LangGraph"):
            yield {"type": "tool", "name": name, "status": "start"}
            if name == "scan":
                yield {"type": "thought", "content": "Scanning sandbox..."}
            elif name == "read_files":
                yield {"type": "thought", "content": "Reading files for context..."}
            elif name == "plan_and_diff":
                yield {"type": "thought", "content": "Planning changes and generating diffs..."}

        if event_type == "on_chain_end" and name not in (None, "LangGraph"):
            yield {"type": "tool", "name": name, "status": "success"}

        # Streamed state chunks
        if event_type == "on_chain_stream" and name not in (None, "LangGraph"):
            chunk = data.get("chunk") or {}
            if not isinstance(chunk, dict):
                continue

            if "tree" in chunk:
                yield {"type": "file_tree", "tree": chunk["tree"]}

            if "file_contents" in chunk and isinstance(chunk["file_contents"], dict):
                for path, content in chunk["file_contents"].items():
                    if isinstance(path, str) and isinstance(content, str):
                        yield {"type": "file_content", "path": path, "content": content}

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
                    await set_pending_diff(file, oldCode, newCode)
                    yield {"type": "diff", "file": file, "oldCode": oldCode, "newCode": newCode}

    # Optional build placeholder to exercise UI.
    yield {"type": "build", "status": "start"}
    await asyncio.sleep(0.05)
    yield {"type": "build", "status": "output", "data": "Build step placeholder (no-op)\n"}
    await asyncio.sleep(0.05)
    yield {"type": "build", "status": "success", "data": "No build executed (placeholder)\n"}

    yield {"type": "thought", "content": "Agent stream complete."}
