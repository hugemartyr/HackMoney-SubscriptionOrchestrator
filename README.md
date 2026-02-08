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

Run project by 


```bash
make install
make dev
```

See `frontend/README.md` for frontend-specific details.
