import {
  createAppSessionMessage,
  parseAnyRPCResponse,
} from "@erc7824/nitrolite";

export class SimplePaymentApp {
  ws: WebSocket | null = null;
  messageSigner: ((m: string) => Promise<string>) | null = null;
  userAddress: string | null = null;
  sessionId: string | null = null;
  initialized = false;

  async init() {
    // ✅ Prevent double init (HMR / re-renders)
    if (this.initialized) return this.userAddress;

    if (typeof window === "undefined") {
      throw new Error("Must run in browser");
    }

    if (!window.ethereum) {
      throw new Error("MetaMask not installed");
    }

    // ✅ Wallet connect ONLY on explicit call
    const accounts = await window.ethereum.request({
      method: "eth_requestAccounts",
    });

    this.userAddress = accounts[0];

    this.messageSigner = async (msg: string) => {
      return await window.ethereum.request({
        method: "personal_sign",
        params: [msg, this.userAddress],
      });
    };

    this.ws = new WebSocket("wss://clearnet-sandbox.yellow.com/ws");

    this.ws.onmessage = (event) => {
      const msg = parseAnyRPCResponse(event.data);

      if (msg.type === "session_created") {
        this.sessionId = msg.sessionId;
        localStorage.setItem("yellow_session_id", msg.sessionId);
      }
    };

    this.initialized = true;
    return this.userAddress;
  }

  async createSession(merchantAddress: string) {
    if (!this.ws || !this.messageSigner || !this.userAddress) {
      throw new Error("Yellow not initialized");
    }

    const sessionMessage = await createAppSessionMessage(this.messageSigner, [
      {
        definition: {
          protocol: "subscription-v1",
          participants: [this.userAddress, merchantAddress],
          weights: [50, 50],
          quorum: 100,
          challenge: 0,
          nonce: Date.now(),
        },
        allocations: [],
      },
    ]);

    this.ws.send(sessionMessage);
  }
}
