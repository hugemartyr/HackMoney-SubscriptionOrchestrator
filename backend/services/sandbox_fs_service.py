import posixpath
from pathlib import Path
from typing import Any, Dict

from fastapi import HTTPException

from services.upload_service import get_current_root


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
        # Auto-detect existing sandbox if server was restarted
        from config import settings
        sandbox_path = Path(settings.SANDBOX_DIR).resolve()
        if sandbox_path.exists() and sandbox_path.is_dir():
            # Check if it has content (not just empty directory)
            try:
                entries = list(sandbox_path.iterdir())
                # Filter out just .git (common in cloned repos)
                non_git_entries = [e for e in entries if e.name != '.git']
                if non_git_entries:
                    # Sandbox exists with content, auto-initialize
                    from services.upload_service import _set_current_root
                    _set_current_root(sandbox_path)
                    return sandbox_path
            except Exception:
                pass
        raise HTTPException(status_code=400, detail="No project uploaded yet")
    return root


def normalize_and_validate_rel_path(requested_path: str, *, for_directory: bool = False) -> str:
    """
    Relative paths only.
    - Reject absolute paths
    - Reject traversal ("..")
    - Normalize separators
    """
    if not requested_path or "\x00" in requested_path:
        raise HTTPException(status_code=400, detail="Invalid path")

    p = requested_path.strip()
    if p.startswith("/"):
        raise HTTPException(status_code=400, detail="Path must be relative")

    norm = posixpath.normpath(p)
    if norm in (".", ""):
        if for_directory:
            return ""
        raise HTTPException(status_code=400, detail="Invalid path")
    if norm == ".." or norm.startswith("../"):
        raise HTTPException(status_code=403, detail="Path traversal is not allowed")
    if norm.startswith("./"):
        norm = norm[2:]

    return norm


async def get_file_tree() -> Dict[str, Any]:
    root = require_root()

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
        return build(root, "")
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to build file tree")


async def read_text_file(path: str) -> Dict[str, str]:
    root = require_root()
    norm = normalize_and_validate_rel_path(path)
    abs_path = (root / norm).resolve()
    root_resolved = root.resolve()
    if abs_path != root_resolved and not str(abs_path).startswith(str(root_resolved) + "/"):
        raise HTTPException(status_code=403, detail="Path is outside sandbox root")

    try:
        content = abs_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        raise HTTPException(status_code=404, detail="File not found or unreadable")

    return {"path": norm, "content": content}


async def write_text_file(path: str, content: str) -> Dict[str, str]:
    root = require_root()
    if path.strip().endswith("/"):
        raise HTTPException(status_code=400, detail="Path must be a file, not a directory")
    norm = normalize_and_validate_rel_path(path)
    abs_path = (root / norm).resolve()
    root_resolved = root.resolve()
    if abs_path != root_resolved and not str(abs_path).startswith(str(root_resolved) + "/"):
        raise HTTPException(status_code=403, detail="Path is outside sandbox root")

    try:
        if abs_path.exists() and abs_path.is_dir():
            raise HTTPException(status_code=400, detail="Path points to a directory")
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_text(content, encoding="utf-8")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to write file")

    return {"path": norm}


async def delete_file(path: str) -> Dict[str, str]:
    root = require_root()
    if path.strip().endswith("/"):
        raise HTTPException(status_code=400, detail="Path must be a file, not a directory")
    norm = normalize_and_validate_rel_path(path)
    abs_path = (root / norm).resolve()
    root_resolved = root.resolve()
    if abs_path != root_resolved and not str(abs_path).startswith(str(root_resolved) + "/"):
        raise HTTPException(status_code=403, detail="Path is outside sandbox root")

    try:
        if not abs_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        if abs_path.is_dir():
            raise HTTPException(status_code=400, detail="Path points to a directory")
        abs_path.unlink()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to delete file")

    return {"path": norm}

