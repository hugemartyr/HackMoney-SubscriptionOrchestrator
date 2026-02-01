export type SubscriptionStatus = "active" | "paused" | "cancelled";

export type Subscription = {
  id: string;

  merchantAddress: string;
  userAddress: string;

  amountPerCycle: number; // e.g. 10 USDC
  currency: "USDC";
  cadence: "monthly";

  startTimestamp: number;
  nextBillingTimestamp: number;
  endTimestamp?: number;

  cyclesBilled: number;
  totalAccrued: number;

  yellowSessionId: string;
  status: SubscriptionStatus;
};
