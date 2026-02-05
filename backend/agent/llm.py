from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from config import settings
from agent.state import Diff
from agent import prompts

def _extract_text_from_content(content) -> str:
    """
    Extract text from LLM response content which can be:
    - A string
    - A list of strings or dicts like {'type': 'text', 'text': '...'}
    - A dict like {'type': 'text', 'text': '...'}
    """
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict):
                # Extract text from dict content blocks
                text = item.get("text", "") if item.get("type") == "text" else str(item)
                if text:
                    text_parts.append(text)
            else:
                text_parts.append(str(item))
        return "".join(text_parts)
    elif isinstance(content, dict):
        # Single dict content block
        return content.get("text", "") if content.get("type") == "text" else str(content)
    else:
        return str(content)


def extract_json_from_response(text: str) -> Optional[dict]:
    """
    Best-effort: extract the first {...} JSON object from an LLM response.
    """
    if not text:
        return None
    s = text.strip()
    
    # Try parsing the entire string as JSON first
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass

    # Try fenced ```json ... ``` or ``` ... ```
    patterns = [
        r"```(?:json)?\s*(\{[\s\S]*?\})\s*```",  # Standard markdown
        r"```\s*(\{[\s\S]*?\})\s*```",  # Without json label
        r"`\s*(\{[\s\S]*?\})\s*`",  # Single backtick
    ]
    for pattern in patterns:
        m = re.search(pattern, s, flags=re.IGNORECASE | re.DOTALL)
        if m:
            try:
                obj = json.loads(m.group(1).strip())
                return obj if isinstance(obj, dict) else None
            except Exception:
                continue

    # Try to find JSON object by matching braces more carefully
    start = s.find("{")
    if start != -1:
        brace_count = 0
        end = start
        for i in range(start, len(s)):
            if s[i] == "{":
                brace_count += 1
            elif s[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    end = i
                    break
        
        if end > start:
            try:
                json_str = s[start : end + 1]
                obj = json.loads(json_str)
                return obj if isinstance(obj, dict) else None
            except Exception:
                pass
    
    # Last resort: scanning
    for i, char in enumerate(s):
        if char == "{":
            brace_count = 0
            for j in range(i, len(s)):
                if s[j] == "{":
                    brace_count += 1
                elif s[j] == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        try:
                            json_str = s[i : j + 1]
                            obj = json.loads(json_str)
                            return obj if isinstance(obj, dict) else None
                        except Exception:
                            break
            break  # Only try the first opening brace
    
    return None


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
    content = _extract_text_from_content(raw_content)
    
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


async def propose_code_changes(
    prompt: str, files: Dict[str, str], plan_notes: str, sdk_version: str, rag_context: str
) -> List[Diff]:
    """
    Use LLM to propose code changes for integrating Yellow Network SDK.
    Returns a list of Diff objects with file paths and code changes.
    """
    if not settings.GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is not set. Cannot propose code changes without LLM.")

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except Exception as e:
        raise RuntimeError(f"Failed to import required LLM libraries: {e}")

    # Prepare file context - include full content of key files, snippets of others
    file_contexts: list[str] = []
    key_files = ["package.json", "package-lock.json", "src/main.ts", "src/index.ts", "app/page.tsx", "main.py", "routes.py"]
    
    for path in sorted(files.keys()):
        content = files.get(path, "")
        if not content:
            continue
        
        # Include full content for key files, snippets for others
        if any(key in path for key in key_files) or len(content) < 2000:
            file_contexts.append(f"--- {path} ---\n{content}\n")
        else:
            snippet = content[:2000] + ("\n... (truncated)" if len(content) > 2000 else "")
            file_contexts.append(f"--- {path} ---\n{snippet}\n")
    
    context = "\n".join(file_contexts)

    # Load "The Constitution"
    # Assuming code runs from backend/ or root. Try both.
    rules_path = Path("docs/yellow_integration_rules.md")
    if not rules_path.exists():
        rules_path = Path("../docs/yellow_integration_rules.md")
    if not rules_path.exists():
         # Fallback to backend/docs relative to this file
         rules_path = Path(__file__).parent.parent.parent / "docs" / "yellow_integration_rules.md"
    
    rules_text = ""
    if rules_path.exists():
        rules_text = rules_path.read_text()
    else:
        # Graceful fallback if file missing
        rules_text = "No specific rules provided."

    messages = prompts.build_coder_prompt(
        user_query=prompt,
        plan=plan_notes,
        rules=rules_text,
        rag_context=rag_context,
        file_context=context,
        sdk_version=sdk_version
    )

    # Use single model from config
    llm = ChatGoogleGenerativeAI(
        model=settings.GOOGLE_MODEL,
        api_key=settings.GOOGLE_API_KEY,
        temperature=0.2,
        max_tokens=(8192 * 2),  # Larger token limit for code generation
        disable_streaming=True,
    )

    resp = await llm.ainvoke(messages)
    raw_content = getattr(resp, "content", "") or ""
    
    # Extract text from content (handles strings, lists, dicts)
    content = _extract_text_from_content(raw_content)
    
    obj = extract_json_from_response(content)
    if not obj:
        # Include a snippet of the actual response for debugging
        content_snippet = content[:500] if len(content) > 500 else content
        error_msg = (
            f"Failed to generate code changes from LLM. No valid JSON response received.\n"
            f"Response preview (first 500 chars): {content_snippet!r}\n"
            f"Full response length: {len(content)} chars"
        )
        raise RuntimeError(error_msg)

    diffs_list = obj.get("diffs")
    if not isinstance(diffs_list, list):
        raise RuntimeError("Failed to generate code changes from LLM. Invalid response structure.")

    # Validate and convert to Diff format
    validated_diffs: List[Diff] = []
    for d in diffs_list:
        if not isinstance(d, dict):
            continue
        file_path = d.get("file")
        old_code = d.get("oldCode", "")
        new_code = d.get("newCode", "")
        
        if not isinstance(file_path, str) or not file_path:
            continue
        if not isinstance(old_code, str) or not isinstance(new_code, str):
            continue
        
        # Only include if there's an actual change
        if old_code != new_code:
            validated_diffs.append({
                "file": file_path,
                "oldCode": old_code,
                "newCode": new_code,
            })
    
    return validated_diffs
