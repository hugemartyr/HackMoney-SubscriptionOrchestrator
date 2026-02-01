"use client";

import { useEffect } from "react";
import { useYellow } from "@/lib/yellow/useYellow";
import { createSubscription } from "@/lib/subscriptions/api";
import {
  runBillingCycle,
  calculateSessionDebt,
} from "@/lib/subscriptions/billing";

export default function Page() {
  const { init, createSession, address, sessionId } = useYellow();

  // ✅ Billing only — no wallet access
  useEffect(() => {
    runBillingCycle();
  }, []);

  return (
    <main style={{ padding: 24 }}>
      <h1>Yellow Subscriptions MVP</h1>

      {!address && <button onClick={init}>Connect Wallet</button>}

      {address && !sessionId && (
        <button onClick={() => createSession("0xMerchantAddress")}>
          Open Yellow Session
        </button>
      )}

      {sessionId && (
        <>
          <p>Connected: {address}</p>
          <p>Session ID: {sessionId}</p>

          <button
            onClick={() =>
              createSubscription({
                merchantAddress: "0xMerchantAddress",
                amountPerCycle: 10,
                yellowSessionId: sessionId,
                userAddress: address!,
              })
            }
          >
            Add $10/month Subscription
          </button>

          <p>Outstanding: ${calculateSessionDebt(sessionId)}</p>
        </>
      )}
    </main>
  );
}
