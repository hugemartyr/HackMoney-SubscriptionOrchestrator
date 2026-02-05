from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass(frozen=True)
class PendingDiff:
    file: str
    oldCode: str
    newCode: str
    created_at: datetime


_LOCK = asyncio.Lock()
_PENDING_BY_RUN: Dict[str, Dict[str, PendingDiff]] = {}
_LAST_RUN_ID: Optional[str] = None


def _now() -> datetime:
    return datetime.now(timezone.utc)

def _resolve_run_id(runId: Optional[str]) -> Optional[str]:
    return runId or _LAST_RUN_ID


async def set_pending_diff(runId: str, file: str, oldCode: str, newCode: str) -> PendingDiff:
    """
    Store/replace the pending diff for a given file under a runId (single-session, in-memory).
    """
    diff = PendingDiff(file=file, oldCode=oldCode, newCode=newCode, created_at=_now())
    async with _LOCK:
        global _LAST_RUN_ID
        _LAST_RUN_ID = runId
        per_run = _PENDING_BY_RUN.setdefault(runId, {})
        per_run[file] = diff
    return diff


async def get_pending_diff(file: str, runId: Optional[str] = None) -> Optional[PendingDiff]:
    rid = _resolve_run_id(runId)
    if not rid:
        return None
    async with _LOCK:
        return (_PENDING_BY_RUN.get(rid) or {}).get(file)


async def pop_pending_diff(file: str, runId: Optional[str] = None) -> Optional[PendingDiff]:
    rid = _resolve_run_id(runId)
    if not rid:
        return None
    async with _LOCK:
        per_run = _PENDING_BY_RUN.get(rid)
        if not per_run:
            return None
        return per_run.pop(file, None)


async def list_pending_diffs(runId: Optional[str] = None) -> List[PendingDiff]:
    rid = _resolve_run_id(runId)
    if not rid:
        return []
    async with _LOCK:
        return list((_PENDING_BY_RUN.get(rid) or {}).values())


async def clear_pending_diffs(runId: Optional[str] = None) -> None:
    rid = _resolve_run_id(runId)
    async with _LOCK:
        if rid:
            _PENDING_BY_RUN.pop(rid, None)
        else:
            _PENDING_BY_RUN.clear()
