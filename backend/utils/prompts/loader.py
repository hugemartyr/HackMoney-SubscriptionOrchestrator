from __future__ import annotations

from pathlib import Path

PROMPT_DIR = Path(__file__).resolve().parent


def load_prompt(filename: str) -> str:
    path = PROMPT_DIR / filename
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")
