import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from pydantic import BaseModel
from langchain_core.callbacks import AsyncCallbackHandler


class YellowVersionedIntegrationInput(BaseModel):
    """Input for versioned integration tool."""
    repo_path: str
    framework_hint: Optional[str] = None
    requires_versioned: bool = False


class YellowVersionedIntegrationOutput(BaseModel):
    """Output from versioned integration execution."""
    success: bool
    action: Optional[str]  # installed, already_up_to_date, upgraded
    version: str
    files_modified: List[str]
    message: str
    error: Optional[str] = None


def detect_versioned_integration_requirement(prompt: str) -> bool:
    """
    Detect if user prompt requires versioned Yellow integration layer.
    Looks for keywords indicating structured integration, library setup, or framework init.
    """
    keywords = [
        "integration layer", "versioned", "version control",
        "library setup", "initialize", "scaffold",
        "abstract", "abstraction", "helper", "wrapper",
        "reusable", "framework", "sdk layer",
        "config", "configuration", "session"
    ]
    prompt_lower = prompt.lower()
    return any(kw in prompt_lower for kw in keywords)


class YellowVersionedIntegrationTool:
    """
    LangGraph-compatible tool for versioned Yellow integration layer in Next.js/TypeScript.
    
    Creates and maintains a structured integration layer:
    - version.ts: Version tracking
    - config.ts: Configuration and constants
    - utils.ts: Helper functions
    - auth.ts: Authentication utilities
    
    Safe, idempotent, upgrade-aware. Designed to run after yellow_initialiser.
    """
    
    name = "yellow_versioned_integration"
    description = "Create versioned Yellow integration layer in project"

    INTEGRATION_VERSION = "1.0.0"

    def __init__(self, stream_callback: Optional[AsyncCallbackHandler] = None):
        self.stream_callback = stream_callback

    async def emit_event(self, event_type: str, **kwargs) -> None:
        """Emit SSE event through callback."""
        if self.stream_callback:
            await self.stream_callback.on_tool_start(
                {"name": event_type},
                input_str=json.dumps(kwargs)
            )

    async def async_run(self, repo_path: str, framework_hint: Optional[str] = None, requires_versioned: bool = False) -> YellowVersionedIntegrationOutput:
        """
        Async entry point for LangGraph integration.
        Creates versioned Yellow integration layer.
        """
        if not requires_versioned:
            return YellowVersionedIntegrationOutput(
                success=True,
                action="skipped",
                version=self.INTEGRATION_VERSION,
                files_modified=[],
                message="Versioned integration not required for this project"
            )

        try:
            repo = Path(repo_path).resolve()
            if not repo.exists():
                return YellowVersionedIntegrationOutput(
                    success=False,
                    action=None,
                    version=self.INTEGRATION_VERSION,
                    files_modified=[],
                    message="Repository path does not exist",
                    error=f"Path not found: {repo_path}"
                )

            if not (repo / "package.json").exists():
                return YellowVersionedIntegrationOutput(
                    success=False,
                    action=None,
                    version=self.INTEGRATION_VERSION,
                    files_modified=[],
                    message="Not a Node.js project",
                    error="Missing package.json"
                )

            # Emit start
            await self.emit_event("tool", name=self.name, status="running")
            await self.emit_event("thought", content="Setting up versioned integration layer...")

            yellow_dir = repo / "src" / "lib" / "yellow"
            version_file = yellow_dir / "version.ts"

            # Check if layer already exists
            if not yellow_dir.exists():
                await self.emit_event("thought", content="Creating new Yellow integration layer...")
                files = self._inject_full_layer(yellow_dir)
                return YellowVersionedIntegrationOutput(
                    success=True,
                    action="installed",
                    version=self.INTEGRATION_VERSION,
                    files_modified=files,
                    message="Yellow integration layer installed"
                )

            # Check version
            if not version_file.exists():
                return YellowVersionedIntegrationOutput(
                    success=False,
                    action=None,
                    version=self.INTEGRATION_VERSION,
                    files_modified=[],
                    message="Yellow folder exists but version.ts missing",
                    error="Manual intervention required"
                )

            current_version = self._read_version(version_file)

            if current_version == self.INTEGRATION_VERSION:
                await self.emit_event("thought", content="Integration layer already up to date")
                return YellowVersionedIntegrationOutput(
                    success=True,
                    action="already_up_to_date",
                    version=current_version,
                    files_modified=[],
                    message="Yellow integration layer is current"
                )

            if self._is_upgrade_needed(current_version):
                await self.emit_event("thought", content=f"Upgrading from {current_version} to {self.INTEGRATION_VERSION}...")
                files = self._inject_full_layer(yellow_dir, overwrite=True)
                return YellowVersionedIntegrationOutput(
                    success=True,
                    action="upgraded",
                    version=self.INTEGRATION_VERSION,
                    files_modified=files,
                    message=f"Upgraded from {current_version} to {self.INTEGRATION_VERSION}"
                )

            return YellowVersionedIntegrationOutput(
                success=False,
                action=None,
                version=current_version,
                files_modified=[],
                message="Existing version is newer",
                error=f"Version {current_version} is newer than tool version {self.INTEGRATION_VERSION}"
            )

        except Exception as e:
            await self.emit_event("thought", content=f"Versioned integration setup failed: {e}")
            return YellowVersionedIntegrationOutput(
                success=False,
                action=None,
                version=self.INTEGRATION_VERSION,
                files_modified=[],
                message="Versioned integration setup failed",
                error=str(e)
            )

    async def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangGraph node invocation.
        
        Input state:
        - repo_path: str
        - prompt: str (to detect versioned requirement)
        
        Output state:
        - yellow_versioned_status: success/skipped/failed
        - yellow_versioned_action: installed/upgraded/already_up_to_date/skipped
        - yellow_versioned_files: files modified
        """
        repo_path = state.get("repo_path")
        prompt = state.get("prompt", "")
        
        # Detect if versioned integration is needed (prefer parse node flag)
        requires_versioned = state.get("needs_versioned")
        if requires_versioned is None:
            requires_versioned = detect_versioned_integration_requirement(prompt)

        if not requires_versioned:
            await self.emit_event("thought", content="Prompt does not require versioned integration layer")
            return {
                "yellow_versioned_status": "skipped",
                "yellow_versioned_action": "skipped",
                "thinking_log": state.get("thinking_log", []) + ["Versioned integration skipped (not required by prompt)"]
            }
        
        if not repo_path:
            await self.emit_event("thought", content="No repo_path provided for versioned integration")
            return {
                "yellow_versioned_status": "failed",
                "thinking_log": state.get("thinking_log", []) + ["Versioned integration failed: no repo_path"]
            }
        
        # Run and update state
        await self.emit_event("tool", name=self.name, status="running")
        await self.emit_event("thought", content="Creating versioned Yellow integration layer...")

        result = await self.async_run(repo_path, state.get("framework_detected"), True)

        new_state = {
            "yellow_versioned_status": "success" if result.success else "failed",
            "yellow_versioned_action": result.action,
            "yellow_versioned_files": result.files_modified,
            "thinking_log": state.get("thinking_log", []) + [result.message]
        }

        if result.error:
            new_state["versioned_error"] = result.error

        return new_state

    # -----------------------------------------
    # Version Helpers
    # -----------------------------------------

    def _read_version(self, version_file: Path) -> str:
        """Extract version from version.ts file."""
        try:
            content = version_file.read_text()
            return content.split('"')[1]
        except Exception:
            return "0.0.0"

    def _is_upgrade_needed(self, current_version: str) -> bool:
        """Check if upgrade is needed (current < tool version)."""
        return current_version < self.INTEGRATION_VERSION

    # -----------------------------------------
    # Inject Layer
    # -----------------------------------------

    def _inject_full_layer(self, yellow_dir: Path, overwrite: bool = False) -> List[str]:
        """
        Create full Yellow integration layer.
        Returns list of files created/modified.
        """
        yellow_dir.mkdir(parents=True, exist_ok=True)

        files_created = []
        file_templates = {
            "version.ts": self._version_template(),
            "config.ts": self._config_template(),
            "utils.ts": self._utils_template(),
            "auth.ts": self._auth_template(),
        }

        for filename, content in file_templates.items():
            file_path = yellow_dir / filename
            if not file_path.exists() or overwrite:
                file_path.write_text(content)
                files_created.append(f"src/lib/yellow/{filename}")

        return files_created

    # -----------------------------------------
    # Templates
    # -----------------------------------------

    def _version_template(self) -> str:
        return f'export const YELLOW_INTEGRATION_VERSION = "{self.INTEGRATION_VERSION}";'

    def _config_template(self) -> str:
        return """
import { base } from "viem/chains";

export const YELLOW_WS =
  process.env.YELLOW_WS ??
  "wss://clearnet-sandbox.yellow.com/ws";

export const YELLOW_CHAIN = base;

export const AUTH_SCOPE =
  process.env.YELLOW_SCOPE ?? "test.app";

export const APP_NAME =
  process.env.YELLOW_APP_NAME ?? "Test app";

export const SESSION_DURATION = 3600;

export const DEFAULT_ALLOWANCES = [
  {
    asset: "usdc",
    amount: "1",
  },
];
"""

    def _utils_template(self) -> str:
        return """
import { generatePrivateKey, privateKeyToAccount } from "viem/accounts";
import { type Address } from "viem";

export interface SessionKey {
  privateKey: `0x${string}`;
  address: Address;
}

export const generateSessionKey = (): SessionKey => {
  const privateKey = generatePrivateKey();
  const account = privateKeyToAccount(privateKey);
  return { privateKey, address: account.address };
};
"""

    def _auth_template(self) -> str:
        return """
import {
  createAuthRequestMessage,
  createEIP712AuthMessageSigner,
  createAuthVerifyMessage,
  RPCMethod,
  RPCResponse
} from "@erc7824/nitrolite";

import { Client } from "yellow-ts";
import { createWalletClient, http, WalletClient } from "viem";
import { mnemonicToAccount } from "viem/accounts";

import {
  AUTH_SCOPE,
  APP_NAME,
  SESSION_DURATION,
  DEFAULT_ALLOWANCES,
  YELLOW_CHAIN
} from "./config";

import { generateSessionKey, SessionKey } from "./utils";

export function createWalletFromMnemonic(seed: string): WalletClient {
  return createWalletClient({
    account: mnemonicToAccount(seed),
    chain: YELLOW_CHAIN,
    transport: http(),
  });
}

export async function authenticateWallet(
  client: Client,
  walletClient: WalletClient
): Promise<SessionKey> {

  const sessionKey = generateSessionKey();
  const expires = String(Math.floor(Date.now() / 1000) + SESSION_DURATION);

  const authMessage = await createAuthRequestMessage({
    address: walletClient.account?.address!,
    session_key: sessionKey.address,
    application: APP_NAME,
    allowances: DEFAULT_ALLOWANCES,
    expires_at: BigInt(expires),
    scope: AUTH_SCOPE,
  });

  client.listen(async (message: RPCResponse) => {
    if (message.method === RPCMethod.AuthChallenge) {
      const authParams = {
        scope: AUTH_SCOPE,
        application: walletClient.account?.address!,
        participant: sessionKey.address,
        expire: expires,
        allowances: DEFAULT_ALLOWANCES,
        session_key: sessionKey.address,
        expires_at: BigInt(expires),
      };

      const signer = createEIP712AuthMessageSigner(
        walletClient,
        authParams,
        { name: APP_NAME }
      );

      const verifyMsg = await createAuthVerifyMessage(
        signer,
        message
      );

      await client.sendMessage(verifyMsg);
    }
  });

  await client.sendMessage(authMessage);

  return sessionKey;
}
"""