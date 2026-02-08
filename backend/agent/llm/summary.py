from __future__ import annotations

from typing import List, Dict, Any

from config import settings
from agent import prompts
from agent.llm.utils import extract_text_from_content

async def generate_summary(
    thinking_log: List[str], 
    diffs: List[Dict[str, str]], 
    build_success: bool, 
    error_count: int
) -> str:
    """
    Generate a Cursor-style final summary of actions taken using LLM.
    """
    # Fallback template
    def template_summary() -> str:
        status = "✅ Success" if build_success else "❌ Failed"
        files_changed = len(diffs)
        
        summary = f"""# Integration Summary

**Status:** {status}
**Files Changed:** {files_changed}
**Errors Encountered:** {error_count}

## Changes Applied
"""
        
        for diff in diffs:
            file = diff.get("file", "unknown")
            summary += f"- Modified `{file}`\n"
            
        summary += "\n## Next Steps\n"
        if build_success:
            summary += "- Verify the application functionality\n- Check the Yellow Network dashboard\n"
        else:
            summary += "- Review build errors\n- Check logs for details\n"
            
        return summary
    
    if not settings.OPENROUTER_API_KEY:
        return template_summary()
    
    try:
        from agent.llm.utils import get_llm
    except Exception:
        return template_summary()
    
    messages = prompts.build_summary_prompt(thinking_log, diffs, build_success, error_count)
    
    llm = get_llm(temperature=0.3, max_tokens=2048)
    
    resp = await llm.ainvoke(messages)
    content = extract_text_from_content(getattr(resp, "content", ""))
    
    # LLM should return markdown directly, not JSON
    return content.strip() if content else template_summary()
