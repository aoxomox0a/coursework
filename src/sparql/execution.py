"""
Execute SPARQL queries on endpoint and format results.
"""
import requests
from typing import List, Dict, Any
from config.settings import SPARQL_ENDPOINT


def execute_query(
    query: str,
    endpoint_url: str = SPARQL_ENDPOINT
) -> Dict[str, Any]:
    """
    Execute SPARQL query on endpoint.

    Args:
        query: Valid SPARQL query string
        endpoint_url: SPARQL endpoint URL

    Returns:
        Dict with results or error info
    """
    try:
        response = requests.get(
            endpoint_url,
            params={"query": query, "format": "json"},
            timeout=60
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {
                "error": f"Endpoint returned {response.status_code}",
                "status": response.status_code
            }
    except Exception as e:
        return {"error": str(e)}


def format_results(results_json: Dict) -> str:
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

    # Format results as readable text
    formatted_lines = []
    for i, binding in enumerate(bindings, 1):
        items = []
        for var, value_obj in binding.items():
            value = value_obj.get("value", "")
            items.append(f"{var}: {value}")
        formatted_lines.append(f"{i}. {', '.join(items)}")

    return "\n".join(formatted_lines)


def execute_and_format(
    query: str,
    endpoint_url: str = SPARQL_ENDPOINT
) -> str:
    """
    Execute query and return formatted results.

    Args:
        query: SPARQL query
        endpoint_url: SPARQL endpoint URL

    Returns:
        Formatted results string
    """
    results = execute_query(query, endpoint_url)
    return format_results(results)
