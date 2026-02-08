import posixpath
from pathlib import Path
from typing import Any, Dict

from fastapi import HTTPException

from services.upload_service import get_current_root
from utils.logger import get_logger


logger = get_logger(__name__)

SKIP_DIRS = {
    ".git",
    "node_modules",
    ".next",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
}


def require_root() -> Path:
    root = get_current_root()
    if root is None:
        logger.info("No in-memory sandbox root; attempting auto-detection from settings")
        # Auto-detect existing sandbox if server was restarted
        from config import settings

        sandbox_path = Path(settings.SANDBOX_DIR).resolve()
        if sandbox_path.exists() and sandbox_path.is_dir():
            # Check if it has content (not just empty directory)
            try:
                entries = list(sandbox_path.iterdir())
                # Filter out just .git (common in cloned repos)
                non_git_entries = [e for e in entries if e.name != ".git"]
                if non_git_entries:
                    # Sandbox exists with content, auto-initialize
                    from services.upload_service import _set_current_root

                    logger.info(
                        "Auto-initializing sandbox root from existing directory",
                        extra={"sandbox_path": str(sandbox_path)},
                    )
                    _set_current_root(sandbox_path)
                    return sandbox_path
            except Exception:
                logger.info("Failed to auto-detect sandbox root from filesystem")
        logger.info("No project uploaded yet when requiring sandbox root")
        raise HTTPException(status_code=400, detail="No project uploaded yet")
    logger.info("Using existing sandbox root", extra={"root": str(root)})
    return root


def normalize_and_validate_rel_path(requested_path: str, *, for_directory: bool = False) -> str:
    """
    Relative paths only.
    - Reject absolute paths
    - Reject traversal ("..")
    - Normalize separators
    """
    if not requested_path or "\x00" in requested_path:
        logger.info("Invalid path requested (empty or null byte)")
        raise HTTPException(status_code=400, detail="Invalid path")

    p = requested_path.strip()
    if p.startswith("/"):
        logger.info("Rejected absolute path", extra={"requested_path": requested_path})
        raise HTTPException(status_code=400, detail="Path must be relative")

    norm = posixpath.normpath(p)
    if norm in (".", ""):
        if for_directory:
            logger.info("Normalized directory path to root", extra={"requested_path": requested_path})
            return ""
        logger.info("Invalid normalized path for file", extra={"requested_path": requested_path})
        raise HTTPException(status_code=400, detail="Invalid path")
    if norm == ".." or norm.startswith("../"):
        logger.info("Rejected path traversal attempt", extra={"requested_path": requested_path})
        raise HTTPException(status_code=403, detail="Path traversal is not allowed")
    if norm.startswith("./"):
        norm = norm[2:]

    logger.info("Normalized relative path", extra={"requested_path": requested_path, "normalized": norm})
    return norm


async def get_file_tree() -> Dict[str, Any]:
    root = require_root()
    logger.info("Building file tree", extra={"root": str(root)})

    def build(abs_path: Path, rel_path: str) -> Dict[str, Any]:
        name = abs_path.name if rel_path else abs_path.name  # root name too
        if abs_path.is_dir():
            children: list[Dict[str, Any]] = []
            try:
                entries = sorted(abs_path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
            except Exception:
                entries = []

            for entry in entries:
                if entry.name in SKIP_DIRS:
                    continue
                child_rel = entry.name if not rel_path else f"{rel_path}/{entry.name}"
                children.append(build(entry, child_rel))

            node: Dict[str, Any] = {"path": rel_path, "name": name, "type": "folder", "children": children}
            return node

        return {"path": rel_path, "name": name, "type": "file"}

    try:
        tree = build(root, "")
        logger.info("File tree built successfully")
        return tree
    except Exception:
        logger.info("Failed to build file tree", extra={"root": str(root)})
        raise HTTPException(status_code=500, detail="Failed to build file tree")


async def read_text_file(path: str) -> Dict[str, str]:
    root = require_root()
    norm = normalize_and_validate_rel_path(path)
    logger.info("Reading text file from sandbox", extra={"requested_path": path, "normalized": norm})
    abs_path = (root / norm).resolve()
    root_resolved = root.resolve()
    if abs_path != root_resolved and not str(abs_path).startswith(str(root_resolved) + "/"):
        logger.info(
            "Rejected read outside sandbox root",
            extra={"abs_path": str(abs_path), "root": str(root_resolved)},
        )
        raise HTTPException(status_code=403, detail="Path is outside sandbox root")

    try:
        content = abs_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        logger.info("File not found or unreadable", extra={"abs_path": str(abs_path)})
        raise HTTPException(status_code=404, detail="File not found or unreadable")

    logger.info("Read text file successfully", extra={"path": norm})
    return {"path": norm, "content": content}


async def write_text_file(path: str, content: str) -> Dict[str, str]:
    root = require_root()
    if path.strip().endswith("/"):
        logger.info("Rejected write to directory-like path", extra={"path": path})
        raise HTTPException(status_code=400, detail="Path must be a file, not a directory")
    norm = normalize_and_validate_rel_path(path)
    logger.info("Writing text file to sandbox", extra={"requested_path": path, "normalized": norm})
    abs_path = (root / norm).resolve()
    root_resolved = root.resolve()
    if abs_path != root_resolved and not str(abs_path).startswith(str(root_resolved) + "/"):
        logger.info(
            "Rejected write outside sandbox root",
            extra={"abs_path": str(abs_path), "root": str(root_resolved)},
        )
        raise HTTPException(status_code=403, detail="Path is outside sandbox root")

    try:
        if abs_path.exists() and abs_path.is_dir():
            logger.info("Rejected write to existing directory", extra={"abs_path": str(abs_path)})
            raise HTTPException(status_code=400, detail="Path points to a directory")
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(content, encoding="utf-8")
    except HTTPException:
        raise
    except Exception:
        logger.info("Failed to write file", extra={"abs_path": str(abs_path)})
        raise HTTPException(status_code=500, detail="Failed to write file")

    logger.info("Write text file successful", extra={"path": norm})
    return {"path": norm}


async def delete_file(path: str) -> Dict[str, str]:
    root = require_root()
    if path.strip().endswith("/"):
        logger.info("Rejected delete for directory-like path", extra={"path": path})
        raise HTTPException(status_code=400, detail="Path must be a file, not a directory")
    norm = normalize_and_validate_rel_path(path)
    logger.info("Deleting file from sandbox", extra={"requested_path": path, "normalized": norm})
    abs_path = (root / norm).resolve()
    root_resolved = root.resolve()
    if abs_path != root_resolved and not str(abs_path).startswith(str(root_resolved) + "/"):
        logger.info(
            "Rejected delete outside sandbox root",
            extra={"abs_path": str(abs_path), "root": str(root_resolved)},
        )
        raise HTTPException(status_code=403, detail="Path is outside sandbox root")

    try:
        if not abs_path.exists():
            logger.info("File not found for delete", extra={"abs_path": str(abs_path)})
            raise HTTPException(status_code=404, detail="File not found")
        if abs_path.is_dir():
            logger.info("Rejected delete for directory path", extra={"abs_path": str(abs_path)})
            raise HTTPException(status_code=400, detail="Path points to a directory")
        abs_path.unlink()
    except HTTPException:
        raise
    except Exception:
        logger.info("Failed to delete file", extra={"abs_path": str(abs_path)})
        raise HTTPException(status_code=500, detail="Failed to delete file")

    logger.info("Delete file successful", extra={"path": norm})
    return {"path": norm}

