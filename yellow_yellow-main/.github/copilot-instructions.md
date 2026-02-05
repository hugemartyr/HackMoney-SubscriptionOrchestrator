# Yellow Network Integration Agent - Copilot Instructions

You are assisting in the development of "Yellow Yellow", a vertical AI software engineer designed to refactor user applications for Yellow Network (L3 State Channels) integration.

## ❌ Critical Architecture Warning
This application operates on a **Remote Sandbox Model**.
- **The Agent (Backend)** does NOT edit files on the local server or the user's local machine directly.
- **The Agent** interacts exclusively with an **E2B Sandbox** (remote VM).
- **The Frontend** displays code from the sandbox, not the local file system.

## 🏗 Project Structure & Tech Stack

### Frontend (`/frontend`)
- **Framework**: Next.js 14+ (App Router), TypeScript.
- **Key Librarires**: `@monaco-editor/react` (Code Editor), `lucide-react`, `shadcn/ui`.
- **State**: `useAgentStream` (handles SSE), `useEditorContext`.
- **Communication**: POST `/api/yellow-agent/stream` -> Server-Sent Events (SSE).
- **Pattern**: Manually parses `data: {...}` lines from the stream to update UI log/code.

### Backend (`/backend`)
- **Framework**: FastAPI (Python).
- **Agent Orchestration**: LangGraph (`backend/app/agent/graph.py`).
- **Execution Environment**: E2B Code Interpreter (`backend/app/tools/e2b_sandbox.py`).
- **Entry Point**: `backend/main.py` (currently contains mock logic - transition to graph pending).

## 🧠 specific Coding Guidelines

### 1. Agent Streaming Protocol (SSE)
Communication between Backend and Frontend follows a strict JSON-over-SSE format.
When modifying stream logic, ensure events match:
```json
// "thought" -> Updates chat log
{"type": "thought", "content": "Analyzing dependency tree..."}

// "tool" -> distinct status update
{"type": "tool", "name": "e2b_executor", "status": "running"}

// "code_update" -> Replaces Monaco Editor content
{"type": "code_update", "content": "import { YellowSDK } ..."}
```

### 2. Yellow Network Integration Rules (`docs/yellow_integration_rules.md`)
The core value proposition is strict adherence to Yellow SDK patterns.
- **Singleton Pattern**: Always instantiate `new YellowSDK()` once.
- **Deposit Flow**: L1 Approve -> L1 Deposit -> Wait for Channel.
- **State Updates**: Off-chain `yellow.channel.updateState` instead of on-chain txs.
- *Refer to `docs/yellow_integration_rules.md` when defining agent behaviors or RAG content.*

### 3. LangGraph Workflow
The agent logic resides in `backend/app/agent/graph.py`.
- **Nodes**: `scanner` -> `planner` -> `coder` -> `tester`.
- **State**: `AgentState` (tracks messages, code, sandbox_id, errors).
- **Tools**: All file operations must go through `e2b_sandbox` tools (`read_file`, `write_file`). DO NOT use Python's built-in `open()`.

## 🛠 Development Workflow
- **Frontend**: `cd frontend && npm install && npm run dev` (Port 3000)
- **Backend**: `cd backend && pip install -r requirements.txt && uvicorn main:app --reload` (Port 8000)
- **Sandbox**: Requires `E2B_API_KEY` in environment variables.

## ⚠️ Common Pitfalls
- **Mocking**: `backend/main.py` currently mocks the agent stream. When implementing real logic, route requests to `app_graph.astream`.
- **File Paths**: In the E2B sandbox, user code typically resides in `/home/user/app/`. Ensure tools prepend this path.
