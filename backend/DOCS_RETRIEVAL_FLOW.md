# Documentation Retrieval Flow - Integration Verification

## Overview
This document verifies that documentation retrieval from the vector database is properly integrated into the main agent flow.

## Current Flow with Documentation Retrieval

### 1. Initialization
```
start_agent → context_check
```

### 2. Context Gathering Loop
```
context_check → route_context_decision → [read_code | retrieve_docs | research | ready]
```

**Routing Logic** (`route_context_decision` in `graph.py`):
1. **Loop safety**: If loop_count > 4 → `ready` (force proceed)
2. **Fast path**: If `context_ready == True` → `ready`
3. **Priority 1**: If `files_to_read` exists → `read_code`
4. **Priority 2**: If no `file_contents` AND no docs retrieved AND prompt mentions Yellow/SDK → `retrieve_docs` (NEW!)
5. **Priority 3**: If no `file_contents` → `read_code`
6. **Priority 4**: Classify `missing_info` into file-like vs doc-like
7. **Priority 5**: If doc-like gaps AND docs not retrieved → `retrieve_docs`
8. **Priority 6**: If docs not retrieved at all → `retrieve_docs`
9. **Fallback**: → `research`

### 3. Documentation Retrieval Node
**File**: `backend/agent/nodes/context.py` (lines 100-120)

```python
async def retrieve_docs_node(state: AgentState) -> AgentState:
    docs = await asyncio.to_thread(
        _search_docs_wrapper, 
        state.get("prompt", ""), 
        state.get("missing_info", [])
    )
    state["docs_retrieved"] = True
    state["doc_context"] = docs  # ✅ Sets doc_context
    return state
```

**What it does**:
- Calls `_search_docs_wrapper` which uses `YellowVectorStore().search()`
- Stores result in `state["doc_context"]`
- Marks `docs_retrieved = True` to prevent infinite loops

### 4. Context Check Enhancement
**File**: `backend/agent/nodes/context.py` (line 14-19)

Now passes `doc_context` to `analyze_context`:
```python
result = await analyze_context(
    state.get("prompt", ""), 
    state.get("file_contents", {}),
    state.get("session_memory", []),
    state.get("tree"),
    state.get("doc_context", "")  # ✅ NEW: Passes doc_context
)
```

This allows the LLM to see if docs are already retrieved when deciding if context is ready.

### 5. Code Generation with Documentation
**File**: `backend/agent/nodes/architecture.py` (lines 172-183)

```python
async def write_code_node(state: AgentState) -> AgentState:
    llm_diffs = await write_code(
        state.get("prompt", ""),
        state.get("file_contents", {}),
        state.get("plan_notes", ""),
        state.get("sdk_version", "latest"),
        state.get("doc_context", ""),  # ✅ Passes doc_context
        state.get("tool_diffs", [])
    )
```

### 6. Prompt Building
**File**: `backend/agent/llm/coding.py` (lines 115-123)

```python
messages = prompts.build_coder_prompt(
    user_query=prompt,
    plan=plan_notes,
    rules=rules_text,  # ✅ Integration rules
    rag_context=rag_context,  # ✅ This is doc_context!
    file_context=context,
    sdk_version=sdk_version,
    tool_diffs=tool_diffs,
)
```

**File**: `backend/agent/prompts/prompts.py` (lines 57-120)

The prompt includes:
- `=== KNOWLEDGE BASE / DOCS (RAG context) ===` section with `rag_context` (which is `doc_context`)
- Integration rules in system prompt
- All context needed for code generation

## State Variables

### Key State Variables for Documentation:
- `doc_context` (str): Retrieved documentation from vector database
- `docs_retrieved` (bool): Flag indicating if docs have been retrieved
- `context_ready` (bool): Whether we have enough context (code + docs)

## Verification Checklist

✅ **Vector Database**:
- Database exists with 335 documents
- Using OpenRouter `text-embedding-3-large` (3072 dimensions)
- Search functionality working

✅ **Retrieval Node**:
- `retrieve_docs_node` properly calls `_search_docs_wrapper`
- Sets `state["doc_context"]` with retrieved docs
- Sets `state["docs_retrieved"] = True`

✅ **Routing Logic**:
- Routes to `retrieve_docs` when docs not retrieved
- Routes to `retrieve_docs` when doc-like gaps exist
- **NEW**: Routes to `retrieve_docs` first when no files and prompt mentions Yellow/SDK

✅ **Context Check**:
- Now passes `doc_context` to `analyze_context`
- LLM can see if docs are already retrieved

✅ **Code Generation**:
- `write_code_node` passes `doc_context` to `write_code()`
- `build_coder_prompt` receives `rag_context` (which is `doc_context`)
- Prompt includes "=== KNOWLEDGE BASE / DOCS (RAG context) ===" section

✅ **Error Handling**:
- `fix_plan_node` also uses `doc_context` for error fixes

## Flow Diagram

```
User Prompt
    ↓
start_agent
    ↓
context_check (checks if ready)
    ↓
route_context_decision
    ├─→ read_code → analyze_imports → update_memory → context_check (loop)
    ├─→ retrieve_docs → update_memory → context_check (loop) ✅
    ├─→ research → update_memory → context_check (loop)
    └─→ ready → architect
                ↓
            yellow_init → yellow_workflow → write_code
                                                ↓
                                        Uses doc_context ✅
                                                ↓
                                        await_approval → coding → build
```

## Testing

Run the test suite to verify:
```bash
cd backend
source .venv/bin/activate
python3 test_docs_retrieval.py
```

Expected results:
- ✅ All search functionality tests pass
- ✅ retrieve_docs_node simulation works
- ✅ doc_context is populated with documentation

## Summary

**Documentation retrieval is now properly integrated:**

1. ✅ Vector database uses OpenRouter embeddings (working)
2. ✅ `retrieve_docs_node` retrieves and stores docs in `doc_context`
3. ✅ Routing logic prioritizes docs retrieval when needed
4. ✅ `doc_context` is passed to code generation
5. ✅ Code generation prompt includes documentation in "RAG context" section
6. ✅ Context check considers `doc_context` when determining readiness

The system should now successfully retrieve Yellow Network SDK documentation during agent runs and use it for code generation.
