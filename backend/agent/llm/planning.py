from __future__ import annotations

from typing import Dict

from config import settings
from agent import prompts
from agent.llm.utils import extract_text_from_content, extract_json_from_response

async def generate_plan(prompt: str, files: Dict[str, str]) -> dict:
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
    context = "\n".join(snippets)

    messages = prompts.build_planner_prompt(prompt, context)

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

async def generate_architecture(prompt: str, files: Dict[str, str], research_notes: str = "") -> dict:
    """
    Generate a detailed architectural plan for integration.
    """
    # Placeholder for now - reuses generate_plan logic
    return await generate_plan(prompt, files)
