from typing import List, Dict, Any
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage

class AgentPrompts:
    PLANNER_SYSTEM_TEMPLATE = (
        "You are a senior engineer helping integrate Yellow Network SDK into an existing project.\n"
        "Return ONLY a single JSON object with keys:\n"
        "- notes_markdown: string (markdown)\n"
        "- yellow_sdk_version: string (npm semver like \"^1.2.3\" or \"latest\")\n"
        "No additional keys. No surrounding text."
    )

    CODER_SYSTEM_TEMPLATE = (
        "You are a senior engineer helping integrate Yellow Network SDK (@yellow-network/sdk) into an existing project.\n"
        "Analyze the codebase, the plan, and the provided documentation to propose specific code changes.\n\n"
        "Return ONLY a single JSON object with this exact structure:\n"
        "{\n"
        '  "diffs": [\n'
        "    {\n"
        '      "file": "path/to/file.ext",\n'
        '      "oldCode": "original file content (complete)",\n'
        '      "newCode": "modified file content (complete)"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "- Include the COMPLETE file content in both oldCode and newCode\n"
        "- Only propose changes to files that need Yellow SDK integration\n"
        "- Be precise and maintain existing code style\n"
        "- Include import statements for @yellow-network/sdk where needed\n"
        "- Do not create new files, only modify existing ones\n"
        "- Return empty diffs array if no changes are needed\n"
        "- FOLLOW THE INTEGRATION RULES STRICTLY.\n"
        "No additional keys. No surrounding text."
    )

    # New prompts for enhanced flow
    CONTEXT_CHECK_SYSTEM_TEMPLATE = (
        "You are a senior engineer analyzing if we have enough context to proceed with Yellow Network SDK integration.\n"
        "Return a JSON object with:\n"
        "- status: 'ready' | 'missing_code' | 'missing_docs' | 'need_research'\n"
        "- missing_info: List[str] (what specifically is missing)\n"
        "- files_to_read: List[str] (specific file paths to read if status is 'missing_code')\n"
        "- reason: string (brief explanation)"
    )

    ARCHITECT_SYSTEM_TEMPLATE = (
        "You are a System Architect designing a Yellow Network integration.\n"
        "Create a detailed architectural plan. Return a JSON object with:\n"
        "- notes_markdown: string (detailed plan in markdown)\n"
        "- yellow_sdk_version: string\n"
        "- architecture_diagram: string (mermaid diagram code)\n"
        "- key_components: List[str]"
    )

    ERROR_ANALYSIS_SYSTEM_TEMPLATE = (
        "You are a debugging expert analyzing build/test errors.\n"
        "Analyze the error log and return a JSON object with:\n"
        "- error_type: string\n"
        "- root_cause: string\n"
        "- fix_suggestion: string\n"
        "- files_to_fix: List[str]"
    )

    FIX_PLAN_SYSTEM_TEMPLATE = (
        "You are a senior engineer fixing integration errors.\n"
        "Propose code changes to fix the identified errors. Return JSON with 'diffs' array (same format as coder)."
    )

    ESCALATION_SYSTEM_TEMPLATE = (
        "You are an AI agent that has encountered a blocking issue.\n"
        "Generate a clear escalation message for a human engineer. Return JSON with:\n"
        "- message: string (markdown formatted)\n"
        "- context: string\n"
        "- attempted_fixes: List[str]"
    )

    RESEARCH_SYSTEM_TEMPLATE = (
        "You are a technical researcher gathering information for Yellow Network integration.\n"
        "Analyze code snippets and docs. Return JSON with:\n"
        "- findings: string (markdown)\n"
        "- useful_snippets: List[str]\n"
        "- next_steps: List[str]"
    )

    IMPORT_ANALYSIS_SYSTEM_TEMPLATE = (
        "You are analyzing project dependencies and imports.\n"
        "Return JSON with:\n"
        "- imports: List[str]\n"
        "- dependencies: List[str]\n"
        "- yellow_sdk_present: boolean"
    )

    SUMMARY_SYSTEM_TEMPLATE = (
        "You are generating a final summary of the integration session.\n"
        "Return a markdown string (not JSON) that summarizes:\n"
        "- What was achieved\n"
        "- Files changed\n"
        "- Build status\n"
        "- Next steps for the user\n"
        "Be concise, professional, and use the 'Cursor' style (helpful, direct)."
    )

def build_planner_prompt(user_query: str, file_context: str) -> List[BaseMessage]:
    user_msg = (
        f"User prompt:\n{user_query}\n\n"
        "Repository context (snippets):\n"
        f"{file_context}\n\n"
        "Generate the JSON now."
    )
    return [
        SystemMessage(content=AgentPrompts.PLANNER_SYSTEM_TEMPLATE),
        HumanMessage(content=user_msg)
    ]

def build_coder_prompt(
    user_query: str,
    plan: str,
    rules: str,
    rag_context: str,
    file_context: str,
    sdk_version: str
) -> List[BaseMessage]:
    user_msg = (
        f"User prompt:\n{user_query}\n\n"
        f"Plan notes:\n{plan}\n\n"
        f"Yellow SDK version to use: {sdk_version}\n\n"
        "=== THE CONSTITUTION (INTEGRATION RULES) ===\n"
        f"{rules}\n\n"
        "=== KNOWLEDGE BASE (DOCS) ===\n"
        f"{rag_context}\n\n"
        "=== REPOSITORY FILES ===\n"
        f"{file_context}\n\n"
        "Generate the JSON with proposed code changes now."
    )
    
    return [
        SystemMessage(content=AgentPrompts.CODER_SYSTEM_TEMPLATE),
        HumanMessage(content=user_msg)
    ]

# New builder functions

def build_context_check_prompt(user_query: str, file_context: str, memory: List[str]) -> List[BaseMessage]:
    memory_str = "\n".join(memory) if memory else "No previous actions."
    user_msg = (
        f"User prompt: {user_query}\n\n"
        f"Session Memory:\n{memory_str}\n\n"
        f"Context:\n{file_context}\n\n"
        "Do we have enough information to proceed? Generate JSON."
    )
    return [
        SystemMessage(content=AgentPrompts.CONTEXT_CHECK_SYSTEM_TEMPLATE),
        HumanMessage(content=user_msg)
    ]

def build_architect_prompt(user_query: str, file_context: str, research_notes: str) -> List[BaseMessage]:
    user_msg = (
        f"User prompt: {user_query}\n\n"
        f"Research Notes:\n{research_notes}\n\n"
        f"Context:\n{file_context}\n\n"
        "Design the integration architecture. Generate JSON."
    )
    return [
        SystemMessage(content=AgentPrompts.ARCHITECT_SYSTEM_TEMPLATE),
        HumanMessage(content=user_msg)
    ]

def build_error_analysis_prompt(build_output: str, file_context: str) -> List[BaseMessage]:
    user_msg = (
        f"Build/Test Output:\n{build_output}\n\n"
        f"Relevant Files:\n{file_context}\n\n"
        "Analyze the error. Generate JSON."
    )
    return [
        SystemMessage(content=AgentPrompts.ERROR_ANALYSIS_SYSTEM_TEMPLATE),
        HumanMessage(content=user_msg)
    ]

def build_fix_plan_prompt(error_analysis: Dict[str, Any], file_context: str) -> List[BaseMessage]:
    user_msg = (
        f"Error Analysis:\n{error_analysis}\n\n"
        f"Files:\n{file_context}\n\n"
        "Propose fixes. Generate JSON with diffs."
    )
    return [
        SystemMessage(content=AgentPrompts.FIX_PLAN_SYSTEM_TEMPLATE),
        HumanMessage(content=user_msg)
    ]

def build_escalation_prompt(error_context: str, attempted_fixes: List[str]) -> List[BaseMessage]:
    fixes_str = "\n".join(attempted_fixes)
    user_msg = (
        f"Error Context:\n{error_context}\n\n"
        f"Attempted Fixes:\n{fixes_str}\n\n"
        "Generate escalation message. Generate JSON."
    )
    return [
        SystemMessage(content=AgentPrompts.ESCALATION_SYSTEM_TEMPLATE),
        HumanMessage(content=user_msg)
    ]

def build_research_prompt(query: str, file_context: str, docs_context: str) -> List[BaseMessage]:
    user_msg = (
        f"Research Query: {query}\n\n"
        f"Docs:\n{docs_context}\n\n"
        f"Code:\n{file_context}\n\n"
        "Analyze and summarize. Generate JSON."
    )
    return [
        SystemMessage(content=AgentPrompts.RESEARCH_SYSTEM_TEMPLATE),
        HumanMessage(content=user_msg)
    ]

def build_import_analysis_prompt(file_context: str) -> List[BaseMessage]:
    user_msg = (
        f"Code:\n{file_context}\n\n"
        "Analyze imports. Generate JSON."
    )
    return [
        SystemMessage(content=AgentPrompts.IMPORT_ANALYSIS_SYSTEM_TEMPLATE),
        HumanMessage(content=user_msg)
    ]

def build_summary_prompt(
    thinking_log: List[str], 
    diffs: List[Dict[str, str]], 
    build_success: bool, 
    error_count: int
) -> List[BaseMessage]:
    thinking_str = "\n".join(thinking_log[-5:]) # Last 5 thoughts
    diff_files = [d.get("file", "unknown") for d in diffs]
    user_msg = (
        f"Build Success: {build_success}\n"
        f"Error Count: {error_count}\n"
        f"Files Changed: {', '.join(diff_files)}\n"
        f"Recent Thinking:\n{thinking_str}\n\n"
        "Generate a helpful Cursor-style summary markdown."
    )
    return [
        SystemMessage(content=AgentPrompts.SUMMARY_SYSTEM_TEMPLATE),
        HumanMessage(content=user_msg)
    ]
