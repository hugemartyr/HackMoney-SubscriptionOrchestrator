from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional
import json

from config import settings
from agent.state import Diff
from agent import prompts
from agent.llm.utils import extract_text_from_content, get_llm
from logging import getLogger

logger = getLogger(__name__)


def _extract_json_from_text(text: str) -> Optional[str]:
    """
    Extract the first complete JSON object (between braces) from text.
    Uses simple brace counting; respects strings so braces inside strings are ignored.
    """
    if not text:
        return None
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    quote_char = None
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\" and in_string:
            escape = True
            continue
        if not in_string:
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
            elif c in ("\"", "'"):
                in_string = True
                quote_char = c
            continue
        if c == quote_char:
            in_string = False
    return None


def _parse_coder_json_response(content: str) -> Optional[dict]:
    """
    Parse LLM response into one JSON object.
    Step 1: strip. Step 2: if ``` present, take content between first and second ```; else extract first { }.
    Step 3: json.loads.
    """
    if not content:
        logger.info("parse_coder_json: empty content")
        return None
    s = content.strip()
    logger.info("parse_coder_json: step 1 stripped len=%s", len(s))

    json_str = None
    if "```" in s:
        i = s.find("```")
        j = s.find("```", i + 3)
        if j != -1:
            block = s[i + 3 : j].strip()
            if block.lower().startswith("json"):
                block = block[4:].lstrip()
            if block.startswith("{"):
                json_str = block
                logger.info("parse_coder_json: step 2 fenced block len=%s", len(json_str))
    if json_str is None:
        json_str = _extract_json_from_text(s)
        if json_str:
            logger.info("parse_coder_json: step 2 brace-extract len=%s", len(json_str))
        else:
            logger.info("parse_coder_json: step 2 no JSON block")

    if not json_str:
        return None
    try:
        obj = json.loads(json_str)
        logger.info("parse_coder_json: step 3 json.loads ok keys=%s", list(obj.keys()) if isinstance(obj, dict) else [])
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError as e:
        logger.info("parse_coder_json: step 3 json.loads failed err=%s", str(e))
        return None


def _build_file_context(files: Dict[str, str], max_per_file: int = 8000) -> str:
    """Build prompt file context: --- path ---\\ncontent for each file. Truncate very large files."""
    parts = []
    for path in sorted(files.keys()):
        content = files.get(path) or ""
        if len(content) > max_per_file:
            content = content[:max_per_file] + "\n... [truncated]"
        parts.append(f"--- {path} ---\n{content}\n")
    return "\n".join(parts)


def _diffs_from_llm_response(obj: dict) -> List[Diff]:
    """
    Build list of Diff from parsed LLM JSON. Expects obj["diffs"] = [ { "file", "oldCode", "newCode" }, ... ].
    Accepts oldCode/newCode or old_code/new_code; coerces to str; skips when oldCode == newCode.
    """
    out: List[Diff] = []
    diffs_list = obj.get("diffs")
    if not isinstance(diffs_list, list):
        return out
    for d in diffs_list:
        if not isinstance(d, dict):
            continue
        file_path = d.get("file")
        if not file_path:
            continue
        old_code = d.get("oldCode") or d.get("old_code") or ""
        new_code = d.get("newCode") or d.get("new_code") or ""
        old_code = str(old_code)
        new_code = str(new_code)
        if old_code == new_code:
            continue
        out.append({"file": file_path, "oldCode": old_code, "newCode": new_code})
    return out


async def propose_code_changes(
    prompt: str,
    files: Dict[str, str],
    plan_notes: str,
    sdk_version: str,
    rag_context: str,
    tool_diffs: List[Diff],
) -> List[Diff]:
    """
    Invoke LLM with coder prompt (plan, rag, file context, tool_diffs), parse response JSON,
    and return list of Diff from obj["diffs"].
    """
    # Effective files: repo files + tool-proposed newCode per file
    effective_files: Dict[str, str] = dict(files or {})
    for d in tool_diffs or []:
        path = d.get("file")
        if path and "newCode" in d:
            effective_files[path] = d.get("newCode", "")

    file_context = _build_file_context(effective_files)
    messages = prompts.build_coder_prompt(
        user_query=prompt,
        plan=plan_notes,
        rag_context=rag_context or "",
        file_context=file_context,
        sdk_version=sdk_version or "latest",
        tool_diffs=tool_diffs or [],
    )

    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set. Cannot propose code changes.")

    llm = get_llm(temperature=0.2, max_tokens=8192 * 2)
    logger.info("Invoking coder LLM", extra={"model": settings.OPENROUTER_MODEL})

    response = await llm.ainvoke(messages)
    raw_content = getattr(response, "content", "") or ""
    content = extract_text_from_content(raw_content)
    logger.info(
        "Coder LLM response received",
        extra={"content_len": len(content or ""), "raw_type": type(raw_content).__name__},
    )

    obj = _parse_coder_json_response(content)
    if obj is None:
        logger.warning("propose_code_changes: no valid JSON from LLM")
        return []

    valid_diffs = _diffs_from_llm_response(obj)
    logger.info("propose_code_changes: parsed %s diffs", len(valid_diffs), extra={"files": [d["file"] for d in valid_diffs]})
    return valid_diffs


async def write_code(
    prompt: str,
    files: Dict[str, str],
    plan_notes: str,
    sdk_version: str,
    rag_context: str,
    tool_diffs: List[Diff],
) -> List[Diff]:
    """Alias for propose_code_changes."""
    return await propose_code_changes(prompt, files, plan_notes, sdk_version, rag_context, tool_diffs)
