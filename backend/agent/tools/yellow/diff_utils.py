from __future__ import annotations

from pathlib import Path
from typing import Optional

from agent.state import Diff


def read_text_safe(path: Path) -> Optional[str]:
    try:
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def make_diff(repo_root: Path, rel_path: str, new_content: str) -> Optional[Diff]:
    abs_path = repo_root / rel_path
    old_content = read_text_safe(abs_path)

    if old_content is None:
        old_content = ""

    if old_content == new_content:
        return None

    return {
        "file": rel_path,
        "oldCode": old_content,
        "newCode": new_content,
    }


def write_file_with_diff(repo_root: Path, rel_path: str, content: str) -> Optional[Diff]:
    abs_path = repo_root / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)

    diff = make_diff(repo_root, rel_path, content)
    abs_path.write_text(content, encoding="utf-8")
    return diff
