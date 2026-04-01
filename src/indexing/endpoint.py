"""SPARQL Endpoint Connection - Connect to and query the SPARQL endpoint."""

import httpx
from config.settings import SPARQL_ENDPOINT

# Global variable to override default endpoint
_current_endpoint = None

# Headers for SPARQL requests
HEADERS = {"User-Agent": "NL-to-SPARQL-Agent/1.0 (Knowledge Graph Indexing System)"}


def set_endpoint(endpoint: str):
    """Set a custom SPARQL endpoint for this session."""
    global _current_endpoint
    _current_endpoint = endpoint


def get_endpoint() -> str:
    """Get the current SPARQL endpoint."""
    global _current_endpoint
    return _current_endpoint if _current_endpoint else SPARQL_ENDPOINT


async def test_connection():
    """Test connection to SPARQL endpoint with a simple query."""
    query = """
    SELECT ?s ?label
    WHERE {
        ?s rdfs:label "Albert Einstein"@en .
        ?s rdfs:label ?label .
    }
    LIMIT 1
    """

    current_endpoint = get_endpoint()
    print(f"Testing connection to: {current_endpoint}")

    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(
                current_endpoint,
                params={"query": query, "format": "json"},
                headers=HEADERS,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            if "results" in data and "bindings" in data["results"]:
                print("✓ Connection successful!")
                return True
            else:
                print("✓ Connection OK (no results for test query)")
                return True

        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False


async def query_sparql(query: str, format: str = "json") -> dict:
    """
    Execute a SPARQL query on the endpoint.

    Args:
        query: SPARQL query string
        format: Response format (json, xml, etc.)

    Returns:
        Query results as dict
    """
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            current_endpoint = get_endpoint()
            response = await client.get(
                current_endpoint,
                params={"query": query, "format": format},
                headers=HEADERS,
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error executing SPARQL query: {e}")
            return {}


async def query_sparql_custom(query: str, endpoint: str, format: str = "json") -> dict:
    """
    Execute a SPARQL query on a custom endpoint.

    Args:
        query: SPARQL query string
        endpoint: Custom SPARQL endpoint URL
        format: Response format (json, xml, etc.)

    Returns:
        Query results as dict
    """
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(
                endpoint,
                params={"query": query, "format": format},
                headers=HEADERS,
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error executing SPARQL query: {e}")
            return {}
