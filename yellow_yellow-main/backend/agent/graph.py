from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from langgraph.graph import END, StateGraph

from agent.llm import generate_plan, propose_code_changes
from agent.state import AgentState, Diff
from services.sandbox_fs_service import get_file_tree, read_text_file


def _safe_file_list_from_tree(tree: Dict[str, Any], limit: int = 10) -> list[str]:
    out: list[str] = []

    def walk(node: Dict[str, Any]) -> None:
        nonlocal out
        if len(out) >= limit:
            return
        if node.get("type") == "file":
            p = node.get("path")
            if isinstance(p, str) and p:
                out.append(p)
            return
        for child in node.get("children", []) or []:
            if isinstance(child, dict):
                walk(child)

    walk(tree)
    return out[:limit]


async def scan_node(state: AgentState) -> AgentState:
    tree = await get_file_tree()

    # A few "usual suspects" + a handful from the actual tree.
    candidates: list[str] = [
        "package.json",
        "README.md",
        "requirements.txt",
        "src/main.ts",
        "src/index.ts",
        "app/page.tsx",
    ]
    candidates.extend(_safe_file_list_from_tree(tree, limit=8))

    # De-dupe while preserving order.
    seen: set[str] = set()
    files_to_read: list[str] = []
    for p in candidates:
        if p and p not in seen:
            files_to_read.append(p)
            seen.add(p)

    return {"tree": tree, "files_to_read": files_to_read}


async def read_files_node(state: AgentState) -> AgentState:
    file_contents: dict[str, str] = {}
    for p in state.get("files_to_read", []):
        try:
            obj = await read_text_file(p)
        except Exception:
            continue
        file_contents[obj["path"]] = obj["content"]
    return {"file_contents": file_contents}


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


async def plan_node(state: AgentState) -> AgentState:
    prompt = state.get("prompt", "")
    files = state.get("file_contents", {}) or {}

    llm_out = await generate_plan(prompt, files)
    plan_notes = llm_out["notes_markdown"].rstrip() + "\n"
    sdk_version = llm_out["yellow_sdk_version"].strip() or "latest"

    return {"plan_notes": plan_notes, "sdk_version": sdk_version}


async def propose_changes_node(state: AgentState) -> AgentState:
    prompt = state.get("prompt", "")
    files = state.get("file_contents", {}) or {}
    plan_notes = state.get("plan_notes", "")
    sdk_version = state.get("sdk_version", "latest")

    diffs: list[Diff] = []

    # Use LLM to propose code changes
    llm_diffs = await propose_code_changes(prompt, files, plan_notes, sdk_version)
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


async def validate_node(state: AgentState) -> AgentState:
    # Placeholder for future: run lint/build/test in sandbox and stream output.
    # Return state unchanged to ensure proper graph completion
    return state


workflow = StateGraph(AgentState)
workflow.add_node("scan", scan_node)
workflow.add_node("read_files", read_files_node)
workflow.add_node("plan", plan_node)
workflow.add_node("propose_changes", propose_changes_node)
workflow.add_node("validate", validate_node)

workflow.set_entry_point("scan")
workflow.add_edge("scan", "read_files")
workflow.add_edge("read_files", "plan")
workflow.add_edge("plan", "propose_changes")
workflow.add_edge("propose_changes", "validate")
workflow.add_edge("validate", END)

app_graph = workflow.compile()
