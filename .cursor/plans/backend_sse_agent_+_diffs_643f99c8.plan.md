---
name: Backend SSE Agent + Diffs
overview: Add backend SSE streaming for the Yellow agent and implement pending diff storage plus approval/apply endpoints that match the existing frontend expectations, while also supporting an optional keep/discard-all workflow.
todos:
  - id: add-pending-diff-store
    content: Create a singleton pending diff store service with CRUD helpers for per-file diffs.
    status: completed
  - id: add-agent-schemas
    content: Add Pydantic request schemas for agent prompt, diff approval, and apply-all.
    status: completed
  - id: implement-sse-stream
    content: Implement POST /api/yellow-agent/stream SSE endpoint emitting frontend-compatible events via an agent runner.
    status: completed
    dependencies:
      - add-agent-schemas
      - add-pending-diff-store
  - id: implement-diff-approve
    content: Implement POST /api/diff/approve to approve/reject and (if approved) write newCode into the sandbox.
    status: completed
    dependencies:
      - add-agent-schemas
      - add-pending-diff-store
  - id: implement-apply-all
    content: Implement POST /api/yellow-agent/apply to keep/discard all pending diffs in one call.
    status: completed
    dependencies:
      - add-agent-schemas
      - add-pending-diff-store
  - id: implement-download
    content: Implement GET /api/project/download that zips the sandbox root and returns it as a download.
    status: completed
---

# Backend SSE agent stream + diff apply

## Goals

- Implement **`POST /api/yellow-agent/stream`** that returns **SSE** (`text/event-stream`) emitting events compatible with the frontend’s `SSEEvent` union (`thought`, `tool`, `file_tree`, `file_content`, `diff`, `build`, etc.).
- Implement **diff persistence + approvals** so the frontend’s `POST /api/diff/approve` can approve/reject a diff and (if approved) apply it into the sandbox via the existing FS service.
- Add an optional **keep-all/discard-all** endpoint for the flow in your sequence diagram.
- Implement **`GET /api/project/download`** used by the frontend to download the sandbox as a zip.

## What we’ll change

### 1) Add SSE endpoints + approval/apply routes

- Update [`/home/dev/Projects/yellow_yellow/backend/routes.py`](/home/dev/Projects/yellow_yellow/backend/routes.py)
- Add an `/api`-scoped router section:
- `POST /api/yellow-agent/stream`
- `POST /api/diff/approve`
- `POST /api/yellow-agent/apply` (keep/discard-all)
- `GET /api/project/download`

**SSE details**

- Use `fastapi.responses.StreamingResponse`.
- Emit each event as `data: <json>\n\n`.
- Set headers such as `Cache-Control: no-cache`.

### 2) Add an in-memory pending-diff store (single-session)

- Add [`/home/dev/Projects/yellow_yellow/backend/services/pending_diff_service.py`](/home/dev/Projects/yellow_yellow/backend/services/pending_diff_service.py)
- Maintain a process-local mapping: `file -> {oldCode, newCode, created_at}`.
- API surface:
- `set_pending_diff(file, oldCode, newCode)`
- `get_pending_diff(file)`
- `pop_pending_diff(file)`
- `list_pending_diffs()`
- `clear_pending_diffs()`

This matches the repo’s current “single sandbox root / single session” approach in `upload_service.py`.

### 3) Add Pydantic schemas for agent + approvals

- Add [`/home/dev/Projects/yellow_yellow/backend/utils/schemas/agent.py`](/home/dev/Projects/yellow_yellow/backend/utils/schemas/agent.py)
- `AgentPromptRequest { prompt: str }`
- `DiffApproveRequest { file: str, approved: bool }`
- `ApplyAllRequest { approved: bool }`

### 4) Implement a minimal agent “runner” that yields events

- Add [`/home/dev/Projects/yellow_yellow/backend/agent/runner.py`](/home/dev/Projects/yellow_yellow/backend/agent/runner.py)
- `async def run_agent(prompt: str) -> AsyncIterator[dict]`
- Initial behavior (scaffolding, but real FS integration):
- Emit `thought` (“starting…”, “scanning sandbox…”, …)
- Call existing `get_file_tree()` and emit `file_tree`
- Optionally read a small set of key files (e.g. `package.json`, `README`, entrypoints) using `read_text_file()` and emit `file_content`
- When producing a candidate change, emit `diff` **and** store it in `pending_diff_service` so `/api/diff/approve` can apply it
- Emit a terminal/build placeholder event sequence (or wire to a real build later)

This keeps us aligned with your sequence diagram even though the current [`backend/agent/graph.py`](/home/dev/Projects/yellow_yellow/backend/agent/graph.py) is only a stub today.

### 5) Wire diff approval to sandbox writes

- `POST /api/diff/approve`
- If `approved=true`: look up the pending diff by `file`, then call `write_text_file(file, newCode)`.
- If `approved=false`: remove pending diff without writing.

### 6) Keep/discard all endpoint (diagram flow)

- `POST /api/yellow-agent/apply { approved: boolean }`
- If approved: apply all pending diffs via repeated `write_text_file(...)`.
- Else: clear pending diffs.

### 7) Project download endpoint

- `GET /api/project/download`
- Zip the current sandbox root (from `upload_service.get_current_root()` or `sandbox_fs_service.require_root()`), skipping known ignored dirs.
- Return as a download response (zip bytes).

## Notes / constraints

- **No multi-user session management**: we’ll implement the pending-diff store as a simple singleton, consistent with the existing single-sandbox design.
- **Frontend compatibility**: we’ll match the frontend’s current endpoints (`/api/yellow-agent/stream`, `/api/diff/approve`, `/api/project/download`) and also add the optional apply-all endpoint.

## Implementation todos

- `add-pending-diff-store`: Create `pending_diff_service.py` and its API.
- `add-agent-schemas`: Add `utils/schemas/agent.py` Pydantic models.
- `implement-sse-stream`: Add `POST /api/yellow-agent/stream` using `StreamingResponse` and the runner.
- `implement-diff-approve`: Add `POST /api/diff/approve` to apply or discard stored diffs.
- `implement-apply-all`: Add `POST /api/yellow-agent/apply` for keep/discard-all.
- `implement-download`: Add `GET /api/project/download` zipping the sandbox root.