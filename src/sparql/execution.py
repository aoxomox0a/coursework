"""
Execute SPARQL queries on endpoint and format results.
"""

import logging
from typing import Any
from config.settings import SPARQL_ENDPOINT

import httpx

logger = logging.getLogger(__name__)

_ACCEPT_JSON = "application/sparql-results+json"


async def execute_query(
    query: str,
    endpoint_url: str = SPARQL_ENDPOINT,
) -> dict[str, Any]:

    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(
                endpoint_url,
                params={"query": query, "format": "json"},
                headers={"Accept": _ACCEPT_JSON},
                timeout=60,
            )

            if response.status_code == 200:
                return response.json()

            logger.error(
                "SPARQL endpoint returned %d for query: %.100s",
                response.status_code,
                query,
            )
            return {"error": f"Endpoint returned {response.status_code}"}
        except Exception as exc:
            logger.error("Error executing SPARQL query: %s", exc)
            return {"error": str(exc)}


def format_results(results_json: dict[str, Any]) -> str:
    """
    Format SPARQL JSON results into human-readable text.

    Args:
        results_json: Raw JSON results from SPARQL endpoint

    Returns:
        Formatted string answer
    """
    if "error" in results_json:
        return f"Query execution error: {results_json['error']}"

    bindings = results_json.get("results", {}).get("bindings", [])

    if not bindings:
        return "No results found."

    lines = []
    for i, binding in enumerate(bindings, 1):
        items = [
            f"{var}: {val_obj.get('value', '')}" for var, val_obj in binding.items()
        ]
        lines.append(f"{i}. {', '.join(items)}")

    return "\n".join(lines)


async def execute_and_format(
    query: str,
    endpoint_url: str = SPARQL_ENDPOINT,
) -> str:
    """
    Execute query and return formatted results string.

    Args:
        query: SPARQL query
        endpoint_url: SPARQL endpoint URL

    Returns:
        Formatted results string
    """
    results = await execute_query(query, endpoint_url)
    return format_results(results)
