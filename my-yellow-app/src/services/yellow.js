// import { createRequire } from "module";
// const require = createRequire(import.meta.url);
// const {
//   parseAnyRPCResponse,
//   createAuthRequestMessage,
// } = require("@erc7824/nitrolite");
// import { config } from "../config/index.js";

// export const initializeYellow = () => {
//   const ws = new WebSocket(config.clearnodeUrl);

//   ws.onopen = () => {
//     console.log("🚀 Connected to Yellow ClearNode");

//     // Example: Initiate Auth immediately on connection
//     const authRequest = createAuthRequestMessage();
//     ws.send(JSON.stringify(authRequest));
//   };

//   ws.onmessage = (event) => {
//     try {
//       const data = parseAnyRPCResponse(event.data);
//       console.log("📨 Message Type:", data.method || "Response", data);
//     } catch (e) {
//       console.log("📩 Raw message:", event.data);
//     }
//   };

//   return ws;
// };

import WebSocket from "ws";
import {
  createAppSessionMessage,
  parseAnyRPCResponse,
} from "@erc7824/nitrolite";

import { setupWallet } from "./signer.js";

class SimplePaymentApp {
  constructor() {
    this.ws = null;
    this.messageSigner = null;
    this.userAddress = null;
  }

  async init() {
    const { userAddress, messageSigner } = await setupWallet();
    this.userAddress = userAddress;
    this.messageSigner = messageSigner;

    this.ws = new WebSocket("wss://clearnet-sandbox.yellow.com/ws");

    this.ws.onopen = () => {
      console.log("🟢 Connected to Yellow Network");
    };

    this.ws.onmessage = (event) => {
      const msg = parseAnyRPCResponse(event.data);
      this.handleMessage(msg);
    };
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

    // 🔑 This automatically performs auth under the hood
    this.ws.send(sessionMessage);
    console.log("✅ App session requested");
  }

  handleMessage(message) {
    if (message.type === "session_created") {
      console.log("🔓 Session created:", message.sessionId);
    }
  }
}
