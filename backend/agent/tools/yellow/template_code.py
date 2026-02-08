"""
Template content for Yellow SDK initialization.
All file contents written to the repo are defined here for single-source updates.
"""

# Default .env content for Yellow / ClearNode
DEFAULT_ENV = """PRIVATE_KEY=
SEPOLIA_RPC_URL=
BASE_RPC_URL=
CLEARNODE_WS_URL=wss://clearnet-sandbox.yellow.com/ws
"""

# src/yellow.ts scaffold – Yellow SDK connection to ClearNode
YELLOW_SCAFFOLD = """import WebSocket from 'ws';
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

# Inline script to generate a dev wallet (viem) – run with node
WALLET_GEN_SCRIPT = """
import { generatePrivateKey } from 'viem/accounts';
const privateKey = generatePrivateKey();
console.log(privateKey);
"""

# Dependencies to add to package.json (user runs npm i)
YELLOW_DEPENDENCIES = [
    "@erc7824/nitrolite",
    "viem",
    "dotenv",
    "ws",
]

YELLOW_DEV_DEPENDENCIES = [
    "typescript",
    "@types/node",
    "tsx",
]

# ---------- Network workflow (yellow_network_workflow_tool) ----------
WORKFLOW_SANDBOX_WS = "wss://clearnet-sandbox.yellow.com/ws"
WORKFLOW_SANDBOX_FAUCET = "https://clearnet-sandbox.yellow.com/faucet/requestTokens"
WORKFLOW_DEFAULT_SEPOLIA_RPC = "https://rpc.sepolia.org"

# src/yellowWorkflow.ts – run with npx tsx (deps and .env assumed from initialiser)
def get_yellow_workflow_ts(rpc_url: str = WORKFLOW_DEFAULT_SEPOLIA_RPC, ws_url: str = WORKFLOW_SANDBOX_WS) -> str:
    return f"""import {{ NitroliteClient, WalletStateSigner, createECDSAMessageSigner, createAuthRequestMessage }} from '@erc7824/nitrolite';
import {{ createPublicClient, createWalletClient, http }} from 'viem';
import {{ sepolia }} from 'viem/chains';
import {{ privateKeyToAccount, generatePrivateKey }} from 'viem/accounts';
import WebSocket from 'ws';
import 'dotenv/config';

const account = privateKeyToAccount(process.env.PRIVATE_KEY as `0x${{string}}`);
const rpcUrl = process.env.ALCHEMY_RPC_URL || process.env.SEPOLIA_RPC_URL || '{rpc_url}';

console.log('Wallet:', account.address);

const wsUrl = '{ws_url}';
const ws = new WebSocket(wsUrl);

ws.on('open', () => {{
  console.log('Connected to Yellow sandbox');
}});

ws.on('message', (msg) => {{
  console.log('WS:', msg.toString());
}});
"""

# Inline script to read wallet address from .env (for faucet/logging)
WALLET_ADDR_SCRIPT = """
import { privateKeyToAccount } from 'viem/accounts';
import 'dotenv/config';
const account = privateKeyToAccount(process.env.PRIVATE_KEY);
console.log(account.address);
"""

# ---------- Multiparty (yellow_next_multi_party_full_lifecycle) ----------
MULTIPARTY_SANDBOX_URL = "wss://clearnet-sandbox.yellow.com/ws"
MULTIPARTY_SCRIPT_CMD = "curl http://localhost:3000/api/yellow/multi-party"


def get_multiparty_route_ts(sandbox_url: str = MULTIPARTY_SANDBOX_URL) -> str:
    """Next.js API route for full multi-party Yellow session lifecycle (create session, submit state, close)."""
    return f'''
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
      url: "{sandbox_url}",
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

    const sessionKey1 = await yellow.authenticate(wallet1);
    const signer1 = createECDSAMessageSigner(sessionKey1.privateKey);

    const sessionKey2 = await yellow.authenticate(wallet2);
    const signer2 = createECDSAMessageSigner(sessionKey2.privateKey);

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
'''

# ---------- Versioned integration (yellow_versioned_integration_tool) ----------
VERSIONED_INTEGRATION_VERSION = "1.0.0"


def get_versioned_version_ts(version: str = VERSIONED_INTEGRATION_VERSION) -> str:
    return f'export const YELLOW_INTEGRATION_VERSION = "{version}";'


VERSIONED_CONFIG_TS = """
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

VERSIONED_UTILS_TS = """
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

# auth.ts requires yellow-ts (Client) and @erc7824/nitrolite; yellow-ts installed by initialiser/workflow.
VERSIONED_AUTH_TS = """
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

# ---------- Tip tool (yellow_tip_tool) ----------
YELLOW_TIP_TS = r'''import { Client } from "yellow-ts";
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

const TOKEN_MAP: Record<string, string> = {
  usdc: "usdc",
  eth: "eth",
  sepolia: "eth"
};

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

      if (message.method === RPCMethod.BalanceUpdate && !resolved) {
        resolved = true;
        await yellow.disconnect();
        resolve({
          success: true,
          tx: message.params
        });
      }

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

# ---------- Deposit tool (yellow_deposit_tool) ----------
YELLOW_DEPOSIT_TS = r'''import { NitroliteClient, WalletStateSigner } from "@erc7824/nitrolite";
import { createWalletClient, formatUnits, http, parseUnits } from "viem";
import { mnemonicToAccount } from "viem/accounts";
import * as chains from "viem/chains";
import { getContractAddresses } from "./utils";
import { publicClient } from "./auth";
import "dotenv/config";

const USDC_MAP: Record<number, string> = {
  8453: "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913", // Base Mainnet
  84532: "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913", // Base Sepolia (replace)
  11155111: "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913", // Sepolia (replace)
};

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
