import { createAppSessionMessage, parseRPCResponse } from "@erc7824/nitrolite";

class SimplePaymentApp {
  constructor() {
    this.ws = null;
    this.messageSigner = null;
    this.userAddress = null;
    this.sessionId = null;
  }

  async init() {
    // Step 1: Set up wallet
    const { userAddress, messageSigner } = await this.setupWallet();
    this.userAddress = userAddress;
    this.messageSigner = messageSigner;

    // Step 2: Connect to ClearNode (sandbox for testing)
    this.ws = new WebSocket("wss://clearnet-sandbox.yellow.com/ws");

    this.ws.onopen = () => {
      console.log("🟢 Connected to Yellow Network!");
    };

    this.ws.onmessage = (event) => {
      this.handleMessage(parseRPCResponse(event.data));
    };

    return userAddress;
  }

  async setupWallet() {
    const accounts = await window.ethereum.request({
      method: "eth_requestAccounts",
    });

    const userAddress = accounts[0];
    const messageSigner = async (message) => {
      return await window.ethereum.request({
        method: "personal_sign",
        params: [message, userAddress],
      });
    };

    return { userAddress, messageSigner };
  }

  async createSession(partnerAddress) {
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
    console.log("✅ Payment session created!");
  }

  async sendPayment(amount, recipient) {
    const paymentData = {
      type: "payment",
      amount: amount.toString(),
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

    console.log(`💸 Sent ${amount} instantly!`);
  }

  handleMessage(message) {
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

// Usage
const app = new SimplePaymentApp();
await app.init();
await app.createSession("0xPartnerAddress");
await app.sendPayment("100000", "0xPartnerAddress"); // Send 0.1 USDC
