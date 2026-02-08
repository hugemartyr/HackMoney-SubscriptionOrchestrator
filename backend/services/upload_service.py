import asyncio
from pathlib import Path
import shutil
import subprocess

from config import settings
from utils.logger import get_logger


logger = get_logger(__name__)

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
    logger.info("Sandbox root updated", extra={"root": str(root)})


def _git_clone_repo(github_url: str, dest_dir: str) -> None:
    logger.info("Cloning GitHub repository", extra={"github_url": github_url, "dest_dir": dest_dir})
    subprocess.run(
        ["git", "clone", "--depth", "1", github_url, dest_dir],
        check=True,
        capture_output=True,
        text=True,
        timeout=settings.GIT_CLONE_TIMEOUT_SECONDS,
    )
    logger.info("Git clone completed", extra={"github_url": github_url, "dest_dir": dest_dir})


def _ensure_empty_dir(path: Path) -> None:
    if path.exists():
        logger.info("Existing sandbox directory found; removing", extra={"path": str(path)})
        shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    logger.info("Sandbox directory prepared", extra={"path": str(path)})


async def upload_from_github(github_url: str) -> None:
    """
    Single-session upload:
    - clones into one fixed local directory: backend/sandbox (configurable)
    - tracks exactly one local sandbox root at a time

    Raises: subprocess.TimeoutExpired, subprocess.CalledProcessError
    """
    async with _UPLOAD_LOCK:
        logger.info("Starting upload_from_github", extra={"github_url": github_url})
        sandbox_root = Path(settings.SANDBOX_DIR).resolve()
        await asyncio.to_thread(_ensure_empty_dir, sandbox_root)

        await asyncio.to_thread(_git_clone_repo, github_url, str(sandbox_root))
        _set_current_root(sandbox_root)
        logger.info("Upload from GitHub completed", extra={"sandbox_root": str(sandbox_root)})
