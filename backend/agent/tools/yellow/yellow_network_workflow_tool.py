from pathlib import Path
from typing import Optional

from agent.tools.yellow.helper_function import make_diff
from agent.tools.yellow.template_code import (
    get_yellow_workflow_ts,
    WORKFLOW_DEFAULT_SEPOLIA_RPC,
    WORKFLOW_SANDBOX_WS,
)
from agent.state import AgentState
from logging import getLogger

logger = getLogger(__name__)

class YellowNetworkWorkflowTool:
    """
    Proposes Yellow Network workflow script as diffs only.
    Injects src/yellowWorkflow.ts via state["tool_diffs"]. No file writes, no npm/faucet/run.
    """
    def __init__(self):
        pass

    async def invoke(self, state: AgentState) -> None:
        """Update state in place: propose workflow file as tool_diffs; set yellow_workflow_status, thinking_log."""
        repo_path = state.get("repo_path") or "./sandbox"
        prompt = (state.get("prompt") or "").lower()
        requires_simple = state.get("needs_simple_channel")
        if requires_simple is None:
            requires_simple = any(
                k in prompt
                for k in (
                    "channel",
                    "nitrolite",
                    "create channel",
                    "open channel",
                    "state update",
                    "stateless",
                )
            )
        requires_yellow = state.get("needs_yellow")

        if not (requires_yellow or requires_simple):
            logger.info("Yellow workflow skipped: not required by prompt")
            state["yellow_workflow_status"] = "skipped"
            state["thinking_log"] = state.get("thinking_log", []) + [
                "Skipped Yellow network workflow (not required)",
            ]
            return

        if not repo_path:
            logger.warning("Yellow workflow: no repo_path in state")
            state["yellow_workflow_status"] = "failed"
            state["thinking_log"] = state.get("thinking_log", []) + ["No repo_path for workflow"]
            return

        repo = Path(repo_path).resolve()
        if not repo.exists():
            logger.warning("Workflow repo missing: %s", repo_path)
            state["yellow_workflow_status"] = "failed"
            state["thinking_log"] = state.get("thinking_log", []) + [f"Repo not found: {repo_path}"]
            return
        if not (repo / "package.json").exists():
            logger.warning("Workflow: not a Node project at %s", repo_path)
            state["yellow_workflow_status"] = "failed"
            state["thinking_log"] = state.get("thinking_log", []) + ["Missing package.json"]
            return

        workflow_code = get_yellow_workflow_ts(
            rpc_url=WORKFLOW_DEFAULT_SEPOLIA_RPC,
            ws_url=WORKFLOW_SANDBOX_WS,
        )
        diff = make_diff(repo, "src/yellowWorkflow.ts", workflow_code)
        if diff:
            state["tool_diffs"] = (state.get("tool_diffs") or []) + [diff]
            state["thinking_log"] = state.get("thinking_log", []) + [
                "Proposed src/yellowWorkflow.ts",
            ]
        else:
            state["thinking_log"] = state.get("thinking_log", []) + [
                "Workflow file unchanged (src/yellowWorkflow.ts)",
            ]
        state["yellow_workflow_status"] = "success"
        
        logger.info(f"Yellow workflow: diff: {diff}")
