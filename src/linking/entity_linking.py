"""
Link extracted entities to URIs in knowledge graph using ChromaDB.
"""
from typing import List, Dict
from config.settings import SPARQL_ENDPOINT
from src.indexing.chroma_storage import query_candidates


def link_entities(
    extracted_entities: List[str],
    top_k: int = 3,
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
    for entity in extracted_entities:
        candidates = query_candidates(
            query_text=entity,
            collection_name="entities",
            endpoint=SPARQL_ENDPOINT,
            top_k=top_k,
        )
        results.append({"entity": entity, "candidates": candidates})
    return results


def disambiguate_entities(
    linking_results: List[Dict],
    context: str = "",
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
            disambiguated.append(
                {
                    "entity": result["entity"],
                    "uri": best_candidate["uri"],
                    "confidence": best_candidate["score"],
                }
            )
    return disambiguated
