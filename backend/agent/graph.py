from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from services.sandbox_fs_service import get_file_tree, read_text_file


class Diff(TypedDict):
    file: str
    oldCode: str
    newCode: str


class AgentState(TypedDict, total=False):
    prompt: str
    tree: Dict[str, Any]
    files_to_read: List[str]
    file_contents: Dict[str, str]
    diffs: List[Diff]
    errors: List[str]


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


def _extract_first_json_object(text: str) -> Optional[dict]:
    """
    Best-effort: extract the first {...} JSON object from an LLM response.
    """
    if not text:
        return None
    s = text.strip()
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass

    # Try fenced ```json ... ```
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", s, flags=re.IGNORECASE)
    if m:
        try:
            obj = json.loads(m.group(1))
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None

    # Try substring from first { to last }
    start = s.find("{")
    end = s.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            obj = json.loads(s[start : end + 1])
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    return None


async def _llm_generate_notes_and_version(prompt: str, files: Dict[str, str]) -> Optional[dict]:
    """
    If GOOGLE_API_KEY is set and langchain-google-genai is installed, ask Gemini
    for a short notes markdown + recommended @yellow-network/sdk version.

    Returns dict like:
      {\"notes_markdown\": \"...\", \"yellow_sdk_version\": \"^x.y.z\"}
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import HumanMessage, SystemMessage
    except Exception:
        return None

    # Keep context small to avoid huge prompts; just provide a snippet of a few files.
    snippets: list[str] = []
    for path in sorted(files.keys())[:10]:
        content = files.get(path, "")
        snippet = content[:1200]
        snippets.append(f"--- {path} ---\n{snippet}\n")
    context = "\n".join(snippets)

    system = (
        "You are a senior engineer helping integrate Yellow Network SDK into an existing project.\n"
        "Return ONLY a single JSON object with keys:\n"
        "- notes_markdown: string (markdown)\n"
        "- yellow_sdk_version: string (npm semver like \"^1.2.3\" or \"latest\")\n"
        "No additional keys. No surrounding text."
    )
    user = (
        f"User prompt:\n{prompt}\n\n"
        "Repository context (snippets):\n"
        f"{context}\n\n"
        "Generate the JSON now."
    )

    # Model selection:
    # - GOOGLE_MODEL can be a single model name
    # - GOOGLE_MODELS can be a comma-separated fallback list
    models_env = (os.getenv("GOOGLE_MODELS") or "").strip()
    if models_env:
        model_candidates = [m.strip() for m in models_env.split(",") if m.strip()]
    else:
        model_candidates = [os.getenv("GOOGLE_MODEL", "").strip()]
        model_candidates = [m for m in model_candidates if m]

    # Reasonable defaults (varies by account / API version support).
    if not model_candidates:
        model_candidates = ["gemini-2.0-flash", "gemini-1.5-flash-latest", "gemini-1.5-flash"]

    for model in model_candidates:
        try:
            llm = ChatGoogleGenerativeAI(
                model=model,
                api_key=api_key,
                temperature=0.2,
                max_tokens=1024,
                # Avoid server-side streaming differences; we just want one JSON blob.
                disable_streaming=True,
            )

            resp = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=user)])
            content = getattr(resp, "content", "") or ""
            obj = _extract_first_json_object(content)
            if not obj:
                continue

            notes = obj.get("notes_markdown")
            version = obj.get("yellow_sdk_version")
            if not isinstance(notes, str) or not isinstance(version, str):
                continue
            return {"notes_markdown": notes, "yellow_sdk_version": version}
        except Exception:
            # Any model/API failure should not break the agent stream.
            continue

    return None


async def plan_and_diff_node(state: AgentState) -> AgentState:
    prompt = state.get("prompt", "")
    files = state.get("file_contents", {}) or {}

    diffs: list[Diff] = []

    # Prefer LLM-generated notes + version if available; fallback to deterministic.
    notes_file = "YELLOW_AGENT_NOTES.md"
    old_notes = files.get(notes_file, "")
    llm_out = await _llm_generate_notes_and_version(prompt, files)
    if llm_out is not None:
        new_notes = llm_out["notes_markdown"].rstrip() + "\n"
        sdk_version = llm_out["yellow_sdk_version"].strip() or "latest"
    else:
        new_notes = (
            "# Yellow Agent Notes\n\n"
            f"## Prompt\n\n{prompt}\n\n"
            "## Next steps\n\n"
            "- Audit the project entrypoints and payment/trading flows\n"
            "- Add Yellow SDK integration points\n"
            "- Generate per-file diffs for review\n"
        )
        sdk_version = "latest"

    if new_notes != old_notes:
        diffs.append({"file": notes_file, "oldCode": old_notes, "newCode": new_notes})

    # If we have a package.json, propose adding the SDK dependency.
    pkg_path: Optional[str] = None
    for p in ["package.json", "frontend/package.json", "backend/package.json"]:
        if p in files:
            pkg_path = p
            break
    if pkg_path is None:
        # fallback: any path that ends with package.json
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
            diffs.append({"file": pkg_path, "oldCode": old_pkg, "newCode": new_pkg})

    return {"diffs": diffs}


workflow = StateGraph(AgentState)
workflow.add_node("scan", scan_node)
workflow.add_node("read_files", read_files_node)
workflow.add_node("plan_and_diff", plan_and_diff_node)

workflow.set_entry_point("scan")
workflow.add_edge("scan", "read_files")
workflow.add_edge("read_files", "plan_and_diff")
workflow.add_edge("plan_and_diff", END)

app_graph = workflow.compile()
