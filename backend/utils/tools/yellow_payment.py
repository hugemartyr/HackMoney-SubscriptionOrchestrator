from __future__ import annotations

from typing import Any


def yellow_simple_payment(payload: dict[str, Any]) -> dict[str, Any]:
    amount = payload.get("amount", "0")
    currency = payload.get("currency", "USDC")
    recipient = payload.get("recipient", "yellow-demo-wallet")
    return {
        "tool": "yellow_simple_payment",
        "status": "simulated",
        "amount": amount,
        "currency": currency,
        "recipient": recipient,
        "note": "Demo tool execution only. Replace with Yellow SDK calls.",
    }
