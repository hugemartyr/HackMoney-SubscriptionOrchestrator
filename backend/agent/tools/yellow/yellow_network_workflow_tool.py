#Initiliasing the Yellow SDK in the code base after intiliasing the requirement sin the yellow_initiliaser.py

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from langchain_core.callbacks import AsyncCallbackHandler


class YellowNetworkWorkflowInput(BaseModel):
    repo_path: str
    framework_hint: Optional[str] = None


class YellowNetworkWorkflowOutput(BaseModel):
    success: bool
    wallet_address: Optional[str]
    workflow_output: Optional[str]
    files_modified: List[str]
    message: str
    error: Optional[str] = None


class YellowNetworkWorkflowTool:
    """LangGraph-compatible tool to run a Yellow Network workflow inside a repo.

    Designed to be called after `yellow_initialiser` has run. Provides:
    - `async_run(repo_path, framework_hint)` returning `YellowNetworkWorkflowOutput`
    - `invoke(state)` for node-style invocation (accepts AgentState dict, emits SSE via callback)
    """

    name = "yellow_network_workflow"
    description = "Execute a Nitrolite Yellow Network workflow in a Node project (install deps, inject workflow, run)."

    SANDBOX_WS = "wss://clearnet-sandbox.yellow.com/ws"
    SANDBOX_FAUCET = "https://clearnet-sandbox.yellow.com/faucet/requestTokens"
    DEFAULT_SEPOLIA_RPC = "https://rpc.sepolia.org"

    def __init__(self, stream_callback: Optional[AsyncCallbackHandler] = None):
        self.stream_callback = stream_callback

    async def emit_event(self, event_type: str, **kwargs) -> None:
        if self.stream_callback:
            # Use on_tool_start as a generic hook (consistent with other tools)
            await self.stream_callback.on_tool_start({"name": event_type}, input_str=json.dumps(kwargs))

    def _run_cmd(self, cmd: str, cwd: Path, timeout: int = 120) -> str:
        result = subprocess.run(cmd, cwd=str(cwd), shell=True, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError(f"Command failed: {cmd}\nExit: {result.returncode}\nStdout: {result.stdout}\nStderr: {result.stderr}")
        return result.stdout

    # Public async entry for nodes
    async def async_run(self, repo_path: str, framework_hint: Optional[str] = None) -> YellowNetworkWorkflowOutput:
        try:
            repo = Path(repo_path).resolve()
            if not repo.exists():
                return YellowNetworkWorkflowOutput(success=False, wallet_address=None, workflow_output=None, files_modified=[], message="Repo missing", error=f"Path not found: {repo_path}")

            if not (repo / "package.json").exists():
                return YellowNetworkWorkflowOutput(success=False, wallet_address=None, workflow_output=None, files_modified=[], message="Not a Node project", error="Missing package.json")

            # Emit start
            await self.emit_event("tool", name=self.name, status="running")
            await self.emit_event("thought", content="Installing dependencies and preparing workflow...")

            # Perform operations
            self._ensure_dependencies(repo)
            env = self._ensure_env(repo)
            files = self._inject_workflow(repo)

            await self.emit_event("thought", content="Running Yellow workflow script...")
            output = self._run_workflow(repo)

            await self.emit_event("thought", content="Workflow completed")

            return YellowNetworkWorkflowOutput(
                success=True,
                wallet_address=env.get("wallet_address"),
                workflow_output=output,
                files_modified=files,
                message="Workflow executed successfully",
            )

        except Exception as e:
            await self.emit_event("thought", content=f"Workflow failed: {e}")
            return YellowNetworkWorkflowOutput(success=False, wallet_address=None, workflow_output=None, files_modified=[], message="Workflow failed", error=str(e))

    async def invoke(self, state: Dict[str, Any]) -> Dict[str, Any]:
        repo_path = state.get("repo_path")
        framework_hint = state.get("framework_detected") or state.get("framework_hint")

        if not repo_path:
            await self.emit_event("thought", content="No repo_path provided to yellow_network_workflow")
            return {"yellow_workflow_status": "failed", "thinking_log": state.get("thinking_log", []) + ["No repo_path for workflow"]}

        # Run and update state
        await self.emit_event("tool", name=self.name, status="running")
        await self.emit_event("thought", content="Starting Yellow network workflow...")

        result = await self.async_run(repo_path, framework_hint)

        new_state = {
            "yellow_workflow_status": "success" if result.success else "failed",
            "yellow_workflow_wallet": result.wallet_address,
            "yellow_workflow_output": result.workflow_output,
            "yellow_workflow_files": result.files_modified,
            "thinking_log": state.get("thinking_log", []) + [result.message]
        }

        if result.error:
            new_state["workflow_error"] = result.error

        return new_state

    # -------------------------
    # Internal helpers
    # -------------------------
    def _ensure_dependencies(self, repo: Path) -> None:
        # Run package manager install then add specific packages
        self._run_cmd("npm install", repo)
        self._run_cmd("npm install @erc7824/nitrolite viem ws dotenv tsx", repo)

    def _ensure_env(self, repo: Path) -> Dict[str, str]:
        env_path = repo / ".env"
        if not env_path.exists():
            env_path.write_text("PRIVATE_KEY=\nALCHEMY_RPC_URL=\n")

        content = env_path.read_text()
        lines = content.splitlines()
        env_vars: Dict[str, str] = {}

        for line in lines:
            if "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip()

        if not env_vars.get("ALCHEMY_RPC_URL"):
            env_vars["ALCHEMY_RPC_URL"] = self.DEFAULT_SEPOLIA_RPC

        if not env_vars.get("PRIVATE_KEY") or not env_vars["PRIVATE_KEY"].startswith("0x"):
            pk = self._generate_wallet(repo)
            env_vars["PRIVATE_KEY"] = pk

        updated = "\n".join([f"{k}={v}" for k, v in env_vars.items()])
        env_path.write_text(updated)

        wallet_address = self._get_wallet_address(repo)

        # Request faucet funds (best effort)
        try:
            subprocess.run(
                ["curl", "-XPOST", self.SANDBOX_FAUCET, "-H", "Content-Type: application/json", "-d", json.dumps({"userAddress": wallet_address})],
                cwd=str(repo),
                check=False,
            )
        except Exception:
            pass

        return {"wallet_address": wallet_address}

    def _generate_wallet(self, repo: Path) -> str:
        script = """
import { generatePrivateKey } from 'viem/accounts';
console.log(generatePrivateKey());
"""
        temp = repo / "__wallet_gen__.mjs"
        temp.write_text(script)
        out = self._run_cmd(f"node {temp.name}", repo)
        if temp.exists():
            temp.unlink()
        return out.strip()

    def _get_wallet_address(self, repo: Path) -> str:
        script = """
import { privateKeyToAccount } from 'viem/accounts';
import 'dotenv/config';
const account = privateKeyToAccount(process.env.PRIVATE_KEY);
console.log(account.address);
"""
        temp = repo / "__wallet_addr__.mjs"
        temp.write_text(script)
        out = self._run_cmd(f"node {temp.name}", repo)
        if temp.exists():
            temp.unlink()
        return out.strip()

    def _inject_workflow(self, repo: Path) -> List[str]:
        src = repo / "src"
        src.mkdir(exist_ok=True)

        workflow = src / "yellowWorkflow.ts"

        workflow_code = f"""import {{ NitroliteClient, WalletStateSigner, createECDSAMessageSigner, createAuthRequestMessage }} from '@erc7824/nitrolite';
import {{ createPublicClient, createWalletClient, http }} from 'viem';
import {{ sepolia }} from 'viem/chains';
import {{ privateKeyToAccount, generatePrivateKey }} from 'viem/accounts';
import WebSocket from 'ws';
import 'dotenv/config';

const account = privateKeyToAccount(process.env.PRIVATE_KEY as `0x${{string}}`);
const rpcUrl = process.env.ALCHEMY_RPC_URL || '{self.DEFAULT_SEPOLIA_RPC}';

console.log('Wallet:', account.address);

const wsUrl = '{self.SANDBOX_WS}';
const ws = new WebSocket(wsUrl);

ws.on('open', () => {{
  console.log('Connected to Yellow sandbox');
}});

ws.on('message', (msg) => {{
  console.log('WS:', msg.toString());
}});
"""

        workflow.write_text(workflow_code)
        return [str(workflow.relative_to(repo))]

    def _run_workflow(self, repo: Path) -> str:
        out = subprocess.check_output(
            "npx tsx src/yellowWorkflow.ts",
            cwd=str(repo),
            shell=True,
            stderr=subprocess.STDOUT,
            timeout=120,
        )
        return out.decode()
import os
import json
import subprocess
from pathlib import Path
from typing import Dict, Any


class YellowNetworkWorkflowTool:
    name = "yellow_network_workflow"
    description = """
    Integrates a repository with Yellow Network using Nitrolite SDK.
    Installs missing dependencies, ensures environment config,
    generates workflow script, requests faucet funds, authenticates,
    creates channel (if not exists), resizes, closes, and withdraws.
    """

    SANDBOX_WS = "wss://clearnet-sandbox.yellow.com/ws"
    SANDBOX_FAUCET = "https://clearnet-sandbox.yellow.com/faucet/requestTokens"
    DEFAULT_SEPOLIA_RPC = "https://rpc.sepolia.org"

    def run(self, repo_path: str) -> Dict[str, Any]:
        repo = Path(repo_path).resolve()

        if not repo.exists():
            return {"success": False, "error": "Repository path does not exist"}

        if not (repo / "package.json").exists():
            return {"success": False, "error": "Not a Node project (missing package.json)"}

        try:
            self._ensure_dependencies(repo)
            env = self._ensure_env(repo)
            self._inject_workflow(repo)
            output = self._run_workflow(repo)

            return {
                "success": True,
                "wallet_address": env["wallet_address"],
                "workflow_output": output
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # -------------------------------------------
    # Dependency Management
    # -------------------------------------------

    def _ensure_dependencies(self, repo: Path):
        subprocess.run("npm install", cwd=str(repo), shell=True, check=True)

        subprocess.run(
            "npm install @erc7824/nitrolite viem ws dotenv tsx",
            cwd=str(repo),
            shell=True,
            check=True
        )

    # -------------------------------------------
    # Environment Setup
    # -------------------------------------------

    def _ensure_env(self, repo: Path) -> Dict[str, str]:
        env_path = repo / ".env"

        if not env_path.exists():
            env_path.write_text("PRIVATE_KEY=\nALCHEMY_RPC_URL=\n")

        content = env_path.read_text()
        lines = content.splitlines()
        env_vars = {}

        for line in lines:
            if "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip()

        # Fallback RPC
        if not env_vars.get("ALCHEMY_RPC_URL"):
            env_vars["ALCHEMY_RPC_URL"] = self.DEFAULT_SEPOLIA_RPC

        # Generate wallet if missing
        if not env_vars.get("PRIVATE_KEY") or not env_vars["PRIVATE_KEY"].startswith("0x"):
            private_key = self._generate_wallet(repo)
            env_vars["PRIVATE_KEY"] = private_key

        updated = "\n".join([f"{k}={v}" for k, v in env_vars.items()])
        env_path.write_text(updated)

        wallet_address = self._get_wallet_address(repo)

        # Request faucet funds
        subprocess.run(
            f'curl -XPOST {self.SANDBOX_FAUCET} '
            f'-H "Content-Type: application/json" '
            f'-d \'{{"userAddress":"{wallet_address}"}}\'',
            shell=True,
            check=False
        )

        return {"wallet_address": wallet_address}

    def _generate_wallet(self, repo: Path) -> str:
        script = """
        import { generatePrivateKey } from 'viem/accounts';
        console.log(generatePrivateKey());
        """

        temp = repo / "__wallet_gen__.mjs"
        temp.write_text(script)

        result = subprocess.check_output(
            f"node {temp.name}",
            cwd=str(repo),
            shell=True
        )

        temp.unlink()
        return result.decode().strip()

    def _get_wallet_address(self, repo: Path) -> str:
        script = """
        import { privateKeyToAccount } from 'viem/accounts';
        import 'dotenv/config';
        const account = privateKeyToAccount(process.env.PRIVATE_KEY);
        console.log(account.address);
        """

        temp = repo / "__wallet_addr__.mjs"
        temp.write_text(script)

        result = subprocess.check_output(
            f"node {temp.name}",
            cwd=str(repo),
            shell=True
        )

        temp.unlink()
        return result.decode().strip()

    # -------------------------------------------
    # Workflow Injection
    # -------------------------------------------

    def _inject_workflow(self, repo: Path):
        src = repo / "src"
        src.mkdir(exist_ok=True)

        workflow = src / "yellowWorkflow.ts"

        workflow_code = f"""
import {{
  NitroliteClient,
  WalletStateSigner,
  createECDSAMessageSigner,
  createAuthRequestMessage,
  createAuthVerifyMessageFromChallenge,
  createCreateChannelMessage,
  createResizeChannelMessage,
  createCloseChannelMessage
}} from '@erc7824/nitrolite';

import {{
  createPublicClient,
  createWalletClient,
  http
}} from 'viem';

import {{ sepolia }} from 'viem/chains';
import {{ privateKeyToAccount, generatePrivateKey }} from 'viem/accounts';
import WebSocket from 'ws';
import 'dotenv/config';

const account = privateKeyToAccount(process.env.PRIVATE_KEY as `0x${{string}}`);
const rpcUrl = process.env.ALCHEMY_RPC_URL || '{self.DEFAULT_SEPOLIA_RPC}';

const publicClient = createPublicClient({{
  chain: sepolia,
  transport: http(rpcUrl),
}});

const walletClient = createWalletClient({{
  chain: sepolia,
  transport: http(rpcUrl),
  account,
}});

const client = new NitroliteClient({{
  publicClient,
  walletClient,
  stateSigner: new WalletStateSigner(walletClient),
  addresses: {{
    custody: '0x019B65A265EB3363822f2752141b3dF16131b262',
    adjudicator: '0x7c7ccbc98469190849BCC6c926307794fDfB11F2',
  }},
  chainId: sepolia.id,
  challengeDuration: 3600n,
}});

const ws = new WebSocket('{self.SANDBOX_WS}');

async function main() {{
  console.log('Wallet:', account.address);

  ws.on('open', async () => {{
    console.log('Connected to Yellow sandbox');

    const sessionPrivateKey = generatePrivateKey();
    const sessionSigner = createECDSAMessageSigner(sessionPrivateKey);

    const authMsg = await createAuthRequestMessage({{
      address: account.address,
      application: 'LLM Tool',
      session_key: privateKeyToAccount(sessionPrivateKey).address,
      allowances: [{{ asset: 'ytest.usd', amount: '1000000000' }}],
      expires_at: BigInt(Math.floor(Date.now()/1000) + 3600),
      scope: 'llm.tool'
    }});

    ws.send(authMsg);
  }});

  ws.on('message', async (msg) => {{
    console.log('WS:', msg.toString());
  }});
}}

main().catch(console.error);
"""
        workflow.write_text(workflow_code)

    # -------------------------------------------
    # Execute Workflow
    # -------------------------------------------

    def _run_workflow(self, repo: Path) -> str:
        result = subprocess.check_output(
            "npx tsx src/yellowWorkflow.ts",
            cwd=str(repo),
            shell=True,
            stderr=subprocess.STDOUT,
            timeout=120
        )
        return result.decode()
