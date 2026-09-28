"""
LLM prompt templates for SPARQL generation.
Optimized for instruction-tuned small models (Mistral-7b, Llama, etc.) via Hactar/HuggingFace.
Output is always wrapped in ```sparql ... ``` fences for reliable extraction.

Two templates coexist:
- SPARQL_GENERATION_TEMPLATE (legacy) — fires when no KGProfile is passed.
  Preserved verbatim so existing DBpedia callers see identical output.
- SPARQL_PROFILE_TEMPLATE (new) — fires when a KGProfile is supplied; prefixes,
  one-shot examples and style hints are injected from the profile.
"""
from src.kg_profiles import KGProfile, OneShotExample

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

SPARQL_PROFILE_TEMPLATE = """\
You are a SPARQL query generator. Your only output is a valid SPARQL query wrapped in a code fence.

## Rules
- Output EXACTLY one ```sparql ... ``` block — nothing before, nothing after.
- Declare only the PREFIX aliases you actually use in the query body.
- Use ONLY the URIs provided below. Do NOT invent new URIs or properties.
- Default to SELECT unless the question requires ASK or DESCRIBE.
- Every query must have a WHERE {{ }} clause with at least one triple pattern.
{style_hints}

## Available prefixes (for this endpoint)
{prefix_block}

## Examples
{one_shot_block}

## Input

Question: {question}

Entity URIs (use these as subjects or objects in triple patterns):
{entity_uris}

Main property URI (the relation that links entities):
<{property_uri}>

Additional candidate properties (use if they add precision):
{related_properties}

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

ANSWER_GENERATION_TEMPLATE = """\
    You are given:
    - Question: {question}
    - SPARQL query: {sparql_query}
    - Query result: {raw_result}

    Convert the result into a concise natural language answer.
    If multiple values, summarize clearly.
    Only output the answer.
"""


def _render_entity_list(entity_uris: list[str]) -> str:
    if not entity_uris:
        return "  (none provided)"
    return "\n".join(f"  <{uri}>" for uri in entity_uris)


def _render_related_list(related_properties: list) -> str:
    """Render the candidate properties block.

    Accepts either bare URI strings (legacy) or dicts ``{uri, label, score}``
    (preferred — gives the LLM a label to reason over). Multi-hop SciQA-style
    questions need the LLM to *pick the right predicate* among several with
    different labels, so labels matter as much as URIs.
    """
    if not related_properties:
        return "  (none)"
    rendered = []
    for p in related_properties:
        if isinstance(p, dict):
            uri = p.get("uri", "")
            label = p.get("label", "")
            if not uri:
                continue
            rendered.append(
                f"  <{uri}>  — \"{label}\"" if label else f"  <{uri}>"
            )
        else:
            rendered.append(f"  <{p}>")
    return "\n".join(rendered) if rendered else "  (none)"


def _render_prefix_block(prefixes: tuple[tuple[str, str], ...]) -> str:
    if not prefixes:
        return "(no prefixes registered)"
    return "\n".join(f"PREFIX {alias}: <{ns}>" for alias, ns in prefixes)


def _render_one_shot_block(examples: tuple[OneShotExample, ...], limit: int = 2) -> str:
    if not examples:
        return "(no curated examples available for this endpoint — rely on the rules above)"
    rendered = []
    for ex in examples[:limit]:
        ent_list = (
            "\n".join(f"  <{u}>" for u in ex.entity_uris)
            if ex.entity_uris
            else "  (none)"
        )
        prop = f"<{ex.property_uri}>" if ex.property_uri else "(none)"
        rendered.append(
            f"Question: {ex.question}\n"
            f"Entities:\n{ent_list}\n"
            f"Property: {prop}\n\n"
            f"```sparql\n{ex.sparql}\n```"
        )
    return "\n\n".join(rendered)


def _render_style_hints(hints: tuple[str, ...]) -> str:
    if not hints:
        return ""
    return "\n## Notes for this endpoint\n" + "\n".join(f"- {h}" for h in hints)


def generate_sparql_prompt(
    question: str,
    entity_uris: list[str],
    property_uri: str,
    related_properties: list[str] | None = None,
    profile: KGProfile | None = None,
) -> str:
    """
    Generate an LLM prompt for SPARQL query generation.

    Args:
        question: Natural language question.
        entity_uris: List of linked entity URIs.
        property_uri: Main property/relation URI.
        related_properties: Optional list of additional candidate property URIs.
        profile: Optional KGProfile. When None, the legacy DBpedia-flavored
            template is used verbatim (backward-compatible). When provided,
            prefixes, one-shot examples and style hints come from the profile.

    Returns:
        Formatted prompt string with ```sparql fence instruction.
    """
    if related_properties is None:
        related_properties = []

    entity_list = _render_entity_list(entity_uris)
    related_list = _render_related_list(related_properties)

    if profile is None:
        return SPARQL_GENERATION_TEMPLATE.format(
            question=question,
            entity_uris=entity_list,
            property_uri=property_uri,
            related_properties=related_list,
        )

    return SPARQL_PROFILE_TEMPLATE.format(
        question=question,
        entity_uris=entity_list,
        property_uri=property_uri,
        related_properties=related_list,
        prefix_block=_render_prefix_block(profile.prefixes),
        one_shot_block=_render_one_shot_block(profile.one_shot_examples),
        style_hints=_render_style_hints(profile.query_style_hints),
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


def generate_answer_prompt(question: str, sparql_query: str, raw_result: str) -> str:
    return ANSWER_GENERATION_TEMPLATE.format(
        question=question, sparql_query=sparql_query, raw_result=raw_result
    )
