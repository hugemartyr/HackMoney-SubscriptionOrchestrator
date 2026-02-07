import subprocess
from pathlib import Path
from typing import Dict, Any


class YellowDepositTool:
    """
    Deposits USDC to Nitrolite custody contract.

    - Injects src/lib/yellow/deposit.ts
    - Supports dynamic viem chain resolution
    - Defaults to Base if chainId not provided
    - Returns structured JSON
    """

    name = "yellow_deposit"
    description = "Injects and executes Yellow custody deposit tool."

    # ---------------------------------------------------------
    # ENTRY
    # ---------------------------------------------------------

    def run(
        self,
        repo_path: str,
        amount: str,
        chain_id: int | None = None,
        execute: bool = True,
    ) -> Dict[str, Any]:

        repo = Path(repo_path).resolve()
        deposit_file = repo / "src" / "lib" / "yellow" / "deposit.ts"

        if not repo.exists():
            return {"success": False, "error": "Repo not found"}

        deposit_file.parent.mkdir(parents=True, exist_ok=True)

        deposit_file.write_text(self._deposit_ts_code())

        if not execute:
            return {
                "success": True,
                "message": "deposit.ts injected successfully"
            }

        try:
            cmd = ["npx", "tsx", "src/lib/yellow/deposit.ts", amount]
            if chain_id:
                cmd.append(str(chain_id))

            result = subprocess.run(
                cmd,
                cwd=repo,
                capture_output=True,
                text=True,
                timeout=120,
            )

            return {
                "success": True,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    # ---------------------------------------------------------
    # TS CODE INJECTED
    # ---------------------------------------------------------

    def _deposit_ts_code(self) -> str:
        return r'''
import { NitroliteClient, WalletStateSigner } from "@erc7824/nitrolite";
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
  84532: "0x0000000000000000000000000000000000000000", // Base Sepolia (replace)
  11155111: "0x0000000000000000000000000000000000000000", // Sepolia (replace)
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

// --------------------------------------
// CLI SUPPORT
// --------------------------------------

if (require.main === module) {

  const [amount, chainId] = process.argv.slice(2);

  deposit(amount, chainId ? Number(chainId) : undefined)
    .then((res) => {
      console.log(JSON.stringify(res, null, 2));
      process.exit(0);
    })
    .catch((err) => {
      console.error(JSON.stringify({ success: false, error: err.message }));
      process.exit(1);
    });
}
'''
