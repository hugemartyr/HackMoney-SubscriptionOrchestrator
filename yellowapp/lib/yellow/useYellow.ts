"use client";

import { useRef, useState } from "react";
import { SimplePaymentApp } from "./SimplePaymentApp";

export function useYellow() {
  const appRef = useRef<SimplePaymentApp | null>(null);
  const [address, setAddress] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const init = async () => {
    if (!appRef.current) {
      appRef.current = new SimplePaymentApp();
    }

    const addr = await appRef.current.init();
    setAddress(addr || null);

    const storedSession = localStorage.getItem("yellow_session_id");
    if (storedSession) {
      setSessionId(storedSession);
    }
  };

  const createSession = async (merchant: string) => {
    await appRef.current?.createSession(merchant);

    // session_created comes async, poll once
    setTimeout(() => {
      const sid = localStorage.getItem("yellow_session_id");
      if (sid) setSessionId(sid);
    }, 500);
  };

  return {
    address,
    sessionId,
    init,
    createSession,
  };
}
