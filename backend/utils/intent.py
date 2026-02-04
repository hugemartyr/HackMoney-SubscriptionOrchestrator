from __future__ import annotations

import re
from typing import Optional

INTENT_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("yellow_payment", re.compile(r"\b(pay|payment|send|transfer)\b", re.IGNORECASE)),
    ("create_kb_agent", re.compile(r"\b(kb|knowledge base|kb agent|dataset|docs)\b", re.IGNORECASE)),
]


def detect_intent(prompt: str) -> Optional[str]:
    for intent, pattern in INTENT_RULES:
        if pattern.search(prompt):
            return intent
    return None
