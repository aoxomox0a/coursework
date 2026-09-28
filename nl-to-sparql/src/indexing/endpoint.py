"""SPARQL Endpoint Connection - Connect to and query the SPARQL endpoint."""

import os
import httpx
import json
from typing import Optional
from config.settings import SPARQL_ENDPOINT

# Global variable to override default endpoint
_current_endpoint = None

# read verify_ssl from env var making non-verification opt-in
VERIFY_SSL = os.getenv("VERIFY_SPARQL_SSL", "True").lower() in ("true", "1", "yes")

# Headers for SPARQL requests
# force to return json
HEADERS = {
    "User-Agent": "NL-to-SPARQL-Agent/1.0 (Knowledge Graph Indexing System)",
    "Accept": "application/sparql-results+json, application/json",
}


def set_endpoint(endpoint: str):
    """Set a custom SPARQL endpoint for this session."""
    global _current_endpoint
    _current_endpoint = endpoint


def get_endpoint() -> str:
    """Get the current SPARQL endpoint."""
    global _current_endpoint
    return _current_endpoint if _current_endpoint else SPARQL_ENDPOINT


async def test_connection():
    """Return True iff the endpoint responds to a generic SPARQL probe (ASK query)."""
    # Endpoint-agnostic: any conformant SPARQL 1.1 endpoint with any triple returns true.
    query = "ASK { ?s ?p ?o }"

    current_endpoint = get_endpoint()
    print(f"Testing connection to: {current_endpoint}")

    async with httpx.AsyncClient(follow_redirects=True, verify=VERIFY_SSL) as client:
        try:
            response = await client.get(
                current_endpoint,
                params={"query": query, "format": "json"},
                headers=HEADERS,
                timeout=120,
            )
            response.raise_for_status()
            try:
                data = response.json()
            except json.JSONDecodeError:
                print(
                    f"Connection failed. Server returned non-JSON: {response.text[:200]}"
                )
                return False

            # ASK returns {"boolean": true/false}; legacy SELECT-shaped responses also accepted.
            if "boolean" in data or (
                "results" in data and "bindings" in data.get("results", {})
            ):
                print("✓ Connection successful!")
                return True
            print("✗ Connection OK but response shape unexpected")
            return False

        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False


async def query_sparql(
    query: str, format: str = "json", client: Optional[httpx.AsyncClient] = None
) -> dict:
    """
    Execute a SPARQL query on the endpoint.

    Args:
        query: SPARQL query string
        format: Response format (json, xml, etc.)

    Returns:
        Query results as dict
    """
    current_endpoint = get_endpoint()

    # If a shared client is passed in, use it
    if client:
        try:
            response = await client.get(
                current_endpoint,
                params={"query": query, "format": format},
                headers=HEADERS,
                timeout=120,  # Keep the bumped timeout!
            )
            response.raise_for_status()
            try:
                return response.json()
            except json.JSONDecodeError:
                print(
                    f"Error: Expected JSON from {current_endpoint}, got HTML/Text: {response.text[:200]}"
                )
                return {}
        except Exception as e:
            print(f"Error executing SPARQL query: {e}")
            return {}

    async with httpx.AsyncClient(
        follow_redirects=True, verify=VERIFY_SSL
    ) as new_client:
        try:
            response = await new_client.get(
                current_endpoint,
                params={"query": query, "format": format},
                headers=HEADERS,
                timeout=120,
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
    async with httpx.AsyncClient(follow_redirects=True, verify=VERIFY_SSL) as client:
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
