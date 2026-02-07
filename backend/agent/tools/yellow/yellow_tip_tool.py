from pathlib import Path
from typing import Any, Optional

from agent.tools.yellow.helper_function import make_diff
from agent.tools.yellow.template_code import YELLOW_TIP_TS
from agent.state import AgentState
from logging import getLogger

logger = getLogger(__name__)

class YellowTipTool:
    """
    Proposes Yellow sandbox tipping utility (tip.ts) in src/lib/yellow/ as diff only.
    No file writes; updates state in place via tool_diffs.
    """
    async def invoke(self, state: AgentState) -> None:
        """Update state in place: propose tip.ts as tool_diffs; set yellow_tip_status, thinking_log."""
        repo_path = state.get("repo_path") or "./sandbox"

        repo = Path(repo_path).resolve()
        if not repo.exists():
            logger.warning("Tip tool: repo missing %s", repo_path)
            state["yellow_tip_status"] = "failed"
            state["thinking_log"] = state.get("thinking_log", []) + [
                "Repository path does not exist",
            ]
            return
        if not (repo / "package.json").exists():
            logger.warning("Tip tool: not a Node project at %s", repo_path)
            state["yellow_tip_status"] = "failed"
            state["thinking_log"] = state.get("thinking_log", []) + [
                "Not a Node.js project (missing package.json)",
            ]
            return

        diff = make_diff(repo, "src/lib/yellow/tip.ts", YELLOW_TIP_TS)
        if diff:
            state["tool_diffs"] = (state.get("tool_diffs") or []) + [diff]
            state["thinking_log"] = state.get("thinking_log", []) + [
                "Proposed tipping utility (src/lib/yellow/tip.ts)",
            ]
        else:
            state["thinking_log"] = state.get("thinking_log", []) + [
                "Tip file unchanged (src/lib/yellow/tip.ts)",
            ]
        state["yellow_tip_status"] = "success"
        
        logger.info(f"Tip tool: diff: {diff}")