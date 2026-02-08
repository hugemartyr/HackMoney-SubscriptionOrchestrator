from typing import List
from agent.tools.vector_store import YellowVectorStore

def _search_docs_wrapper(query: str, missing_info: list[str] | None) -> str:
    """Helper to run blocking vector store operations in a thread."""
    try:
        vs = YellowVectorStore()
        final_query = query
        if missing_info:
            final_query += " " + " ".join(missing_info)
        return vs.search(final_query)
    except Exception as e:
        return f"Error searching docs: {str(e)}"

def _search_docs_with_checklist(checklist: List[str]) -> str:
    """
    Search vector database using checklist items.
    Each checklist item becomes a search query.
    """
    vector_store = YellowVectorStore(use_openrouter=True)
    all_results = []
    
    for checklist_item in checklist:
        try:
            # Search with each checklist item as a query
            results = vector_store.search(checklist_item, k=5)  # Top 5 results per item
            all_results.extend(results)
        except Exception as e:
            print(f"Error searching for '{checklist_item}': {e}")
            continue
    
    # Deduplicate results
    seen = set()
    unique_results = []
    for result in all_results:
        content = result.page_content
        if content not in seen:
            seen.add(content)
            unique_results.append(result)
    
    # Combine into context string, organized by checklist item
    combined_parts = []
    used_content = set()
    
    for checklist_item in checklist:
        # Find results that match this checklist item
        matching_results = [
            r for r in unique_results 
            if r.page_content not in used_content and (
                checklist_item.lower() in r.page_content.lower() or 
                any(word in r.page_content.lower() for word in checklist_item.lower().split())
            )
        ][:3]  # Top 3 matches per item
        
        if matching_results:
            combined_parts.append(f"=== Documentation for: {checklist_item} ===\n")
            for result in matching_results:
                combined_parts.append(f"{result.page_content}\n\n")
                used_content.add(result.page_content)
    
    # Add any remaining unique results
    remaining = [r for r in unique_results if r.page_content not in used_content]
    if remaining:
        combined_parts.append("\n=== Additional Relevant Documentation ===\n")
        for result in remaining[:5]:
            combined_parts.append(f"{result.page_content}\n\n")
    
    return "\n".join(combined_parts)
