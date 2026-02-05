import json
import asyncio
from typing import Optional

from agent.state import AgentState, Diff
from agent.llm import propose_code_changes
from services.vector_store import YellowVectorStore


def _maybe_add_yellow_sdk_to_package_json(old: str) -> Optional[str]:
    """
    Best-effort JSON edit:
    - If invalid JSON, return None
    - If dependency already exists, return None
    - Else add @yellow-network/sdk to dependencies
    """
    try:
        data = json.loads(old) if old.strip() else {}
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    deps = data.get("dependencies")
    if deps is None:
        deps = {}
        data["dependencies"] = deps
    if not isinstance(deps, dict):
        return None

    if "@yellow-network/sdk" in deps:
        return None

    # Version intentionally left flexible; real integrator should pin/validate.
    deps["@yellow-network/sdk"] = "latest"
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _maybe_set_yellow_sdk_version_in_package_json(old: str, version: str) -> Optional[str]:
    """
    Like _maybe_add_yellow_sdk_to_package_json but uses the provided version and
    updates the dependency if it already exists.
    """
    try:
        data = json.loads(old) if old.strip() else {}
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    deps = data.get("dependencies")
    if deps is None:
        deps = {}
        data["dependencies"] = deps
    if not isinstance(deps, dict):
        return None

    deps["@yellow-network/sdk"] = version
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


async def propose_changes_node(state: AgentState) -> AgentState:
    prompt = state.get("prompt", "")
    files = state.get("file_contents", {}) or {}
    plan_notes = state.get("plan_notes", "")
    sdk_version = state.get("sdk_version", "latest")

    diffs: list[Diff] = []

    # Perform RAG retrieval
    search_query = f"{prompt} {plan_notes[:200]}"
    try:
        vector_store = YellowVectorStore()
        rag_context = await asyncio.to_thread(vector_store.search, search_query)
    except Exception as e:
        # Fallback if RAG fails (e.g. no docs ingested)
        rag_context = f"Error retrieving docs: {e}"

    # Use LLM to propose code changes
    llm_diffs = await propose_code_changes(prompt, files, plan_notes, sdk_version, rag_context)
    diffs.extend(llm_diffs)

    # Notes file diff (always add this)
    notes_file = "YELLOW_AGENT_NOTES.md"
    old_notes = files.get(notes_file, "")
    new_notes = plan_notes
    if new_notes != old_notes:
        # Only add if LLM didn't already propose it
        if not any(d["file"] == notes_file for d in diffs):
            diffs.append({"file": notes_file, "oldCode": old_notes, "newCode": new_notes})

    # If we have a package.json, ensure SDK dependency is added/updated
    # (LLM might have already done this, but we ensure it's correct)
    pkg_path: Optional[str] = None
    for p in ["package.json", "frontend/package.json", "backend/package.json"]:
        if p in files:
            pkg_path = p
            break
    if pkg_path is None:
        for p in files.keys():
            if p.endswith("package.json"):
                pkg_path = p
                break

    if pkg_path is not None:
        old_pkg = files.get(pkg_path, "")
        new_pkg = _maybe_set_yellow_sdk_version_in_package_json(old_pkg, sdk_version)
        if new_pkg is None:
            new_pkg = _maybe_add_yellow_sdk_to_package_json(old_pkg)
        if new_pkg is not None and new_pkg != old_pkg:
            # Only add if LLM didn't already propose it
            if not any(d["file"] == pkg_path for d in diffs):
                diffs.append({"file": pkg_path, "oldCode": old_pkg, "newCode": new_pkg})

    return {"diffs": diffs}
