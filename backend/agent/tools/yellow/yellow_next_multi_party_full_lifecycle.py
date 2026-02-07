import json
from pathlib import Path
from typing import List

from agent.tools.yellow.helper_function import make_diff, read_text_safe
from agent.tools.yellow.template_code import (
    get_multiparty_route_ts,
    MULTIPARTY_SANDBOX_URL,
    MULTIPARTY_SCRIPT_CMD,
)
from agent.state import AgentState, Diff
from logging import getLogger

logger = getLogger(__name__)


class YellowNextMultiPartyFullLifecycle:
    """
    Proposes multiparty Yellow API route and package.json script for a Next.js repo as diffs only.
    No file writes; no dependency install or .env. Assumes initialiser has run.
    """
    def __init__(self):
        pass

    async def invoke(self, state: AgentState) -> None:
        """Update state in place: propose route + script as tool_diffs; set yellow_multiparty_status, thinking_log."""
        repo_path = state.get("repo_path")
        if not repo_path:
            logger.warning("Multiparty: no repo_path in state")
            state["yellow_multiparty_status"] = "failed"
            state["thinking_log"] = state.get("thinking_log", []) + [
                "Multiparty failed: no repo_path",
            ]
            return

        repo = Path(repo_path).resolve()
        if not repo.exists():
            logger.warning("Multiparty repo missing: %s", repo_path)
            state["yellow_multiparty_status"] = "failed"
            state["thinking_log"] = state.get("thinking_log", []) + [
                "Repository path does not exist",
            ]
            return
        if not (repo / "package.json").exists():
            logger.warning("Multiparty: not a Node project at %s", repo_path)
            state["yellow_multiparty_status"] = "failed"
            state["thinking_log"] = state.get("thinking_log", []) + [
                "Not a Node.js project (missing package.json)",
            ]
            return
        if not self._is_next(repo):
            logger.warning("Multiparty: Next.js required at %s", repo_path)
            state["yellow_multiparty_status"] = "failed"
            state["thinking_log"] = state.get("thinking_log", []) + [
                "Next.js project required for multiparty workflow",
            ]
            return

        diffs: List[Diff] = []

        route_rel = "src/app/api/yellow/multi-party/route.ts"
        route_content = get_multiparty_route_ts(sandbox_url=MULTIPARTY_SANDBOX_URL)
        route_diff = make_diff(repo, route_rel, route_content)
        if route_diff:
            diffs.append(route_diff)

        script_diff = self._propose_script_diff(repo)
        if script_diff:
            diffs.append(script_diff)

        if diffs:
            state["tool_diffs"] = (state.get("tool_diffs") or []) + diffs
            state["thinking_log"] = state.get("thinking_log", []) + [
                "Proposed multiparty route and script. Run `npm run dev` then call /api/yellow/multi-party",
            ]
        else:
            state["thinking_log"] = state.get("thinking_log", []) + [
                "Multiparty route and script unchanged",
            ]
        state["yellow_multiparty_status"] = "success"
        
        logger.info(f"Multiparty: diffs: {diffs}")

    def _is_next(self, repo: Path) -> bool:
        content = read_text_safe(repo / "package.json")
        if not content:
            return False
        try:
            pkg = json.loads(content)
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            return "next" in deps
        except Exception:
            return False

    def _propose_script_diff(self, repo: Path) -> Diff | None:
        """Propose package.json with yellow:multi script. No file write."""
        content = read_text_safe(repo / "package.json")
        if not content:
            return None
        try:
            pkg = json.loads(content)
            if "scripts" not in pkg:
                pkg["scripts"] = {}
            pkg["scripts"]["yellow:multi"] = MULTIPARTY_SCRIPT_CMD
            new_content = json.dumps(pkg, indent=2)
            return make_diff(repo, "package.json", new_content)
        except Exception:
            return None
