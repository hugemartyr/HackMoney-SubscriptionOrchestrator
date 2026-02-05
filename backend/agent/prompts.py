from typing import List
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
