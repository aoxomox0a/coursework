"""
LLM prompt templates for SPARQL generation.
Optimized for instruction-tuned small models (Mistral-7b, Llama, etc.) via Hactar/HuggingFace.
Output is always wrapped in ```sparql ... ``` fences for reliable extraction.
"""

SPARQL_GENERATION_TEMPLATE = """\
You are a SPARQL query generator. Your only output is a valid SPARQL query wrapped in a code fence.

## Rules
- Output EXACTLY one ```sparql ... ``` block — nothing before, nothing after.
- Declare only the PREFIX aliases you actually use in the query body.
- Use ONLY the URIs provided below. Do NOT invent new URIs or properties.
- Default to SELECT unless the question requires ASK or DESCRIBE.
- Every query must have a WHERE {{ }} clause with at least one triple pattern.
- Use ?subject and ?object as primary variable names when applicable.
- Wrap optional values in OPTIONAL {{ }}.
- Apply FILTER only when the question implies a constraint (date range, language, number).

## Input

Question: {question}

Entity URIs (use these as subjects or objects in triple patterns):
{entity_uris}

Main property URI (the relation that links entities):
<{property_uri}>

Additional candidate properties (use if they add precision):
{related_properties}

## One-shot example

Question: "What is the capital of France?"
Entities:
  <http://dbpedia.org/resource/France>
Property: <http://dbpedia.org/ontology/capital>

```sparql
PREFIX dbo: <http://dbpedia.org/ontology/>
SELECT ?capital WHERE {{
  <http://dbpedia.org/resource/France> dbo:capital ?capital .
}}
```

## Now generate the query for the question above.

```sparql
"""

SPARQL_FIX_TEMPLATE = """\
You are a SPARQL repair assistant. Your only output is a corrected SPARQL query wrapped in a code fence.

## Rules
- Output EXACTLY one ```sparql ... ``` block — nothing before, nothing after.
- Preserve the original query intent; fix ONLY what the error describes.
- Declare only the PREFIX aliases you actually use.
- Use ONLY the URIs that appear in the original query. Do NOT introduce new ones.

## Error report

Question the query must answer: {question}

Validation error:
{error_message}

Broken query:
```sparql
{original_query}
```

## How to fix common errors
- "Missing WHERE clause" → add WHERE {{ <original triple patterns> }}
- "Unbalanced braces" → count {{ and }} and add the missing closing brace at the right nesting level
- "No SPARQL variables" → replace literal values used as results with ?varName
- "Missing query type" → prepend SELECT ?var or ASK as appropriate
- "Unbalanced parentheses" → close or remove the dangling parenthesis in FILTER or function calls

## Corrected query:

```sparql
"""

SPARQL_EXPLANATION_TEMPLATE = """\
You are an expert at converting SPARQL queries back to natural language questions.

Analyze this SPARQL query and output ONLY the natural language question that would generate it.

The output should be a single, clear question ending with a question mark.
No code. No explanation. Just the question.

SPARQL Query:
```
{sparql_query}
```

Natural Language Question:
"""


def generate_sparql_prompt(
    question: str,
    entity_uris: list[str],
    property_uri: str,
    related_properties: list[str] | None = None,
) -> str:
    """
    Generate an LLM prompt for SPARQL query generation.

    Args:
        question: Natural language question
        entity_uris: List of linked entity URIs
        property_uri: Main property/relation URI
        related_properties: Optional list of additional candidate property URIs

    Returns:
        Formatted prompt string with ```sparql fence instruction
    """
    if related_properties is None:
        related_properties = []

    entity_list = (
        "\n".join(f"  <{uri}>" for uri in entity_uris)
        if entity_uris
        else "  (none provided)"
    )
    related_list = (
        "\n".join(f"  <{p}>" for p in related_properties)
        if related_properties
        else "  (none)"
    )

    return SPARQL_GENERATION_TEMPLATE.format(
        question=question,
        entity_uris=entity_list,
        property_uri=property_uri,
        related_properties=related_list,
    )


def generate_fix_sparql_prompt(
    question: str,
    original_query: str,
    error_message: str,
) -> str:
    """
    Generate an LLM prompt to repair an invalid SPARQL query.

    Args:
        question: Original natural language question
        original_query: The invalid SPARQL query
        error_message: Validation error description

    Returns:
        Formatted repair prompt string with ```sparql fence instruction
    """
    return SPARQL_FIX_TEMPLATE.format(
        question=question,
        original_query=original_query,
        error_message=error_message,
    )


def generate_sparql_explanation_prompt(sparql_query: str) -> str:
    """
    Generate an LLM prompt to explain a SPARQL query in natural language.

    Args:
        sparql_query: The SPARQL query to explain

    Returns:
        Formatted explanation prompt string
    """
    return SPARQL_EXPLANATION_TEMPLATE.format(sparql_query=sparql_query)
