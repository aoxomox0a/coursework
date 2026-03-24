"""
Link relations in questions to properties in knowledge graph.
"""
from typing import List, Dict, Any
import chromadb
from config.settings import CHROMA_DB_PATH


def _get_collection(collection_name: str):
    """Get collection from ChromaDB."""
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return client.get_collection(collection_name)


def _query_collection(collection, query_text: str, n_results: int = 5) -> List[Dict[str, Any]]:
    """Query collection with text similarity search."""
    results = collection.query(query_texts=[query_text], n_results=n_results)
    formatted_results = []
    if results and results["metadatas"] and len(results["metadatas"]) > 0:
        for i, metadata in enumerate(results["metadatas"][0]):
            score = results["distances"][0][i] if results["distances"] else 0
            similarity = 1 / (1 + score) if score > 0 else 1.0
            formatted_results.append({
                "uri": metadata.get("uri", ""),
                "label": metadata.get("label", ""),
                "score": similarity
            })
    return formatted_results


def find_relation_candidates(
    question: str,
    top_k: int = 5
) -> List[Dict[str, any]]:
    """
    Embed the question and find closest properties in ChromaDB.

    Args:
        question: Natural language question
        top_k: Number of property candidates to return

    Returns:
        List of candidate properties with scores
    """
    properties_collection = _get_collection("properties")
    candidates = _query_collection(
        properties_collection,
        query_text=question,
        n_results=top_k
    )

    return candidates


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
