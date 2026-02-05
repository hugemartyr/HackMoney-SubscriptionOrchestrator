from __future__ import annotations

import posixpath
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple
import json

from services.sandbox_fs_service import read_text_file
from agent.state import Diff

PAY_FUNCTION_NAMES = ("pay", "handlePay", "makePayment", "payNow")
SUPPORTED_EXTS = (".ts", ".tsx", ".js", ".jsx")


def _walk_tree(tree: Dict[str, Any]) -> Iterable[str]:
    stack = [tree]
    while stack:
        node = stack.pop()
        if not isinstance(node, dict):
            continue
        if node.get("type") == "file":
            path = node.get("path")
            if isinstance(path, str):
                yield path
        for child in node.get("children", []) or []:
            stack.append(child)


def _find_frontend_root(paths: Iterable[str]) -> str:
    path_set = set(paths)
    for candidate in ("frontend/src", "src", "app"):
        if any(p == candidate or p.startswith(candidate + "/") for p in path_set):
            return candidate
    return "src"


def _prefer_ts(paths: Iterable[str]) -> bool:
    return any(p.endswith("tsconfig.json") for p in paths)


def _relative_import(from_path: str, to_path: str) -> str:
    rel = posixpath.relpath(to_path, posixpath.dirname(from_path))
    if not rel.startswith("."):
        rel = f"./{rel}"
    return rel


def _extract_first_param(params: str) -> Optional[str]:
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", params)
    return tokens[0] if tokens else None


def _replace_function_body(content: str) -> Tuple[str, bool]:
    updated = content
    changed = False

    patterns = [
        re.compile(
            rf"(export\s+)?(async\s+)?function\s+({'|'.join(PAY_FUNCTION_NAMES)})\s*\(([^)]*)\)\s*\{{",
            re.MULTILINE,
        ),
        re.compile(
            rf"(export\s+)?const\s+({'|'.join(PAY_FUNCTION_NAMES)})\s*=\s*(async\s*)?\(([^)]*)\)\s*=>\s*\{{",
            re.MULTILINE,
        ),
    ]

    for pattern in patterns:
        matches = list(pattern.finditer(updated))
        matches.sort(key=lambda m: m.start(), reverse=True)
        for match in matches:
            start = match.end() - 1
            brace_count = 0
            end = None
            for idx in range(start, len(updated)):
                if updated[idx] == "{":
                    brace_count += 1
                elif updated[idx] == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        end = idx
                        break
            if end is None:
                continue

            params = match.group(4) if pattern is patterns[0] else match.group(4)
            merchant_var = _extract_first_param(params or "")
            if merchant_var:
                body = f"\n  return createYellowSimplePayment({merchant_var});\n"
            else:
                body = (
                    "\n  // TODO: provide merchant address\n"
                    "  return createYellowSimplePayment(\"merchant-address\");\n"
                )

            updated = updated[: start + 1] + body + updated[end:]
            changed = True

    return updated, changed


def _ensure_import(content: str, import_path: str) -> str:
    import_stmt = f"import {{ createYellowSimplePayment }} from \"{import_path}\";"
    if import_stmt in content:
        return content

    lines = content.splitlines()
    last_import_idx = -1
    for idx, line in enumerate(lines):
        if line.strip().startswith("import "):
            last_import_idx = idx

    if last_import_idx >= 0:
        lines.insert(last_import_idx + 1, import_stmt)
    else:
        lines.insert(0, import_stmt)
    return "\n".join(lines) + ("\n" if content.endswith("\n") else "")


def _simple_payment_files(frontend_root: str, use_ts: bool) -> Dict[str, str]:
    ext = "ts" if use_ts else "js"
    base = f"{frontend_root}/lib/yellow"

    simple_payment = f"{base}/simplePayment.{ext}"
    if use_ts:
        simple_payment_content = (
            "import { SimplePaymentApp } from \"./SimplePaymentApp\";\n\n"
            "export async function createYellowSimplePayment(merchantAddress: string) {\n"
            "  const app = new SimplePaymentApp();\n"
            "  await app.init();\n"
            "  await app.createSession(merchantAddress);\n"
            "  return app.sessionId;\n"
            "}\n"
        )
    else:
        simple_payment_content = (
            "import { SimplePaymentApp } from \"./SimplePaymentApp\";\n\n"
            "export async function createYellowSimplePayment(merchantAddress) {\n"
            "  const app = new SimplePaymentApp();\n"
            "  await app.init();\n"
            "  await app.createSession(merchantAddress);\n"
            "  return app.sessionId;\n"
            "}\n"
        )

    simple_payment_app = f"{base}/SimplePaymentApp.{ext}"
    if use_ts:
        simple_payment_app_content = (
            "import { createAppSessionMessage, parseAnyRPCResponse } from \"@erc7824/nitrolite\";\n\n"
            "export class SimplePaymentApp {\n"
            "  ws: WebSocket | null = null;\n"
            "  messageSigner: ((m: string) => Promise<string>) | null = null;\n"
            "  userAddress: string | null = null;\n"
            "  sessionId: string | null = null;\n"
            "  initialized = false;\n\n"
            "  async init() {\n"
            "    if (this.initialized) return this.userAddress;\n"
            "    if (typeof window === \"undefined\") {\n"
            "      throw new Error(\"Must run in browser\");\n"
            "    }\n"
            "    if (!(window as any).ethereum) {\n"
            "      throw new Error(\"MetaMask not installed\");\n"
            "    }\n"
            "    const accounts = await (window as any).ethereum.request({ method: \"eth_requestAccounts\" });\n"
            "    this.userAddress = accounts[0];\n"
            "    this.messageSigner = async (msg: string) => {\n"
            "      return await (window as any).ethereum.request({\n"
            "        method: \"personal_sign\",\n"
            "        params: [msg, this.userAddress],\n"
            "      });\n"
            "    };\n"
            "    this.ws = new WebSocket(\"wss://clearnet-sandbox.yellow.com/ws\");\n"
            "    this.ws.onmessage = (event) => {\n"
            "      const msg = parseAnyRPCResponse(event.data);\n"
            "      if (msg.type === \"session_created\") {\n"
            "        this.sessionId = msg.sessionId;\n"
            "        localStorage.setItem(\"yellow_session_id\", msg.sessionId);\n"
            "      }\n"
            "    };\n"
            "    this.initialized = true;\n"
            "    return this.userAddress;\n"
            "  }\n\n"
            "  async createSession(merchantAddress: string) {\n"
            "    if (!this.ws || !this.messageSigner || !this.userAddress) {\n"
            "      throw new Error(\"Yellow not initialized\");\n"
            "    }\n"
            "    const sessionMessage = await createAppSessionMessage(this.messageSigner, [\n"
            "      {\n"
            "        definition: {\n"
            "          protocol: \"subscription-v1\",\n"
            "          participants: [this.userAddress, merchantAddress],\n"
            "          weights: [50, 50],\n"
            "          quorum: 100,\n"
            "          challenge: 0,\n"
            "          nonce: Date.now(),\n"
            "        },\n"
            "        allocations: [],\n"
            "      },\n"
            "    ]);\n"
            "    this.ws.send(sessionMessage);\n"
            "  }\n"
            "}\n"
        )
    else:
        simple_payment_app_content = (
            "import { createAppSessionMessage, parseAnyRPCResponse } from \"@erc7824/nitrolite\";\n\n"
            "export class SimplePaymentApp {\n"
            "  ws = null;\n"
            "  messageSigner = null;\n"
            "  userAddress = null;\n"
            "  sessionId = null;\n"
            "  initialized = false;\n\n"
            "  async init() {\n"
            "    if (this.initialized) return this.userAddress;\n"
            "    if (typeof window === \"undefined\") {\n"
            "      throw new Error(\"Must run in browser\");\n"
            "    }\n"
            "    if (!window.ethereum) {\n"
            "      throw new Error(\"MetaMask not installed\");\n"
            "    }\n"
            "    const accounts = await window.ethereum.request({ method: \"eth_requestAccounts\" });\n"
            "    this.userAddress = accounts[0];\n"
            "    this.messageSigner = async (msg) => {\n"
            "      return await window.ethereum.request({\n"
            "        method: \"personal_sign\",\n"
            "        params: [msg, this.userAddress],\n"
            "      });\n"
            "    };\n"
            "    this.ws = new WebSocket(\"wss://clearnet-sandbox.yellow.com/ws\");\n"
            "    this.ws.onmessage = (event) => {\n"
            "      const msg = parseAnyRPCResponse(event.data);\n"
            "      if (msg.type === \"session_created\") {\n"
            "        this.sessionId = msg.sessionId;\n"
            "        localStorage.setItem(\"yellow_session_id\", msg.sessionId);\n"
            "      }\n"
            "    };\n"
            "    this.initialized = true;\n"
            "    return this.userAddress;\n"
            "  }\n\n"
            "  async createSession(merchantAddress) {\n"
            "    if (!this.ws || !this.messageSigner || !this.userAddress) {\n"
            "      throw new Error(\"Yellow not initialized\");\n"
            "    }\n"
            "    const sessionMessage = await createAppSessionMessage(this.messageSigner, [\n"
            "      {\n"x 
            "        definition: {\n"
            "          protocol: \"subscription-v1\",\n"
            "          participants: [this.userAddress, merchantAddress],\n"
            "          weights: [50, 50],\n"
            "          quorum: 100,\n"
            "          challenge: 0,\n"
            "          nonce: Date.now(),\n"
            "        },\n"
            "        allocations: [],\n"
            "      },\n"
            "    ]);\n"
            "    this.ws.send(sessionMessage);\n"
            "  }\n"
            "}\n"
        )

    use_yellow = f"{base}/useYellow.{ext}"
    if use_ts:
        use_yellow_content = (
            "\"use client\";\n\n"
            "import { useRef, useState } from \"react\";\n"
            "import { SimplePaymentApp } from \"./SimplePaymentApp\";\n\n"
            "export function useYellow() {\n"
            "  const appRef = useRef<SimplePaymentApp | null>(null);\n"
            "  const [address, setAddress] = useState<string | null>(null);\n"
            "  const [sessionId, setSessionId] = useState<string | null>(null);\n\n"
            "  const init = async () => {\n"
            "    if (!appRef.current) {\n"
            "      appRef.current = new SimplePaymentApp();\n"
            "    }\n"
            "    const addr = await appRef.current.init();\n"
            "    setAddress(addr || null);\n"
            "    const storedSession = localStorage.getItem(\"yellow_session_id\");\n"
            "    if (storedSession) {\n"
            "      setSessionId(storedSession);\n"
            "    }\n"
            "  };\n\n"
            "  const createSession = async (merchant: string) => {\n"
            "    await appRef.current?.createSession(merchant);\n"
            "    setTimeout(() => {\n"
            "      const sid = localStorage.getItem(\"yellow_session_id\");\n"
            "      if (sid) setSessionId(sid);\n"
            "    }, 500);\n"
            "  };\n\n"
            "  return { address, sessionId, init, createSession };\n"
            "}\n"
        )
    else:
        use_yellow_content = (
            "\"use client\";\n\n"
            "import { useRef, useState } from \"react\";\n"
            "import { SimplePaymentApp } from \"./SimplePaymentApp\";\n\n"
            "export function useYellow() {\n"
            "  const appRef = useRef(null);\n"
            "  const [address, setAddress] = useState(null);\n"
            "  const [sessionId, setSessionId] = useState(null);\n\n"
            "  const init = async () => {\n"
            "    if (!appRef.current) {\n"
            "      appRef.current = new SimplePaymentApp();\n"
            "    }\n"
            "    const addr = await appRef.current.init();\n"
            "    setAddress(addr || null);\n"
            "    const storedSession = localStorage.getItem(\"yellow_session_id\");\n"
            "    if (storedSession) {\n"
            "      setSessionId(storedSession);\n"
            "    }\n"
            "  };\n\n"
            "  const createSession = async (merchant) => {\n"
            "    await appRef.current?.createSession(merchant);\n"
            "    setTimeout(() => {\n"
            "      const sid = localStorage.getItem(\"yellow_session_id\");\n"
            "      if (sid) setSessionId(sid);\n"
            "    }, 500);\n"
            "  };\n\n"
            "  return { address, sessionId, init, createSession };\n"
            "}\n"
        )

    return {
        "simple_payment": simple_payment_content,
        "simple_payment_app": simple_payment_app_content,
        "use_yellow": use_yellow_content,
    }


def _should_run(prompt: str) -> bool:
    return bool(re.search(r"\b(pay|payment|yellow|session)\b", prompt, re.IGNORECASE))


async def yellow_simplepayment_tool(prompt: str, tree: Dict[str, Any]) -> List[Diff]:
    if not _should_run(prompt):
        return []

    paths = list(_walk_tree(tree))
    frontend_root = _find_frontend_root(paths)
    use_ts = _prefer_ts(paths)

    target_files = [p for p in paths if p.endswith(SUPPORTED_EXTS) and (
        p.startswith(frontend_root + "/")
    )]

    diffs: List[Diff] = []
    helper_files = _simple_payment_files(frontend_root, use_ts)
    ext = "ts" if use_ts else "js"
    helper_path = f"{frontend_root}/lib/yellow/simplePayment.{ext}"

    # Add helper files (new if missing)
    helper_targets = {
        helper_path: helper_files["simple_payment"],
        f"{frontend_root}/lib/yellow/SimplePaymentApp.{ext}": helper_files["simple_payment_app"],
        f"{frontend_root}/lib/yellow/useYellow.{ext}": helper_files["use_yellow"],
    }
    for file_path, new_content in helper_targets.items():
        if file_path in paths:
            continue
        diffs.append({"file": file_path, "oldCode": "", "newCode": new_content})

    # Ensure @erc7824/nitrolite dependency is present
    pkg_candidates = [
        "package.json",
        f"{frontend_root}/package.json",
        "frontend/package.json",
    ]
    pkg_path = next((p for p in pkg_candidates if p in paths), None)
    if pkg_path:
        try:
            pkg_obj = await read_text_file(pkg_path)
            old_pkg = pkg_obj.get("content", "")
            data = json.loads(old_pkg) if old_pkg.strip() else {}
            if isinstance(data, dict):
                deps = data.get("dependencies")
                if deps is None:
                    deps = {}
                    data["dependencies"] = deps
                if isinstance(deps, dict) and "@erc7824/nitrolite" not in deps:
                    deps["@erc7824/nitrolite"] = "latest"
                    new_pkg = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
                    diffs.append({"file": pkg_path, "oldCode": old_pkg, "newCode": new_pkg})
        except Exception:
            pass

    for path in target_files:
        try:
            obj = await read_text_file(path)
        except Exception:
            continue

        content = obj.get("content", "")
        if not content:
            continue

        updated, changed = _replace_function_body(content)
        if not changed:
            continue

        import_path = _relative_import(path, helper_path)
        updated = _ensure_import(updated, import_path)
        diffs.append({"file": path, "oldCode": content, "newCode": updated})

    return diffs
