"""
Validate SPARQL query syntax.
"""
import re


def is_valid_sparql(query: str) -> tuple[bool, str]:
    """
    Basic SPARQL validation.

    Args:
        query: SPARQL query string

    Returns:
        Tuple of (is_valid, error_message)
    """
    errors = []

    # Check for required keywords
    if not any(keyword in query.upper() for keyword in ["SELECT", "CONSTRUCT", "ASK", "DESCRIBE"]):
        errors.append("Missing query type (SELECT, CONSTRUCT, ASK, or DESCRIBE)")

    # Check for balanced braces
    if query.count("{") != query.count("}"):
        errors.append("Unbalanced braces: { and }")

    # Check for balanced parentheses
    if query.count("(") != query.count(")"):
        errors.append("Unbalanced parentheses")

    # Check for WHERE clause
    if "WHERE" not in query.upper():
        errors.append("Missing WHERE clause")

    # Check for basic syntax patterns
    if not re.search(r"\?[a-zA-Z_]\w*", query):
        errors.append("No SPARQL variables found (?var)")

    if errors:
        return False, "; ".join(errors)

    return True, ""


def validate_and_get_error(query: str) -> str:
    """
    Get error message if query is invalid.

    Args:
        query: SPARQL query string

    Returns:
        Error message or empty string if valid
    """
    is_valid, error = is_valid_sparql(query)
    return "" if is_valid else error
