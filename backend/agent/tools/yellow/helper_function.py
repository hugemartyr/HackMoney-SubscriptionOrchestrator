from __future__ import annotations

from pathlib import Path
from typing import Optional
from agent.state import Diff


def detect_yellow_requirement(prompt: str) -> bool:
    """Detect whether the user's prompt indicates Yellow SDK is required."""
    kw = [
        "yellow", "nitrolite", "state channel", "state channels",
        "clear node", "clearnode", "off-chain", "l3", "yellow network", "nitro",
    ]
    pl = (prompt or "").lower()
    return any(k in pl for k in kw)


def detect_versioned_integration_requirement(prompt: str) -> bool:
    """Detect if user prompt requires versioned Yellow integration layer."""
    keywords = [
        "integration layer", "versioned", "version control",
        "library setup", "initialize", "scaffold",
        "abstract", "abstraction", "helper", "wrapper",
        "reusable", "framework", "sdk layer",
        "config", "configuration", "session",
    ]
    return any(kw in (prompt or "").lower() for kw in keywords)


def detect_deposit_requirement(prompt: str) -> bool:
    """Detect whether the user's prompt indicates deposit functionality is required."""
    keywords = [
        "deposit", "custody", "fund", "add funds", "top up", "top-up",
        "deposit usdc", "custody contract", "nitrolite deposit",
    ]
    pl = (prompt or "").lower()
    return any(k in pl for k in keywords)

def detect_multiparty_requirement(prompt: str) -> bool:
    """Detect if user prompt requires multiparty Yellow workflow."""
    keywords = [
        "multiparty", "multi-party", "multi party",
        "two wallet", "two wallets", "dual wallet", "multiple wallet",
        "collaborative", "collaboration", "multi-sig", "multisig",
        "shared state", "shared session", "joint session",
        "participant", "counterparty", "peer", "partner",
        "bilateral", "mutual", "consensus", "agreement",
        "allocate", "allocation", "distribution",
    ]
    return any(kw in (prompt or "").lower() for kw in keywords)

def detect_tip_requirement(prompt: str) -> bool:
    """Detect whether the user's prompt indicates tipping functionality is required."""
    keywords = [
        "tip", "tipping", "send tip", "transfer", "pay", "payment", "donate", "donation",
    ]
    pl = (prompt or "").lower()
    return any(k in pl for k in keywords)

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
