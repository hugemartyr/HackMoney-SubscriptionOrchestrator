import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from pydantic import BaseModel
from langchain_core.callbacks import AsyncCallbackHandler


class YellowMultiPartyInput(BaseModel):
    """Input for multiparty workflow tool."""
    repo_path: str
    framework_hint: Optional[str] = None
    requires_multiparty: bool = False


class YellowMultiPartyOutput(BaseModel):
    """Output from multiparty workflow execution."""
    success: bool
    route_created: Optional[str]
    files_modified: List[str]
    message: str
    error: Optional[str] = None


def detect_multiparty_requirement(prompt: str) -> bool:
    """
    Detect if user prompt requires multiparty Yellow workflow.
    Looks for keywords indicating multi-party, multi-wallet, or collaborative features.
    """
    keywords = [
        "multiparty", "multi-party", "multi party",
        "two wallet", "two wallets", "dual wallet", "multiple wallet",
        "collaborative", "collaboration", "multi-sig", "multisig",
        "shared state", "shared session", "joint session",
        "participant", "counterparty", "peer", "partner",
        "bilateral", "mutual", "consensus", "agreement",
        "allocate", "allocation", "distribution"
    ]
    prompt_lower = prompt.lower()
    return any(kw in prompt_lower for kw in keywords)


class YellowNextMultiPartyFullLifecycle:
    """
    LangGraph-compatible tool for multiparty Yellow workflows in Next.js.
    
    Implements full multi-party session lifecycle:
    - Create session with two participants
    - Submit state update
    - Close session with dual signatures
    
    Designed to be called conditionally after `yellow_initialiser` detects multiparty requirements.
    """
    
    name = "yellow_next_multi_party_full_lifecycle"
    description = "Integrate full multi-party Yellow session lifecycle into a Next.js project"

    REQUIRED_PACKAGES = [
        "yellow-ts",
        "@erc7824/nitrolite",
        "viem",
        "ws",
        "dotenv"
    ]

    SANDBOX_URL = "wss://clearnet-sandbox.yellow.com/ws"

    def __init__(self, stream_callback: Optional[AsyncCallbackHandler] = None):
        self.stream_callback = stream_callback

    async def emit_event(self, event_type: str, **kwargs) -> None:
        """Emit SSE event through callback."""
        if self.stream_callback:
            await self.stream_callback.on_tool_start(
                {"name": event_type},
                input_str=json.dumps(kwargs)
            )

    async def async_run(self, repo_path: str, framework_hint: Optional[str] = None, requires_multiparty: bool = False) -> YellowMultiPartyOutput:
        """
        Async entry point for LangGraph integration.
        Executes multiparty workflow setup.
        """
        if not requires_multiparty:
            return YellowMultiPartyOutput(
                success=True,
                route_created=None,
                files_modified=[],
                message="Multiparty not required for this project"
            )

        try:
            repo = Path(repo_path).resolve()
            if not repo.exists():
                return YellowMultiPartyOutput(
                    success=False,
                    route_created=None,
                    files_modified=[],
                    message="Repository path does not exist",
                    error=f"Path not found: {repo_path}"
                )

            if not (repo / "package.json").exists():
                return YellowMultiPartyOutput(
                    success=False,
                    route_created=None,
                    files_modified=[],
                    message="Not a Node.js project",
                    error="Missing package.json"
                )

            # Emit start
            await self.emit_event("tool", name=self.name, status="running")
            await self.emit_event("thought", content="Setting up multiparty workflow...")

            # Check if Next.js
            if not self._is_next(repo):
                return YellowMultiPartyOutput(
                    success=False,
                    route_created=None,
                    files_modified=[],
                    message="Next.js project required",
                    error="Multiparty workflow requires Next.js"
                )

            # Execute setup
            self._install_dependencies(repo)
            self._ensure_env(repo)
            route_path = self._create_route(repo)
            files = self._update_scripts(repo)
            files.append(str(Path(route_path).relative_to(repo)))

            await self.emit_event("thought", content="Multiparty route created successfully")

            return YellowMultiPartyOutput(
                success=True,
                route_created=str(route_path),
                files_modified=files,
                message="Multiparty workflow setup complete. Run `npm run dev` then call /api/yellow/multi-party"
            )

        except Exception as e:
            await self.emit_event("thought", content=f"Multiparty setup failed: {e}")
            return YellowMultiPartyOutput(
                success=False,
                route_created=None,
                files_modified=[],
                message="Multiparty setup failed",
                error=str(e)
            )

    async def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangGraph node invocation.
        
        Input state:
        - repo_path: str
        - prompt: str (to detect multiparty)
        
        Output state:
        - yellow_multiparty_status: success/skipped/failed
        - yellow_multiparty_route: path to created route
        - yellow_multiparty_files: files modified
        """
        repo_path = state.get("repo_path")
        prompt = state.get("prompt", "")
        
        # Detect if multiparty is needed (prefer parse node flag)
        requires_multiparty = state.get("needs_multiparty")
        if requires_multiparty is None:
            requires_multiparty = detect_multiparty_requirement(prompt)
        
        if not requires_multiparty:
            await self.emit_event("thought", content="Prompt does not require multiparty workflow")
            return {
                "yellow_multiparty_status": "skipped",
                "thinking_log": state.get("thinking_log", []) + ["Multiparty workflow skipped (not required by prompt)"]
            }
        
        if not repo_path:
            await self.emit_event("thought", content="No repo_path provided for multiparty setup")
            return {
                "yellow_multiparty_status": "failed",
                "thinking_log": state.get("thinking_log", []) + ["Multiparty failed: no repo_path"]
            }
        
        # Run and update state
        await self.emit_event("tool", name=self.name, status="running")
        await self.emit_event("thought", content="Setting up multiparty Yellow workflow...")

        result = await self.async_run(repo_path, state.get("framework_detected"), True)

        new_state = {
            "yellow_multiparty_status": "success" if result.success else "failed",
            "yellow_multiparty_route": result.route_created,
            "yellow_multiparty_files": result.files_modified,
            "thinking_log": state.get("thinking_log", []) + [result.message]
        }

        if result.error:
            new_state["multiparty_error"] = result.error

        return new_state

    # --------------------------------------------------
    # Helpers
    # --------------------------------------------------

    async def _run_cmd(self, cmd: List[str], cwd: Path, timeout: int = 60) -> Tuple[str, str]:
        """
        Safely execute command and capture output.
        
        Returns (stdout, stderr)
        Raises exception if command fails.
        """
        try:
            result = subprocess.run(
                cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True
            )
            return result.stdout, result.stderr
        except subprocess.TimeoutExpired as e:
            raise Exception(f"Command timeout after {timeout}s: {' '.join(cmd)}")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Command failed: {' '.join(cmd)}\nStderr: {e.stderr}")

    def _is_next(self, repo: Path) -> bool:
        """Check if repository is a Next.js project."""
        try:
            pkg = json.loads((repo / "package.json").read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            return "next" in deps
        except Exception:
            return False

    def _check_dep(self, repo: Path, dep: str) -> bool:
        """Check if dependency exists in package.json."""
        try:
            pkg = json.loads((repo / "package.json").read_text())
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            return dep in deps
        except Exception:
            return False

    def _install_dependencies(self, repo: Path) -> None:
        """Install all required packages."""
        subprocess.run(
            ["npm", "install"],
            cwd=str(repo),
            capture_output=True,
            check=True
        )
        
        # Install Yellow SDK and dependencies
        all_packages = ["npm", "install"] + self.REQUIRED_PACKAGES
        subprocess.run(
            all_packages,
            cwd=str(repo),
            capture_output=True,
            check=True
        )

    def _ensure_env(self, repo: Path) -> None:
        """Create .env file if it doesn't exist."""
        env_path = repo / ".env"
        if not env_path.exists():
            env_path.write_text(
                "SEED_PHRASE=\nWALLET_2_SEED_PHRASE=\n"
            )

    def _update_scripts(self, repo: Path) -> List[str]:
        """Update package.json with Yellow multiparty script. Returns list of modified files."""
        pkg_path = repo / "package.json"
        pkg = json.loads(pkg_path.read_text())

        if "scripts" not in pkg:
            pkg["scripts"] = {}

        pkg["scripts"]["yellow:multi"] = \
            "curl http://localhost:3000/api/yellow/multi-party"

        pkg_path.write_text(json.dumps(pkg, indent=2))
        return [str(pkg_path.relative_to(repo))]

    # --------------------------------------------------
    # Create Route
    # --------------------------------------------------

    def _create_route(self, repo: Path) -> Path:
        app_router = repo / "src" / "app" / "api" / "yellow" / "multi-party"

        app_router.mkdir(parents=True, exist_ok=True)
        route_file = app_router / "route.ts"
        route_file.write_text(self._route_template())

        return route_file

    # --------------------------------------------------
    # Full Lifecycle Route Template
    # --------------------------------------------------

    def _route_template(self) -> str:
        return f"""
import {{ NextResponse }} from "next/server";
import {{ Client }} from "yellow-ts";
import {{
  createAppSessionMessage,
  createSubmitAppStateMessage,
  createCloseAppSessionMessage,
  createECDSAMessageSigner
}} from "@erc7824/nitrolite";
import {{ createWalletClient, http }} from "viem";
import {{ base }} from "viem/chains";
import {{ mnemonicToAccount }} from "viem/accounts";
import "dotenv/config";

export async function GET() {{
  try {{
    const yellow = new Client({{
      url: "{self.SANDBOX_URL}",
    }});

    await yellow.connect();

    const wallet1 = createWalletClient({{
      account: mnemonicToAccount(process.env.SEED_PHRASE!),
      chain: base,
      transport: http(),
    }});

    const wallet2 = createWalletClient({{
      account: mnemonicToAccount(process.env.WALLET_2_SEED_PHRASE!),
      chain: base,
      transport: http(),
    }});

    const user = wallet1.account.address;
    const partner = wallet2.account.address;

    // Authenticate both
    const sessionKey1 = await yellow.authenticate(wallet1);
    const signer1 = createECDSAMessageSigner(sessionKey1.privateKey);

    const sessionKey2 = await yellow.authenticate(wallet2);
    const signer2 = createECDSAMessageSigner(sessionKey2.privateKey);

    // 1️⃣ Create Session
    const createMsg = await createAppSessionMessage(
      signer1,
      {{
        definition: {{
          protocol: 4,
          participants: [user, partner],
          weights: [50, 50],
          quorum: 100,
          challenge: 0,
          nonce: Date.now(),
          application: "Stateless Full Lifecycle"
        }},
        allocations: [
          {{ participant: user, asset: "usdc", amount: "0.01" }},
          {{ participant: partner, asset: "usdc", amount: "0.00" }}
        ]
      }}
    );

    const createRes = await yellow.sendMessage(createMsg);
    const sessionId = createRes.params.appSessionId;

    // 2️⃣ Submit State Update
    const updateMsg = await createSubmitAppStateMessage(
      signer1,
      {{
        app_session_id: sessionId,
        allocations: [
          {{ participant: user, asset: "usdc", amount: "0.00" }},
          {{ participant: partner, asset: "usdc", amount: "0.01" }}
        ]
      }}
    );

    await yellow.sendMessage(updateMsg);

    // 3️⃣ Close Session
    const closeMsgRaw = await createCloseAppSessionMessage(
      signer1,
      {{
        app_session_id: sessionId,
        allocations: [
          {{ participant: user, asset: "usdc", amount: "0.00" }},
          {{ participant: partner, asset: "usdc", amount: "0.01" }}
        ]
      }}
    );

    const closeMsg = JSON.parse(closeMsgRaw);

    // second signature
    const sig2 = await signer2(closeMsg.req);
    closeMsg.sig.push(sig2);

    const closeRes = await yellow.sendMessage(
      JSON.stringify(closeMsg)
    );

    await yellow.disconnect();

    return NextResponse.json({{
      success: true,
      sessionId,
      closeResponse: closeRes
    }});

  }} catch (err: any) {{
    return NextResponse.json(
      {{ error: err.message }},
      {{ status: 500 }}
    );
  }}
}}
"""