"use client";

import { useYellow } from "../lib/yellow/useYellow";
import { ConnectButton } from "@rainbow-me/rainbowkit";
import { useAccount } from "wagmi"; // Import this to get the wallet state
import { useEffect } from "react";

export default function Home() {
  // 1. Get the address directly from Wagmi/RainbowKit
  const { address: walletAddress, isConnected } = useAccount();

  // 2. Destructure your yellow logic
  const { init, createSession, sendPayment } = useYellow();
  const PartnerAdress = "0xd1ff23d7D928Fbc895193691adB7d5059333A028";

  const handleYellowConnect = async () => {
    if (walletAddress) {
      await init(walletAddress);
    }
  };

  // 3. Optional: Automatically sync the wallet with your Yellow initialization
  // If your useYellow hook needs the address to "init", we do it here.
  useEffect(() => {
    if (isConnected && walletAddress) {
      // If your init function requires the address, pass it here
      // init(walletAddress);
      console.log("Wallet synchronized with Yellow Orchestrator");
    }
  }, [isConnected, walletAddress, init]);

  return (
    <main style={{ padding: 24, fontFamily: "sans-serif" }}>
      <h1>Yellow Payment App</h1>

      <div style={{ marginBottom: 20 }}>
        <ConnectButton />
      </div>

      {isConnected && walletAddress && (
        <section
          style={{
            marginTop: 20,
            display: "flex",
            flexDirection: "column",
            gap: "10px",
            maxWidth: "300px",
          }}
        >
          <p>
            <strong>Status:</strong> Connected to Yellow
          </p>
          <p>
            <strong>Address:</strong> {walletAddress}
          </p>

          <button
            onClick={() => init(walletAddress)}
            style={{ padding: "10px", cursor: "pointer" }}
          >
            Initialize Yellow Session
          </button>

          <button
            onClick={() => createSession(PartnerAdress)}
            style={{ padding: "10px", cursor: "pointer" }}
          >
            Create Session
          </button>

          <button
            onClick={() => sendPayment("100000", PartnerAdress)}
            style={{ padding: "10px", cursor: "pointer" }}
          >
            Send 0.1 USDC
          </button>
        </section>
      )}
    </main>
  );
}
