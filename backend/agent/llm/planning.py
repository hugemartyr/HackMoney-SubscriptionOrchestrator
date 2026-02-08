from __future__ import annotations

from typing import Dict, Any, List, Optional

from config import settings
from agent import prompts
from agent.llm.utils import extract_text_from_content, extract_json_from_response

async def generate_plan(prompt: str, files: Dict[str, str], doc_context: str = "") -> dict:
    """
    If OPENROUTER_API_KEY is set, ask the configured LLM (e.g. Claude Sonnet)
    for a short notes markdown + recommended @yellow-network/sdk version.

    Returns dict like:
      {"notes_markdown": "...", "yellow_sdk_version": "^x.y.z"}
    """
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set. Cannot generate plan without LLM.")

    try:
        from agent.llm.utils import get_llm
    except Exception as e:
        raise RuntimeError(f"Failed to import required LLM libraries: {e}")

    # Keep context small to avoid huge prompts; just provide a snippet of a few files.
    snippets: list[str] = []
    for path in sorted(files.keys())[:10]:
        content = files.get(path, "")
        snippet = content[:1200]
        snippets.append(f"--- {path} ---\n{snippet}\n")
    codebase_context = "\n".join(snippets)

    messages = prompts.build_planner_prompt(prompt, doc_context, codebase_context)

    llm = get_llm(temperature=0.2, max_tokens=(8192 * 2))

    resp = await llm.ainvoke(messages)
    raw_content = getattr(resp, "content", "") or ""
    
    # Extract text from content (handles strings, lists, dicts)
    content = extract_text_from_content(raw_content)
    
    obj = extract_json_from_response(content)
    if not obj:
        # Include a snippet of the actual response for debugging
        content_snippet = content[:500] if len(content) > 500 else content
        error_msg = (
            f"Failed to generate plan from LLM. No valid JSON response received.\n"
            f"Response preview (first 500 chars): {content_snippet!r}\n"
            f"Full response length: {len(content)} chars"
        )
        raise RuntimeError(error_msg)

    notes = obj.get("notes_markdown")
    version = obj.get("yellow_sdk_version")
    if not isinstance(notes, str) or not isinstance(version, str):
        raise RuntimeError("Failed to generate plan from LLM. Invalid response structure.")

    def _bool(key: str) -> bool:
        v = obj.get(key)
        if v is None:
            return False
        return bool(v) if isinstance(v, bool) else str(v).lower() in ("true", "1", "yes")

    return {
        "notes_markdown": notes,
        "yellow_sdk_version": version,
        "needs_yellow": _bool("needs_yellow"),
        "needs_simple_channel": _bool("needs_simple_channel"),
        "needs_multiparty": _bool("needs_multiparty"),
        "needs_versioned": _bool("needs_versioned"),
        "needs_tip": _bool("needs_tip"),
        "needs_deposit": _bool("needs_deposit"),
    }

async def generate_architecture(prompt: str, files: Dict[str, str], research_notes: str = "", doc_context: str = "") -> dict:
    """
    Generate a detailed architectural plan for integration.
    """
    # Placeholder for now - reuses generate_plan logic
    return await generate_plan(prompt, files, doc_context)

def _format_tree_for_prompt(tree: Dict[str, Any], indent: int = 0) -> str:
    """Format file tree structure for LLM prompt."""
    if not tree:
        return ""
    
    lines = []
    prefix = "  " * indent
    name = tree.get("name", "")
    node_type = tree.get("type", "")
    
    if node_type == "folder":
        lines.append(f"{prefix}📁 {name}/")
        for child in tree.get("children", []):
            lines.append(_format_tree_for_prompt(child, indent + 1))
    else:
        lines.append(f"{prefix}📄 {name}")
    
    return "\n".join(lines)

async def create_doc_retrieval_checklist(
    prompt: str,
    plan_notes: str,
    yellow_requirements: Dict[str, bool],
    sdk_version: str,
    tree: Dict[str, Any],
    existing_docs: str = ""
) -> Dict[str, Any]:
    """
    Create a checklist of documentation that needs to be retrieved based on the architect's plan.
    Does NOT use code - only uses plan, requirements, and tree structure.
    """
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set. Cannot create checklist.")

    try:
        from agent.llm.utils import get_llm
    except Exception as e:
        raise RuntimeError(f"Failed to import required LLM libraries: {e}")

    # Format tree structure
    tree_str = _format_tree_for_prompt(tree) if tree else "No tree structure available"
    
    # Format yellow requirements
    reqs_str = "\n".join([
        f"- {key}: {value}" 
        for key, value in yellow_requirements.items()
    ])
    
    messages = prompts.build_doc_checklist_prompt(
        prompt,
        plan_notes,
        reqs_str,
        sdk_version,
        tree_str,
        existing_docs
    )

    llm = get_llm(temperature=0.2, max_tokens=2048)

    resp = await llm.ainvoke(messages)
    content = extract_text_from_content(getattr(resp, "content", ""))
    obj = extract_json_from_response(content)
    
    if not obj:
        # Fallback: create basic checklist from requirements
        checklist = []
        if yellow_requirements.get("needs_yellow"):
            checklist.append("Yellow SDK initialization and setup")
        if yellow_requirements.get("needs_simple_channel"):
            checklist.append("Simple channel creation and management")
        if yellow_requirements.get("needs_multiparty"):
            checklist.append("Multiparty channel operations")
        if yellow_requirements.get("needs_versioned"):
            checklist.append("Versioned state channels")
        if yellow_requirements.get("needs_tip"):
            checklist.append("Tipping functionality")
        if yellow_requirements.get("needs_deposit"):
            checklist.append("Deposit operations")
        
        return {
            "checklist": checklist,
            "reasoning": "Fallback checklist based on requirements"
        }
    
    return obj

async def review_and_correct_plan(
    prompt: str,
    plan_notes: str,
    yellow_requirements: Dict[str, bool],
    sdk_version: str,
    doc_context: str,
    tree: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Review the architect's plan against retrieved documentation.
    Identify issues and correct the plan and requirements.
    """
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set. Cannot review plan.")

    try:
        from agent.llm.utils import get_llm
    except Exception as e:
        raise RuntimeError(f"Failed to import required LLM libraries: {e}")

    # Format tree structure
    tree_str = _format_tree_for_prompt(tree) if tree else "No tree structure available"
    
    # Format yellow requirements
    reqs_str = "\n".join([
        f"- {key}: {value}" 
        for key, value in yellow_requirements.items()
    ])
    
    messages = prompts.build_plan_correction_prompt(
        prompt,
        plan_notes,
        reqs_str,
        sdk_version,
        doc_context,
        tree_str
    )

    llm = get_llm(temperature=0.2, max_tokens=4096)

    resp = await llm.ainvoke(messages)
    content = extract_text_from_content(getattr(resp, "content", ""))
    obj = extract_json_from_response(content)
    
    if not obj:
        return {
            "plan_corrected": False,
            "corrections": [],
            "reasoning": "Could not review plan"
        }
    
    return obj
