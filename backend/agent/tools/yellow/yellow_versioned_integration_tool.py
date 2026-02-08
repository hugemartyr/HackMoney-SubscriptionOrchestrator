from pathlib import Path
from typing import List

from agent.tools.yellow.helper_function import make_diff, read_text_safe
from agent.state import AgentState, Diff
from agent.tools.yellow.template_code import (
    VERSIONED_INTEGRATION_VERSION,
    get_versioned_version_ts,
    VERSIONED_CONFIG_TS,
    VERSIONED_UTILS_TS,
    VERSIONED_AUTH_TS,
)
from logging import getLogger

logger = getLogger(__name__)

def _parse_version(content: str) -> str:
    """Extract version string from version.ts content. Returns '0.0.0' if unreadable."""
    if not content:
        return "0.0.0"
    try:
        parts = content.split('"')
        return parts[1] if len(parts) > 1 else "0.0.0"
    except Exception:
        return "0.0.0"

class YellowVersionedIntegrationTool:
    """
    Proposes versioned Yellow integration layer (version.ts, config.ts, utils.ts, auth.ts) in src/lib/yellow/ as diffs only.
    No file writes; no dependency install or .env. Assumes initialiser has run.
    """

    async def invoke(self, state: AgentState) -> None:
        """Update state in place: propose layer files as tool_diffs; set yellow_versioned_status, thinking_log."""
        repo_path = state.get("repo_path") or "./sandbox"
        repo = Path(repo_path).resolve()

        if not repo.exists():
            logger.warning("Versioned integration repo missing: %s", repo_path)
            state["yellow_versioned_status"] = "failed"
            state["thinking_log"] = state.get("thinking_log", []) + [
                "Repository path does not exist",
            ]
            return
        if not (repo / "package.json").exists():
            logger.warning("Versioned integration: not a Node project at %s", repo_path)
            state["yellow_versioned_status"] = "failed"
            state["thinking_log"] = state.get("thinking_log", []) + [
                "Not a Node.js project (missing package.json)",
            ]
            return

        version_rel = "src/lib/yellow/version.ts"
        version_path = repo / version_rel
        current_content = read_text_safe(version_path)
        current_version = _parse_version(current_content or "")

        templates = {
            "version.ts": get_versioned_version_ts(VERSIONED_INTEGRATION_VERSION),
            "config.ts": VERSIONED_CONFIG_TS,
            "utils.ts": VERSIONED_UTILS_TS,
            "auth.ts": VERSIONED_AUTH_TS,
        }

        diffs: List[Diff] = []

        # No existing version file or folder: propose full layer
        if current_content is None:
            diffs.extend(self._propose_layer_diffs(repo, templates))
            state["tool_diffs"] = (state.get("tool_diffs") or []) + diffs
            state["thinking_log"] = state.get("thinking_log", []) + [
                "Proposed Yellow integration layer (src/lib/yellow/)",
            ]
            state["yellow_versioned_status"] = "success"
            return

        if current_version == VERSIONED_INTEGRATION_VERSION:
            logger.info("Versioned integration already up to date: %s", current_version)
            state["thinking_log"] = state.get("thinking_log", []) + [
                "Yellow integration layer is current",
            ]
            state["yellow_versioned_status"] = "success"
            return

        if current_version < VERSIONED_INTEGRATION_VERSION:
            diffs.extend(self._propose_layer_diffs(repo, templates))
            state["tool_diffs"] = (state.get("tool_diffs") or []) + diffs
            state["thinking_log"] = state.get("thinking_log", []) + [
                f"Proposed upgrade from {current_version} to {VERSIONED_INTEGRATION_VERSION}",
            ]
            state["yellow_versioned_status"] = "success"
            return

        # Existing version is newer
        state["yellow_versioned_status"] = "failed"
        state["thinking_log"] = state.get("thinking_log", []) + [
            f"Existing version {current_version} is newer than {VERSIONED_INTEGRATION_VERSION}",
        ]
        
        logger.info(f"Versioned integration: diffs: {diffs}")

    def _propose_layer_diffs(self, repo: Path, templates: dict) -> List[Diff]:
        """Build diffs for version.ts, config.ts, utils.ts, auth.ts. No file writes."""
        diffs: List[Diff] = []
        for filename, content in templates.items():
            rel = f"src/lib/yellow/{filename}"
            d = make_diff(repo, rel, content)
            if d:
                diffs.append(d)
        return diffs
