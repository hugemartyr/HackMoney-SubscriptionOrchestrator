import { Subscription } from "./types";
import { addSubscription } from "./storage";

const MONTH = 30 * 24 * 60 * 60 * 1000;

export function createSubscription({
  merchantAddress,
  amountPerCycle,
  yellowSessionId,
  userAddress,
}: {
  merchantAddress: string;
  amountPerCycle: number;
  yellowSessionId: string;
  userAddress: string;
}): Subscription {
  const now = Date.now();

  const sub: Subscription = {
    id: crypto.randomUUID(),

    merchantAddress,
    userAddress,

    amountPerCycle,
    currency: "USDC",
    cadence: "monthly",

    startTimestamp: now,
    nextBillingTimestamp: now + MONTH,

    cyclesBilled: 0,
    totalAccrued: 0,

    yellowSessionId,
    status: "active",
  };

  addSubscription(sub);
  return sub;
}
