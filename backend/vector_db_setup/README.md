# Vector Database Setup

This directory contains scripts and documentation for creating and maintaining the vector database used by the Yellow Network SDK documentation search system.

## Files

### Scripts

- **`ingest_docs.py`**: Full ingestion pipeline that chunks documents, enriches them with AI metadata, and populates the vector database
- **`load_enriched_to_vector_db.py`**: Loads pre-enriched documents from JSON and populates the vector database (faster, no API calls)

### Test Files

- **`test_enrichment.py`**: Tests the vector store search functionality with enriched data
- **`test_single_enrichment.py`**: Tests enrichment on a single document chunk

### Documentation

- **`VECTOR_DATABASE.md`**: Complete documentation of the vector database architecture, schema, configuration, and usage

## Quick Start

### Create/Update Vector Database from Enriched JSON

```bash
cd backend
python vector_db_setup/load_enriched_to_vector_db.py
```

### Full Re-ingestion (with AI Enrichment)

```bash
cd backend
python vector_db_setup/ingest_docs.py
```

**Note**: This will make API calls to Google Gemini for enrichment, which takes time and costs money.

## When to Use

- **Setup**: Initial database creation
- **Maintenance**: Re-creating database after schema changes
- **Updates**: Adding new documentation or updating existing docs

These scripts are **not** used by the main uvicorn application. The main app only uses the services in `backend/services/` (vector_store.py, doc_enrichment.py).
