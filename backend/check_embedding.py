#!/usr/bin/env python3
"""
Check what embedding model the vector database is using and test alternatives.

This script:
1. Inspects ChromaDB to see what embeddings were used
2. Tests different Google embedding model names
3. Checks for alternative embedding providers
4. Provides recommendations for fixing the embedding issue

Run from backend/ directory:
    python3 check_embeddings.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend to path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

# Load environment variables
try:
    from utils.dotenv import load_dotenv
    load_dotenv()
except Exception as e:
    print(f"⚠️  Warning: Could not load .env file: {e}")

from config import settings


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_result(name: str, passed: bool, details: str = ""):
    """Print a test result."""
    status = "✅" if passed else "❌"
    print(f"{status} {name}")
    if details:
        print(f"   {details}")


def inspect_chromadb_embeddings():
    """Inspect ChromaDB to see what embedding model was used."""
    print_section("1. Inspecting ChromaDB Database")
    
    try:
        import chromadb
        from pathlib import Path
        
        # Get the persist directory
        base_dir = Path(__file__).resolve().parent
        persist_dir = base_dir / "data" / "chroma_db"
        
        if not persist_dir.exists():
            print_result("ChromaDB directory exists", False, f"Not found: {persist_dir}")
            return None
        
        print_result("ChromaDB directory exists", True, f"Path: {persist_dir}")
        
        # Try to connect to ChromaDB
        try:
            client = chromadb.PersistentClient(path=str(persist_dir))
            collection = client.get_collection("yellow_docs")
            
            print_result("Collection 'yellow_docs' accessible", True)
            
            # Get collection info
            count = collection.count()
            print_result("Document count", True, f"{count} documents")
            
            # Try to get metadata about embeddings
            # ChromaDB doesn't store embedding model info directly, but we can check dimensions
            if count > 0:
                # Get one document to check embedding dimensions
                results = collection.get(limit=1, include=["embeddings"])
                if results and results.get("embeddings"):
                    embedding_dim = len(results["embeddings"][0])
                    print_result("Embedding dimensions", True, f"{embedding_dim} dimensions")
                    
                    # Common embedding dimensions:
                    # - text-embedding-004: 768 dimensions
                    # - text-embedding-3-small: 1536 dimensions
                    # - text-embedding-3-large: 3072 dimensions
                    # - OpenAI ada-002: 1536 dimensions
                    
                    if embedding_dim == 768:
                        print("   💡 Likely model: text-embedding-004 (768 dims)")
                    elif embedding_dim == 1536:
                        print("   💡 Likely model: text-embedding-3-small or OpenAI ada-002")
                    elif embedding_dim == 3072:
                        print("   💡 Likely model: text-embedding-3-large")
                    else:
                        print(f"   ⚠️  Unknown embedding model ({embedding_dim} dims)")
            
            return collection
            
        except Exception as e:
            print_result("ChromaDB connection", False, f"Error: {type(e).__name__}: {e}")
            return None
            
    except ImportError:
        print_result("ChromaDB import", False, "chromadb package not installed")
        return None
    except Exception as e:
        print_result("ChromaDB inspection", False, f"Error: {type(e).__name__}: {e}")
        return None


def test_google_embedding_models():
    """Test different Google embedding model names."""
    print_section("2. Testing Google Embedding Models")
    
    if not settings.GOOGLE_API_KEY:
        print_result("GOOGLE_API_KEY available", False, "Cannot test without API key")
        return []
    
    print_result("GOOGLE_API_KEY available", True)
    
    # Models to test
    models_to_test = [
        "models/text-embedding-004",
        "text-embedding-004",
        "models/embedding-001",
        "embedding-001",
        "textembedding-gecko@001",
        "textembedding-gecko@002",
        "textembedding-gecko@003",
    ]
    
    working_models = []
    
    for model_name in models_to_test:
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            
            print(f"\n   Testing: {model_name}")
            
            embeddings = GoogleGenerativeAIEmbeddings(
                model=model_name,
                google_api_key=settings.GOOGLE_API_KEY,
            )
            
            # Try to embed a test string
            test_text = "This is a test embedding"
            result = embeddings.embed_query(test_text)
            
            if result and len(result) > 0:
                print_result(f"Model: {model_name}", True, f"Works! Dimensions: {len(result)}")
                working_models.append((model_name, len(result)))
            else:
                print_result(f"Model: {model_name}", False, "Returned empty result")
                
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg or "NOT_FOUND" in error_msg:
                print_result(f"Model: {model_name}", False, "Model not found (404)")
            elif "401" in error_msg or "UNAUTHENTICATED" in error_msg:
                print_result(f"Model: {model_name}", False, "Authentication failed")
            else:
                print_result(f"Model: {model_name}", False, f"Error: {error_msg[:100]}")
    
    return working_models


def test_alternative_embedding_providers():
    """Test alternative embedding providers."""
    print_section("3. Testing Alternative Embedding Providers")
    
    alternatives = []
    
    # Test OpenAI embeddings
    print("\n   Testing OpenAI Embeddings...")
    try:
        openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        if openai_key:
            from langchain_openai import OpenAIEmbeddings
            
            embeddings = OpenAIEmbeddings(openai_api_key=openai_key)
            result = embeddings.embed_query("test")
            
            if result and len(result) > 0:
                print_result("OpenAI Embeddings", True, f"Works! Dimensions: {len(result)}")
                alternatives.append({
                    "provider": "OpenAI",
                    "class": "OpenAIEmbeddings",
                    "dimensions": len(result),
                    "model": "text-embedding-3-small (default)",
                })
            else:
                print_result("OpenAI Embeddings", False, "Returned empty result")
        else:
            print_result("OpenAI Embeddings", False, "No API key found (OPENAI_API_KEY or OPENROUTER_API_KEY)")
    except ImportError:
        print_result("OpenAI Embeddings", False, "langchain-openai not installed")
    except Exception as e:
        print_result("OpenAI Embeddings", False, f"Error: {type(e).__name__}: {e}")
    
    # Test HuggingFace embeddings (local)
    print("\n   Testing HuggingFace Embeddings (local)...")
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        
        # Use a small, fast model for testing
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        result = embeddings.embed_query("test")
        
        if result and len(result) > 0:
            print_result("HuggingFace Embeddings", True, f"Works! Dimensions: {len(result)}")
            alternatives.append({
                "provider": "HuggingFace",
                "class": "HuggingFaceEmbeddings",
                "dimensions": len(result),
                "model": "sentence-transformers/all-MiniLM-L6-v2",
            })
        else:
            print_result("HuggingFace Embeddings", False, "Returned empty result")
    except ImportError:
        print_result("HuggingFace Embeddings", False, "langchain-huggingface not installed")
    except Exception as e:
        print_result("HuggingFace Embeddings", False, f"Error: {type(e).__name__}: {e}")
    
    return alternatives


def check_model_compatibility(db_dimensions: Optional[int], working_models: List[tuple]):
    """Check if any working models match the database dimensions."""
    print_section("4. Model Compatibility Check")
    
    if db_dimensions is None:
        print("⚠️  Could not determine database embedding dimensions")
        return
    
    print(f"Database uses embeddings with {db_dimensions} dimensions")
    print("\nChecking compatibility with available models...")
    
    compatible = []
    incompatible = []
    
    for model_name, model_dims in working_models:
        if model_dims == db_dimensions:
            compatible.append((model_name, model_dims))
            print_result(f"✅ {model_name}", True, f"Compatible! ({model_dims} dims)")
        else:
            incompatible.append((model_name, model_dims))
            print_result(f"❌ {model_name}", False, f"Incompatible ({model_dims} dims vs {db_dimensions} dims)")
    
    if compatible:
        print(f"\n✅ Found {len(compatible)} compatible model(s)!")
        print("   You can use these models for queries without re-embedding:")
        for model_name, dims in compatible:
            print(f"   - {model_name}")
    else:
        print(f"\n❌ No compatible models found!")
        print("   You'll need to re-embed all documents with a new model.")
        print("   Recommended: Use one of the working models and re-run:")
        print("   python vector_db_setup/load_enriched_to_vector_db.py")


def provide_recommendations(working_models: List[tuple], alternatives: List[Dict], db_dimensions: Optional[int]):
    """Provide recommendations for fixing the embedding issue."""
    print_section("5. Recommendations")
    
    print("Based on the test results, here are your options:\n")
    
    # Option 1: Fix Google model name
    if working_models:
        print("OPTION 1: Use a working Google embedding model")
        print("   Working models found:")
        for model_name, dims in working_models:
            print(f"   - {model_name} ({dims} dimensions)")
        
        if db_dimensions:
            compatible = [m for m in working_models if m[1] == db_dimensions]
            if compatible:
                print(f"\n   ✅ Recommended: {compatible[0][0]}")
                print("   Update agent/tools/vector_store.py:")
                print(f'   Change: model="models/text-embedding-004"')
                print(f'   To:     model="{compatible[0][0]}"')
            else:
                print("\n   ⚠️  No compatible models found - will need to re-embed")
        else:
            print(f"\n   Try: {working_models[0][0]}")
    else:
        print("OPTION 1: No working Google models found")
        print("   The Google embedding API may have changed.")
        print("   Check Google AI Studio for current model names:")
        print("   https://ai.google.dev/models")
    
    # Option 2: Use alternatives
    if alternatives:
        print("\nOPTION 2: Switch to alternative embedding provider")
        print("   Available alternatives:")
        for alt in alternatives:
            print(f"   - {alt['provider']}: {alt['class']} ({alt['dimensions']} dims)")
            print(f"     Model: {alt['model']}")
        
        print("\n   ⚠️  Note: Switching providers requires re-embedding all documents")
        print("   Run: python vector_db_setup/load_enriched_to_vector_db.py")
    
    # Option 3: Check API version
    print("\nOPTION 3: Check Google API version")
    print("   The error mentioned 'API version v1beta'")
    print("   Try specifying a different API version in GoogleGenerativeAIEmbeddings")
    print("   Check langchain-google-genai documentation for API version parameter")


def main():
    """Run all checks."""
    print("\n" + "=" * 80)
    print("  EMBEDDING MODEL DIAGNOSTIC TOOL")
    print("=" * 80)
    
    # 1. Inspect database
    collection = inspect_chromadb_embeddings()
    db_dimensions = None
    if collection:
        try:
            results = collection.get(limit=1, include=["embeddings"])
            if results and results.get("embeddings"):
                db_dimensions = len(results["embeddings"][0])
        except:
            pass
    
    # 2. Test Google models
    working_models = test_google_embedding_models()
    
    # 3. Test alternatives
    alternatives = test_alternative_embedding_providers()
    
    # 4. Check compatibility
    if db_dimensions:
        check_model_compatibility(db_dimensions, working_models)
    
    # 5. Recommendations
    provide_recommendations(working_models, alternatives, db_dimensions)
    
    print("\n" + "=" * 80)
    print("  DIAGNOSTIC COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()