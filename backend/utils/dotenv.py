from __future__ import annotations

from pathlib import Path
import os


def _load_env_file(p: Path) -> None:
    """Load KEY=VALUE pairs from a file into os.environ (does not override existing)."""
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


def load_dotenv(dotenv_path: str | os.PathLike[str] | None = None) -> None:
    """
    Minimal .env loader (no external dependency).
    - Only supports KEY=VALUE lines (optionally quoted).
    - Ignores blank lines and comments starting with '#'.
    - Does not override existing environment variables.
    - Loads backend/.env, backend/.env.local, root .env, root .env.local (later overrides earlier).
    """
    if dotenv_path is not None:
        p = Path(dotenv_path)
        if p.exists() and p.is_file():
            _load_env_file(p)
        return
    backend_dir = Path(__file__).resolve().parents[1]
    root_dir = Path(__file__).resolve().parents[2]
    for base in (backend_dir, root_dir):
        for name in (".env", ".env.local"):
            p = base / name
            if p.exists() and p.is_file():
                _load_env_file(p)
