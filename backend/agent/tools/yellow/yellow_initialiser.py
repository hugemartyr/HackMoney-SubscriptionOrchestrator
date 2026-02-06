#The Code for initilaising the Yellow SDK requirements in the code base such as tsconfig.js updates etc

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel
from langchain_core.callbacks import AsyncCallbackHandler
from agent.tools.yellow.diff_utils import write_file_with_diff


class YellowInitializerInput(BaseModel):
    """Input schema for the Yellow SDK initializer tool."""
    repo_path: str
    framework_hint: Optional[str] = None


class YellowInitializerOutput(BaseModel):
    """Output schema for tool responses."""
    success: bool
    framework_detected: str
    steps_completed: Dict[str, bool]
    files_modified: list[str]
    diffs: list[Dict[str, Any]] = []
    message: str
    error: Optional[str] = None


def detect_yellow_requirement(prompt: str) -> bool:
    """Detect whether the user's prompt indicates Yellow SDK is required."""
    kw = [
        "yellow",
        "nitrolite",
        "state channel",
        "state channels",
        "clear node",
        "clearnode",
        "off-chain",
        "l3",
        "yellow network",
        "nitro",
    ]
    pl = (prompt or "").lower()
    return any(k in pl for k in kw)


class YellowInitializerTool:
    """
    LangGraph-compatible tool for initializing Yellow SDK in Node.js repositories.
    
    This tool is designed to be called as a node in the LangGraph workflow,
    receiving AgentState and returning updated AgentState with streamed events.
    
    Integration:
    - Called by the "initializer" node in graph.py
    - Receives: AgentState with repo_path
    - Yields: SSE events ("thought", "tool", "code_update")
    - Returns: Updated AgentState with initialization results
    """
    
    name = "yellow_sdk_initializer"
    description = "Initialize Yellow SDK in a Node.js project with auto-detection of framework and configuration setup"
    
    def __init__(self, stream_callback: Optional[AsyncCallbackHandler] = None):
        """Initialize with optional stream callback for SSE emission."""
        self.stream_callback = stream_callback

    async def emit_event(self, event_type: str, **kwargs) -> None:
        """Emit SSE event through callback."""
        if self.stream_callback:
            await self.stream_callback.on_tool_start(
                {"name": event_type},
                input_str=json.dumps(kwargs)
            )

    async def async_run(self, repo_path: str, framework_hint: Optional[str] = None) -> YellowInitializerOutput:
        """
        Async entry point for LangGraph integration.
        Gracefully handles execution and returns structured response.
        """
        try:
            return self._execute_init(repo_path, framework_hint)
        except Exception as e:
            return YellowInitializerOutput(
                success=False,
                framework_detected="unknown",
                steps_completed={},
                files_modified=[],
                message="Yellow SDK initialization failed",
                error=str(e)
            )

    async def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangGraph node invocation.
        
        Input state:
        - repo_path: str
        - framework_hint: Optional[str]
        
        Output state:
        - yellow_initialized: bool
        - framework_detected: str
        - initialization_results: YellowInitializerOutput (as dict)
        - messages: Updated with initialization results
        """
        repo_path = state.get("repo_path")
        framework_hint = state.get("framework_hint")
        prompt = state.get("prompt", "")

        # Respect pre-computed flag if present, else detect from prompt
        requires_yellow = state.get("needs_yellow")
        if requires_yellow is None:
            requires_yellow = detect_yellow_requirement(prompt)

        if not requires_yellow:
            await self.emit_event("thought", content="Yellow SDK not required by prompt; skipping initializer")
            return {
                "yellow_initialized": False,
                "initialization_results": {"success": True, "message": "Skipped (not required)"},
                "messages": state.get("messages", []) + [{"role": "assistant", "content": "Skipped Yellow initialization (not required by prompt)"}]
            }
        
        if not repo_path:
            error_msg = "repo_path not provided in state"
            await self.emit_event("thought", content=f"❌ Error: {error_msg}")
            return {
                "yellow_initialized": False,
                "initialization_results": {
                    "success": False,
                    "error": error_msg
                },
                "messages": state.get("messages", []) + [{"role": "assistant", "content": error_msg}]
            }
        
        try:
            # Emit start event
            await self.emit_event("tool", name=self.name, status="running")
            await self.emit_event("thought", content=f"🚀 Initializing Yellow SDK in {repo_path}")
            
            # Execute initialization
            result = self._execute_init(repo_path, framework_hint)
            
            # Emit completion event
            if result.success:
                await self.emit_event("thought", content=f"✅ {result.message}")
                
                # Optionally emit code update if scaffold was created
                if "src/yellow.ts" in result.files_modified:
                    scaffold = self._read_scaffold_file(Path(repo_path) / "src" / "yellow.ts")
                    await self.emit_event("code_update", content=scaffold)
            else:
                await self.emit_event("thought", content=f"❌ Initialization failed: {result.error}")
            
            # Return updated state
            return {
                "yellow_initialized": result.success,
                "framework_detected": result.framework_detected,
                "initialization_results": result.dict(),
                "yellow_tool_diffs": result.diffs,
                "messages": state.get("messages", []) + [{
                    "role": "assistant",
                    "content": result.message
                }]
            }
            
        except Exception as e:
            error_msg = f"Yellow SDK initialization failed: {str(e)}"
            await self.emit_event("thought", content=f"❌ {error_msg}")
            return {
                "yellow_initialized": False,
                "initialization_results": {"success": False, "error": str(e)},
                "messages": state.get("messages", []) + [{"role": "assistant", "content": error_msg}]
            }

    def _execute_init(self, repo_path: str, framework_hint: Optional[str] = None) -> YellowInitializerOutput:
        """
        Core initialization logic.
        Returns structured YellowInitializerOutput.
        """
        repo = Path(repo_path).resolve()

        if not repo.exists():
            return YellowInitializerOutput(
                success=False,
                framework_detected="unknown",
                steps_completed={},
                files_modified=[],
                message="Repository path does not exist",
                error=f"Path not found: {repo_path}"
            )

        package_json = repo / "package.json"
        if not package_json.exists():
            return YellowInitializerOutput(
                success=False,
                framework_detected="unknown",
                steps_completed={},
                files_modified=[],
                message="Not a Node.js project",
                error="No package.json found in repository"
            )

        framework = framework_hint or self._detect_framework(package_json)
        files_modified = []
        diffs: list[Dict[str, Any]] = []
        steps_completed = {
            "dependencies_installed": False,
            "typescript_configured": False,
            "env_created": False,
            "wallet_generated": False,
            "scaffold_injected": False
        }

        try:
            # Step 1: Install dependencies
            self._install_dependencies(repo)
            steps_completed["dependencies_installed"] = True

            # Step 2: Configure TypeScript
            ts_files, ts_diffs = self._setup_typescript(repo)
            steps_completed["typescript_configured"] = True
            files_modified.extend(ts_files)
            diffs.extend(ts_diffs)

            # Step 3: Setup environment and wallet
            env_result = self._setup_env(repo)
            steps_completed.update(env_result["steps"])
            files_modified.extend(env_result["files"])
            diffs.extend(env_result["diffs"])

            # Step 4: Inject Yellow scaffold
            scaffold_files, scaffold_diffs = self._inject_scaffold(repo, framework)
            steps_completed["scaffold_injected"] = True
            files_modified.extend(scaffold_files)
            diffs.extend(scaffold_diffs)

            return YellowInitializerOutput(
                success=True,
                framework_detected=framework,
                steps_completed=steps_completed,
                files_modified=files_modified,
                diffs=diffs,
                message=f"Yellow SDK initialized successfully for {framework} project"
            )

        except Exception as e:
            return YellowInitializerOutput(
                success=False,
                framework_detected=framework,
                steps_completed=steps_completed,
                files_modified=files_modified,
                diffs=diffs,
                message="Yellow SDK initialization failed partway through",
                error=str(e)
            )

    # --------------------------------------------------
    # Framework Detection
    # --------------------------------------------------

    def _detect_framework(self, package_json_path: Path) -> str:
        """Auto-detect framework from package.json dependencies."""
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

    # --------------------------------------------------
    # Install Dependencies
    # --------------------------------------------------

    def _run_cmd(self, cmd: str, cwd: Path) -> None:
        """Execute shell command and raise on failure."""
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            shell=True,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Command failed: {cmd}\nStderr: {result.stderr}")

    def _install_dependencies(self, repo: Path) -> None:
        """Install Yellow SDK dependencies."""
        self._run_cmd("npm install @erc7824/nitrolite viem dotenv", repo)
        self._run_cmd("npm install -D typescript @types/node tsx", repo)

    # --------------------------------------------------
    # TypeScript Setup
    # --------------------------------------------------

    def _setup_typescript(self, repo: Path) -> tuple[list[str], list[Dict[str, Any]]]:
        """Configure TypeScript safely merging with existing tsconfig.json."""
        tsconfig_path = repo / "tsconfig.json"

        yellow_config = {
            "compilerOptions": {
                "target": "ES2022",
                "module": "ESNext",
                "moduleResolution": "bundler",
                "strict": True,
                "esModuleInterop": True,
                "skipLibCheck": True,
                "outDir": "./dist",
                "rootDir": "./src"
            },
            "include": ["src/**/*"],
            "exclude": ["node_modules"]
        }

        modified_files = []
        diffs: list[Dict[str, Any]] = []

        if tsconfig_path.exists():
            existing = json.loads(tsconfig_path.read_text())
            existing.update(yellow_config)
            content = json.dumps(existing, indent=2)
            diff = write_file_with_diff(repo, "tsconfig.json", content)
            if diff:
                diffs.append(diff)
        else:
            content = json.dumps(yellow_config, indent=2)
            diff = write_file_with_diff(repo, "tsconfig.json", content)
            if diff:
                diffs.append(diff)

        modified_files.append("tsconfig.json")
        return modified_files, diffs

    # --------------------------------------------------
    # Environment + Wallet
    # --------------------------------------------------

    def _setup_env(self, repo: Path) -> Dict[str, Any]:
        """Setup .env file with Yellow config and generate wallet if needed."""
        env_path = repo / ".env"

        default_env = """PRIVATE_KEY=
SEPOLIA_RPC_URL=
BASE_RPC_URL=
CLEARNODE_WS_URL=wss://clearnet-sandbox.yellow.com/ws
"""

        modified_files = []
        diffs: list[Dict[str, Any]] = []
        steps = {
            "env_created": False,
            "wallet_generated": False
        }

        if not env_path.exists():
            diff = write_file_with_diff(repo, ".env", default_env)
            if diff:
                diffs.append(diff)
            modified_files.append(".env")
            steps["env_created"] = True

        content = env_path.read_text()

        if "PRIVATE_KEY=" in content and "0x" not in content:
            try:
                private_key = self._generate_wallet(repo)
                content = content.replace("PRIVATE_KEY=", f"PRIVATE_KEY={private_key}")
                diff = write_file_with_diff(repo, ".env", content)
                if diff:
                    diffs.append(diff)
                steps["wallet_generated"] = True
                if ".env" not in modified_files:
                    modified_files.append(".env")
            except Exception as e:
                print(f"Warning: Failed to generate wallet: {e}")

        return {
            "files": modified_files,
            "steps": steps,
            "diffs": diffs,
        }

    def _generate_wallet(self, repo: Path) -> str:
        """Generate a dev wallet using viem."""
        script = """
import { generatePrivateKey } from 'viem/accounts';
const privateKey = generatePrivateKey();
console.log(privateKey);
"""

        temp_script = repo / "__wallet_gen__.mjs"
        temp_script.write_text(script)

        try:
            result = subprocess.check_output(
                f"node {temp_script.name}",
                cwd=str(repo),
                shell=True,
                text=True
            )
            return result.strip()
        finally:
            if temp_script.exists():
                temp_script.unlink()

    # --------------------------------------------------
    # Yellow Scaffold Injection
    # --------------------------------------------------

    def _inject_scaffold(self, repo: Path, framework: str) -> tuple[list[str], list[Dict[str, Any]]]:
        """Inject Yellow initialization scaffold."""
        src_dir = repo / "src"
        src_dir.mkdir(exist_ok=True)

        target = src_dir / "yellow.ts"

        scaffold = """import WebSocket from 'ws';
import { createAppSessionMessage } from '@erc7824/nitrolite';
import dotenv from 'dotenv';

dotenv.config();

/**
 * Initialize Yellow SDK connection to ClearNode.
 * This function establishes a WebSocket connection for state channel operations.
 */
export async function initYellow(): Promise<WebSocket> {
  const clearNodeUrl = process.env.CLEARNODE_WS_URL || 'wss://clearnet-sandbox.yellow.com/ws';
  
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(clearNodeUrl);

    ws.onopen = () => {
      console.log('[Yellow] Connected to ClearNode');
      resolve(ws);
    };

    ws.onerror = (error) => {
      console.error('[Yellow] WebSocket connection error:', error);
      reject(error);
    };

    ws.onmessage = (event) => {
      console.log('[Yellow] Message received:', event.data);
    };

    ws.onclose = () => {
      console.log('[Yellow] Disconnected from ClearNode');
    };
  });
}

export default initYellow;
"""

        modified_files = []
        diffs: list[Dict[str, Any]] = []

        if not target.exists():
            diff = write_file_with_diff(repo, str(target.relative_to(repo)), scaffold)
            if diff:
                diffs.append(diff)
            modified_files.append(str(target.relative_to(repo)))

        return modified_files, diffs

    def _read_scaffold_file(self, path: Path) -> str:
        """Read scaffold file for code_update event."""
        if path.exists():
            return path.read_text()
        return ""
