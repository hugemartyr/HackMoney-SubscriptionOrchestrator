from __future__ import annotations

import json
import re
from typing import Dict, List, Optional
from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI
from config import settings


class DocumentEnricher:
    """
    Enriches documentation chunks with AI-generated metadata to improve
    searchability and bridge the vocabulary gap for autonomous agents.
    """
    
    def __init__(self):
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set. Cannot initialize enricher.")
        
        self.llm = ChatGoogleGenerativeAI(
            model=settings.GOOGLE_MODEL,
            api_key=settings.GOOGLE_API_KEY,
            temperature=0.1,  # Low temperature for consistent metadata
            max_tokens=2048,
        )
    
    def extract_function_names(self, text: str) -> List[str]:
        """
        Extract function/method names from code snippets using regex.
        This is a fast pre-filter before LLM enrichment.
        """
        # Match function definitions: `functionName(...)` or `#### functionName`
        patterns = [
            r'`([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',  # `functionName(`
            r'####\s+`([a-zA-Z_][a-zA-Z0-9_]*)',  # #### `functionName
            r'create([A-Z][a-zA-Z0-9]*)',  # createAppSession, createChannel, etc.
            r'([a-z]+_[a-z_]+)',  # snake_case like create_app_session
        ]
        
        functions = set()
        for pattern in patterns:
            matches = re.findall(pattern, text)
            functions.update(matches)
        
        return list(functions)[:5]  # Limit to top 5
    
    async def enrich_chunk(self, doc: Document) -> Document:
        """
        Enrich a single document chunk with AI-generated metadata.
        """
        content = doc.page_content
        metadata = doc.metadata.copy()
        chunk_type = metadata.get("chunk_type", "unknown")
        title = metadata.get("title", "Unknown")
        
        # Skip if chunk is too small
        if len(content.strip()) < 50:
            return doc
        
        # Fast extraction of function names (no LLM needed)
        function_names = self.extract_function_names(content)
        
        # Build enrichment prompt
        prompt = self._build_enrichment_prompt(content, title, chunk_type, function_names)
        
        try:
            # Call LLM for intelligent metadata
            response = await self.llm.ainvoke(prompt)
            raw_content = getattr(response, "content", "") or ""
            
            # Extract text from content (handles strings, lists, dicts)
            content_text = self._extract_text_from_content(raw_content)
            
            # Parse JSON response
            enrichment_data = self._parse_enrichment_response(content_text)
            
            # Merge metadata
            enriched_metadata = {
                **metadata,
                **enrichment_data,
                "function_names": function_names,  # Add extracted functions
            }
            
            # Enhance page_content with keywords for better searchability
            enhanced_content = self._enhance_content(content, enrichment_data)
            
            return Document(
                page_content=enhanced_content,
                metadata=enriched_metadata
            )
            
        except Exception as e:
            # Fallback: return original doc with basic metadata
            print(f"Warning: Failed to enrich chunk from '{title}': {e}")
            return Document(
                page_content=content,
                metadata={**metadata, "error": str(e)}
            )
    
    def _build_enrichment_prompt(
        self, 
        content: str, 
        title: str, 
        chunk_type: str,
        function_names: List[str]
    ) -> str:
        """
        Build the prompt for LLM enrichment.
        """
        # Truncate content if too long (keep first 2000 chars for context)
        content_preview = content[:2000] + ("..." if len(content) > 2000 else "")
        
        prompt = f"""You are indexing documentation for the Yellow Network crypto payment protocol SDK.

Analyze this documentation chunk and return a JSON object with exactly these fields:

1. "summary": A 1-2 sentence explanation of what this component DOES (written for a System Architect who needs to understand the purpose, not implementation details).

2. "keywords": A list of 8-15 technical and non-technical synonyms/terms that users might search for. Include:
   - User-friendly terms (e.g., "start payment", "checkout", "deposit")
   - Technical terms (e.g., "session", "channel", "state update")
   - Related concepts (e.g., "authentication", "signing", "multi-party")
   - Common misspellings or variations

3. "function_name": If this chunk documents a specific API method/function, extract its exact name (e.g., 'createAppSessionMessage', 'submitAppState'). If multiple functions are mentioned, list the primary one. If none, return null.

4. "intent": One of: "api_reference", "tutorial", "concept", "migration", "error_handling", "configuration"

5. "use_cases": A list of 2-4 specific use cases or scenarios where this would be relevant (e.g., ["peer-to-peer payment", "subscription billing", "multi-party escrow"])

CHUNK TYPE: {chunk_type}
SECTION TITLE: {title}
EXTRACTED FUNCTION NAMES: {', '.join(function_names) if function_names else 'None'}

CHUNK TEXT:
{content_preview}

Return ONLY valid JSON, no markdown, no explanation."""

        return prompt
    
    def _extract_text_from_content(self, content) -> str:
        """
        Extract text from LLM response content which can be:
        - A string
        - A list of strings or dicts like {'type': 'text', 'text': '...'}
        - A dict like {'type': 'text', 'text': '...'}
        """
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict):
                    # Extract text from dict content blocks
                    text = item.get("text", "") if item.get("type") == "text" else str(item)
                    if text:
                        text_parts.append(text)
                else:
                    text_parts.append(str(item))
            return "".join(text_parts)
        elif isinstance(content, dict):
            # Single dict content block
            return content.get("text", "") if content.get("type") == "text" else str(content)
        else:
            return str(content)
    
    def _parse_enrichment_response(self, raw_content: str) -> Dict:
        """
        Parse LLM response and extract JSON.
        """
        # Try to extract JSON from response
        content = raw_content.strip()
        
        # Remove markdown code fences if present
        if content.startswith("```"):
            content = re.sub(r'^```(?:json)?\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
        
        try:
            data = json.loads(content)
            # Validate required fields
            required = ["summary", "keywords", "intent", "use_cases"]
            for field in required:
                if field not in data:
                    data[field] = "" if field != "keywords" else []
            
            # Ensure function_name is present (can be null)
            if "function_name" not in data:
                data["function_name"] = None
            
            return data
        except json.JSONDecodeError as e:
            # Fallback: return minimal metadata
            print(f"Warning: Failed to parse enrichment JSON: {e}")
            return {
                "summary": "",
                "keywords": [],
                "function_name": None,
                "intent": "unknown",
                "use_cases": []
            }
    
    def _enhance_content(self, content: str, enrichment_data: Dict) -> str:
        """
        Enhance the page_content by appending keywords and summary.
        This makes the content more searchable while keeping original text intact.
        """
        keywords = enrichment_data.get("keywords", [])
        summary = enrichment_data.get("summary", "")
        
        # Append enrichment data to content for better semantic search
        # The embedding will capture these terms
        enhancement = []
        
        if summary:
            enhancement.append(f"\n\nSummary: {summary}")
        
        if keywords:
            # Add keywords in a way that's natural for embeddings
            keywords_text = ", ".join(keywords)
            enhancement.append(f"\n\nRelated terms: {keywords_text}")
        
        use_cases = enrichment_data.get("use_cases", [])
        if use_cases:
            enhancement.append(f"\n\nUse cases: {', '.join(use_cases)}")
        
        return content + "".join(enhancement)
    
    async def enrich_batch(self, documents: List[Document], batch_size: int = 10) -> List[Document]:
        """
        Enrich multiple documents with rate limiting and progress tracking.
        """
        enriched = []
        total = len(documents)
        
        for i in range(0, total, batch_size):
            batch = documents[i:i + batch_size]
            print(f"Enriching batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size} ({len(batch)} chunks)...")
            
            # Process batch concurrently
            import asyncio
            batch_results = await asyncio.gather(
                *[self.enrich_chunk(doc) for doc in batch],
                return_exceptions=True
            )
            
            for result in batch_results:
                if isinstance(result, Exception):
                    print(f"Error in batch processing: {result}")
                    continue
                enriched.append(result)
        
        return enriched
