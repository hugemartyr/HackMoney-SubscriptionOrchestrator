#!/usr/bin/env python3
"""Load enriched documents from JSON and populate vector DB."""
import json
import sys
from pathlib import Path

# Add backend directory to sys.path
current_file = Path(__file__).resolve()
backend_root = current_file.parent.parent
sys.path.append(str(backend_root))

from utils.dotenv import load_dotenv
load_dotenv(backend_root / ".env")

from services.vector_store import YellowVectorStore
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
        # Remove 'enriched' flag from metadata if present
        metadata = item["metadata"].copy()
        metadata.pop("enriched", None)
        
        documents.append(Document(
            page_content=item["page_content"],
            metadata=metadata
        ))
    
    print("\nInitializing Vector Store...")
    print("Using embeddings: Google Generative AI (models/text-embedding-004)")
    vector_store = YellowVectorStore()
    
    print("Adding documents to ChromaDB (with metadata normalization)...")
    vector_store.add_documents(documents)
    
    print(f"✅ Successfully added {len(documents)} documents to ChromaDB!")

if __name__ == "__main__":
    main()
