"""
Yellow Sandbox Deposit Tool: proposes src/lib/yellow/deposit.ts as diff only.
Assumes initialiser/versioned layer has set up deps and config. No file writes; updates state["tool_diffs"].
"""

from pathlib import Path
from typing import Any, Optional

from agent.tools.yellow.helper_function import make_diff
from agent.tools.yellow.template_code import YELLOW_DEPOSIT_TS
from agent.state import AgentState
from logging import getLogger

logger = getLogger(__name__)


class YellowDepositTool:
    """
    Proposes Yellow custody deposit utility (deposit.ts) in src/lib/yellow/ as diff only.
    No file writes; updates state in place via tool_diffs.
    """

    async def invoke(self, state: AgentState) -> None:
        """Update state in place: propose deposit.ts as tool_diffs; set yellow_deposit_status, thinking_log."""
        repo_path = state.get("repo_path") or "./sandbox"
        
        repo = Path(repo_path).resolve()
        if not repo.exists():
            logger.warning("Deposit tool: repo missing %s", repo_path)
            state["yellow_deposit_status"] = "failed"
            state["thinking_log"] = state.get("thinking_log", []) + [
                "Repository path does not exist",
            ]
            return
        if not (repo / "package.json").exists():
            logger.warning("Deposit tool: not a Node project at %s", repo_path)
            state["yellow_deposit_status"] = "failed"
            state["thinking_log"] = state.get("thinking_log", []) + [
                "Not a Node.js project (missing package.json)",
            ]
            return

        diff = make_diff(repo, "src/lib/yellow/deposit.ts", YELLOW_DEPOSIT_TS)
        
        logger.info(f"Deposit tool: diff: {diff}")
        if diff:
            state["tool_diffs"] = (state.get("tool_diffs") or []) + [diff]
            state["thinking_log"] = state.get("thinking_log", []) + [
                "Proposed deposit utility (src/lib/yellow/deposit.ts)",
            ]
        else:
            state["thinking_log"] = state.get("thinking_log", []) + [
                "Deposit file unchanged (src/lib/yellow/deposit.ts)",
            ]
        state["yellow_deposit_status"] = "success"
