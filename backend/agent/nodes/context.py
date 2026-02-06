from __future__ import annotations
import asyncio
from agent.state import AgentState
from agent.llm.analysis import analyze_context, analyze_imports, conduct_research
from services.sandbox_fs_service import read_text_file, get_file_tree
from utils.helper_functions import _search_docs_wrapper

async def context_check_node(state: AgentState) -> AgentState:
    """
    Decide if we have enough information (code + docs) to proceed.
    """
    # Increment loop counter
    state["context_loop_count"] = state.get("context_loop_count", 0) + 1
    result = await analyze_context(
        state.get("prompt", ""), 
        state.get("file_contents", {}),
        state.get("session_memory", []),
        state.get("tree")  # Pass tree to analyze_context
    )
    
    status = result.get("status", "ready")
    missing_info = result.get("missing_info", [])
    files_to_read = result.get("files_to_read", []) # Explicit list from LLM
    
    state["context_ready"] = status == "ready"
    state["context_loop_count"] = state.get("context_loop_count", 0) + 1
    state["missing_info"] = missing_info
    state["files_to_read"] = files_to_read # Store in state for read_code_node
    state["docs_retrieved"] = state.get("docs_retrieved", False)
    state["thinking_log"] = state.get("thinking_log", []) + [f"Context Status: {status} (Loop {state.get("context_loop_count", 0)})"]
    return state

async def read_code_node(state: AgentState) -> AgentState:
    """
    Read files from the sandbox.
    """

    current_files = state.get("file_contents", {})
    requested_files = state.get("files_to_read", [])
    files_to_read = []

    if not current_files:
        # Initial scan if completely empty
        try:
            files_to_read = ["package.json", "README.md", "requirements.txt", "src/index.ts", "src/main.ts", "app/page.tsx", "main.py"]
        except Exception:
            files_to_read = []
    elif requested_files:
        # Use explicit list from LLM
        files_to_read = requested_files
    else:
        missing_info = state.get("missing_info", [])
        for item in missing_info:
             if "." in item or "/" in item:
                files_to_read.append(item)

    if not files_to_read and not current_files:
        state["thinking_log"] = state.get("thinking_log", []) + ["No specific files identified to read."]
        return state

    new_contents = current_files.copy()
    read_count = 0
    read_list = []
    
    for path in files_to_read:
        # Avoid re-reading if we have it (unless we want to refresh?)
        if path in new_contents:
            continue
            
        try:
            res = await read_text_file(path)
            new_contents[res["path"]] = res["content"]
            read_count += 1
            read_list.append(res["path"])
        except Exception:
            continue # Skip if not found
    
    log_msg = f"Read {read_count} new files: {', '.join(read_list)}" if read_count > 0 else "No new files found."
    
    state["file_contents"] = new_contents
    state["thinking_log"] = state.get("thinking_log", []) + [log_msg]
    return state

async def analyze_imports_node(state: AgentState) -> AgentState:
    """
    Analyze dependencies to understand the stack.
    """
    result = await analyze_imports(state.get("file_contents", {}))
    
    # Format a summary for memory so analyze_context sees it
    imports_summary = f"Import Analysis: Yellow SDK present: {result.get('yellow_sdk_present')}. "
    imports_summary += f"Dependencies: {', '.join(result.get('dependencies', [])[:5])}..."
    state["imports_analyzed"] = True
    state["analyzed_imports"] = result.get("dependencies", [])
    state["session_memory"] = state.get("session_memory", []) + [imports_summary]
    state["thinking_log"] = state.get("thinking_log", []) + ["Analyzed imports"]
    
    return state

async def retrieve_docs_node(state: AgentState) -> AgentState:
    """
    Retrieve relevant documentation from Vector Store.
    """
    try:
        # Run blocking DB init and search in a separate thread
        docs = await asyncio.to_thread(
            _search_docs_wrapper, 
            state.get("prompt", ""), 
            state.get("missing_info", [])
        )
        state["docs_retrieved"] = True
        state["doc_context"] = docs
        state["thinking_log"] = state.get("thinking_log", []) + ["Retrieved documentation"]
        
        return state
    except Exception as e:
        state["docs_retrieved"] = True # Mark as retrieved to avoid infinite loop, but log error
        state["doc_context"] = f"Error retrieving docs: {e}"
        state["thinking_log"] = state.get("thinking_log", []) + [f"Error retrieving docs: {e}"]
        return state

async def research_node(state: AgentState) -> AgentState:
    """
    Conduct research to answer specific questions.
    """
    result = await conduct_research(
        state.get("prompt", ""),
        state.get("file_contents", {}),
        state.get("doc_context", "")
    )
    
    findings = result.get("findings", "No findings")

    state["thinking_log"] = state.get("thinking_log", []) + [f"Research findings: {findings[:100]}..."]
    # Add findings to memory to progress the context check
    state["session_memory"] = state.get("session_memory", []) + [f"Research: {findings}"]
    return state

async def update_memory_node(state: AgentState) -> AgentState:
    """
    Update session memory to avoid loops.
    """
    # This node is a pass-through to ensure the loop progresses
    state["thinking_log"] = state.get("thinking_log", []) + ["Memory updated"]
    return state
