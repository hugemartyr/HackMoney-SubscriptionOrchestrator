from __future__ import annotations
import asyncio
from agent.state import AgentState
from services.sandbox_fs_service import read_text_file, get_file_tree
from agent.tools.vector_store import YellowVectorStore
from agent.llm.analysis import analyze_context, analyze_imports, conduct_research

async def context_check_node(state: AgentState) -> AgentState:
    """
    Decide if we have enough information (code + docs) to proceed.
    """
    # Increment loop counter
    loop_count = state.get("context_loop_count", 0) + 1
    
    result = await analyze_context(
        state.get("prompt", ""), 
        state.get("file_contents", {}),
        state.get("session_memory", []),
        state.get("tree")  # Pass tree to analyze_context
    )
    
    status = result.get("status", "ready")
    missing_info = result.get("missing_info", [])
    files_to_read = result.get("files_to_read", []) # Explicit list from LLM
    
    return {
        "context_ready": status == "ready",
        "context_loop_count": loop_count,
        "missing_info": missing_info,
        "files_to_read": files_to_read, # Store in state for read_code_node
        "docs_retrieved": state.get("docs_retrieved", False),
        "thinking_log": state.get("thinking_log", []) + [f"Context Status: {status} (Loop {loop_count})"]
    }

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
        # Fallback to heuristic from missing_info if files_to_read is empty
        # (Legacy fallback, though prompt should now provide files_to_read)
        missing_info = state.get("missing_info", [])
        for item in missing_info:
             if "." in item or "/" in item:
                files_to_read.append(item)

    if not files_to_read and not current_files:
         return {"thinking_log": state.get("thinking_log", []) + ["No specific files identified to read."]}

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
    
    return {
        "file_contents": new_contents,
        "thinking_log": state.get("thinking_log", []) + [log_msg]
    }

async def analyze_imports_node(state: AgentState) -> AgentState:
    """
    Analyze dependencies to understand the stack.
    """
    result = await analyze_imports(state.get("file_contents", {}))
    
    # Format a summary for memory so analyze_context sees it
    imports_summary = f"Import Analysis: Yellow SDK present: {result.get('yellow_sdk_present')}. "
    imports_summary += f"Dependencies: {', '.join(result.get('dependencies', [])[:5])}..."

    return {
        "imports_analyzed": True,
        "analyzed_imports": result,
        "session_memory": state.get("session_memory", []) + [imports_summary],
        "thinking_log": state.get("thinking_log", []) + ["Analyzed imports"]
    }

def _search_docs_wrapper(query: str, missing_info: list[str] | None) -> str:
    """Helper to run blocking vector store operations in a thread."""
    try:
        vs = YellowVectorStore()
        final_query = query
        if missing_info:
            final_query += " " + " ".join(missing_info)
        return vs.search(final_query)
    except Exception as e:
        return f"Error searching docs: {str(e)}"

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
        
        return {
            "docs_retrieved": True,
            "doc_context": docs,
            "thinking_log": state.get("thinking_log", []) + ["Retrieved documentation"]
        }
    except Exception as e:
        return {
            "docs_retrieved": True, # Mark as retrieved to avoid infinite loop, but log error
            "doc_context": f"Error retrieving docs: {e}",
            "thinking_log": state.get("thinking_log", []) + [f"Error retrieving docs: {e}"]
        }

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
    
    return {
        "thinking_log": state.get("thinking_log", []) + [f"Research findings: {findings[:100]}..."],
        # Add findings to memory to progress the context check
        "session_memory": state.get("session_memory", []) + [f"Research: {findings}"]
    }

async def update_memory_node(state: AgentState) -> AgentState:
    """
    Update session memory to avoid loops.
    """
    # This node is a pass-through to ensure the loop progresses
    return {"thinking_log": state.get("thinking_log", []) + ["Memory updated"]}
