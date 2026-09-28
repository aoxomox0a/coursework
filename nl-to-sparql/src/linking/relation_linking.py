"""
Link relations in questions to properties in knowledge graph.
"""

from typing import List, Dict

from src.indexing.chroma_storage import query_candidates


def find_relation_candidates(
    question: str,
    endpoint: str,
    top_k: int = 5,
) -> List[Dict[str, any]]:
    """
    Embed the question and find closest properties in ChromaDB.

    The endpoint is resolved via get_endpoint() at call time so runtime
    endpoint switches are respected.

    Args:
        question: Natural language question
        top_k: Number of property candidates to return

    Returns:
        List of candidate properties with scores
    """
    return query_candidates(
        query_text=question,
        collection_name="properties",
        endpoint=endpoint,
        top_k=top_k,
    )


def select_relation(candidates: List[Dict]) -> Dict[str, any]:
    """
    Select best property/relation from candidates.

    Args:
        candidates: Output from find_relation_candidates()

    Returns:
        Best candidate dict or empty dict if no candidates
    """
    if candidates:
        return candidates[0]
    return {}
