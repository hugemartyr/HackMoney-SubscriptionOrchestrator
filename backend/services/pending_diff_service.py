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
_PENDING: Dict[str, PendingDiff] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def set_pending_diff(file: str, oldCode: str, newCode: str) -> PendingDiff:
    """
    Store/replace the pending diff for a given file (single-session, in-memory).
    """
    diff = PendingDiff(file=file, oldCode=oldCode, newCode=newCode, created_at=_now())
    async with _LOCK:
        _PENDING[file] = diff
    return diff


async def get_pending_diff(file: str) -> Optional[PendingDiff]:
    async with _LOCK:
        return _PENDING.get(file)


async def pop_pending_diff(file: str) -> Optional[PendingDiff]:
    async with _LOCK:
        return _PENDING.pop(file, None)


async def list_pending_diffs() -> List[PendingDiff]:
    async with _LOCK:
        return list(_PENDING.values())


async def clear_pending_diffs() -> None:
    async with _LOCK:
        _PENDING.clear()
