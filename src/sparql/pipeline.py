"""
SPARQL Pipeline: Orchestrate prompt generation, LLM call, validation, and execution.
"""

import logging
from typing import TypedDict, Dict, List
from src.sparql import prompt, llm, validation, execution
import asyncio

logger = logging.getLogger(__name__)


class SparqlPipelineResult(TypedDict):
    status: str
    answer: str
    sparql_query: str
    error_message: str | None


async def run_sparql_pipeline(
    question: str, linking_result: dict
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

    related = [c.get("uri") for c in relation_candidates if c.get("uri")]

    # Step 1: Generate prompt and call LLM
    logger.info("Generating SPARQL prompt for: %s", question)
    sparql_prompt = prompt.generate_sparql_prompt(
        question=question,
        entity_uris=entity_uris,
        property_uri=property_uri,
        related_properties=related,
    )

    raw_response = await llm.call_llm(sparql_prompt)
    generated_query = llm.extract_sparql_from_response(raw_response)
    logger.info("Generated query:\n%s", generated_query)

    # Step 2: Validate — one retry with fix prompt
    is_valid, error_msg = validation.is_valid_sparql(generated_query)

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
    answer = await execution.execute_and_format(generated_query)
    logger.info("Query executed: %s", answer[:100])

    return SparqlPipelineResult(
        status="success",
        answer=answer,
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
