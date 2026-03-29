"""
Validate SPARQL query syntax using rdflib's full SPARQL 1.1 parser.
"""
import logging
from rdflib.plugins.sparql import prepareQuery

logger = logging.getLogger(__name__)


def is_valid_sparql(query: str) -> tuple[bool, str]:
    """
    Validate SPARQL syntax using rdflib prepareQuery.

    Args:
        query: SPARQL query string

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not query or not query.strip():
        return False, "Query is empty"

    try:
        prepareQuery(query)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def validate_and_get_error(query: str) -> str:
    """
    Return error message if query is invalid, empty string if valid.

    Args:
        query: SPARQL query string

    Returns:
        Error message or empty string
    """
    is_valid, error = is_valid_sparql(query)
    return "" if is_valid else error
