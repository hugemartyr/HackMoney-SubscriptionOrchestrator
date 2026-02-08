"""
Yellow SDK initializer: proposes all changes as state["tool_diffs"] (no file writes).
Merge of invoke + _execute_init; uses make_diff only (diffs proposed, not written).
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.state import AgentState, Diff
from agent.tools.yellow.helper_function import make_diff
from agent.tools.yellow.template_code import (
    DEFAULT_ENV,
    YELLOW_SCAFFOLD,
    YELLOW_DEPENDENCIES,
    YELLOW_DEV_DEPENDENCIES,
)
from logging import getLogger

logger = getLogger(__name__)

class YellowInitializerTool:
    """
    Proposes Yellow SDK setup as diffs only (package.json, tsconfig, .env, src/yellow.ts).
    Updates state["tool_diffs"] and other AgentState fields; does not write files.
    """

    name = "yellow_sdk_initializer"
    description = "Propose Yellow SDK setup as diffs: package.json deps, tsconfig, .env, scaffold"

    def __init__(self) -> None:
        pass

    async def invoke(self, state: AgentState) -> None:
        """Compute proposed diffs and update state in place (no file writes)."""
        repo_path = state.get("repo_path") or "./sandbox"
        framework_hint = state.get("framework_hint")
       

        repo = Path(repo_path).resolve()
        if not repo.exists():
            state["yellow_initialized"] = False
            state["yellow_framework"] = ""
            state["yellow_init_status"] = "failed"
            state["thinking_log"] = state.get("thinking_log", []) + [f"Repo not found: {repo_path}"]
            return

        pkg_path = repo / "package.json"
        if not pkg_path.exists():
            state["yellow_initialized"] = False
            state["yellow_framework"] = ""
            state["yellow_init_status"] = "failed"
            state["thinking_log"] = state.get("thinking_log", []) + ["Not a Node project (no package.json)"]
            return

        try:
            framework = framework_hint or self._detect_framework(pkg_path)
            diffs: List[Diff] = []

            # 1) package.json: merge Yellow deps
            pkg_diff = self._propose_package_json_diff(repo)
            if pkg_diff:
                diffs.append(pkg_diff)

            # 2) tsconfig.json: merge or create
            ts_diff = self._propose_tsconfig_diff(repo)
            if ts_diff:
                diffs.append(ts_diff)

            # 3) .env: propose default (new file or existing; no wallet gen)
            env_diff = self._propose_env_diff(repo)
            if env_diff:
                diffs.append(env_diff)

            # 4) src/yellow.ts: propose scaffold (new file = oldCode "")
            scaffold_diff = self._propose_scaffold_diff(repo)
            if scaffold_diff:
                diffs.append(scaffold_diff)

            state["yellow_initialized"] = True
            state["yellow_framework"] = framework
            state["yellow_init_status"] = "success"
            state["thinking_log"] = state.get("thinking_log", []) + [
                f"Yellow SDK proposed for {framework} project ({len(diffs)} file changes). Run npm i to install."
            ]
            if diffs:
                state["tool_diffs"] = (state.get("tool_diffs") or []) + diffs

            pkg_info = self._read_package_json_yellow_fields(repo)
            if pkg_info:
                state["yellow_version"] = pkg_info.get("yellow_version", "")
                state["yellow_dependencies"] = pkg_info.get("yellow_dependencies", [])
                state["yellow_devDependencies"] = pkg_info.get("yellow_devDependencies", [])
                
            logger.info(f"Yellow init: diffs: {diffs}")
            logger.info(f"Yellow init: pkg_info: {pkg_info}")

        except Exception as e:
            logger.exception("Yellow init failed: %s", e)
            state["yellow_initialized"] = False
            state["yellow_framework"] = ""
            state["yellow_init_status"] = "failed"
            state["thinking_log"] = state.get("thinking_log", []) + [f"Yellow SDK initialization failed: {str(e)}"]

    def _detect_framework(self, package_json_path: Path) -> str:
        try:
            data = json.loads(package_json_path.read_text())
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            if "next" in deps:
                return "nextjs"
            if "express" in deps:
                return "express"
            if "vite" in deps:
                return "vite"
            if "react" in deps:
                return "react"
            return "node"
        except Exception:
            return "node"

    def _propose_package_json_diff(self, repo: Path) -> Optional[Diff]:
        pkg_path = repo / "package.json"
        data = json.loads(pkg_path.read_text())
        deps = dict(data.get("dependencies") or {})
        dev_deps = dict(data.get("devDependencies") or {})
        for dep in YELLOW_DEPENDENCIES:
            deps.setdefault(dep, "latest")
        for dep in YELLOW_DEV_DEPENDENCIES:
            dev_deps.setdefault(dep, "latest")
        data["dependencies"] = deps
        data["devDependencies"] = dev_deps
        content = json.dumps(data, indent=2)
        return make_diff(repo, "package.json", content)

    def _propose_tsconfig_diff(self, repo: Path) -> Optional[Diff]:
        yellow_config = {
            "compilerOptions": {
                "target": "ES2022",
                "module": "ESNext",
                "moduleResolution": "bundler",
                "strict": True,
                "esModuleInterop": True,
                "skipLibCheck": True,
                "outDir": "./dist",
                "rootDir": "./src",
            },
            "include": ["src/**/*"],
            "exclude": ["node_modules"],
        }
        ts_path = repo / "tsconfig.json"
        if ts_path.exists():
            existing = json.loads(ts_path.read_text())
            existing.update(yellow_config)
            content = json.dumps(existing, indent=2)
        else:
            content = json.dumps(yellow_config, indent=2)
        return make_diff(repo, "tsconfig.json", content)

    def _propose_env_diff(self, repo: Path) -> Optional[Diff]:
        """Propose .env only when missing (new file = oldCode '')."""
        if (repo / ".env").exists():
            return None
        return make_diff(repo, ".env", DEFAULT_ENV)

    def _propose_scaffold_diff(self, repo: Path) -> Optional[Diff]:
        """Propose src/yellow.ts only when missing (new file = oldCode '')."""
        rel = "src/yellow.ts"
        if (repo / rel).exists():
            return None
        return make_diff(repo, rel, YELLOW_SCAFFOLD)

    def _read_package_json_yellow_fields(self, repo: Path) -> Optional[Dict[str, Any]]:
        pkg_path = repo / "package.json"
        if not pkg_path.exists():
            return None
        try:
            data = json.loads(pkg_path.read_text())
            return {
                "yellow_version": data.get("version", ""),
                "yellow_dependencies": list((data.get("dependencies") or {}).keys()),
                "yellow_devDependencies": list((data.get("devDependencies") or {}).keys()),
            }
        except Exception as e:
            logger.debug("Read package.json fields: %s", e)
            return None
