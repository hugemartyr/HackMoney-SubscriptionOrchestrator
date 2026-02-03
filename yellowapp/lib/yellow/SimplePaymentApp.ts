import {
  createAppSessionMessage,
  parseAnyRPCResponse,
} from "@erc7824/nitrolite";

export class SimplePaymentApp {
  ws: WebSocket | null = null;
  messageSigner: ((msg: string) => Promise<string>) | null = null;
  userAddress: string | null = null;
  sessionId: string | null = null;

  async init(externalAddress = null) {
    if (typeof window === "undefined") {
      throw new Error("Must run in browser");
    }

    // If we have an external address from RainbowKit, use it
    if (externalAddress) {
      this.userAddress = externalAddress;

      // Create a signer wrapper that uses window.ethereum
      // but doesn't re-trigger eth_requestAccounts
      this.messageSigner = async (message) => {
        return await window.ethereum.request({
          method: "personal_sign",
          params: [message, externalAddress],
        });
      };
      console.log("♻️ Reusing RainbowKit wallet:", this.userAddress);
    } else {
      // Fallback to your original logic if no address is passed
      const { userAddress, messageSigner } = await this.setupWallet();
      this.userAddress = userAddress;
      this.messageSigner = messageSigner;
    }

    // Initialize WebSocket
    this.ws = new WebSocket("wss://clearnet-sandbox.yellow.com/ws");

    this.ws.onopen = () => {
      console.log("🟢 Connected to Yellow Network");
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = parseAnyRPCResponse(event.data);
        this.handleMessage(msg);
      } catch (e) {
        console.log("📩 Raw Message:", event.data);
      }
    };

    return this.userAddress;
  }

  async setupWallet() {
    if (!window.ethereum) {
      throw new Error("MetaMask not installed");
    }

    const accounts = await window.ethereum.request({
      method: "eth_requestAccounts",
    });

    const userAddress = accounts[0];

    const messageSigner = async (message: string) => {
      return await window.ethereum.request({
        method: "personal_sign",
        params: [message, userAddress],
      });
    };

    return { userAddress, messageSigner };
  }

  async createSession(partnerAddress: string) {
    if (!this.ws || !this.messageSigner || !this.userAddress) {
      throw new Error("App not initialized");
    }

    const appDefinition = {
      protocol: "payment-app-v1",
      participants: [this.userAddress, partnerAddress],
      weights: [50, 50],
      quorum: 100,
      challenge: 0,
      nonce: Date.now(),
    };

    const allocations = [
      { participant: this.userAddress, asset: "usdc", amount: "800000" },
      { participant: partnerAddress, asset: "usdc", amount: "200000" },
    ];

    const sessionMessage = await createAppSessionMessage(this.messageSigner, [
      { definition: appDefinition, allocations },
    ]);

    this.ws.send(sessionMessage);
    console.log("✅ Payment session created");
  }

  async sendPayment(amount: string, recipient: string) {
    if (!this.ws || !this.messageSigner || !this.userAddress) return;

    const paymentData = {
      type: "payment",
      amount,
      recipient,
      timestamp: Date.now(),
    };

    const signature = await this.messageSigner(JSON.stringify(paymentData));

    this.ws.send(
      JSON.stringify({
        ...paymentData,
        signature,
        sender: this.userAddress,
      }),
    );

    console.log(`💸 Sent ${amount}`);
  }

  handleMessage(message: any) {
    switch (message.type) {
      case "session_created":
        this.sessionId = message.sessionId;
        console.log("✅ Session ready:", this.sessionId);
        break;

      case "payment":
        console.log("💰 Payment received:", message.amount);
        break;
    }
  }
}
