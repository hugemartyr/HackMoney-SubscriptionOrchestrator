from __future__ import annotations

from typing import Dict

from config import settings
from agent import prompts
from agent.llm.utils import extract_text_from_content, extract_json_from_response

async def generate_plan(prompt: str, files: Dict[str, str]) -> dict:
    """
    If GOOGLE_API_KEY is set and langchain-google-genai is installed, ask Gemini
    for a short notes markdown + recommended @yellow-network/sdk version.

    Returns dict like:
      {"notes_markdown": "...", "yellow_sdk_version": "^x.y.z"}
    """
    if not settings.GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is not set. Cannot generate plan without LLM.")

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
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

    # Use single model from config
    llm = ChatGoogleGenerativeAI(
        model=settings.GOOGLE_MODEL,
        api_key=settings.GOOGLE_API_KEY,
        temperature=0.2,
        max_tokens=(8192*2),
        disable_streaming=True,
    )

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
    
    return {"notes_markdown": notes, "yellow_sdk_version": version}

async def generate_architecture(prompt: str, files: Dict[str, str], research_notes: str = "") -> dict:
    """
    Generate a detailed architectural plan for integration.
    """
    # Placeholder for now - reuses generate_plan logic
    return await generate_plan(prompt, files)
