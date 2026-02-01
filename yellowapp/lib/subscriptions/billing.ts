import { getSubscriptions, saveSubscriptions } from "./storage";
import { Subscription } from "./types";

const MONTH = 30 * 24 * 60 * 60 * 1000;

export function runBillingCycle() {
  const subs = getSubscriptions();
  const now = Date.now();

  let updated = false;

  for (const sub of subs) {
    if (sub.status === "active" && now >= sub.nextBillingTimestamp) {
      sub.cyclesBilled += 1;
      sub.totalAccrued += sub.amountPerCycle;
      sub.nextBillingTimestamp += MONTH;
      updated = true;
    }
  }

  if (updated) saveSubscriptions(subs);
}

export function calculateSessionDebt(sessionId: string): number {
  const subs = getSubscriptions();

  return subs
    .filter((s) => s.yellowSessionId === sessionId)
    .reduce((sum, s) => sum + s.totalAccrued, 0);
}
