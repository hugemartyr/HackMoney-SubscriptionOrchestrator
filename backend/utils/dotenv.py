from __future__ import annotations

from pathlib import Path
import os


def load_dotenv(dotenv_path: str | os.PathLike[str] | None = None) -> None:
    """
    Minimal .env loader (no external dependency).
    - Only supports KEY=VALUE lines (optionally quoted).
    - Ignores blank lines and comments starting with '#'.
    - Does not override existing environment variables.
    """
    if dotenv_path is None:
        # Try backend/.env first
        p = Path(__file__).resolve().parents[1] / ".env"
        if not p.exists():
            # Try project root .env
            p = Path(__file__).resolve().parents[2] / ".env"
    else:
        p = Path(dotenv_path)

    if not p.exists() or not p.is_file():
        return

    try:
        raw = p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return

    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "=" not in s:
            continue

        key, value = s.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        if key in os.environ:
            continue
        os.environ[key] = value
