import nitrolite from "@erc7824/nitrolite";

export const NITROLITE_WS_URL = "wss://clearnet-sandbox.yellow.com/ws";

export type SessionKey = {
  id: string;
  publicKey: string;
};

export type SubscriptionChannelPlan = {
  wsUrl: string;
  durationDays: number;
  dailySettlement: boolean;
  closeAfterDays: number;
  sessionKey: SessionKey;
  clientReady: boolean;
};

const randomId = (prefix: string) => {
  const bytes = new Uint8Array(6);
  globalThis.crypto.getRandomValues(bytes);
  const hex = Array.from(bytes)
    .map((value) => value.toString(16).padStart(2, "0"))
    .join("");
  return `${prefix}_${hex}`;
};

export const createSessionKey = (): SessionKey => {
  // Session keys should be ephemeral and scoped to off-chain updates.
  const id = randomId("sk");
  const publicKey = randomId("pk");
  return { id, publicKey };
};

export const prepareSubscriptionChannelPlan = async (durationDays: number): Promise<SubscriptionChannelPlan> => {
  const sessionKey = createSessionKey();
  let clientReady = false;

  try {
    const api: any = nitrolite;
    if (api?.NitroliteClient) {
      const client = new api.NitroliteClient({ wsUrl: NITROLITE_WS_URL });
      clientReady = !!client;
    } else if (api?.createClient) {
      const client = await api.createClient({ wsUrl: NITROLITE_WS_URL });
      clientReady = !!client;
    }
  } catch {
    clientReady = false;
  }

  return {
    wsUrl: NITROLITE_WS_URL,
    durationDays,
    dailySettlement: true,
    closeAfterDays: durationDays,
    sessionKey,
    clientReady,
  };
};

export const signOffchainUpdate = (sessionKey: SessionKey, payload: string) => {
  // Placeholder signature that demonstrates session-key usage for off-chain state updates.
  return `sig_${sessionKey.id}_${payload}`;
};
