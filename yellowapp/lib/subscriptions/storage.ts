import { Subscription } from "./types";

const KEY = "subscriptions";

export function getSubscriptions(): Subscription[] {
  return JSON.parse(localStorage.getItem(KEY) || "[]");
}

export function saveSubscriptions(subs: Subscription[]) {
  localStorage.setItem(KEY, JSON.stringify(subs));
}

export function addSubscription(sub: Subscription) {
  const subs = getSubscriptions();
  subs.push(sub);
  saveSubscriptions(subs);
}
