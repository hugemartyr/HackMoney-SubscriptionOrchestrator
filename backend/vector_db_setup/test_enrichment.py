#!/usr/bin/env python3
"""Quick test to verify enrichment worked."""
import sys
from pathlib import Path

# Add backend directory to sys.path
current_file = Path(__file__).resolve()
backend_root = current_file.parent
sys.path.append(str(backend_root))

from utils.dotenv import load_dotenv
load_dotenv(backend_root / ".env")

from services.vector_store import YellowVectorStore

def main():
    print("Testing vector store with enriched data...")
    vs = YellowVectorStore()
    
    # Test search
    query = "start payment"
    print(f"\nSearching for: '{query}'")
    results = vs.search(query, k=3)
    
    print(f"\n=== Search Results ===")
    print(results[:1000] + "..." if len(results) > 1000 else results)
    
    # Check if we can access enriched metadata directly
    print("\n=== Checking for enriched documents ===")
    raw_results = vs.vector_store.similarity_search(query, k=5)
    enriched_count = 0
    for i, doc in enumerate(raw_results[:3]):
        # Check if document has enrichment metadata (summary, keywords, etc.)
        has_summary = bool(doc.metadata.get("summary"))
        has_keywords = bool(doc.metadata.get("keywords"))
        is_enriched = has_summary or has_keywords
        
        if is_enriched:
            enriched_count += 1
            print(f"\nDocument {i+1}:")
            print(f"  Title: {doc.metadata.get('title', 'Unknown')}")
            print(f"  Has enrichment: {is_enriched}")
            print(f"  Function name: {doc.metadata.get('function_name', 'None')}")
            print(f"  Intent: {doc.metadata.get('intent', 'unknown')}")
            # Keywords might be a string (comma-separated) or list
            keywords = doc.metadata.get('keywords', '')
            if isinstance(keywords, str):
                keywords_list = [k.strip() for k in keywords.split(',')[:5]]
            else:
                keywords_list = keywords[:5] if isinstance(keywords, list) else []
            print(f"  Keywords: {keywords_list}...")
            print(f"  Summary: {doc.metadata.get('summary', '')[:100]}...")
    
    print(f"\nFound {enriched_count}/3 documents with enrichment metadata")

if __name__ == "__main__":
    main()
