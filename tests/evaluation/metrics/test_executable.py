"""Tests for src/evaluation/metrics/executable.py — funnel stage 2."""
from unittest.mock import AsyncMock

import pytest

from src.evaluation.metrics.executable import (
    ExecutableResult,
    ExecutableStatus,
    evaluate_executable,
)


@pytest.fixture
def mock_executor(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr("src.evaluation.metrics.executable.execute_query", mock)
    return mock


async def test_ok_response_returns_bindings(mock_executor):
    mock_executor.return_value = {
        "results": {"bindings": [{"x": {"type": "uri", "value": "http://a"}}]}
    }
    r = await evaluate_executable("SELECT ?x WHERE {}", endpoint="http://e")
    assert r.status == ExecutableStatus.OK
    assert r.bindings == [{"x": {"type": "uri", "value": "http://a"}}]
    assert r.error == ""


async def test_ok_with_empty_bindings(mock_executor):
    mock_executor.return_value = {"results": {"bindings": []}}
    r = await evaluate_executable("SELECT ?x WHERE {}", endpoint="http://e")
    assert r.status == ExecutableStatus.OK
    assert r.bindings == []


async def test_endpoint_error_is_classified(mock_executor):
    mock_executor.return_value = {"error": "Endpoint returned 500"}
    r = await evaluate_executable("SELECT ?x WHERE {}", endpoint="http://e")
    assert r.status == ExecutableStatus.ENDPOINT_ERROR
    assert r.bindings is None
    assert "500" in r.error


async def test_timeout_is_classified_separately(mock_executor):
    mock_executor.return_value = {"error": "request timed out"}
    r = await evaluate_executable("SELECT ?x WHERE {}", endpoint="http://e")
    assert r.status == ExecutableStatus.TIMEOUT
    assert "timed out" in r.error


async def test_passes_endpoint_through(mock_executor):
    mock_executor.return_value = {"results": {"bindings": []}}
    await evaluate_executable("Q", endpoint="http://custom-endpoint/sparql")
    args, kwargs = mock_executor.call_args
    # query is positional or kw, endpoint is the second arg
    assert kwargs.get("endpoint_url") == "http://custom-endpoint/sparql" or args[1] == "http://custom-endpoint/sparql"


async def test_result_is_frozen():
    import dataclasses

    r = ExecutableResult(status=ExecutableStatus.OK, bindings=[], error="")
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.error = "mutated"  # type: ignore[misc]
