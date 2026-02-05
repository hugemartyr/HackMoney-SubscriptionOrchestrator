from typing import Any, Dict
from agent.state import AgentState
from services.sandbox_fs_service import get_file_tree

def _safe_file_list_from_tree(tree: Dict[str, Any], limit: int = 10) -> list[str]:
    out: list[str] = []

    def walk(node: Dict[str, Any]) -> None:
        nonlocal out
        if len(out) >= limit:
            return
        if node.get("type") == "file":
            p = node.get("path")
            if isinstance(p, str) and p:
                out.append(p)
            return
        for child in node.get("children", []) or []:
            if isinstance(child, dict):
                walk(child)

    walk(tree)
    return out[:limit]


async def scan_node(state: AgentState) -> AgentState:
    tree = await get_file_tree()

    # A few "usual suspects" + a handful from the actual tree.
    candidates: list[str] = [
        "package.json",
        "README.md",
        "requirements.txt",
        "src/main.ts",
        "src/index.ts",
        "app/page.tsx",
        "main.py",
        "routes.py",
    ]
    candidates.extend(_safe_file_list_from_tree(tree, limit=8))

    # De-dupe while preserving order.
    seen: set[str] = set()
    files_to_read: list[str] = []
    for p in candidates:
        if p and p not in seen:
            files_to_read.append(p)
            seen.add(p)

    return {"tree": tree, "files_to_read": files_to_read}
