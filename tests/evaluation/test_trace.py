"""Tests for src/evaluation/trace.py — instrumented SPARQL pipeline runner."""
from unittest.mock import AsyncMock

import pytest

from src.evaluation.trace import PipelineTrace, run_with_trace


@pytest.fixture
def linking_result():
    return {
        "entities": [{"uri": "http://example.org/Inception", "label": "Inception"}],
        "relation": {"uri": "http://example.org/director", "label": "director"},
        "relation_candidates": [],
    }


@pytest.fixture
def patched_pipeline(monkeypatch):
    """Patch the underlying primitives so we can drive any branch of the orchestration."""
    llm_mock = AsyncMock()
    monkeypatch.setattr("src.evaluation.trace.call_llm", llm_mock)
    monkeypatch.setattr(
        "src.evaluation.trace.extract_sparql_from_response",
        lambda raw: raw,
    )
    monkeypatch.setattr(
        "src.evaluation.trace.execute_and_format",
        AsyncMock(return_value="formatted answer"),
    )
    return llm_mock


# ---------- happy path: first pass valid ----------------------------------


async def test_first_pass_valid_no_retry(patched_pipeline, linking_result):
    patched_pipeline.return_value = "SELECT ?x WHERE { ?x ?p ?o }"
    trace = await run_with_trace("Q?", linking_result)
    assert trace.first_pass_valid is True
    assert trace.used_retry is False
    assert trace.retry_query is None
    assert trace.retry_valid is None
    assert trace.final_query == "SELECT ?x WHERE { ?x ?p ?o }"
    assert trace.final_valid is True
    assert trace.status == "success"


# ---------- recovery: first pass invalid, retry valid ---------------------


async def test_first_invalid_retry_valid_records_recovery(patched_pipeline, linking_result):
    # First call returns broken SPARQL, second returns valid.
    patched_pipeline.side_effect = [
        "SELECT ?x WHERE { broken {{{",
        "SELECT ?x WHERE { ?x ?p ?o }",
    ]
    trace = await run_with_trace("Q?", linking_result)
    assert trace.first_pass_valid is False
    assert trace.first_pass_error  # populated
    assert trace.used_retry is True
    assert trace.retry_valid is True
    assert trace.final_query == "SELECT ?x WHERE { ?x ?p ?o }"
    assert trace.final_valid is True
    assert trace.status == "success"


# ---------- failure: both passes invalid ---------------------------------


async def test_both_invalid_records_failure(patched_pipeline, linking_result):
    patched_pipeline.side_effect = [
        "SELECT ?x WHERE { broken {{{",
        "still {{ broken",
    ]
    trace = await run_with_trace("Q?", linking_result)
    assert trace.first_pass_valid is False
    assert trace.used_retry is True
    assert trace.retry_valid is False
    assert trace.final_valid is False
    assert trace.status == "error"


# ---------- short-circuit: no entity URIs --------------------------------


async def test_no_entity_uris_short_circuits():
    linking = {"entities": [], "relation": {}, "relation_candidates": []}
    trace = await run_with_trace("Q?", linking)
    assert trace.status == "error"
    assert trace.first_pass_valid is False
    assert trace.used_retry is False
    # No LLM call was made, so first_pass_query is empty.
    assert trace.first_pass_query == ""


# ---------- result invariants --------------------------------------------


async def test_trace_is_frozen(patched_pipeline, linking_result):
    import dataclasses

    patched_pipeline.return_value = "SELECT ?x WHERE { ?x ?p ?o }"
    trace = await run_with_trace("Q?", linking_result)
    with pytest.raises(dataclasses.FrozenInstanceError):
        trace.status = "mutated"  # type: ignore[misc]
