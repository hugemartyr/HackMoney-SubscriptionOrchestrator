# Yellow Network Integration Agent

A specialized Vertical AI Software Engineer that refactors existing web applications to integrate the Yellow Network (Layer-3 State Channels).

## Architecture Overview

This project uses a **Remote Sandbox Model** where:
1. User uploads project (files or GitHub URL)
2. Backend spins up an E2B Sandbox VM
3. Agent (LangGraph) operates within the sandbox
4. Real-time sync via SSE (Server-Sent Events) to frontend
5. User reviews changes via diff view before approval

## Tech Stack

### Frontend
- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript
- **Editor**: Monaco Editor (VS Code engine)
- **State**: React Context + Hooks
- **Communication**: SSE (Server-Sent Events)

### Backend
- **Framework**: FastAPI (Python)
- **Agent**: LangGraph (state machine)
- **LLM**: Anthropic Claude 3.5 Sonnet
- **Sandbox**: E2B Code Interpreter
- **Knowledge Base**: Supabase (pgvector) for Yellow SDK docs

---

## Backend Implementation Status

### ✅ **What's Already Done**

1. **Basic FastAPI Setup**
   - FastAPI app with CORS middleware configured
   - Basic SSE endpoint: `/api/yellow-agent/stream`
   - Mock SSE event generator (currently returns mock events)

2. **LangGraph Structure**
   - Basic graph defined in `app/agent/graph.py`
   - State structure: `AgentState` with messages, current_code, errors
   - Node skeleton: scanner, planner, coder, tester nodes (currently stubs)

3. **E2B Sandbox Tools (Stubs)**
   - Tool functions defined: `read_file_tool`, `write_file_tool`, `run_terminal_command`
   - Currently mocked (E2B API calls are commented out)

4. **Dependencies**
   - All required packages listed in `requirements.txt`: fastapi, langgraph, langchain, e2b-code-interpreter, etc.

---

### ❌ **What's Remaining**

#### **1. Project Upload Endpoint** (Critical)
**Missing:** `/api/project/upload`

**Requirements:**
- Accept GitHub URL (JSON)
- Create E2B sandbox instance (singleton, single session)
- Upload/extract project files to sandbox
- Run initial setup (e.g., `npm install`)
- Return success status

**Implementation needed:**
```python
@app.post("/upload")
async def upload_project(githubUrl: str):
    # 1. Create E2B sandbox (singleton)
    # 2. Clone from GitHub
    # 3. Upload files to sandbox
    # 4. Run npm install
    # 5. Return {"ok": True}
```

#### **2. Enhanced SSE Stream Integration** (Critical)
**Current:** Mock events only  
**Needed:** Connect LangGraph to SSE stream

**Requirements:**
- Integrate LangGraph execution into `/api/yellow-agent/stream`
- Emit real SSE events from graph nodes:
  - `file_tree` - when scanning files
  - `file_content` - when reading/writing files
  - `terminal` - when running commands
  - `audit` - after framework detection
  - `diff` - before applying changes
  - `build` - during build process
  - `thought` - agent reasoning
  - `tool` - tool execution status

**Implementation needed:**
```python
async def event_generator():
    # Initialize LangGraph (uses singleton sandbox)
    # Stream graph execution
    async for event in graph.astream(...):
        # Emit SSE events based on node outputs
        yield f"data: {json.dumps(event)}\n\n"
```

#### **3. LangGraph Node Implementation** (Critical)
**Current:** All nodes are stubs  
**Needed:** Full implementation

**Scanner Node:**
- Read file structure from E2B sandbox
- Build `FileSystemNode` tree recursively
- Emit `file_tree` SSE event

**Planner Node:**
- Detect framework (Next.js, React, etc.)
- Analyze payment integration points
- Generate audit result with fee savings estimate
- Emit `audit` SSE event

**Coder Node:**
- Read files from sandbox
- Query RAG for Yellow SDK docs
- Generate code changes
- Calculate diff before writing
- Emit `diff` SSE event
- Wait for approval (or auto-approve)
- Write files to sandbox
- Emit `file_content` SSE events

**Tester Node:**
- Run build commands (`npm run build`)
- Stream terminal output in real-time
- Emit `terminal` and `build` SSE events
- Handle errors and retry logic

#### **4. E2B Sandbox Integration** (Critical)
**Current:** Tools are mocked  
**Needed:** Real E2B API calls

**Requirements:**
- Implement actual E2B Sandbox connection
- File operations: read, write, list directory
- Command execution with streaming output
- Sandbox lifecycle management (create, keep alive, cleanup)

#### **5. Diff Approval Endpoint** (Required)
**Missing:** `/api/diff/approve`

**Requirements:**
- Accept approval/rejection of pending diff
- Update agent state to proceed or skip
- Resume graph execution

#### **6. Project Download Endpoint** (Required)
**Missing:** `/api/project/download`

**Requirements:**
- Zip project files from E2B sandbox
- Return as downloadable blob
- Triggered after successful build

#### **7. RAG Integration** (Required)
**Missing:** RAG system for Yellow SDK docs

**Requirements:**
- Supabase connection setup
- Vector search implementation
- Query Yellow SDK documentation
- Inject context into Coder node

**Files needed:**
- `app/tools/rag.py` - RAG query functions
- `app/knowledge/ingest.py` - Document embedding script
- Supabase configuration in `app/core/config.py`

#### **8. State Management** (Required)
**Current:** Basic `AgentState`  
**Needed:** Enhanced state tracking

**Requirements:**
- Use singleton sandbox (single session, no tracking needed)
- Store pending diffs
- Track build status
- Store audit results
- Session/state persistence (in-memory or database)

#### **9. Error Handling & Recovery** (Important)
**Missing:**
- Comprehensive error handling in nodes
- Retry logic for failed operations
- Graceful degradation
- Error SSE events

#### **10. Terminal Output Streaming** (Important)
**Current:** Mock output  
**Needed:** Real-time command output

**Requirements:**
- Stream E2B command execution output line-by-line
- Emit `terminal` SSE events in real-time
- Handle long-running commands

---

## Implementation Priority

### **Phase 1 (Critical - Blocks Frontend):**
1. ✅ Project upload endpoint
2. ✅ E2B sandbox integration (real implementation)
3. ✅ Enhanced SSE stream with LangGraph
4. ✅ Basic node implementations (scanner, coder, tester)

### **Phase 2 (Required for Full Workflow):**
5. ✅ Diff approval endpoint
6. ✅ Project download endpoint
7. ✅ RAG integration
8. ✅ Terminal streaming

### **Phase 3 (Polish):**
9. ✅ Error handling
10. ✅ State persistence
11. ✅ Build monitoring enhancements

---

## Summary

**Done:** ~15% (basic structure, mocks)  
**Remaining:** ~85% (core functionality)

The backend has the skeleton but needs:
- Real E2B integration
- LangGraph node implementations
- SSE event emission from graph execution
- API endpoints for upload/download/approval
- RAG system for Yellow SDK docs

The frontend is ready and expects these backend features. The main gap is connecting the LangGraph workflow to real sandbox operations and emitting the required SSE events.

---

## Project Structure

```
yellow_yellow/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   └── graph.py          # LangGraph workflow
│   │   ├── api/                  # API endpoints (empty - needs implementation)
│   │   ├── core/                  # Config, database (empty - needs implementation)
│   │   ├── knowledge/             # RAG system (needs implementation)
│   │   └── tools/
│   │       └── e2b_sandbox.py     # E2B integration (stubbed)
│   ├── main.py                    # FastAPI app entry
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/            # UI components (ready)
│       ├── hooks/                 # SSE hooks (ready)
│       ├── context/               # State management (ready)
│       └── lib/                   # Types & API (ready)
└── docs/
    └── yellow_integration_rules.md
```

---

## How to Run

### Quick Start (Makefile)

```bash
# Install all dependencies (backend venv + frontend npm)
make install

# Run everything: Backend (port 8000), Dashboard (8080), Editor (3000)
make dev
```

### Run Individual Components

```bash
make backend    # FastAPI backend on http://localhost:8000
make dashboard  # Agent-Nexus Dashboard on http://localhost:8080
make editor     # Yellow Agent Editor on http://localhost:3000
```

### Backend Setup (Manual)

The `make backend` target will:
1. Create a Python venv in `backend/.venv` if it doesn't exist
2. Activate it and install `requirements.txt`
3. Run the app with uvicorn

To run manually:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup (Manual)

```bash
cd frontend
npm install
npm run dev
```

---

## Environment Variables

You **must** configure environment variables before running the backend.

1. Copy the example file:
   ```bash
   cp backend/.env.local.example backend/.env.local
   ```

2. Edit `backend/.env.local` and fill in your values:

   | Variable | Required | Description |
   |----------|----------|-------------|
   | `LANGSMITH_TRACING` | No | Set to `true` for LangChain tracing |
   | `LANGSMITH_ENDPOINT` | No | LangSmith API endpoint |
   | `LANGSMITH_API_KEY` | Yes* | Get from [smith.langchain.com](https://smith.langchain.com) |
   | `LANGSMITH_PROJECT` | No | Project name for traces (e.g. `yellow`) |
   | `BACKEND_LOG_LEVEL` | No | `DEBUG`, `INFO`, `WARNING`, `ERROR` (default: `INFO`) |
   | `OPENROUTER_API_KEY` | **Yes** | Get from [openrouter.ai](https://openrouter.ai) |
   | `OPENROUTER_MODEL` | No | Model override (e.g. `Xiaomi MiMo-V2-Flash`) |

   \* Required if `LANGSMITH_TRACING=true`

3. `.env.local` is git-ignored. Never commit real API keys.

---

## Frontend Status

The frontend is **fully implemented** and ready:
- ✅ SSE event handling (`useAgentStream.ts`)
- ✅ Project upload component
- ✅ File tree sync
- ✅ Editor with Monaco
- ✅ Terminal component
- ✅ Diff review UI
- ✅ Audit & build status display
- ✅ Project context for state management

See `frontend/README.md` for frontend-specific details.
