from __future__ import annotations

import os
from typing import List, Optional
from pathlib import Path

from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from config import settings


class OpenRouterEmbeddings:
    """Custom embedding class that uses OpenRouter API for embeddings."""
    
    def __init__(self, model: str = "text-embedding-3-large"):
        """
        Initialize OpenRouter embeddings.
        
        Args:
            model: Embedding model name. OpenRouter supports:
                   - text-embedding-3-small (1536 dims)
                   - text-embedding-3-large (3072 dims)
                   - text-embedding-ada-002 (1536 dims)
        """
        import requests
        
        self.api_key = settings.OPENROUTER_API_KEY
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not set")
        
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"
        
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


class YellowVectorStore:
    def __init__(self, use_openrouter: bool = True):
        """
        Initialize vector store.
        
        Args:
            use_openrouter: If True, use OpenRouter embeddings. If False, use Google.
        """
        if use_openrouter:
            if not settings.OPENROUTER_API_KEY:
                raise ValueError("OPENROUTER_API_KEY is not set. Cannot initialize embeddings.")
            
            # Use OpenRouter embeddings
            self.embeddings = OpenRouterEmbeddings(model="text-embedding-3-large")
        else:
            # Original Google embeddings (for backward compatibility)
            if not settings.GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY is not set. Cannot initialize embeddings.")
            
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=settings.GOOGLE_API_KEY,
            )

        # Persist in backend/data/chroma_db
        # We assume this code runs from backend/ or root, so we resolve relative to this file
        # File is now at backend/agent/tools/vector_store.py, so go up 3 levels to backend/
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.persist_directory = str(base_dir / "data" / "chroma_db")
        
        # Ensure directory exists
        os.makedirs(self.persist_directory, exist_ok=True)

        self.vector_store = Chroma(
            collection_name="yellow_docs",
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory,
        )

    def _normalize_metadata_for_chromadb(self, metadata: dict) -> dict:
        """
        Convert list metadata fields to strings for ChromaDB compatibility.
        ChromaDB only accepts str, int, float, bool, None in metadata.
        """
        normalized = metadata.copy()
        
        # Remove 'enriched' flag if present
        normalized.pop("enriched", None)
        normalized.pop("error", None)  # Also remove error field if present
        
        # Convert lists to comma-separated strings
        list_fields = ["keywords", "function_names", "use_cases"]
        for field in list_fields:
            if field in normalized and isinstance(normalized[field], list):
                normalized[field] = ", ".join(str(item) for item in normalized[field])
        
        return normalized

    def _parse_metadata_list(self, value) -> List[str]:
        """
        Parse metadata value that might be a list or comma-separated string.
        """
        if isinstance(value, list):
            return value
        elif isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        else:
            return []

    def add_documents(self, documents: List[Document]):
        """
        Add documents to the vector store.
        Normalizes metadata to be ChromaDB-compatible.
        """
        if not documents:
            return
        
        # Normalize metadata for ChromaDB (convert lists to strings, remove enriched flag)
        normalized_docs = []
        for doc in documents:
            normalized_metadata = self._normalize_metadata_for_chromadb(doc.metadata)
            normalized_docs.append(Document(
                page_content=doc.page_content,
                metadata=normalized_metadata
            ))
        
        self.vector_store.add_documents(normalized_docs)

    def search(self, query: str, k: int = 5, use_metadata_filter: bool = True) -> str:
        """
        Search for documents with enhanced metadata filtering and re-ranking.
        
        Args:
            query: Search query string
            k: Number of results to return
            use_metadata_filter: If True, re-rank results using metadata (default: True)
        
        Returns:
            Formatted string with search results
        """
        # Get more candidates for re-ranking
        candidate_count = k * 2 if use_metadata_filter else k
        results = self.vector_store.similarity_search(query, k=candidate_count)
        
        # If metadata filtering is enabled, re-rank by relevance
        if use_metadata_filter and results:
            scored_results = self._score_and_rerank(results, query)
            results = [doc for _, doc in scored_results[:k]]
        else:
            results = results[:k]
        
        # Format results with enhanced metadata
        return self._format_results(results)
    
    def _score_and_rerank(self, results: List[Document], query: str) -> List[tuple[float, Document]]:
        """
        Score and re-rank results based on metadata matches.
        
        Returns:
            List of (score, document) tuples sorted by score (descending)
        """
        query_lower = query.lower()
        scored_results = []
        
        for doc in results:
            score = 1.0  # Base score from semantic similarity
            metadata = doc.metadata
            
            # Boost if function name matches
            function_name = metadata.get("function_name")
            if function_name and function_name.lower() in query_lower:
                score += 2.0
            
            # Boost if any extracted function names match
            function_names = self._parse_metadata_list(metadata.get("function_names", []))
            for fn in function_names:
                if fn.lower() in query_lower:
                    score += 1.5
                    break
            
            # Boost if keywords match
            keywords = self._parse_metadata_list(metadata.get("keywords", []))
            keyword_matches = sum(1 for kw in keywords if kw.lower() in query_lower)
            if keyword_matches > 0:
                score += keyword_matches * 0.5
            
            # Boost if intent matches query context
            intent = metadata.get("intent", "")
            if "api" in query_lower and intent == "api_reference":
                score += 1.0
            if ("tutorial" in query_lower or "how" in query_lower or "guide" in query_lower) and intent == "tutorial":
                score += 1.0
            if "migration" in query_lower and intent == "migration":
                score += 1.0
            if "error" in query_lower and intent == "error_handling":
                score += 1.0
            
            # Boost if use cases match
            use_cases = self._parse_metadata_list(metadata.get("use_cases", []))
            use_case_matches = sum(1 for uc in use_cases if uc.lower() in query_lower)
            if use_case_matches > 0:
                score += use_case_matches * 0.3
            
            scored_results.append((score, doc))
        
        # Sort by score (descending)
        scored_results.sort(key=lambda x: x[0], reverse=True)
        return scored_results
    
    def _format_results(self, results: List[Document]) -> str:
        """
        Format search results with enhanced metadata.
        """
        formatted_results = []
        for doc in results:
            metadata = doc.metadata
            source = metadata.get("title", "Unknown Source")
            content = doc.page_content
            
            # Include enrichment metadata if available
            summary = metadata.get("summary", "")
            function_name = metadata.get("function_name")
            
            header = f"--- Documentation: {source} ---"
            if function_name:
                header += f" [Function: {function_name}]"
            if summary:
                header += f"\nSummary: {summary}"
            
            formatted_results.append(f"{header}\n{content}\n")
            
        return "\n".join(formatted_results)
