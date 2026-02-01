// //
// import { createRequire } from "module";
// const require = createRequire(import.meta.url);
// const nitrolite = require("@erc7824/nitrolite");

// // Use the actual function names found in your console log
// const { parseAnyRPCResponse, createAppSessionMessage } = nitrolite;

// const CLEARNODE_URL = "wss://clearnet-sandbox.yellow.com/ws";
// const ws = new WebSocket(CLEARNODE_URL);

// ws.onopen = () => {
//   console.log("✅ Connected to Yellow Network!");
// };

// ws.onmessage = (event) => {
//   try {
//     // parseAnyRPCResponse is the correct function from your list
//     const message = parseAnyRPCResponse(event.data);
//     console.log("📨 Received:", message);
//   } catch (error) {
//     // If it's a string from a simple ping, it might fail parsing, which is fine
//     console.error("❌ Parsing Error:", error.message);
//   }
// };

// ws.onerror = (error) => console.error("❗ Connection error:", error);

import { initializeYellow } from "./services/yellow.js";

console.log("🛠 Starting Subscription Orchestrator...");

try {
  const yellowConn = await initializeYellow();

  // Keep process alive
  process.on("SIGINT", () => {
    console.log("Shutting down...");
    yellowConn.close();
    process.exit();
  });
} catch (error) {
  console.error("Failed to start app:", error);
}
