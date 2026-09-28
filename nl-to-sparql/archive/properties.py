"""
Fetch properties and classes from SPARQL endpoint.
"""

from typing import List, Tuple
import httpx
from config.settings import SPARQL_ENDPOINT


async def fetch_properties(
    endpoint_url: str = SPARQL_ENDPOINT,
) -> List[Tuple[str, str]]:
    """
    Fetch all properties (predicates) from the knowledge graph.
    Returns list of (URI, label) pairs.

    Args:
        endpoint_url: SPARQL endpoint URL

    Returns:
        List of tuples: (property_uri, property_label)
    """
    query = """
    SELECT DISTINCT ?property ?label
    WHERE {
        ?property a rdf:Property .
        OPTIONAL { ?property rdfs:label ?label }
    }
    """

    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(
                endpoint_url, params={"query": query, "format": "json"}, timeout=30
            )
            results = []
            for binding in response.json().get("results", {}).get("bindings", []):
                uri = binding.get("property", {}).get("value", "")
                label = binding.get("label", {}).get("value", uri)
                if uri:
                    results.append((uri, label))
            return results
        except Exception as e:
            print(f"Error fetching properties: {e}")
            return []


async def fetch_classes(endpoint_url: str = SPARQL_ENDPOINT) -> List[Tuple[str, str]]:
    """
    Fetch all classes from the knowledge graph.
    Returns list of (URI, label) pairs.

    Args:
        endpoint_url: SPARQL endpoint URL

    Returns:
        List of tuples: (class_uri, class_label)
    """
    query = """
    SELECT DISTINCT ?class ?label
    WHERE {
        ?instance a ?class .
        OPTIONAL { ?class rdfs:label ?label }
    }
    LIMIT 1000
    """

    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(
                endpoint_url, params={"query": query, "format": "json"}, timeout=30
            )
            results = []
            for binding in response.json().get("results", {}).get("bindings", []):
                uri = binding.get("class", {}).get("value", "")
                label = binding.get("label", {}).get("value", uri)
                if uri:
                    results.append((uri, label))
            return results
        except Exception as e:
            print(f"Error fetching classes: {e}")
            return []
