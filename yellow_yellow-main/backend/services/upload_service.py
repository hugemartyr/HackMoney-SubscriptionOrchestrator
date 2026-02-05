import asyncio
from pathlib import Path
import shutil
import subprocess

from config import settings


_UPLOAD_LOCK = asyncio.Lock()
_CURRENT_ROOT: Path | None = None


def get_current_root() -> Path | None:
    """
    Returns the current (singleton) local sandbox root directory, or None if no upload has occurred yet.
    """
    return _CURRENT_ROOT


def _set_current_root(root: Path) -> None:
    global _CURRENT_ROOT
    _CURRENT_ROOT = root


def _git_clone_repo(github_url: str, dest_dir: str) -> None:
    subprocess.run(
        ["git", "clone", "--depth", "1", github_url, dest_dir],
        check=True,
        capture_output=True,
        text=True,
        timeout=settings.GIT_CLONE_TIMEOUT_SECONDS,
    )


def _ensure_empty_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)


async def upload_from_github(github_url: str) -> None:
    """
    Single-session upload:
    - clones into one fixed local directory: backend/sandbox (configurable)
    - tracks exactly one local sandbox root at a time

    Raises: subprocess.TimeoutExpired, subprocess.CalledProcessError
    """
    async with _UPLOAD_LOCK:
        sandbox_root = Path(settings.SANDBOX_DIR).resolve()
        await asyncio.to_thread(_ensure_empty_dir, sandbox_root)

        await asyncio.to_thread(_git_clone_repo, github_url, str(sandbox_root))
        _set_current_root(sandbox_root)

