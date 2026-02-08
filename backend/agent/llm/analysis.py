from __future__ import annotations

from typing import Dict, Any, List, Optional

from config import settings
from agent import prompts
from agent.llm.utils import extract_text_from_content, extract_json_from_response

async def analyze_context(prompt: str, files: Dict[str, str], memory: List[str], tree: Optional[Dict[str, Any]] = None, doc_context: str = "") -> Dict[str, Any]:
    """
    Analyze if we have enough context to proceed.
    Decides between: 'ready', 'missing_code', 'missing_docs', 'need_research'.
    """
    if not settings.OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set.")

    try:
        from agent.llm.utils import get_llm
    except Exception as e:
        raise RuntimeError(f"Failed to import required LLM libraries: {e}")

    # Prepare file context snippet
    context_parts = []
    file_list = list(files.keys())
    
    # Add file tree structure if available (especially useful when files is empty)
    if tree:
        tree_str = _format_tree_for_prompt(tree)
        context_parts.append(f"File Tree Structure:\n{tree_str}\n")
    
    # Add file list summary
    if file_list:
        context_parts.append(f"Available Files: {', '.join(file_list)}\n")
    
    # Add snippets for files to give LLM context
    # Limit to avoid huge prompts, but ensure we show content
    for path in sorted(files.keys()):
        content = files.get(path, "")
        # clear any large binary or lock files from view if they accidentally got in
        if "lock" in path or len(content) > 100000: 
            continue
            
        snippet = content[:2000] # 2KB limit per file for decision making
        if len(content) > 2000:
            snippet += "\n... (truncated)"
        context_parts.append(f"--- {path} ---\n{snippet}\n")
        
        # Soft limit to prevent context window explosion
        if len(context_parts) > 10: 
            context_parts.append("... (more files available)")
            break
            
    file_context_str = "\n".join(context_parts) if context_parts else "No files loaded yet."
    
    # Add doc context info if available
    if doc_context and len(doc_context.strip()) > 0:
        doc_preview = doc_context[:500] if len(doc_context) > 500 else doc_context
        context_parts.append(f"\n=== Documentation Retrieved ===\n{doc_preview}...\n(Total: {len(doc_context)} characters)")
    
    file_context_str = "\n".join(context_parts) if context_parts else "No files loaded yet."
    
    # REMOVED: Early return when files is empty - now LLM can use tree to decide
    # Always call LLM to make informed decision about which files to read

    messages = prompts.build_context_check_prompt(prompt, file_context_str, memory)

    llm = get_llm(temperature=0.1, max_tokens=1024)

    resp = await llm.ainvoke(messages)
    content = extract_text_from_content(getattr(resp, "content", ""))
    obj = extract_json_from_response(content)

    if not obj:
        # Default to ready if LLM fails to structure response, 
        # or research if we are unsure.
        return {"status": "ready", "missing_info": []}

    return obj

async def analyze_imports(files: Dict[str, str]) -> Dict[str, Any]:
    """
    Analyze imports and dependencies to understand the tech stack.
    """
    if not settings.OPENROUTER_API_KEY:
        return {"imports": [], "dependencies": []}

    try:
        from agent.llm.utils import get_llm
    except Exception:
        return {"imports": [], "dependencies": []}

    # Focus on package management files
    relevant_files = ["package.json", "requirements.txt", "pyproject.toml", "go.mod"]
    context_parts = []
    
    for fname in relevant_files:
        if fname in files:
            context_parts.append(f"--- {fname} ---\n{files[fname]}")
            
    # Also grab imports from main source files (first 50 lines)
    for fname, content in files.items():
        if fname.endswith((".ts", ".tsx", ".js", ".py", ".go")) and fname not in relevant_files:
            snippet = "\n".join(content.splitlines()[:50])
            context_parts.append(f"--- {fname} (imports) ---\n{snippet}")
            if len(context_parts) > 5: break # Limit context

    if not context_parts:
        return {"imports": [], "dependencies": [], "yellow_sdk_present": False}

    context = "\n".join(context_parts)
    messages = prompts.build_import_analysis_prompt(context)

    llm = get_llm(temperature=0.1, max_tokens=1024)

    resp = await llm.ainvoke(messages)
    content = extract_text_from_content(getattr(resp, "content", ""))
    obj = extract_json_from_response(content)
    
    return obj or {"imports": [], "dependencies": [], "yellow_sdk_present": False}

async def conduct_research(query: str, files: Dict[str, str], docs_context: str) -> Dict[str, Any]:
    """
    Synthesize findings from code + docs.
    """
    if not settings.OPENROUTER_API_KEY:
        return {"findings": "LLM not configured", "next_steps": []}

    try:
        from agent.llm.utils import get_llm
    except Exception:
        return {"findings": "LLM Error", "next_steps": []}

    # Provide snippets of key files
    snippets = []
    for path in sorted(files.keys())[:5]:
        content = files.get(path, "")
        snippet = content[:1000]
        snippets.append(f"--- {path} ---\n{snippet}")
    
    file_context = "\n".join(snippets)
    
    messages = prompts.build_research_prompt(query, file_context, docs_context)

    llm = get_llm(temperature=0.2, max_tokens=2048)

    resp = await llm.ainvoke(messages)
    content = extract_text_from_content(getattr(resp, "content", ""))
    obj = extract_json_from_response(content)
    
    return obj or {"findings": "Could not generate findings", "next_steps": []}

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

async def analyze_errors(build_output: str) -> Dict[str, Any]:
    """
    Analyze build/test errors.
    """
    if not settings.OPENROUTER_API_KEY:
        return {"error_type": "unknown", "fix_suggestion": "Check logs"}

    try:
        from agent.llm.utils import get_llm
    except Exception:
        return {"error_type": "unknown", "fix_suggestion": "Check logs"}

    # Use prompts.build_error_analysis_prompt
    # For now, we assume simple context
    messages = prompts.build_error_analysis_prompt(build_output, "See build output")

    llm = get_llm(temperature=0.1, max_tokens=1024)

    resp = await llm.ainvoke(messages)
    content = extract_text_from_content(getattr(resp, "content", ""))
    obj = extract_json_from_response(content)
    
    return obj or {"error_type": "unknown", "fix_suggestion": "Check logs"}
