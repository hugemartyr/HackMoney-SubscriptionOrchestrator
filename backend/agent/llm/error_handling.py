from __future__ import annotations

from typing import Dict, Any, List
from agent.state import Diff

from config import settings
from agent import prompts
from agent.llm.utils import extract_text_from_content, extract_json_from_response

async def generate_fix_plan(
    error_analysis: Dict[str, Any], 
    files: Dict[str, str], 
    prompt: str, 
    doc_context: str = ""
) -> List[Diff]:
    """
    Generate a plan to fix errors using LLM.
    """
    if not settings.OPENROUTER_API_KEY:
        return []
    
    try:
        from agent.llm.utils import get_llm
    except Exception:
        return []
    
    # Prepare file context
    file_context_parts = []
    files_to_fix = error_analysis.get("files_to_fix", [])
    
    # Include files mentioned in error analysis
    for file_path in files_to_fix:
        if file_path in files:
            content = files[file_path]
            # Limit content size to avoid huge prompts
            snippet = content[:2000] if len(content) > 2000 else content
            if len(content) > 2000:
                snippet += "\n... (truncated)"
            file_context_parts.append(f"--- {file_path} ---\n{snippet}\n")
    
    # Also include a few other relevant files for context
    for path, content in list(files.items())[:5]:
        if path not in files_to_fix:
            snippet = content[:1000] if len(content) > 1000 else content
            if len(content) > 1000:
                snippet += "\n... (truncated)"
            file_context_parts.append(f"--- {path} ---\n{snippet}\n")
    
    file_context = "\n".join(file_context_parts)
    
    # Build prompt
    messages = prompts.build_fix_plan_prompt(error_analysis, file_context)
    
    llm = get_llm(temperature=0.1, max_tokens=8192)
    
    resp = await llm.ainvoke(messages)
    content = extract_text_from_content(getattr(resp, "content", ""))
    obj = extract_json_from_response(content)
    
    if not obj or "diffs" not in obj:
        return []
    
    # Convert to Diff format
    diffs = []
    for diff_data in obj["diffs"]:
        if all(k in diff_data for k in ["file", "oldCode", "newCode"]):
            diffs.append({
                "file": diff_data["file"],
                "oldCode": diff_data["oldCode"],
                "newCode": diff_data["newCode"]
            })
    
    return diffs

async def escalate_issue(
    error_context: str, 
    attempted_fixes: List[str], 
    build_output: str = ""
) -> str:
    """
    Generate escalation message for human intervention using LLM.
    """
    if not settings.OPENROUTER_API_KEY:
        return "Issue escalated to human review due to persistent errors."
    
    try:
        from agent.llm.utils import get_llm
    except Exception:
        return "Issue escalated to human review due to persistent errors."
    
    messages = prompts.build_escalation_prompt(error_context, attempted_fixes)
    
    llm = get_llm(temperature=0.2, max_tokens=1024)
    
    resp = await llm.ainvoke(messages)
    content = extract_text_from_content(getattr(resp, "content", ""))
    obj = extract_json_from_response(content)
    
    if obj and "message" in obj:
        return obj["message"]
    
    return "Issue escalated to human review due to persistent errors."
