import json
import sys
import os
import re
import asyncio
from typing import List
from pathlib import Path

# Add backend directory to sys.path to allow imports
# This script is located at backend/vector_db_setup/ingest_docs.py
current_file = Path(__file__).resolve()
backend_root = current_file.parent.parent
sys.path.append(str(backend_root))

from utils.dotenv import load_dotenv
load_dotenv(backend_root / ".env")

from agent.tools.vector_store import YellowVectorStore
from doc_enrichment import DocumentEnricher
from langchain_core.documents import Document

DOCS_JSON_PATH = backend_root.parent / "docs" / "yellow_docs_vector_data.json"

def clean_text(text: str) -> str:
    # Remove breadcrumbs like "* [](/)"
    text = re.sub(r'^\s*\* \[\]\(/.*\)$', '', text, flags=re.MULTILINE)
    # Remove "On this page" TOC
    text = re.sub(r'^On this page.*$', '', text, flags=re.MULTILINE)
    # Remove footer "Edit this page"
    text = re.sub(r'\[Edit this page\].*$', '', text, flags=re.MULTILINE)
    return text.strip()

def chunk_content(item: dict) -> List[Document]:
    url = item.get("id", "")
    raw_text = item.get("text", "")
    metadata_base = item.get("metadata", {})
    
    clean_content = clean_text(raw_text)
    
    chunks = []
    
    # API Reference mode: split by Level 4 headers (#### `functionName`)
    if "/api-reference/" in url:
        # Split by #### to capture function definitions
        # The split will consume the delimiter, so we need to be careful.
        # simpler approach: split by `#### ` and re-attach?
        # Or just use LangChain's Markdown splitter if we wanted, but let's stick to the plan's custom logic
        # for precision on these specific docs.
        
        parts = re.split(r'(^####\s+.*$)', clean_content, flags=re.MULTILINE)
        
        # parts[0] is intro text
        # parts[1] is header 1
        # parts[2] is body 1
        # parts[3] is header 2
        # parts[4] is body 2...
        
        current_chunk = parts[0]
        
        for i in range(1, len(parts), 2):
            header = parts[i]
            body = parts[i+1] if i+1 < len(parts) else ""
            
            # If the current chunk is substantial, save it
            if len(current_chunk.strip()) > 50:
                 chunks.append(Document(
                    page_content=current_chunk.strip(),
                    metadata={**metadata_base, "chunk_type": "api_intro"}
                ))
            
            # New chunk for this function
            current_chunk = header + "\n" + body
            
        # Add the last one
        if current_chunk.strip():
             chunks.append(Document(
                page_content=current_chunk.strip(),
                metadata={**metadata_base, "chunk_type": "api_function"}
            ))
            
    else:
        # Guide mode: split by Level 2 headers (## )
        parts = re.split(r'(^##\s+.*$)', clean_content, flags=re.MULTILINE)
        
        current_chunk = parts[0]
        
        for i in range(1, len(parts), 2):
            header = parts[i]
            body = parts[i+1] if i+1 < len(parts) else ""
            
            if len(current_chunk.strip()) > 50:
                 chunks.append(Document(
                    page_content=current_chunk.strip(),
                    metadata={**metadata_base, "chunk_type": "guide_section"}
                ))
            
            current_chunk = header + "\n" + body
            
        if current_chunk.strip():
             chunks.append(Document(
                page_content=current_chunk.strip(),
                metadata={**metadata_base, "chunk_type": "guide_section"}
            ))
            
    # Fallback: if no chunks (e.g. no headers found), use the whole text
    if not chunks and clean_content:
        chunks.append(Document(
            page_content=clean_content,
            metadata=metadata_base
        ))
        
    return chunks

async def main():
    print(f"Loading docs from {DOCS_JSON_PATH}...")
    try:
        with open(DOCS_JSON_PATH, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find {DOCS_JSON_PATH}")
        sys.exit(1)

    all_docs = []
    print(f"Processing {len(data)} pages...")
    
    for item in data:
        page_chunks = chunk_content(item)
        all_docs.extend(page_chunks)
        
    print(f"Generated {len(all_docs)} chunks.")
    
    # Enrich documents before storing
    print("\n" + "="*60)
    print("ENRICHING DOCUMENTS WITH AI METADATA")
    print("="*60)
    
    try:
        enricher = DocumentEnricher()
        enriched_docs = await enricher.enrich_batch(all_docs, batch_size=10)
        
        # Count enrichment stats
        enriched_count = sum(1 for d in enriched_docs if d.metadata.get("enriched", False))
        failed_count = len(enriched_docs) - enriched_count
        print(f"\nEnrichment complete: {enriched_count}/{len(enriched_docs)} chunks enriched successfully.")
        if failed_count > 0:
            print(f"Warning: {failed_count} chunks failed enrichment and will use original content.")
    except Exception as e:
        print(f"Error during enrichment: {e}")
        print("Falling back to unenriched documents...")
        enriched_docs = all_docs
    
    # Save enriched documents as JSON for backup/inspection
    enriched_json_path = backend_root / "data" / "enriched_docs.json"
    print(f"\nSaving enriched documents to {enriched_json_path}...")
    
    enriched_data = []
    for doc in enriched_docs:
        enriched_data.append({
            "page_content": doc.page_content,
            "metadata": doc.metadata
        })
    
    os.makedirs(enriched_json_path.parent, exist_ok=True)
    with open(enriched_json_path, "w", encoding="utf-8") as f:
        json.dump(enriched_data, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(enriched_data)} enriched documents to JSON.")
    
    print("\nInitializing Vector Store...")
    vector_store = YellowVectorStore()
    
    print("Adding documents to ChromaDB...")
    vector_store.add_documents(enriched_docs)
    
    print("Ingestion complete.")

if __name__ == "__main__":
    asyncio.run(main())
