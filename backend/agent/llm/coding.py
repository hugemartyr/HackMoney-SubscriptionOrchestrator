from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from config import settings
from agent.state import Diff
from agent import prompts
from agent.llm.utils import extract_text_from_content, extract_json_from_response

async def propose_code_changes(
    prompt: str, files: Dict[str, str], plan_notes: str, sdk_version: str, rag_context: str
) -> List[Diff]:
    """
    Use LLM to propose code changes for integrating Yellow Network SDK.
    Uses efficient Search/Replace blocks to save tokens and improve reliability.
    Returns standard Diff objects (hydrated with full old/new content) for frontend compatibility.
    """
    if not settings.GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is not set. Cannot propose code changes without LLM.")

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except Exception as e:
        raise RuntimeError(f"Failed to import required LLM libraries: {e}")

    # Prepare file context
    file_contexts: list[str] = []
    key_files = ["package.json", "package-lock.json", "src/main.ts", "src/index.ts", "app/page.tsx", "main.py", "routes.py"]
    
    for path in sorted(files.keys()):
        content = files.get(path, "")
        if not content:
            continue
        
        # Include full content for key files, snippets for others if too large
        # With Search/Replace, we need to be careful about snippets, but 
        # usually providing enough context is fine. 
        # Ideally, we should provide full files to ensure the LLM sees everything it needs to match.
        # For very large files, this might still be an issue, but let's stick to the existing logic for now.
        if any(key in path for key in key_files) or len(content) < 5000: # Increased limit slightly
            file_contexts.append(f"--- {path} ---\n{content}\n")
        else:
            snippet = content[:5000] + ("\n... (truncated)" if len(content) > 5000 else "")
            file_contexts.append(f"--- {path} ---\n{snippet}\n")
    
    context = "\n".join(file_contexts)

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
    else:
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
        max_tokens=(8192 * 2),
        disable_streaming=True,
    )

    resp = await llm.ainvoke(messages)
    raw_content = getattr(resp, "content", "") or ""
    content = extract_text_from_content(raw_content)
    
    # Try extraction
    obj = extract_json_from_response(content)
    
    if not obj:
        # Try one more time with content stripped of leading/trailing whitespace
        content_stripped = content.strip()
        if content_stripped != content:
            obj = extract_json_from_response(content_stripped)
    
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
            import re
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
        
        raise RuntimeError(error_msg)

    # Support both new "changes" list (search/replace) and legacy "diffs" list
    changes_list = obj.get("changes")
    diffs_list = obj.get("diffs")
    
    validated_diffs: List[Diff] = []

    # ---------------------------------------------------------
    # PATH A: Efficient Search/Replace (Preferred)
    # ---------------------------------------------------------
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
            
        # 2. Process each file
        for file_path, file_changes in changes_by_file.items():
            # Get original content
            original_content = files.get(file_path, "")
            
            # Use a buffer for sequential edits
            # If original_content is empty, we assume creation (start with empty buffer)
            current_content = original_content
            
            changes_applied = False
            
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
                        print(f"Warning: Search block not found in {file_path}. Skipping hunk.")
                        # Debugging hint: print(f"Search: {repr(search_block)}")
            
            # 3. Generate Diff Object
            # If changes were applied and result is different
            if changes_applied and current_content != original_content:
                # Handle Deletion: if current_content is empty string, we treat it as deleted?
                # The Diff object will show newCode="" which frontend might treat as empty file.
                validated_diffs.append({
                    "file": file_path,
                    "oldCode": original_content,
                    "newCode": current_content
                })

    # ---------------------------------------------------------
    # PATH B: Legacy Full-File Diffs (Fallback)
    # ---------------------------------------------------------
    elif diffs_list and isinstance(diffs_list, list):
        for d in diffs_list:
            if not isinstance(d, dict): continue
            file_path = d.get("file")
            old_code = d.get("oldCode", "")
            new_code = d.get("newCode", "")
            
            if not file_path or old_code == new_code:
                continue
            
            validated_diffs.append({
                "file": file_path,
                "oldCode": old_code,
                "newCode": new_code,
            })
    
    return validated_diffs

async def write_code(prompt: str, files: Dict[str, str], plan_notes: str, sdk_version: str, rag_context: str) -> List[Diff]:
    """
    Write code implementation. Alias for propose_code_changes.
    """
    return await propose_code_changes(prompt, files, plan_notes, sdk_version, rag_context)
