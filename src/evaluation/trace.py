"""
Instrumented variant of the SPARQL pipeline that captures first-pass and
retry outcomes separately, so the self-correction lift metric can be measured
without touching ``src/sparql/pipeline.run_sparql_pipeline`` (which colleagues
depend on at its current shape).

Mirrors the orchestration of ``run_sparql_pipeline`` step-for-step using the
same primitives (prompt, llm, validation, execution). If the colleague
pipeline changes shape (e.g. adds a second retry), keep this module in sync.
"""
import logging
from dataclasses import dataclass

from src.sparql.execution import execute_and_format
from src.sparql.llm import call_llm, extract_sparql_from_response
from src.sparql.prompt import generate_fix_sparql_prompt, generate_sparql_prompt
from src.sparql.validation import is_valid_sparql

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineTrace:
    question: str
    first_pass_query: str
    first_pass_valid: bool
    first_pass_error: str
    used_retry: bool
    retry_query: str | None
    retry_valid: bool | None
    retry_error: str | None
    final_query: str
    final_valid: bool
    answer: str
    status: str  # "success" | "error"


def _short_circuit(question: str, reason: str) -> PipelineTrace:
    return PipelineTrace(
        question=question,
        first_pass_query="",
        first_pass_valid=False,
        first_pass_error=reason,
        used_retry=False,
        retry_query=None,
        retry_valid=None,
        retry_error=None,
        final_query="",
        final_valid=False,
        answer="",
        status="error",
    )


def _load_profile_or_none():
    try:
        from src.indexing.endpoint import get_endpoint
        from src.kg_profiles import profile_from_index

        return profile_from_index(get_endpoint())
    except Exception:
        return None


async def run_with_trace(question: str, linking_result: dict) -> PipelineTrace:
    """Run the SPARQL generation + execution pipeline, recording every stage.

    Returns a PipelineTrace capturing both LLM calls (when retry happens) so
    downstream metrics (self-correction lift) can quantify the retry's value.
    """
    entities = linking_result.get("entities", [])
    relation = linking_result.get("relation", {})
    relation_candidates = linking_result.get("relation_candidates", [])

    entity_uris = [e.get("uri") for e in entities if e.get("uri")]
    property_uri = relation.get("uri", "")

    if not entity_uris:
        return _short_circuit(question, "no entity URIs in linking result")

    related = [c.get("uri") for c in relation_candidates if c.get("uri")]
    profile = _load_profile_or_none()

    sparql_prompt = generate_sparql_prompt(
        question=question,
        entity_uris=entity_uris,
        property_uri=property_uri,
        related_properties=related,
        profile=profile,
    )

    raw_first = await call_llm(sparql_prompt)
    first_query = extract_sparql_from_response(raw_first)
    first_valid, first_error = is_valid_sparql(first_query)

    used_retry = False
    retry_query: str | None = None
    retry_valid: bool | None = None
    retry_error: str | None = None
    final_query = first_query
    final_valid = first_valid
    final_error = first_error

    if not first_valid:
        used_retry = True
        fix_prompt = generate_fix_sparql_prompt(question, first_query, first_error)
        raw_retry = await call_llm(fix_prompt)
        retry_query = extract_sparql_from_response(raw_retry)
        retry_valid, retry_error = is_valid_sparql(retry_query)
        if retry_valid:
            final_query = retry_query
            final_valid = True
            final_error = ""
        else:
            final_query = retry_query
            final_valid = False
            final_error = retry_error

    if not final_valid:
        return PipelineTrace(
            question=question,
            first_pass_query=first_query,
            first_pass_valid=first_valid,
            first_pass_error=first_error,
            used_retry=used_retry,
            retry_query=retry_query,
            retry_valid=retry_valid,
            retry_error=retry_error,
            final_query=final_query,
            final_valid=False,
            answer="",
            status="error",
        )

    answer = await execute_and_format(final_query)
    return PipelineTrace(
        question=question,
        first_pass_query=first_query,
        first_pass_valid=first_valid,
        first_pass_error=first_error,
        used_retry=used_retry,
        retry_query=retry_query,
        retry_valid=retry_valid,
        retry_error=retry_error,
        final_query=final_query,
        final_valid=True,
        answer=answer,
        status="success",
    )
