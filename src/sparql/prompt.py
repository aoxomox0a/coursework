"""
LLM prompt templates for SPARQL generation.
"""


def generate_sparql_prompt(
    question: str,
    entity_uris: list,
    property_uri: str,
    related_properties: list = None
) -> str:
    """
    Generate a prompt for the LLM to create SPARQL query.

    Args:
        question: Original natural language question
        entity_uris: List of linked entity URIs
        property_uri: Selected property/relation URI
        related_properties: Optional list of related properties

    Returns:
        Formatted prompt string
    """
    if related_properties is None:
        related_properties = []

    prompt = f"""Generate a SPARQL query to answer: "{question}"

Given:
- Question: {question}
- Entities (URIs): {entity_uris}
- Main property/relation: <{property_uri}>
- Related properties: {related_properties}

Generate a valid SPARQL query that retrieves the answer.
Return ONLY the SPARQL query, no explanation.

Query:"""

    return prompt


def generate_fix_sparql_prompt(
    question: str,
    original_query: str,
    error_message: str
) -> str:
    """
    Generate a prompt to fix invalid SPARQL syntax.

    Args:
        question: Original question
        original_query: Invalid SPARQL query
        error_message: Error message from validator

    Returns:
        Formatted prompt for LLM
    """
    prompt = f"""Fix this SPARQL query that has syntax errors:

Question: {question}
Error: {error_message}

Original (invalid) query:
{original_query}

Generate a corrected SPARQL query that answers the question.
Return ONLY the corrected SPARQL query, no explanation.

Query:"""

    return prompt
