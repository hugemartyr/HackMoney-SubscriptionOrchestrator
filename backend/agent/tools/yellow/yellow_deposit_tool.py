# Yellow Sandbox Deposit Tool
# Refactored to match LangGraph workflow patterns

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from langchain_core.callbacks import AsyncCallbackHandler
from agent.tools.yellow.diff_utils import write_file_with_diff


def detect_deposit_requirement(prompt: str) -> bool:
    """Detect whether the user's prompt indicates deposit functionality is required."""
    keywords = [
        "deposit",
        "custody",
        "fund",
        "add funds",
        "top up",
        "top-up",
        "deposit usdc",
        "custody contract",
        "nitrolite deposit",
    ]
    pl = (prompt or "").lower()
    return any(k in pl for k in keywords)


class YellowDepositToolInput(BaseModel):
    """Input schema for the Yellow deposit tool."""
    repo_path: str


class YellowDepositToolOutput(BaseModel):
    """Output schema for tool responses."""
    success: bool
    files_modified: List[str]
    diffs: List[Dict[str, Any]] = []
    message: str
    error: Optional[str] = None


class YellowDepositTool:
    """
    Yellow Sandbox Deposit Tool (LangGraph Compatible)

    - Injects src/lib/yellow/deposit.ts
    - Supports dynamic viem chain resolution
    - Designed to be called after yellow_init and yellow_workflow
    - Returns structured output with diffs for frontend display

    Integration:
    - Called by the "yellow_deposit" node in graph.py
    - Receives: AgentState with repo_path
    - Returns: Updated state with deposit tool injection results
    """

    name = "yellow_deposit"
    description = "Injects Yellow custody deposit utility (deposit.ts) into the project."

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

    async def async_run(self, repo_path: str) -> YellowDepositToolOutput:
        """
        Async entry point for LangGraph integration.
        Injects deposit.ts file and returns structured response.
        """
        try:
            repo = Path(repo_path).resolve()

            if not repo.exists():
                return YellowDepositToolOutput(
                    success=False,
                    files_modified=[],
                    message="Repository path does not exist",
                    error=f"Path not found: {repo_path}"
                )

            if not (repo / "package.json").exists():
                return YellowDepositToolOutput(
                    success=False,
                    files_modified=[],
                    message="Not a Node.js project",
                    error="Missing package.json"
                )

            # Inject deposit.ts
            files_modified, diffs = self._inject_deposit_file(repo)

            return YellowDepositToolOutput(
                success=True,
                files_modified=files_modified,
                diffs=diffs,
                message="Deposit utility (deposit.ts) injected successfully"
            )

        except Exception as e:
            return YellowDepositToolOutput(
                success=False,
                files_modified=[],
                message="Failed to inject deposit utility",
                error=str(e)
            )

    async def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        LangGraph node invocation.

        Input state:
        - repo_path: str
        - needs_deposit: bool (optional, detected from prompt if not set)
        - prompt: str

        Output state:
        - yellow_deposit_status: str
        - yellow_tool_diffs: List[Dict]
        - thinking_log: List[str]
        """
        repo_path = state.get("repo_path")
        prompt = state.get("prompt", "")

        # Respect pre-computed flag if present, else detect from prompt
        requires_deposit = state.get("needs_deposit")
        if requires_deposit is None:
            requires_deposit = detect_deposit_requirement(prompt)

        if not requires_deposit:
            await self.emit_event("thought", content="Deposit functionality not required by prompt; skipping")
            return {
                "yellow_deposit_status": "skipped",
                "thinking_log": state.get("thinking_log", []) + ["Skipped Yellow deposit tool (not required)"]
            }

        if not repo_path:
            error_msg = "repo_path not provided in state"
            await self.emit_event("thought", content=f"❌ Error: {error_msg}")
            return {
                "yellow_deposit_status": "failed",
                "thinking_log": state.get("thinking_log", []) + [f"Yellow deposit failed: {error_msg}"]
            }

        try:
            # Emit start event
            await self.emit_event("tool", name=self.name, status="running")
            await self.emit_event("thought", content="🚀 Injecting Yellow deposit utility...")

            # Execute injection
            result = await self.async_run(repo_path)

            # Emit completion event
            if result.success:
                await self.emit_event("thought", content=f"✅ {result.message}")
            else:
                await self.emit_event("thought", content=f"❌ {result.message}: {result.error}")

            # Return updated state
            return {
                "yellow_deposit_status": "success" if result.success else "failed",
                "yellow_tool_diffs": result.diffs,
                "thinking_log": state.get("thinking_log", []) + [result.message]
            }

        except Exception as e:
            error_msg = f"Yellow deposit tool failed: {str(e)}"
            await self.emit_event("thought", content=f"❌ {error_msg}")
            return {
                "yellow_deposit_status": "failed",
                "thinking_log": state.get("thinking_log", []) + [error_msg]
            }

    # ---------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------

    def _inject_deposit_file(self, repo: Path) -> tuple[List[str], List[Dict[str, Any]]]:
        """Inject deposit.ts file into src/lib/yellow/ directory."""
        deposit_dir = repo / "src" / "lib" / "yellow"
        deposit_dir.mkdir(parents=True, exist_ok=True)

        deposit_file_rel = "src/lib/yellow/deposit.ts"
        deposit_code = self._deposit_ts_code()

        diff = write_file_with_diff(repo, deposit_file_rel, deposit_code)
        diffs = [diff] if diff else []

        return [deposit_file_rel], diffs

    def _deposit_ts_code(self) -> str:
        return r'''import { NitroliteClient, WalletStateSigner } from "@erc7824/nitrolite";
import { createWalletClient, formatUnits, http, parseUnits } from "viem";
import { mnemonicToAccount } from "viem/accounts";
import * as chains from "viem/chains";
import { getContractAddresses } from "./utils";
import { publicClient } from "./auth";
import "dotenv/config";

// --------------------------------------
// USDC CONTRACT MAPPING (HARDCODED)
// --------------------------------------

const USDC_MAP: Record<number, string> = {
  8453: "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913", // Base Mainnet
  84532: "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913", // Base Sepolia (replace)
  11155111: "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913", // Sepolia (replace)
};

// --------------------------------------
// CORE FUNCTION
// --------------------------------------

export async function deposit(amount: string, chainId?: number) {

  if (!process.env.SEED_PHRASE) {
    return { success: false, error: "SEED_PHRASE missing" };
  }

  const resolvedChainId = chainId ?? 8453;

  const chain = Object.values(chains).find(
    (c: any) => c.id === resolvedChainId
  );

  if (!chain) {
    return { success: false, error: "Unsupported chainId" };
  }

  const usdcAddress = USDC_MAP[resolvedChainId];

  if (!usdcAddress || usdcAddress === "0x0000000000000000000000000000000000000000") {
    return { success: false, error: "USDC not configured for this chain" };
  }

  const wallet = mnemonicToAccount(process.env.SEED_PHRASE);

  const walletClient = createWalletClient({
    account: wallet,
    chain,
    transport: http(),
  });

  const balance = await publicClient.readContract({
    address: usdcAddress as `0x${string}`,
    abi: [{
      name: "balanceOf",
      type: "function",
      stateMutability: "view",
      inputs: [{ name: "account", type: "address" }],
      outputs: [{ name: "", type: "uint256" }],
    }],
    functionName: "balanceOf",
    args: [wallet.address],
  });

  const decimals = 6;
  const parsedAmount = parseUnits(amount, decimals);

  if (balance < parsedAmount) {
    return {
      success: false,
      error: "Insufficient USDC balance",
      balance: formatUnits(balance, decimals)
    };
  }

  const nitroliteClient = new NitroliteClient({
    walletClient,
    publicClient: publicClient as any,
    stateSigner: new WalletStateSigner(walletClient),
    addresses: getContractAddresses(resolvedChainId),
    chainId: resolvedChainId,
    challengeDuration: 3600n,
  });

  const txHash = await nitroliteClient.deposit(
    usdcAddress,
    parsedAmount
  );

  const receipt = await publicClient.waitForTransactionReceipt({
    hash: txHash,
  });

  return {
    success: true,
    chainId: resolvedChainId,
    txHash,
    receipt,
  };
}

export default deposit;
'''
