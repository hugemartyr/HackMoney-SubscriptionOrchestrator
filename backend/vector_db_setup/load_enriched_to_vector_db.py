#!/usr/bin/env python3
"""Load enriched documents from JSON and populate vector DB with OpenRouter embeddings."""
import json
import sys
import shutil
from pathlib import Path

# Add backend directory to sys.path
current_file = Path(__file__).resolve()
backend_root = current_file.parent.parent
sys.path.append(str(backend_root))

from utils.dotenv import load_dotenv
load_dotenv(backend_root / ".env")

from agent.tools.vector_store import YellowVectorStore
from langchain_core.documents import Document

ENRICHED_JSON_PATH = backend_root / "data" / "enriched_docs.json"

def main():
    print(f"Loading enriched documents from {ENRICHED_JSON_PATH}...")
    
    try:
        with open(ENRICHED_JSON_PATH, "r", encoding="utf-8") as f:
            enriched_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find {ENRICHED_JSON_PATH}")
        sys.exit(1)
    
    print(f"Loaded {len(enriched_data)} enriched documents.")
    
    # Convert JSON to Document objects
    documents = []
    for item in enriched_data:
        metadata = item["metadata"].copy()
        metadata.pop("enriched", None)
        
        documents.append(Document(
            page_content=item["page_content"],
            metadata=metadata
        ))
    
    print("\nInitializing Vector Store with OpenRouter embeddings...")
    print("Using embeddings: OpenRouter (text-embedding-3-large)")
    
    # Delete old database first
    chroma_dir = backend_root / "data" / "chroma_db"
    if chroma_dir.exists():
        print(f"\n⚠️  Deleting old database at {chroma_dir}...")
        shutil.rmtree(chroma_dir)
        print("✅ Old database deleted")
    
    # Create new vector store with OpenRouter
    vector_store = YellowVectorStore(use_openrouter=True)
    
    print("Adding documents to ChromaDB (with metadata normalization)...")
    print(f"Processing {len(documents)} documents...")
    
    # Process in batches to show progress
    batch_size = 50
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        vector_store.add_documents(batch)
        print(f"   Processed {min(i + batch_size, len(documents))}/{len(documents)} documents...")
    
    print(f"\n✅ Successfully added {len(documents)} documents to ChromaDB!")
    print("✅ Database rebuilt with OpenRouter embeddings!")

if __name__ == "__main__":
    main()
