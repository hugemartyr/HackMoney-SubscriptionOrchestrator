# Yellow Network Integration Agent - Project Plan & Architecture

## 1. Project Overview
This project builds a specialized **Vertical AI Software Engineer** capable of refactoring existing web applications to integrate the **Yellow Network** (Layer-3 State Channels).

Unlike generic coding assistants, this agent operates within a secure **Remote Sandbox (E2B)**, allowing it to:
1. Install dependencies (`npm install @yellow-network/sdk`).
2. Run compilers (`tsc`) to verify code.
3. Apply complex refactoring patterns specifically for Yellow Network integration.

## 2. Tech Stack

### Frontend (The Interface)
- **Framework**: Next.js 14+ (App Router)
- **Language**: TypeScript
- **Editor**: `@monaco-editor/react` (VS Code engine in browser)
- **UI Components**: `shadcn/ui` + `lucide-react`
- **State Management**: React Hooks (`useAgentStream`, `useProjectSync`)
- **Communication**: WebSockets (or SSE) for live file updates and terminal logs.

### Backend (The Brain)
- **Framework**: FastAPI (Python)
- **Agent Orchestration**: `LangGraph` (Cyclic state machine for Plan -> Code -> Test loops)
- **LLM**: Anthropic Claude 3.5 Sonnet (via checking LangChain)
- **Sandbox Environment**: **E2B Code Interpreter** (Secure cloud VMs for running user code)
- **Knowledge Base (RAG)**: Supabase (pgvector) stores Yellow Network SDK documentation and rules.

## 3. Architecture: The "Remote Sandbox" Model

1.  **Ingestion**: User opens the web app. Frontend zips their local project (or clones GitHub repo) and uploads it to the Backend.
2.  **Environment Setup**: Backend spins up an **E2B Sandbox**, uploads the zip, unzips it, and runs `npm install`.
3.  **Agent Loop**: 
    -   Agent (LangGraph) receives a prompt ("Yellow-fy this app").
    -   Agent retrieves Yellow SDK docs via RAG.
    -   Agent reads files from the **Sandbox** (not the backend server).
    -   Agent writes code to the **Sandbox**.
    -   Agent verifies code by running build commands in the **Sandbox**.
4.  **Sync**: When the Agent writes a file in the Sandbox, the Backend pushes the change via WebSocket to the Frontend to update the Monaco Editor live.

## 4. Folder Structure

```graphql
yellow-agent-app/
├── README.md
├── docker-compose.yml          # For local database/services
├── .env.example
│
├── frontend/                   # Next.js Application
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── next.config.mjs
│   │
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx        # Main Workspace Interface
│   │   │   └── providers.tsx
│   │   │
│   │   ├── components/
│   │   │   ├── editor/
│   │   │   │   ├── YellowEditor.tsx    # Main Monaco Wrapper
│   │   │   │   ├── DiffEditor.tsx      # For comparing Agent changes
│   │   │   │   └── FileTree.tsx        # Recursive file explorer
│   │   │   ├── chat/
│   │   │   │   ├── AgentChat.tsx       # Chat interface
│   │   │   │   └── Terminal.tsx        # Streaming logs output
│   │   │   └── ui/                     # Shadcn components (Button, Resizable, etc.)
│   │   │
│   │   ├── hooks/
│   │   │   ├── useAgentStream.ts       # Handles WebSocket stream from Agent
│   │   │   ├── useEditorContext.ts     # Captures selection/cursor context
│   │   │   └── useProjectSync.ts       # Manages Zipping/Uploading to E2B
│   │   │
│   │   └── lib/
│   │       ├── api.ts                  # Fetch wrappers
│   │       ├── yellow-rules.ts         # Static rules for highlighting/validation
│   │       └── types.ts
│   │
│   └── public/
│       └── yellow-manifest.json        # Manifest for PWA/Settings
│
├── backend/                    # Python FastAPI Server
│   ├── requirements.txt
│   ├── main.py                 # App Entrypoint & WebSocket handling
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── core/
│   │   │   ├── config.py       # Env vars (API Keys)
│   │   │   └── database.py     # Supabase connection
│   │   │
│   │   ├── api/
│   │   │   ├── routes.py       # API Endpoints (/stream, /init-session)
│   │   │   └── websocket.py    # Socket manager for file sync
│   │   │
│   │   ├── agent/              # LangGraph Logic
│   │   │   ├── graph.py        # The Core State Machine definition
│   │   │   ├── state.py        # AgentState definition (TypedDict)
│   │   │   └── nodes.py        # Node logic (Planner, Coder, Tester)
│   │   │
│   │   ├── tools/
│   │   │   ├── e2b_sandbox.py  # Wrapper for E2B Sandbox API (read/write/exec)
│   │   │   └── rag.py          # Vector search for Yellow SDK docs
│   │   │
│   │   └── knowledge/
│   │       ├── ingest.py       # Script to embed docs into Supabase
│   │       └── documents/      # Raw .md files of Yellow Network Docs
│   │
│   └── tests/
│
└── docs/                       # Project Documentation
    ├── ARCHITECTURE.md
    └── yellow_integration_rules.md  # The "Brain" instructions for the LLM
```

## 5. Development Roadmap

### Phase 1: Infrastructure & "The Brain" (Days 1-2)
1.  **Backend Setup**: Initialize FastAPI.
2.  **RAG Pipeline**: Create `backend/app/knowledge/ingest.py` to scrape Yellow Network docs and store them in Supabase.
3.  **Sandbox Integration**: Implement `backend/app/tools/e2b_sandbox.py` to spin up VM, read/write files, and run shell commands.

### Phase 2: The Agent Logic (Days 3-4)
1.  **LangGraph Setup**: Define the cyclic graph in `backend/app/agent/graph.py` (Plan → Code → Test → Fix).
2.  **Tool Binding**: Connect the graph nodes to the E2B tools.
3.  **Context Injection**: Ensure the "Coder" node queries the RAG system for specific Yellow SDK syntax before generating code.

### Phase 3: The Frontend Experience (Days 5-6)
1.  **Monaco Setup**: Build `YellowEditor.tsx` with the `useEditorContext` hook.
2.  **Synchronization**: Implement `useProjectSync.ts` to zip local files and send them to the backend on startup.
3.  **Streaming UI**: Build `AgentChat.tsx` to display thoughts ("Thinking...") and terminal outputs ("Running npm install...") using the `useAgentStream` hook.

### Phase 4: Integration & Polish (Day 7)
1.  **Diff View**: Implement `DiffEditor.tsx` so users can see exactly what the agent changed before accepting.
2.  **File Tree**: Connect the `FileTree.tsx` component to the E2B file system state.
3.  **Testing**: Verify the "Yellow-fy" pipeline on a sample Next.js e-commerce app.
