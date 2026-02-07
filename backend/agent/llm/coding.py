from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, cast
import json
import re

from config import settings
from agent.state import Diff
from agent import prompts
from agent.llm.utils import extract_text_from_content, extract_json_from_response
from logging import getLogger

logger = getLogger(__name__)

async def propose_code_changes(
    prompt: str, files: Dict[str, str], plan_notes: str, sdk_version: str, rag_context: str, tool_diffs: List[Diff]
) -> List[Diff]:
    """
    Use LLM to propose code changes for integrating Yellow Network SDK.
    Uses efficient Search/Replace blocks to save tokens and improve reliability.
    Returns standard Diff objects (hydrated with full old/new content) for frontend compatibility.
    """

    # High-level call overview (full prompt + plan, but summarized file info)
    # Effective files: repo files + tool-proposed content (tool newCode overrides for those paths)
    effective_files: Dict[str, str] = dict(files or {})
    for d in tool_diffs or []:
        path = d.get("file")
        if path and "newCode" in d:
            effective_files[path] = d.get("newCode", "")

    logger.info(
        "propose_code_changes called",
        extra={
            "user_prompt": prompt,
            "plan_notes": plan_notes,
            "sdk_version": sdk_version,
            "rag_context_len": len(rag_context or ""),
            "file_count": len(files or {}),
            "tool_diff_count": len(tool_diffs or []),
            "effective_file_count": len(effective_files),
        },
    )

    # Per-file summary with truncated content preview so logs stay readable (effective = files + tool_diffs)
    for path, content in effective_files.items():
        if content is None:
            content = ""
        preview = content[:400]
        if len(content) > 400:
            preview += "... [truncated]"
        logger.info(
            "propose_code_changes input file",
            extra={
                "file_path": path,
                "content_len": len(content),
                "content_preview": preview,
            },
        )

    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set. Cannot propose code changes without LLM.")

    try:
        from agent.llm.utils import get_llm
    except Exception as e:
        raise RuntimeError(f"Failed to import required LLM libraries: {e}")

    # Prepare file context from effective files (repo + tool-proposed content so LLM sees full picture)
    file_contexts: list[str] = []
    key_files = ["package.json", "package-lock.json", "src/main.ts", "src/index.ts", "app/page.tsx", "main.py", "routes.py"]

    for path in sorted(effective_files.keys()):
        content = effective_files.get(path, "")
        if content is None:
            content = ""
        # Include full content for key files, snippets for others if too large
        if any(key in path for key in key_files) or len(content) < 5000:
            file_contexts.append(f"--- {path} ---\n{content}\n")
        else:
            snippet = content[:5000] + ("\n... (truncated)" if len(content) > 5000 else "")
            file_contexts.append(f"--- {path} ---\n{snippet}\n")
    context = "\n".join(file_contexts)

    logger.info(
        "propose_code_changes file context prepared",
        extra={
            "file_context_len": len(context),
            "file_context_file_count": len(file_contexts),
        },
    )

    # Load "The Constitution"
    # Assuming code runs from backend/ or root. Try both.
    rules_path = Path("docs/yellow_integration_rules.md")
    if not rules_path.exists():
        rules_path = Path("../docs/yellow_integration_rules.md")
    if not rules_path.exists():
         # Fallback to backend/docs relative to this file
         base_dir = Path(__file__).resolve().parent.parent.parent
         rules_path = base_dir / "docs" / "yellow_integration_rules.md"
    
    rules_text = ""
    if rules_path.exists():
        rules_text = rules_path.read_text()
        logger.info(
            "Loaded integration rules for coder",
            extra={"rules_path": str(rules_path), "rules_len": len(rules_text or "")},
        )
    else:
        rules_text = "No specific rules provided."
        logger.info("No integration rules file found for coder", extra={"rules_path": str(rules_path)})

    messages = prompts.build_coder_prompt(
        user_query=prompt,
        plan=plan_notes,
        rules=rules_text,
        rag_context=rag_context,
        file_context=context,
        sdk_version=sdk_version,
        tool_diffs=tool_diffs,
    )

    # Log the full logical prompt we send to the LLM (system + human)
    try:
        serialised_messages = []
        for m in messages:
            role = getattr(m, "type", m.__class__.__name__)
            content = getattr(m, "content", "")
            serialised_messages.append(
                {
                    "role": role,
                    "content": content,
                }
            )
        logger.info(
            "Coder LLM prompt messages",
            extra={
                "prompt_messages": serialised_messages,
                "message_count": len(serialised_messages),
            },
        )
    except Exception as e:
        logger.info("Failed to serialise coder prompt messages", extra={"error": str(e)})

    # Use OpenRouter model from config (e.g. Claude Sonnet)
    llm = get_llm(
        temperature=0.2,
        max_tokens=(8192 * 2),
    )

    logger.info(
        "Invoking coder LLM",
        extra={
            "model": settings.OPENROUTER_MODEL,
            "temperature": 0.2,
        },
    )

    resp = await llm.ainvoke(messages)
    raw_content = getattr(resp, "content", "") or ""

    # Log only a concise preview of the raw response (avoid huge blobs / signatures)
    raw_str = str(raw_content)
    raw_preview = raw_str[:800] + ("... [truncated]" if len(raw_str) > 800 else "")
    logger.info(
        "Coder LLM raw response preview",
        extra={
            "response_type": type(resp).__name__,
            "raw_len": len(raw_str),
            "raw_preview": raw_preview,
        },
    )

    content = extract_text_from_content(raw_content)
    content_preview = content[:800] + ("... [truncated]" if len(content) > 800 else "")
    logger.info(
        "Coder LLM extracted text content",
        extra={
            "content_len": len(content or ""),
            "content_preview": content_preview,
        },
    )

    # Try robust JSON extraction, preferring a fenced ```json block when present
    obj = None

    # 1) Fast path: explicit ```json ... ``` block
    if "```" in content:
        fence_match = re.search(r"```json\s*([\s\S]*?)\s*```", content, flags=re.IGNORECASE)
        if not fence_match:
            # Fallback: any fenced block
            fence_match = re.search(r"```\s*([\s\S]*?)\s*```", content, flags=re.IGNORECASE)
        if fence_match:
            json_candidate = fence_match.group(1).strip()
            # Use robust extractor on the fenced JSON, to handle any truncation
            obj = extract_json_from_response(json_candidate) or None

    # 2) Fallback to generic extractor if fast path failed
    if obj is None:
        obj = extract_json_from_response(content)

    logger.info(
        "Coder LLM JSON extraction result (first pass)",
        extra={
            "has_obj": bool(obj),
            "obj_keys": list(obj.keys()) if isinstance(obj, dict) else None,
        },
    )
    
    if not obj:
        # Try one more time with content stripped of leading/trailing whitespace
        content_stripped = content.strip()
        if content_stripped != content:
            # Try fast path again on stripped content
            if "```" in content_stripped and obj is None:
                fence_match = re.search(r"```json\s*([\s\S]*?)\s*```", content_stripped, flags=re.IGNORECASE)
                if not fence_match:
                    fence_match = re.search(r"```\s*([\s\S]*?)\s*```", content_stripped, flags=re.IGNORECASE)
                if fence_match:
                    json_candidate = fence_match.group(1).strip()
                    try:
                        obj = json.loads(json_candidate)
                    except Exception:
                        obj = None

            if obj is None:
                obj = extract_json_from_response(content_stripped)

            logger.info(
                "Coder LLM JSON extraction result (second pass, stripped)",
                extra={
                    "has_obj": bool(obj),
                    "obj_keys": list(obj.keys()) if isinstance(obj, dict) else None,
                },
            )

    if not obj:
        # Include more context for debugging
        content_len = len(content)
        preview_start = content[:500] if content_len > 500 else content
        preview_end = content[-500:] if content_len > 1000 else ""
        
        # Check if it looks like a code block
        has_code_block = "```" in content
        code_block_info = ""
        if has_code_block:
            # Try to extract what's between code blocks
            code_match = re.search(r"```(?:json)?\s*([\s\S]*?)(?:\s*```|$)", content, re.IGNORECASE | re.DOTALL)
            if code_match:
                code_content = code_match.group(1).strip()
                code_block_info = f"\nCode block content length: {len(code_content)} chars"
                if code_content.startswith("{"):
                    code_block_info += " (starts with {)"

        error_msg = (
            f"Failed to generate code changes. No valid JSON response.\n"
            f"Response length: {content_len} characters"
        )
        if has_code_block:
            error_msg += " (contains code block)"
        error_msg += code_block_info
        error_msg += f"\nPreview (start): {preview_start!r}"
        if preview_end:
            error_msg += f"\nPreview (end): {preview_end!r}"
        
        # Check if content looks truncated
        if content_len > 15000:  # Close to max_tokens limit
            error_msg += "\nNote: Response may be truncated. Consider increasing max_tokens or simplifying the request."

        logger.info(
            "Coder LLM JSON extraction failed",
            extra={
                "content_len": content_len,
                "has_code_block": has_code_block,
                "error_preview_start": preview_start,
                "error_preview_end": preview_end,
            },
        )

        raise RuntimeError(error_msg)

    # Support both new "changes" list (search/replace) and legacy "diffs" list
    changes_list = obj.get("changes")
    diffs_list = obj.get("diffs")

    logger.info(
        "Coder JSON parsed top-level",
        extra={
            "has_changes": bool(changes_list),
            "changes_count": len(changes_list) if isinstance(changes_list, list) else None,
            "has_diffs": bool(diffs_list),
            "diffs_count": len(diffs_list) if isinstance(diffs_list, list) else None,
        },
    )
    
    validated_diffs: List[Diff] = []

    if changes_list and isinstance(changes_list, list):
        # 1. Group changes by file to handle multi-hunk edits
        changes_by_file: Dict[str, List[Dict]] = {}
        for change in changes_list:
            if not isinstance(change, dict): continue
            file_path = change.get("file")
            if not file_path: continue
            
            if file_path not in changes_by_file:
                changes_by_file[file_path] = []
            changes_by_file[file_path].append(change)

        logger.info(
            "Processing search/replace changes",
            extra={
                "file_count": len(changes_by_file),
                "files": list(changes_by_file.keys()),
            },
        )
            
        # 2. Process each file (allow any file in effective set: repo files + tool-proposed)
        for file_path, file_changes in changes_by_file.items():
            if file_path not in effective_files:
                logger.info(
                    "Skipping search/replace changes for unknown file",
                    extra={"file_path": file_path},
                )
                continue

            # Get original content from effective (tool proposals already applied)
            original_content = effective_files.get(file_path, "")
            # Use a buffer for sequential edits
            # If original_content is empty, we assume creation (start with empty buffer)
            current_content = original_content
            
            changes_applied = False
            
            logger.info(
                "Applying changes for file",
                extra={
                    "file_path": file_path,
                    "original_len": len(original_content or ""),
                    "change_count": len(file_changes),
                },
            )

            for change in file_changes:
                search_block = change.get("search")
                replace_block = change.get("replace")
                
                # Validation
                if replace_block is None: 
                    # Default to empty string if missing (deletion safety)
                    replace_block = ""
                
                # Logic:
                # 1. Creation: search is None/Empty -> replace is content
                # 2. Edit: search is found -> replace
                # 3. Deletion: replace is Empty (and search matches) -> content becomes empty or removed
                
                if not search_block:
                    # Case 1: Creation / Overwrite
                    # If we have existing content, we might be overwriting it entirely? 
                    # Usually "creation" implies new file. 
                    # Let's assume overwrite if search is explicitly null/empty.
                    current_content = replace_block
                    changes_applied = True
                else:
                    # Case 2: Edit
                    if search_block in current_content:
                        # Replace only the first occurrence to avoid mass-replacing common patterns
                        # unless prompt specifically said otherwise (but prompt said "unique").
                        current_content = current_content.replace(search_block, replace_block, 1)
                        changes_applied = True
                    else:
                        # Robustness: Try stripping whitespace/normalizing?
                        # For now, strict match. If fail, log/skip.
                        logger.info(
                            "Search block not found in file; skipping change",
                            extra={
                                "file_path": file_path,
                                "search_len": len(search_block or ""),
                            },
                        )
            
            # 3. Generate Diff Object
            # If changes were applied and result is different
            if changes_applied and current_content != original_content:
                # Handle Deletion: if current_content is empty string, we treat it as deleted?
                # The Diff object will show newCode="" which frontend might treat as empty file.
                logger.info(
                    "File changes applied",
                    extra={
                        "file_path": file_path,
                        "original_len": len(original_content or ""),
                        "new_len": len(current_content or ""),
                    },
                )
                validated_diffs.append({
                    "file": file_path,
                    "oldCode": original_content,
                    "newCode": current_content
                })

    elif diffs_list and isinstance(diffs_list, list):
        logger.info(
            "Processing legacy full-file diffs",
            extra={
                "diff_count": len(diffs_list),
            },
        )
        for d in diffs_list:
            if not isinstance(d, dict): continue
            file_path = d.get("file")
            old_code = d.get("oldCode", "")
            new_code = d.get("newCode", "")
            
            if not file_path or old_code == new_code:
                continue

            # Enforce: only accept diffs for files in effective set (repo + tool-proposed)
            if file_path not in effective_files:
                logger.info(
                    "Skipping legacy diff for unknown file",
                    extra={"file_path": file_path},
                )
                continue

            logger.info(
                "Legacy diff entry accepted",
                extra={
                    "file_path": file_path,
                    "old_len": len(old_code or ""),
                    "new_len": len(new_code or ""),
                },
            )

            validated_diffs.append({
                "file": file_path,
                "oldCode": old_code,
                "newCode": new_code,
            })

    logger.info(
        "propose_code_changes completed",
        extra={
            "validated_diff_count": len(validated_diffs),
            "validated_diff_files": [d.get("file") for d in validated_diffs],
        },
    )

    return validated_diffs

async def write_code(prompt: str, files: Dict[str, str], plan_notes: str, sdk_version: str, rag_context: str, tool_diffs: List[Diff]) -> List[Diff]:
    """
    Write code implementation. Alias for propose_code_changes.
    """
    return await propose_code_changes(prompt, files, plan_notes, sdk_version, rag_context, tool_diffs)
