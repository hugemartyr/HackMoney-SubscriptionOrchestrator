"use client";

import { useRef, useState, useCallback } from "react";
import { SimplePaymentApp } from "./SimplePaymentApp";
import { useAccount } from "wagmi";

export function useYellow() {
  const appRef = useRef<SimplePaymentApp | null>(null);
  const [address, setAddress] = useState<string | null>(null);
  const { address: walletAddress, isConnected } = useAccount();

  // We use useCallback to ensure the function reference is stable for useEffects
  const init = async (walletAddress?: string) => {
    if (!appRef.current) {
      appRef.current = new SimplePaymentApp();
    }
    // Pass the address here!
    const addr = await appRef.current.init(walletAddress);
    setAddress(addr);
  };

  const createSession = async (partner: string) => {
    if (!appRef.current) return console.error("Yellow App not initialized");
    await appRef.current.createSession(partner);
  };

  const sendPayment = async (amount: string, recipient: string) => {
    if (!appRef.current) return console.error("Yellow App not initialized");
    await appRef.current.sendPayment(amount, recipient);
  };

  return {
    address, // This will now be populated after calling init()
    init,
    createSession,
    sendPayment,
  };
}
