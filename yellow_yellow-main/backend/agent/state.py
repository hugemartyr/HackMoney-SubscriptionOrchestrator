from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class Diff(TypedDict):
    file: str
    oldCode: str
    newCode: str


class AgentState(TypedDict, total=False):
    prompt: str
    tree: Dict[str, Any]
    files_to_read: List[str]
    file_contents: Dict[str, str]
    plan_notes: str
    sdk_version: str
    diffs: List[Diff]
    tool_diffs: List[Diff]
    errors: List[str]
