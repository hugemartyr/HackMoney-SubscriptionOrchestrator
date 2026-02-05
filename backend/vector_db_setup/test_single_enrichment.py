#!/usr/bin/env python3
"""Test enrichment on a single chunk to verify it works."""
import sys
import asyncio
from pathlib import Path

# Add backend directory to sys.path
current_file = Path(__file__).resolve()
backend_root = current_file.parent
sys.path.append(str(backend_root))

from utils.dotenv import load_dotenv
load_dotenv(backend_root / ".env")

from doc_enrichment import DocumentEnricher
from langchain_core.documents import Document

async def main():
    print("Testing enrichment on a single chunk...")
    
    # Create a test document chunk (similar to what we'd get from ingestion)
    test_doc = Document(
        page_content="""
#### `createAppSessionMessage(signer: MessageSigner, sessions: AppSession[]): Promise<string>`

Creates a signed application session message.

**Parameters:**
- signer: A function that signs messages
- sessions: Array of application sessions to create

**Returns:**
- Promise<string>: The signed session message

This is used to initialize a payment flow on the Yellow Network.
""",
        metadata={
            "title": "API Reference | Yellow Network",
            "url": "https://docs.yellow.org/docs/api-reference",
            "source": "yellow-docs",
            "chunk_type": "api_function"
        }
    )
    
    print(f"\nOriginal document:")
    print(f"  Content length: {len(test_doc.page_content)} chars")
    print(f"  Metadata: {list(test_doc.metadata.keys())}")
    print(f"  Content preview: {test_doc.page_content[:200]}...")
    
    # Enrich it
    print("\n" + "="*60)
    print("ENRICHING...")
    print("="*60)
    
    enricher = DocumentEnricher()
    enriched_doc = await enricher.enrich_chunk(test_doc)
    
    print(f"\nEnriched document:")
    print(f"  Enriched flag: {enriched_doc.metadata.get('enriched', False)}")
    print(f"  Function name: {enriched_doc.metadata.get('function_name', 'None')}")
    print(f"  Function names (extracted): {enriched_doc.metadata.get('function_names', [])}")
    print(f"  Intent: {enriched_doc.metadata.get('intent', 'unknown')}")
    print(f"  Summary: {enriched_doc.metadata.get('summary', '')}")
    print(f"  Keywords: {enriched_doc.metadata.get('keywords', [])}")
    print(f"  Use cases: {enriched_doc.metadata.get('use_cases', [])}")
    print(f"\n  Enhanced content length: {len(enriched_doc.page_content)} chars")
    print(f"  Enhanced content preview (last 300 chars):")
    print(f"  ...{enriched_doc.page_content[-300:]}")
    
    if enriched_doc.metadata.get('enriched', False):
        print("\n✅ Enrichment successful!")
    else:
        print("\n❌ Enrichment failed!")
        if 'error' in enriched_doc.metadata:
            print(f"   Error: {enriched_doc.metadata['error']}")

if __name__ == "__main__":
    asyncio.run(main())
