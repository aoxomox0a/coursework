"""
Link extracted entities to URIs in knowledge graph using ChromaDB.
"""
from typing import List, Dict, Any
from config.settings import SPARQL_ENDPOINT
from src.indexing.chroma_storage import get_chroma_client, get_collection_name


def _get_collection(collection_name: str):
    """Get endpoint-scoped collection from the shared ChromaDB client."""
    scoped_name = get_collection_name(collection_name, SPARQL_ENDPOINT)
    return get_chroma_client().get_collection(scoped_name)


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


def link_entities(
    extracted_entities: List[str],
    top_k: int = 3
) -> List[Dict[str, any]]:
    """
    Match extracted entity texts to URIs in ChromaDB.

    Args:
        extracted_entities: List of entity texts from NER
        top_k: Number of candidates to return per entity

    Returns:
        List of dicts with entity, candidates, and scores
    """
    results = []
    entities_collection = _get_collection("entities")

    for entity in extracted_entities:
        candidates = _query_collection(
            entities_collection,
            query_text=entity,
            n_results=top_k
        )

        results.append({
            "entity": entity,
            "candidates": candidates
        })

    return results


def disambiguate_entities(
    linking_results: List[Dict],
    context: str = ""
) -> List[Dict[str, str]]:
    """
    Select best matching URI for each entity.

    Args:
        linking_results: Output from link_entities()
        context: Additional context for disambiguation (optional)

    Returns:
        List of dicts with entity and selected URI
    """
    disambiguated = []

    for result in linking_results:
        if result["candidates"]:
            best_candidate = result["candidates"][0]
            disambiguated.append({
                "entity": result["entity"],
                "uri": best_candidate["uri"],
                "confidence": best_candidate["score"]
            })

    return disambiguated
