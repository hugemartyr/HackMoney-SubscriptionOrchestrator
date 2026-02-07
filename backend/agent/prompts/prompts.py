from __future__ import annotations
from typing import Any, Dict, List
from agent.state import Diff


def _messages(*parts: tuple[str, str]) -> List[Dict[str, str]]:
    """Build list of message dicts: (role, content) -> [{"role": ..., "content": ...}]."""
    return [{"role": role, "content": content} for role, content in parts]


def build_planner_prompt(prompt: str, context: str) -> List[Dict[str, str]]:
    """Build messages for planning LLM. Returns JSON with plan + Yellow requirement flags."""
    system = """You are a senior engineer helping integrate Yellow Network SDK into an existing project.
    Analyze the user request and the repository context to produce a clear integration plan and detect which Yellow capabilities are required.

    Yellow tools – what they do and when to set each flag:

    • yellow_network_workflow_tool: Proposes/runs Yellow/Nitrolite channel workflow (e.g. src/yellowWorkflow.ts). Use when the user needs channels, state updates, sandbox connections, or workflow execution. Set needs_yellow and needs_simple_channel to true when the request involves creating or running channels, state updates, or related network interactions.

    • yellow_versioned_integration_tool: Installs or upgrades an integration scaffold (version.ts, config.ts, utils.ts, auth.ts). Use when the user needs a reusable SDK layer, scaffolding, versioning, or configuration. Set needs_versioned to true when the request involves integration layer, library setup, scaffold, abstraction, wrapper, or config/session.

    • yellow_next_multi_party_full_lifecycle: Adds Next.js multiparty API route and script for multi-wallet/collaborative flows. Use when the user needs multiparty, multi-wallet, collaborative, multisig, shared session/state, counterparty, or allocation. Set needs_multiparty to true for such bilateral/consensus workflows.

    • yellow_tip_tool: Injects src/lib/yellow/tip.ts for tipping and token movement. Use when the user needs tipping, payments, transfers, or donations. Set needs_tip to true when the request involves tip, send tip, transfer, pay, payment, donate, or donation.

    • Yellow deposit tool: Injects src/lib/yellow/deposit.ts for USDC custody/deposit with viem chain resolution. Use when the user needs deposit, custody, funding, top-up, or Nitrolite deposit. Set needs_deposit to true when the request involves deposit, custody, fund, add funds, top up, or custody contract.

    Return ONLY a single JSON object with these exact keys:
    - notes_markdown: string (markdown summary of the plan: scope, steps, key files, risks)
    - yellow_sdk_version: string (npm semver, e.g. "^1.2.3" or "latest")
    - needs_yellow: boolean (true if user needs Yellow Network / Nitrolite / state channels / clearnode / off-chain / L3 / nitro)
    - needs_simple_channel: boolean (true if user needs channel, nitrolite, create channel, open channel, state update, stateless)
    - needs_multiparty: boolean (true if user needs multiparty, multi-party, two wallets, collaborative, multi-sig, shared state/session, participant, counterparty, bilateral, consensus, allocation)
    - needs_versioned: boolean (true if user needs integration layer, versioned, library setup, scaffold, abstraction, wrapper, reusable, config/session)
    - needs_tip: boolean (true if user needs tip, tipping, send tip, transfer, pay, payment, donate, donation)
    - needs_deposit: boolean (true if user needs deposit, custody, fund, add funds, top up, custody contract, nitrolite deposit)

    No additional keys. No surrounding text or markdown fences.
    """
    user = (
        "User request:\n"
        f"{prompt}\n\n"
        "Repository context (files/snippets):\n"
        f"{context}\n\n"
        "Generate the plan JSON with notes_markdown, yellow_sdk_version, and the six boolean Yellow flags (needs_yellow, needs_simple_channel, needs_multiparty, needs_versioned, needs_tip, needs_deposit) based on the user request."
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
    """Build messages for code generation LLM. file_context should include tool-proposed content. tool_diffs lists files already proposed by tools (each: file, oldCode, newCode)."""
    system = (
        "You are a senior engineer helping integrate Yellow Network SDK into an existing project.\n"
        "Analyze the codebase, the plan, the integration rules, and the provided documentation to propose specific code changes.\n\n"
        "Return ONLY a single JSON object. You may use either format:\n\n"
        "Format A (search/replace, preferred for small edits):\n"
        '  { "changes": [ { "file": "path/to/file.ext", "search": "exact unique string to find", "replace": "replacement string" } ] }\n\n'
        "Format B (full-file diffs):\n"
        '  { "diffs": [ { "file": "path/to/file.ext", "oldCode": "complete original content", "newCode": "complete modified content" } ] }\n\n'
        "Rules:\n"
        "- For search/replace: use a unique, exact search string (multiple lines ok); replace only what is necessary.\n"
        "- For diffs: include the COMPLETE file content in both oldCode and newCode.\n"
        "- Only propose changes to files that need Yellow SDK integration or that are listed in the plan.\n"
        "- Be precise and maintain existing code style, indentation, and formatting.\n"
        "- Return empty changes/diffs array if no changes are needed.\n"
        "- FOLLOW THE INTEGRATION RULES (THE CONSTITUTION) STRICTLY.\n"
        "- SDK version to use: " + sdk_version + "\n\n"
        "No additional keys. No surrounding text or markdown fences."
    )
    tool_section = ""
    if tool_diffs:
        tool_files = [d.get("file", "") for d in tool_diffs if d.get("file")]
        tool_section = (
            "\n\n=== TOOL-PROPOSED CHANGES (already reflected in file contents below) ===\n"
            "Files: " + ", ".join(tool_files) + "\n"
            "You may refine these files or change any other file. Propose your final code changes as JSON (use 'changes' or 'diffs' as above).\n"
        )
    user_content = (
        "=== USER QUERY ===\n"
        f"{user_query}\n\n"
        "=== PLAN (integration plan) ===\n"
        f"{plan}\n\n"
        "=== THE CONSTITUTION (integration rules – follow strictly) ===\n"
        f"{rules}\n\n"
        "=== KNOWLEDGE BASE / DOCS (RAG context) ===\n"
        f"{rag_context}\n\n"
        "=== REPOSITORY FILES (current state; includes tool-proposed content where applicable) ===\n"
        f"{file_context}"
        f"{tool_section}\n\n"
        "Generate the JSON with your proposed code changes now."
    )
    return _messages(("system", system), ("user", user_content))


def build_context_check_prompt(prompt: str, file_context_str: str, memory: Any) -> List[Dict[str, str]]:
    """Build messages for context-check LLM. Returns JSON with status, missing_info, etc."""
    system = (
        "You are a senior engineer analyzing if we have enough context to proceed with Yellow Network SDK integration.\n"
        "Return a JSON object with:\n"
        "- status: 'ready' | 'missing_code' | 'missing_docs' | 'need_research'\n"
        "- missing_info: list of strings (what specifically is missing)\n"
        "- files_to_read: list of strings (specific file paths to read if status is 'missing_code')\n"
        "- reason: string (brief explanation)\n\n"
        "No additional keys. No surrounding text."
    )
    user = (
        f"User prompt: {prompt}\n\n"
        "Current files / code context:\n"
        f"{file_context_str}\n\n"
        "Session memory (previous actions/attempts):\n"
        f"{memory}\n\n"
        "Do we have enough information to proceed? Generate JSON only."
    )
    return _messages(("system", system), ("user", user))


def build_import_analysis_prompt(context: str) -> List[Dict[str, str]]:
    """Build messages for import analysis LLM."""
    system = (
        "You are analyzing project dependencies and imports for Yellow Network SDK integration.\n"
        "Return a JSON object with:\n"
        "- imports: list of strings (notable import paths or module names)\n"
        "- dependencies: list of strings (package names from package.json or equivalent)\n"
        "- yellow_sdk_present: boolean (whether Yellow SDK or related packages are already present)\n\n"
        "No additional keys. No surrounding text."
    )
    user = (
        "Code/package context:\n"
        f"{context}\n\n"
        "Analyze imports and dependencies. Generate JSON only."
    )
    return _messages(("system", system), ("user", user))


def build_research_prompt(query: str, file_context: str, docs_context: str) -> List[Dict[str, str]]:
    """Build messages for research LLM."""
    system = (
        "You are a technical researcher gathering information for Yellow Network SDK integration.\n"
        "Analyze code snippets and documentation. Return a JSON object with:\n"
        "- findings: string (markdown summary of what you learned)\n"
        "- useful_snippets: list of strings (relevant code or doc excerpts)\n"
        "- next_steps: list of strings (recommended next actions)\n\n"
        "No additional keys. No surrounding text."
    )
    user = (
        f"Research query: {query}\n\n"
        "Relevant code context:\n"
        f"{file_context}\n\n"
        "Documentation / knowledge base:\n"
        f"{docs_context}\n\n"
        "Synthesize findings and suggest next steps. Generate JSON only."
    )
    return _messages(("system", system), ("user", user))


def build_error_analysis_prompt(build_output: str, context_note: str = "") -> List[Dict[str, str]]:
    """Build messages for error analysis LLM."""
    system = (
        "You are a debugging expert analyzing build/test errors for Yellow Network SDK integration.\n"
        "Analyze the error log and return a JSON object with:\n"
        "- error_type: string (e.g. compile error, type error, missing dependency)\n"
        "- root_cause: string (brief explanation of what caused the error)\n"
        "- fix_suggestion: string (concrete steps or code changes to fix it)\n"
        "- relevant_files: list of strings (file paths that likely need to be fixed)\n\n"
        "No additional keys. No surrounding text."
    )
    user = (
        "Build/test output:\n"
        f"{build_output}\n\n"
        f"{context_note}\n\n"
        "Analyze the error and suggest fixes. Generate JSON only."
    )
    return _messages(("system", system), ("user", user))


def build_summary_prompt(
    thinking_log: List[str],
    diffs: List[Any],
    build_success: bool,
    error_count: int,
) -> List[Dict[str, str]]:
    """Build messages for final summary LLM."""
    system = (
        "You are generating a final summary of the Yellow Network SDK integration session.\n"
        "Return a markdown string (not JSON) that summarizes:\n"
        "- What was achieved (integration steps completed)\n"
        "- Files changed (list or summary)\n"
        "- Build status (success/failure)\n"
        "- Next steps for the user (if any)\n\n"
        "Be concise, professional, and use a 'Cursor'-style tone: helpful and direct."
    )
    log_str = "\n".join(thinking_log[-20:]) if thinking_log else "No log"
    diff_files = [d.get("file", "unknown") for d in diffs] if diffs else []
    user = (
        "Thinking log (excerpt):\n"
        f"{log_str}\n\n"
        f"Diffs count: {len(diffs)}\n"
        f"Files changed: {', '.join(diff_files) if diff_files else 'none'}\n"
        f"Build success: {build_success}\n"
        f"Error count: {error_count}\n\n"
        "Write the final summary in markdown."
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
