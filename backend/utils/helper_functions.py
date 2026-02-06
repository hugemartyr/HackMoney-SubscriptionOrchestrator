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
