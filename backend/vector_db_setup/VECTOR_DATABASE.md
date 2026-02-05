# Vector Database Documentation

## Overview

This document describes the vector database implementation for the Yellow Network SDK documentation. The database uses **ChromaDB** as the vector store with **Google Generative AI embeddings** to enable semantic search for an autonomous agent that helps developers integrate the Yellow Network SDK.

## Architecture

```
┌─────────────────┐
│  Raw Docs JSON  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Chunk Content  │ (Split by headers)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  AI Enrichment  │ (Google Gemini)
│  - Summary      │
│  - Keywords     │
│  - Function Names│
│  - Intent       │
│  - Use Cases    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Enriched JSON  │ (Backup/Inspection)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Metadata       │
│  Normalization  │ (Lists → Strings)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ChromaDB       │ (Vector Store)
│  + Embeddings   │
└─────────────────┘
```

## Database Configuration

### Vector Store
- **Technology**: ChromaDB
- **Collection Name**: `yellow_docs`
- **Persist Directory**: `backend/data/chroma_db/`
- **Storage Format**: SQLite + Binary index files

### Embedding Model

- **Provider**: Google Generative AI
- **Model**: `models/text-embedding-004`
- **Dimensions**: 768
- **API Key**: Required via `GOOGLE_API_KEY` environment variable
- **Configuration**:
  ```python
  GoogleGenerativeAIEmbeddings(
      model="models/text-embedding-004",
      google_api_key=settings.GOOGLE_API_KEY,
  )
  ```

**Why this model?**
- Strong performance on technical documentation and code
- Good balance of quality and cost
- Already integrated with Google Gemini for LLM tasks
- 768 dimensions provide good semantic understanding

## Document Schema

### Metadata Structure

Each document in the vector database contains the following metadata fields:

#### Original Metadata
- `title` (str): Document title (e.g., "API Reference | Yellow Network")
- `url` (str): Source URL of the documentation
- `source` (str): Source identifier (e.g., "yellow-docs")
- `chunk_type` (str): Type of chunk - one of:
  - `"api_function"`: API method/function documentation
  - `"api_intro"`: API reference introduction
  - `"guide_section"`: Guide/tutorial section

#### Enrichment Metadata (AI-Generated)
- `summary` (str): 1-2 sentence explanation of what the component does (for system architects)
- `keywords` (str): Comma-separated list of 8-15 searchable terms
  - User-friendly terms (e.g., "start payment", "checkout")
  - Technical terms (e.g., "session", "channel", "state update")
  - Related concepts (e.g., "authentication", "signing")
- `function_name` (str | null): Primary API method name if applicable (e.g., "createAppSessionMessage")
- `function_names` (str): Comma-separated list of all extracted function names from the chunk
- `intent` (str): Document intent classification - one of:
  - `"api_reference"`: API documentation
  - `"tutorial"`: Step-by-step guide
  - `"concept"`: Conceptual explanation
  - `"migration"`: Migration guide
  - `"error_handling"`: Error handling documentation
  - `"configuration"`: Configuration documentation
- `use_cases` (str): Comma-separated list of 2-4 specific use case scenarios

### Page Content Structure

The `page_content` field contains:
1. **Original documentation text** (cleaned and chunked)
2. **Enhanced content** (appended during enrichment):
   - Summary paragraph
   - Related terms (keywords)
   - Use cases

Example:
```
Original content...

Summary: [AI-generated summary]

Related terms: keyword1, keyword2, keyword3...

Use cases: use case 1, use case 2...
```

## Creation Process

### Step 1: Document Ingestion

**Script**: `backend/vector_db_setup/ingest_docs.py`

1. **Load Source Data**: Reads from `docs/yellow_docs_vector_data.json`
2. **Text Cleaning**: Removes breadcrumbs, TOC, and footer elements
3. **Chunking Strategy**:
   - **API Reference pages**: Split by Level 4 headers (`#### functionName`)
   - **Guide pages**: Split by Level 2 headers (`## Section`)
   - **Fallback**: Use entire text if no headers found
4. **Minimum Chunk Size**: 50 characters

### Step 2: AI Enrichment

**Service**: `backend/services/doc_enrichment.py`

**Process**:
1. **Function Name Extraction** (Regex-based, no LLM):
   - Extracts function names from code snippets
   - Patterns: `` `functionName(`, `#### functionName`, `createXxx`, snake_case

2. **LLM Enrichment** (Google Gemini):
   - Model: `gemini-3-flash-preview` (configurable via `GOOGLE_MODEL`)
   - Temperature: 0.1 (for consistent metadata)
   - Max Tokens: 2048
   - Batch Processing: 10 chunks at a time (async)

3. **Enrichment Fields Generated**:
   - Summary
   - Keywords (8-15 terms)
   - Function name (primary)
   - Intent classification
   - Use cases (2-4 scenarios)

4. **Content Enhancement**: Appends enrichment data to `page_content` for better embeddings

### Step 3: Metadata Normalization

**Service**: `backend/services/vector_store.py`

**Normalization Process**:
- **List Fields → Strings**: Converts `keywords`, `function_names`, `use_cases` to comma-separated strings
- **Removed Fields**: Strips `enriched` flag and `error` fields (not needed in ChromaDB)
- **Reason**: ChromaDB only accepts primitive types (str, int, float, bool, None) in metadata

### Step 4: Vector Database Population

**Script**: `backend/vector_db_setup/load_enriched_to_vector_db.py`

1. Load enriched documents from `backend/data/enriched_docs.json`
2. Convert JSON to LangChain `Document` objects
3. Normalize metadata for ChromaDB compatibility
4. Generate embeddings using Google's text-embedding-004
5. Store in ChromaDB with metadata

## Statistics

- **Total Documents**: 335 chunks
- **Source Pages**: 46 documentation pages
- **Enrichment Success Rate**: 100% (335/335 chunks enriched)
- **Storage Location**: `backend/data/chroma_db/`
- **Backup Location**: `backend/data/enriched_docs.json`

## Search & Retrieval

### Search Method

**Method**: `YellowVectorStore.search(query, k=5, use_metadata_filter=True)`

**Process**:
1. **Semantic Search**: Retrieves 2k candidates using vector similarity
2. **Metadata Re-ranking**: Scores and re-ranks based on:
   - Function name matches: +2.0
   - Extracted function name matches: +1.5
   - Keyword matches: +0.5 per match
   - Intent matching: +1.0
   - Use case matches: +0.3 per match
3. **Top K Selection**: Returns top k results after re-ranking
4. **Formatting**: Includes summary and function names in output

### Example Query

**Query**: `"start payment"`

**Result**: Matches documents containing:
- Keywords: "start payment", "checkout", "deposit"
- Function names: "createAppSessionMessage"
- Use cases: "peer-to-peer payment", "instant micro-transactions"

This bridges the **vocabulary gap** where user-friendly queries match technical documentation.

## File Structure

```
backend/
├── data/
│   ├── chroma_db/              # Vector database storage
│   │   ├── chroma.sqlite3      # SQLite database
│   │   └── [uuid]/             # Binary index files
│   └── enriched_docs.json       # Backup of enriched documents
├── services/
│   ├── vector_store.py          # Vector store implementation (used by main app)
│   └── doc_enrichment.py        # AI enrichment service (used by main app)
└── vector_db_setup/             # Setup scripts (not used by main app)
    ├── ingest_docs.py           # Full ingestion pipeline
    ├── load_enriched_to_vector_db.py  # Load from JSON to ChromaDB
    ├── test_enrichment.py       # Test scripts
    ├── test_single_enrichment.py
    ├── VECTOR_DATABASE.md       # This documentation
    └── README.md                # Quick reference
```

## Configuration

### Environment Variables

Required:
- `GOOGLE_API_KEY`: Google API key for embeddings and LLM

Optional:
- `GOOGLE_MODEL`: LLM model for enrichment (default: `gemini-3-flash-preview`)

### Code Configuration

**Vector Store** (`backend/services/vector_store.py`):
```python
collection_name = "yellow_docs"
persist_directory = "backend/data/chroma_db"
embedding_model = "models/text-embedding-004"
```

**Enrichment** (`backend/services/doc_enrichment.py`):
```python
llm_model = settings.GOOGLE_MODEL  # Default: gemini-3-flash-preview
temperature = 0.1
max_tokens = 2048
batch_size = 10
```

## Usage Examples

### Basic Search

```python
from agent.tools.vector_store import YellowVectorStore

vector_store = YellowVectorStore()
results = vector_store.search("create payment session", k=5)
print(results)
```

### Direct Vector Store Access

```python
from agent.tools.vector_store import YellowVectorStore

vector_store = YellowVectorStore()
# Access underlying ChromaDB
raw_results = vector_store.vector_store.similarity_search("query", k=10)

# Access metadata
for doc in raw_results:
    print(doc.metadata.get("function_name"))
    print(doc.metadata.get("keywords"))  # Comma-separated string
    print(doc.metadata.get("summary"))
```

### Re-populate from JSON

```bash
cd backend
python vector_db_setup/load_enriched_to_vector_db.py
```

## Maintenance

### Re-creating the Database

1. **Delete existing database**:
   ```bash
   rm -rf backend/data/chroma_db/*
   ```

2. **Load from enriched JSON**:
   ```bash
   python vector_db_setup/load_enriched_to_vector_db.py
   ```

### Full Re-ingestion (with re-enrichment)

1. **Run full ingestion**:
   ```bash
   python vector_db_setup/ingest_docs.py
   ```

   This will:
   - Re-chunk documents
   - Re-enrich with AI (costs API calls)
   - Save to JSON
   - Populate ChromaDB

## Performance Characteristics

- **Embedding Generation**: ~1-2 seconds per document (API call)
- **Search Latency**: <100ms for semantic search
- **Re-ranking Overhead**: ~10-20ms for metadata-based scoring
- **Storage Size**: ~5-10MB for 335 documents

## Future Enhancements

Potential improvements:
1. **Hybrid Retrieval**: Combine keyword search (BM25) with vector search
2. **Query Expansion**: Expand user queries with synonyms before embedding
3. **Embedding Caching**: Cache embeddings to avoid re-computation
4. **Incremental Updates**: Support adding/updating individual documents
5. **Multi-model Support**: Allow switching embedding models

## Troubleshooting

### Common Issues

1. **"GOOGLE_API_KEY is not set"**
   - Solution: Set `GOOGLE_API_KEY` in `.env` file

2. **"Expected metadata value to be a str, int, float, bool, or None, got list"**
   - Solution: Metadata normalization should handle this automatically
   - Check that `_normalize_metadata_for_chromadb()` is being called

3. **Search returns no results**
   - Check that documents were successfully loaded
   - Verify embeddings were generated (check ChromaDB files exist)
   - Try a more general query

4. **Enrichment fails for some chunks**
   - Check API key and quota
   - Review error messages in console output
   - Failed chunks will use original content (no enrichment)

## References

- **ChromaDB**: https://www.trychroma.com/
- **Google Generative AI Embeddings**: https://ai.google.dev/docs/embeddings
- **LangChain Chroma Integration**: https://python.langchain.com/docs/integrations/vectorstores/chroma
