# Yellow Sandbox Tipping Tool
# Refactored to match LangGraph workflow patterns

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from langchain_core.callbacks import AsyncCallbackHandler
from agent.tools.yellow.diff_utils import write_file_with_diff


def detect_tip_requirement(prompt: str) -> bool:
    """Detect whether the user's prompt indicates tipping functionality is required."""
    keywords = [
        "tip",
        "tipping",
        "send tip",
        "transfer",
        "pay",
        "payment",
        "donate",
        "donation",
    ]
    pl = (prompt or "").lower()
    return any(k in pl for k in keywords)


class YellowTipToolInput(BaseModel):
    """Input schema for the Yellow tip tool."""
    repo_path: str


class YellowTipToolOutput(BaseModel):
    """Output schema for tool responses."""
    success: bool
    files_modified: List[str]
    diffs: List[Dict[str, Any]] = []
    message: str
    error: Optional[str] = None


class YellowTipTool:
    """
    Yellow Sandbox Tipping Tool (LangGraph Compatible)

    - Injects src/lib/yellow/tip.ts
    - Uses SEED_PHRASE from .env
    - Designed to be called after yellow_init and yellow_workflow
    - Returns structured output with diffs for frontend display

    Integration:
    - Called by the "yellow_tip" node in graph.py
    - Receives: AgentState with repo_path
    - Returns: Updated state with tip tool injection results
    """

    name = "yellow_tip"
    description = "Injects Yellow sandbox tipping utility (tip.ts) into the project."

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

    async def async_run(self, repo_path: str) -> YellowTipToolOutput:
        """
        Async entry point for LangGraph integration.
        Injects tip.ts file and returns structured response.
        """
        try:
            repo = Path(repo_path).resolve()

            if not repo.exists():
                return YellowTipToolOutput(
                    success=False,
                    files_modified=[],
                    message="Repository path does not exist",
                    error=f"Path not found: {repo_path}"
                )

            if not (repo / "package.json").exists():
                return YellowTipToolOutput(
                    success=False,
                    files_modified=[],
                    message="Not a Node.js project",
                    error="Missing package.json"
                )

            # Inject tip.ts
            files_modified, diffs = self._inject_tip_file(repo)

            return YellowTipToolOutput(
                success=True,
                files_modified=files_modified,
                diffs=diffs,
                message="Tipping utility (tip.ts) injected successfully"
            )

        except Exception as e:
            return YellowTipToolOutput(
                success=False,
                files_modified=[],
                message="Failed to inject tipping utility",
                error=str(e)
            )

    async def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangGraph node invocation.

        Input state:
        - repo_path: str
        - needs_tip: bool (optional, detected from prompt if not set)
        - prompt: str

        Output state:
        - yellow_tip_status: str
        - yellow_tool_diffs: List[Dict]
        - thinking_log: List[str]
        """
        repo_path = state.get("repo_path")
        prompt = state.get("prompt", "")

        # Respect pre-computed flag if present, else detect from prompt
        requires_tip = state.get("needs_tip")
        if requires_tip is None:
            requires_tip = detect_tip_requirement(prompt)

        if not requires_tip:
            await self.emit_event("thought", content="Tipping functionality not required by prompt; skipping")
            return {
                "yellow_tip_status": "skipped",
                "thinking_log": state.get("thinking_log", []) + ["Skipped Yellow tipping tool (not required)"]
            }

        if not repo_path:
            error_msg = "repo_path not provided in state"
            await self.emit_event("thought", content=f"❌ Error: {error_msg}")
            return {
                "yellow_tip_status": "failed",
                "thinking_log": state.get("thinking_log", []) + [f"Yellow tip failed: {error_msg}"]
            }

        try:
            # Emit start event
            await self.emit_event("tool", name=self.name, status="running")
            await self.emit_event("thought", content="🚀 Injecting Yellow tipping utility...")

            # Execute injection
            result = await self.async_run(repo_path)

            # Emit completion event
            if result.success:
                await self.emit_event("thought", content=f"✅ {result.message}")
            else:
                await self.emit_event("thought", content=f"❌ {result.message}: {result.error}")

            # Return updated state
            return {
                "yellow_tip_status": "success" if result.success else "failed",
                "yellow_tool_diffs": result.diffs,
                "thinking_log": state.get("thinking_log", []) + [result.message]
            }

        except Exception as e:
            error_msg = f"Yellow tipping tool failed: {str(e)}"
            await self.emit_event("thought", content=f"❌ {error_msg}")
            return {
                "yellow_tip_status": "failed",
                "thinking_log": state.get("thinking_log", []) + [error_msg]
            }

    # ---------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------

    def _inject_tip_file(self, repo: Path) -> tuple[List[str], List[Dict[str, Any]]]:
        """Inject tip.ts file into src/lib/yellow/ directory."""
        tip_dir = repo / "src" / "lib" / "yellow"
        tip_dir.mkdir(parents=True, exist_ok=True)

        tip_file_rel = "src/lib/yellow/tip.ts"
        tip_code = self._tip_ts_code()

        diff = write_file_with_diff(repo, tip_file_rel, tip_code)
        diffs = [diff] if diff else []

        return [tip_file_rel], diffs

    def _tip_ts_code(self) -> str:
        return r'''import { Client } from "yellow-ts";
import {
  createAuthRequestMessage,
  createEIP712AuthMessageSigner,
  createAuthVerifyMessage,
  createECDSAMessageSigner,
  createTransferMessage,
  RPCMethod,
  RPCResponse,
  AuthChallengeResponse
} from "@erc7824/nitrolite";

import { createWalletClient, http } from "viem";
import { mnemonicToAccount, isAddress } from "viem/accounts";
import { base } from "viem/chains";

import { generateSessionKey } from "./utils";
import { YELLOW_WS, AUTH_SCOPE, APP_NAME } from "./config";

import "dotenv/config";

// -------------------------------
// TOKEN RESOLUTION
// -------------------------------

const TOKEN_MAP: Record<string, string> = {
  usdc: "usdc",
  eth: "eth",
  sepolia: "eth"
};

// -------------------------------
// CORE TIP FUNCTION
// -------------------------------

export async function tip(
  destination: `0x${string}`,
  amount: string,
  assetSymbol: string
) {

  if (!process.env.SEED_PHRASE) {
    return { success: false, error: "SEED_PHRASE missing" };
  }

  if (!isAddress(destination)) {
    return { success: false, error: "Invalid destination address" };
  }

  const asset = TOKEN_MAP[assetSymbol.toLowerCase()];
  if (!asset) {
    return { success: false, error: "Unsupported asset" };
  }

  const wallet = mnemonicToAccount(process.env.SEED_PHRASE);
  const walletClient = createWalletClient({
    account: wallet,
    chain: base,
    transport: http(),
  });

  const sessionKey = generateSessionKey();
  const yellow = new Client({ url: YELLOW_WS });

  await yellow.connect();

  const expires = String(Math.floor(Date.now() / 1000) + 3600);

  const authMessage = await createAuthRequestMessage({
    address: wallet.address,
    session_key: sessionKey.address,
    application: APP_NAME,
    allowances: [{ asset, amount }],
    expires_at: BigInt(expires),
    scope: AUTH_SCOPE,
  });

  let resolved = false;

  return new Promise(async (resolve) => {

    yellow.listen(async (message: RPCResponse) => {

      // ------------------ AUTH CHALLENGE
      if (message.method === RPCMethod.AuthChallenge) {

        const authParams = {
          scope: AUTH_SCOPE,
          application: wallet.address,
          participant: sessionKey.address,
          expire: expires,
          allowances: [{ asset, amount }],
          session_key: sessionKey.address,
          expires_at: BigInt(expires),
        };

        const signer = createEIP712AuthMessageSigner(
          walletClient,
          authParams,
          { name: APP_NAME }
        );

        const verify = await createAuthVerifyMessage(
          signer,
          message as AuthChallengeResponse
        );

        await yellow.sendMessage(verify);
      }

      // ------------------ AUTH VERIFIED
      if (message.method === RPCMethod.AuthVerify) {

        const sessionSigner = createECDSAMessageSigner(
          sessionKey.privateKey
        );

        const transfer = await createTransferMessage(
          sessionSigner,
          {
            destination,
            allocations: [
              { asset, amount }
            ],
          }
        );

        await yellow.sendMessage(transfer);
      }

      // ------------------ SUCCESS
      if (message.method === RPCMethod.BalanceUpdate && !resolved) {
        resolved = true;
        await yellow.disconnect();
        resolve({
          success: true,
          tx: message.params
        });
      }

      // ------------------ ERROR
      if (message.method === RPCMethod.Error && !resolved) {
        resolved = true;
        await yellow.disconnect();
        resolve({
          success: false,
          error: message.params
        });
      }
    });

    await yellow.sendMessage(authMessage);
  });
}

export default tip;
'''
