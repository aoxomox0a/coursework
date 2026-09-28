"""
SPARQL Pipeline: Orchestrate prompt generation, LLM call, validation, and execution.
"""

import logging
from typing import TypedDict
from src.sparql import prompt, llm, validation, execution

logger = logging.getLogger(__name__)


def _load_profile_or_none(endpoint: str):
    """Try to derive a KGProfile for the current endpoint from the indexed state.

    Returns None (and falls back to the legacy prompt) when indexing has not
    been run yet for this endpoint, so the SPARQL pipeline keeps working even
    before the agnostic pipeline has been bootstrapped.
    """
    try:
        from src.kg_profiles import profile_from_index

        return profile_from_index(endpoint)
    except FileNotFoundError:
        logger.info(
            "No persisted KG profile for the current endpoint — using legacy prompt"
        )
        return None
    except (
        Exception
    ) as exc:  # defensive: never fail the SPARQL pipeline on a profile issue
        logger.warning("Failed to load KG profile (%s) — using legacy prompt", exc)
        return None


class SparqlPipelineResult(TypedDict):
    status: str
    answer: str
    sparql_query: str
    error_message: str | None


def get_required_prefixes(query_text: str) -> str:
    """
    Prepends standard Wikidata and DBpedia prefixes only if they are used
    in the query logic but haven't been explicitly defined yet.
    """
    prefixes = ""

    # --- Wikidata logic ---
    if "wd:" in query_text and "PREFIX wd:" not in query_text:
        prefixes += "PREFIX wd: <http://www.wikidata.org/entity/>\n"

    if "wdt:" in query_text and "PREFIX wdt:" not in query_text:
        prefixes += "PREFIX wdt: <http://www.wikidata.org/prop/direct/>\n"

    if "p:" in query_text and "PREFIX p:" not in query_text:
        prefixes += "PREFIX p: <http://www.wikidata.org/prop/>\n"

    if "ps:" in query_text and "PREFIX ps:" not in query_text:
        prefixes += "PREFIX ps: <http://www.wikidata.org/prop/statement/>\n"

    if "pq:" in query_text and "PREFIX pq:" not in query_text:
        prefixes += "PREFIX pq: <http://www.wikidata.org/prop/qualifier/>\n"

    # --- DBpedia logic ---
    if "dbo:" in query_text and "PREFIX dbo:" not in query_text:
        prefixes += "PREFIX dbo: <http://dbpedia.org/ontology/>\n"

    if "dbr:" in query_text and "PREFIX dbr:" not in query_text:
        prefixes += "PREFIX dbr: <http://dbpedia.org/resource/>\n"

    if "dbp:" in query_text and "PREFIX dbp:" not in query_text:
        prefixes += "PREFIX dbp: <http://dbpedia.org/property/>\n"

    if "res:" in query_text and "PREFIX res:" not in query_text:
        prefixes += "PREFIX res: <http://dbpedia.org/resource/>\n"

    return prefixes


async def run_sparql_pipeline(
    question: str, linking_result: dict, endpoint: str
) -> SparqlPipelineResult:
    """
    Execute the complete SPARQL generation & execution pipeline:
    1. Validate inputs — return early if no entity URIs
    2. Build LLM prompt from linked entities and relation
    3. Call LLM → extract SPARQL from fenced response
    4. Validate syntax — one retry with fix prompt if invalid
    5. Execute query on SPARQL endpoint
    6. Return structured result dict

    Args:
        question: Original natural language question
        linking_result: Output from the linking pipeline

    Returns:
        SparqlPipelineResult with status, answer, sparql_query, error_message
    """
    entities = linking_result.get("entities", [])
    relation = linking_result.get("relation", {})
    relation_candidates = linking_result.get("relation_candidates", [])

    entity_uris = [e.get("uri") for e in entities if e.get("uri")]
    property_uri = relation.get("uri", "")

    if not entity_uris:
        logger.warning("No entity URIs available for SPARQL generation")
        return _error("No entity URIs found in linking result")

    if not property_uri:
        logger.warning("No property URI available — attempting generation without it")

    # Pass full {uri, label, score} dicts to the prompt so the LLM can pick
    # by label semantics (essential for ORKG where embedding scores compress
    # candidates into a tight band — see hybrid retrieval rationale).
    related = [c for c in relation_candidates if c.get("uri")]

    # Step 1: Generate prompt and call LLM
    logger.info("Generating SPARQL prompt for: %s", question)
    profile = _load_profile_or_none(endpoint)
    sparql_prompt = prompt.generate_sparql_prompt(
        question=question,
        entity_uris=entity_uris,
        property_uri=property_uri,
        related_properties=related,
        profile=profile,
    )

    raw_response = await llm.call_llm(sparql_prompt)
    generated_query = llm.extract_sparql_from_response(raw_response)

    # prepend prefixes
    generated_query = get_required_prefixes(generated_query) + generated_query
    is_valid, error_msg = validation.is_valid_sparql(generated_query)

    logger.info("Generated query:\n%s", generated_query)

    if not is_valid:
        logger.warning(
            "SPARQL validation failed (%s) — retrying with fix prompt", error_msg
        )
        fix_prompt = prompt.generate_fix_sparql_prompt(
            question, generated_query, error_msg
        )
        raw_response = await llm.call_llm(fix_prompt)
        generated_query = llm.extract_sparql_from_response(raw_response)

        is_valid, error_msg = validation.is_valid_sparql(generated_query)
        if not is_valid:
            logger.error("SPARQL still invalid after retry: %s", error_msg)
            return _error(
                f"Failed to generate valid SPARQL query. Last error: {error_msg}"
            )

    logger.info("Query validated successfully")

    # Step 3: Execute
    answer = await execution.execute_and_format(generated_query, endpoint=endpoint)
    logger.info("Query executed: %s", answer[:100])

    nl_answer_prompt = prompt.generate_answer_prompt(
        question=question, sparql_query=generated_query, raw_result=answer
    )

    nl_answer = await llm.call_llm(nl_answer_prompt)

    return SparqlPipelineResult(
        status="success",
        answer=nl_answer,
        sparql_query=generated_query,
        error_message=None,
    )


def _error(message: str) -> SparqlPipelineResult:
    return SparqlPipelineResult(
        status="error",
        answer="",
        sparql_query="",
        error_message=message,
    )
