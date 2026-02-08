#!/usr/bin/env python3
"""
Test OpenRouter embedding models and create a custom embedding class.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List

# Add backend to path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from utils.dotenv import load_dotenv
load_dotenv()

from config import settings


class OpenRouterEmbeddings:
    """Custom embedding class that uses OpenRouter API for embeddings."""
    
    def __init__(self, model: str = "text-embedding-3-small"):
        """
        Initialize OpenRouter embeddings.
        
        Args:
            model: Embedding model name. OpenRouter supports:
                   - text-embedding-3-small (1536 dims)
                   - text-embedding-3-large (3072 dims)
                   - text-embedding-ada-002 (1536 dims)
        """
        import requests
        from pydantic import SecretStr
        
        self.api_key = settings.OPENROUTER_API_KEY
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not set")
        
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"
        self.requests = requests
        
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query string."""
        return self.embed_documents([text])[0]
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple documents."""
        import requests
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo",  # Optional
            "X-Title": "Yellow Network SDK Agent",  # Optional
        }
        
        # OpenRouter uses OpenAI-compatible endpoint
        url = f"{self.base_url}/embeddings"
        
        embeddings = []
        for text in texts:
            payload = {
                "model": self.model,
                "input": text,
            }
            
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            embeddings.append(data["data"][0]["embedding"])
        
        return embeddings


def test_openrouter_embeddings():
    """Test OpenRouter embedding models."""
    print("=" * 80)
    print("  TESTING OPENROUTER EMBEDDING MODELS")
    print("=" * 80)
    
    if not settings.OPENROUTER_API_KEY:
        print("❌ OPENROUTER_API_KEY is not set")
        return []
    
    print(f"✅ OPENROUTER_API_KEY found")
    print(f"   Using base URL: https://openrouter.ai/api/v1")
    
    # Models to test (OpenRouter supports OpenAI embedding models)
    models_to_test = [
        "text-embedding-3-small",
        "text-embedding-3-large", 
        "text-embedding-ada-002",
        "openai/text-embedding-3-small",
        "openai/text-embedding-3-large",
    ]
    
    working_models = []
    
    for model_name in models_to_test:
        try:
            print(f"\n   Testing: {model_name}")
            embeddings = OpenRouterEmbeddings(model=model_name)
            result = embeddings.embed_query("This is a test embedding")
            
            if result and len(result) > 0:
                print(f"   ✅ Works! Dimensions: {len(result)}")
                working_models.append((model_name, len(result)))
            else:
                print(f"   ❌ Returned empty result")
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "unauthorized" in error_msg.lower():
                print(f"   ❌ Authentication failed")
            elif "404" in error_msg or "not found" in error_msg.lower():
                print(f"   ❌ Model not found")
            else:
                print(f"   ❌ Error: {error_msg[:100]}")
    
    return working_models


if __name__ == "__main__":
    working = test_openrouter_embeddings()
    
    print("\n" + "=" * 80)
    print("  RESULTS")
    print("=" * 80)
    
    if working:
        print(f"✅ Found {len(working)} working model(s):")
        for model_name, dims in working:
            print(f"   - {model_name} ({dims} dimensions)")
        print(f"\n💡 Recommended: {working[0][0]}")
    else:
        print("❌ No working models found")
