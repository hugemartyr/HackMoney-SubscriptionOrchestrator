from __future__ import annotations
from typing import Any, Dict, List
from agent.state import Diff


def _messages(*parts: tuple[str, str]) -> List[Dict[str, str]]:
    """Build list of message dicts: (role, content) -> [{"role": ..., "content": ...}]."""
    return [{"role": role, "content": content} for role, content in parts]


def build_planner_prompt(prompt: str, docs_context: str, codebase_context: str) -> List[Dict[str, str]]:
    system = """
You are an expert senior engineer specializing in integrating Node.js SDKs with existing applications. 
Your task is to integrate the Yellow SDK into a Node.js codebase based strictly on the official Yellow Network documentation provided.

Yellow SDK documentation covers:
- What Yellow SDK is and its architecture
- How the Nitrolite RPC protocol works
- How to open and fund state channels
- How to use NitroliteClient and RPC calls
- Real examples of authentication, session keys, and channel operations

Analyze the user request, Yellow docs, and the repository context to produce:

1) A clear integration plan
2) A breakdown of features required from Yellow SDK
3) SDK capabilities and flags that must be enabled (e.g., channels, multi-party state)
4) Risks, important files, and next steps

Return ONLY a JSON object with these exact keys:
- notes_markdown: string
- yellow_sdk_version: string
- needs_sdk_core: boolean
- needs_channels: boolean
- needs_multi_party: boolean
- needs_config: boolean
- needs_rpc_calls: boolean
- needs_event_listeners: boolean

Focus all reasoning on the Yellow docs, the protocol, and SDK behavior (e.g., NitroliteClient RPC, state channels, unified balance concepts).
    """

    user = (
        "User request:\n"
        f"{prompt}\n\n"
        "Repository / code context:\n"
        f"{codebase_context}\n\n"
        "Yellow documentation context:\n"
        f"{docs_context}\n\n"
        "Generate the JSON integration plan now."
    )

    return _messages(("system", system), ("user", user))



def build_coder_prompt(
    user_query: str,
    plan: str,
    rules: str,
    rag_context: str,
    file_context: str,
    sdk_version: str,
    tool_diffs: List[Diff],
) -> List[Dict[str, str]]:
    system = f"""
You are an expert senior engineer integrating Node.js SDKs using provided documentation. 
Your task is to write precise code changes for integrating the Yellow Network SDK into the existing Node.js repository.

Use ONLY the given plan, Yellow documentation context (Nitrolite RPC, client, channel APIs), and existing repo files to determine:

- Where SDK imports are needed
- How to create/connect to a ClearNode via NitroliteClient
- Where to add RPC calls for session auth, channel open/fund, and event listeners
- Where type definitions, config files, environment variables, and setup scripts belong

Return ONLY a SINGLE JSON object with either:

Format A:
{{
  "changes": [
    {{ "file": "path", "search": "unique string", "replace": "replacement string" }}
  ]
}}

or

Format B:
{{
  "diffs": [
    {{
      "file": "path",
      "oldCode": "original content",
      "newCode": "updated content with Yellow SDK integration"
    }}
  ]
}}

Follow these rules:
- Use import examples and object shapes from Yellow SDK docs
- Preserve existing code style
- Reference real API calls such as createChannel, resizeChannel, auth calls
- Use sdk_version: {sdk_version}
- If tool_diffs were already applied, ensure consistency and refine where needed

=== INTEGRATION RULES (THE CONSTITUTION) ===
{rules}

Return the JSON with your diffs/changes only.
    """

    user = (
        "=== USER QUERY ===\n"
        f"{user_query}\n\n"
        "=== INTEGRATION PLAN ===\n"
        f"{plan}\n\n"
        "=== KNOWLEDGE BASE / DOCS (RAG context) ===\n"
        f"{rag_context}\n\n"
        "=== REPOSITORY FILES (current state; includes tool-proposed content where applicable) ===\n"
        f"{file_context}\n\n"
        "Generate the JSON with your proposed code changes now."
    )

    return _messages(("system", system), ("user", user))



def build_context_check_prompt(prompt: str, code_context: str, memory: Any) -> List[Dict[str, str]]:
    system = """
You are an expert engineer evaluating whether we have enough context to proceed with Yellow SDK integration.
Return ONLY a JSON with:
- status: 'ready' | 'need_code' | 'need_docs' | 'need_research'
- missing_info: [string]
- files_to_read: [string]
- reason: string

Focus on whether:
- SDK docs are present
- key code references exist
- required config/setup files might be missing
    """

    user = (
        f"Prompt:\n{prompt}\n\n"
        "Codebase context:\n"
        f"{code_context}\n\n"
        "Session memory:\n"
        f"{memory}\n\n"
        "Generate JSON now."
    )

    return _messages(("system", system), ("user", user))



def build_import_analysis_prompt(context: str) -> List[Dict[str, str]]:
    system = """
You are a system that analyzes imports and dependencies for a Node.js codebase intended to integrate the Yellow Network SDK.

From the provided code and docs, determine:
- Notable imported modules
- Whether @erc7824/nitrolite or related packages are already present
- Missing parts required for Yellow integration

Return ONLY a JSON with:
- imports: [string]
- dependencies: [string]
- yellow_sdk_present: boolean

Focus all answers strictly on Yellow SDK package names, types, and docs.
    """

    user = (
        "Code and package context:\n"
        f"{context}\n\n"
        "Analyze imports and dependencies; generate JSON now."
    )

    return _messages(("system", system), ("user", user))



def build_research_prompt(query: str, code_context: str, docs_context: str) -> List[Dict[str, str]]:
    system = """
You are a researcher gathering insights for Node.js SDK integration using the Yellow Network docs.

Return ONLY a JSON with:
- findings: string (markdown summary of what you learned)
- relevant_snippets: [string] (from docs/code)
- next_steps: [string] (recommended clear actions)

Focus all answers on things like:
- Nitrolite RPC calls and usage
- How to open/fund channels
- How to auth with session keys
- Real Node.js usage examples
    """

    user = (
        f"Research query:\n{query}\n\n"
        "Repository context:\n"
        f"{code_context}\n\n"
        "Yellow docs context:\n"
        f"{docs_context}\n\n"
        "Generate JSON now."
    )

    return _messages(("system", system), ("user", user))



def build_error_analysis_prompt(build_output: str, context_note: str = "") -> List[Dict[str, str]]:
    system = """
You are an expert debugger analyzing build/test errors related to Yellow SDK integration.
Return ONLY a JSON with:
- error_type
- root_cause
- fix_suggestion
- relevant_files

Use knowledge of TypeScript/Node.js and how Yellow SDK functions (rpc calls, types, channel errors) to explain errors.
    """

    user = (
        f"Build output:\n{build_output}\n\n"
        f"{context_note}\n\n"
        "Yellow docs context is assumed.\n"
        "Generate JSON now."
    )

    return _messages(("system", system), ("user", user))



def build_summary_prompt(thinking_log, diffs, build_success, error_count):
    system = """
You are summarizing the integration session with the Yellow Network SDK.
Return a markdown summary describing:
- What was achieved
- Which files were changed
- Build status
- Remaining tasks
    """

    user = (
        "Thinking log snippet:\n" + "\n".join(thinking_log[-20:]) + "\n\n"
        f"Diffs count: {len(diffs)}\n"
        f"Build success: {build_success}\n"
        f"Error count: {error_count}\n\n"
        "Write the markdown summary now."
    )

    return _messages(("system", system), ("user", user))



def build_fix_plan_prompt(error_analysis: Dict[str, Any], file_context: str) -> List[Dict[str, str]]:
    """Build messages for fix-plan LLM. Returns JSON with diffs (list of file, oldCode, newCode)."""
    system = (
        "You are a senior engineer fixing integration errors.\n"
        "Propose code changes to fix the identified errors. Return a JSON object with:\n"
        "- diffs: array of { file: string, oldCode: string, newCode: string } (same format as the coder; include complete file content in oldCode/newCode where needed)\n\n"
        "Only propose changes that address the root cause. No additional keys. No surrounding text."
    )
    user = (
        "Error analysis (from previous step):\n"
        f"{error_analysis}\n\n"
        "Relevant files (current content):\n"
        f"{file_context}\n\n"
        "Propose fixes as JSON with 'diffs' array."
    )
    return _messages(("system", system), ("user", user))


def build_escalation_prompt(error_context: str, attempted_fixes: List[str]) -> List[Dict[str, str]]:
    """Build messages for escalation LLM. Returns JSON with message for human."""
    system = (
        "You are an AI agent that has encountered a blocking issue and must escalate to a human engineer.\n"
        "Generate a clear escalation message. Return a JSON object with:\n"
        "- message: string (markdown formatted; what went wrong, what was tried, what is needed from the human)\n"
        "- context: string (technical context: env, commands, key paths)\n"
        "- attempted_fixes: list of strings (what was already tried)\n\n"
        "No additional keys. No surrounding text."
    )
    fixes_str = "\n".join(f"- {f}" for f in attempted_fixes) if attempted_fixes else "None"
    user = (
        "Error context:\n"
        f"{error_context}\n\n"
        "Attempted fixes:\n"
        f"{fixes_str}\n\n"
        "Generate the escalation JSON for human review."
    )
    return _messages(("system", system), ("user", user))

def build_doc_checklist_prompt(
    prompt: str,
    plan_notes: str,
    yellow_requirements: str,
    sdk_version: str,
    tree_structure: str,
    existing_docs: str = ""
) -> List[Dict[str, str]]:
    """
    Prompt for creating documentation retrieval checklist.
    Does NOT include code - only plan, requirements, and structure.
    """
    system = """
You are an expert at analyzing integration plans and determining what documentation is needed.

You understand Yellow Network SDK architecture:
- NitroLite protocol and RPC communication
- Channel creation, funding, and management
- Authentication and session management
- Multiparty channels and versioned state
- Tipping and deposit operations

Your task: Review the architect's plan and yellow requirements, then create a checklist of 
specific documentation topics/queries that need to be retrieved from the vector database.

Consider:
- What Yellow SDK features are mentioned in the plan
- What operations are required (channels, auth, payments, etc.)
- What API calls, classes, or concepts need documentation
- What might be missing or unclear in the current plan

Return ONLY a JSON object with:
- checklist: [string] (list of 5-10 specific documentation search queries/topics)
- reasoning: string (explanation of why these docs are needed)
    """

    existing_docs_note = ""
    if existing_docs and len(existing_docs.strip()) > 0:
        existing_docs_note = f"\n\nNote: Some documentation has already been retrieved:\n{existing_docs[:500]}...\n(Focus on gaps and missing information)"
    
    user = (
        f"User Request:\n{prompt}\n\n"
        f"Architect's Plan:\n{plan_notes}\n\n"
        f"Yellow Requirements:\n{yellow_requirements}\n\n"
        f"SDK Version: {sdk_version}\n\n"
        f"Repository Structure:\n{tree_structure}\n\n"
        f"{existing_docs_note}\n\n"
        "Create a documentation retrieval checklist. Return JSON."
    )

    return _messages(("system", system), ("user", user))

def build_plan_correction_prompt(
    prompt: str,
    plan_notes: str,
    yellow_requirements: str,
    sdk_version: str,
    doc_context: str,
    tree_structure: str
) -> List[Dict[str, str]]:
    """
    Prompt for reviewing and correcting the architect's plan.
    Uses retrieved documentation to validate and fix the plan.
    """
    system = """
You are an expert at reviewing integration plans against Yellow Network SDK documentation.

You understand:
- Yellow Network SDK architecture and best practices
- Common mistakes in integration plans
- How to match requirements with actual SDK capabilities
- What features are actually available vs what was assumed

Your task: Review the architect's plan and yellow requirements against the retrieved 
Yellow SDK documentation. Identify:
1. Incorrect assumptions about SDK capabilities
2. Missing or incorrect API calls
3. Wrong feature flags or requirements
4. Architectural issues or misunderstandings
5. SDK version compatibility issues

Then correct the plan and requirements to align with actual SDK documentation.

Return ONLY a JSON object with:
- plan_corrected: boolean (whether plan was corrected)
- corrected_plan: string (corrected plan notes, or original if no changes)
- corrected_sdk_version: string (corrected version if needed)
- corrected_requirements: {needs_yellow: bool, needs_simple_channel: bool, needs_multiparty: bool, needs_versioned: bool, needs_tip: bool, needs_deposit: bool}
- corrections: [string] (list of issues found and fixed)
- reasoning: string (explanation of corrections)
    """

    user = (
        f"User Request:\n{prompt}\n\n"
        f"Architect's Original Plan:\n{plan_notes}\n\n"
        f"Original Yellow Requirements:\n{yellow_requirements}\n\n"
        f"Original SDK Version: {sdk_version}\n\n"
        f"Repository Structure:\n{tree_structure}\n\n"
        f"Retrieved Yellow SDK Documentation:\n{doc_context}\n\n"
        "Review the plan against the documentation. Identify issues and correct them. Return JSON."
    )

    return _messages(("system", system), ("user", user))
