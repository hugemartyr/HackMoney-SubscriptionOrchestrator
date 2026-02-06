from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional

from utils.logger import get_logger


logger = get_logger(__name__)


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
    resolved = runId or _LAST_RUN_ID
    logger.info("Resolved runId for pending diffs", extra={"requested_runId": runId, "resolved_runId": resolved})
    return resolved


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
    logger.info(
        "Set pending diff",
        extra={
            "runId": runId,
            "file": file,
            "total_files_for_run": len(_PENDING_BY_RUN.get(runId, {})),
        },
    )
    return diff


async def get_pending_diff(file: str, runId: Optional[str] = None) -> Optional[PendingDiff]:
    rid = _resolve_run_id(runId)
    if not rid:
        logger.info("No runId resolved when getting pending diff", extra={"file": file})
        return None
    async with _LOCK:
        diff = (_PENDING_BY_RUN.get(rid) or {}).get(file)
    logger.info(
        "Get pending diff",
        extra={"runId": rid, "file": file, "found": diff is not None},
    )
    return diff


async def pop_pending_diff(file: str, runId: Optional[str] = None) -> Optional[PendingDiff]:
    rid = _resolve_run_id(runId)
    if not rid:
        logger.info("No runId resolved when popping pending diff", extra={"file": file})
        return None
    async with _LOCK:
        per_run = _PENDING_BY_RUN.get(rid)
        if not per_run:
            logger.info("No pending diffs for run when popping", extra={"runId": rid, "file": file})
            return None
        diff = per_run.pop(file, None)
    logger.info(
        "Popped pending diff",
        extra={"runId": rid, "file": file, "found": diff is not None},
    )
    return diff


async def list_pending_diffs(runId: Optional[str] = None) -> List[PendingDiff]:
    rid = _resolve_run_id(runId)
    if not rid:
        logger.info("No runId resolved when listing pending diffs")
        return []
    async with _LOCK:
        diffs = list((_PENDING_BY_RUN.get(rid) or {}).values())
    logger.info(
        "Listed pending diffs",
        extra={"runId": rid, "count": len(diffs)},
    )
    return diffs


async def clear_pending_diffs(runId: Optional[str] = None) -> None:
    rid = _resolve_run_id(runId)
    async with _LOCK:
        if rid:
            removed = _PENDING_BY_RUN.pop(rid, None)
            logger.info(
                "Cleared pending diffs for run",
                extra={"runId": rid, "removed_count": len(removed or {})},
            )
        else:
            removed_total = sum(len(v) for v in _PENDING_BY_RUN.values())
            _PENDING_BY_RUN.clear()
            logger.info(
                "Cleared all pending diffs (no runId provided)",
                extra={"removed_total": removed_total},
            )
