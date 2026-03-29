"""Tests for src/sparql/execution.py — TDD (RED phase)."""
import pytest
from unittest.mock import patch, MagicMock
from src.sparql.execution import execute_query, format_results, execute_and_format


def _mock_get(json_data: dict, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    return mock


def test_format_results_with_bindings(sparql_json_response):
    result = format_results(sparql_json_response)
    assert "Christopher_Nolan" in result
    assert "1." in result


def test_format_results_empty_bindings():
    result = format_results({"results": {"bindings": []}})
    assert result == "No results found."


def test_format_results_error_dict():
    result = format_results({"error": "Connection refused"})
    assert "error" in result.lower() or "Connection refused" in result


def test_format_results_multiple_bindings():
    data = {
        "results": {
            "bindings": [
                {"name": {"type": "literal", "value": "Alice"}},
                {"name": {"type": "literal", "value": "Bob"}},
            ]
        }
    }
    result = format_results(data)
    assert "Alice" in result
    assert "Bob" in result
    assert "1." in result
    assert "2." in result


@patch("src.sparql.execution.requests.get")
def test_execute_query_success(mock_get, sparql_json_response, valid_sparql_query):
    mock_get.return_value = _mock_get(sparql_json_response)
    result = execute_query(valid_sparql_query)
    assert "results" in result
    assert mock_get.called


@patch("src.sparql.execution.requests.get")
def test_execute_query_sends_accept_header(mock_get, sparql_json_response, valid_sparql_query):
    mock_get.return_value = _mock_get(sparql_json_response)
    execute_query(valid_sparql_query)
    call_kwargs = mock_get.call_args
    headers = call_kwargs.kwargs.get("headers", {})
    assert "Accept" in headers
    assert "json" in headers["Accept"].lower()


@patch("src.sparql.execution.requests.get")
def test_execute_query_non_200_returns_error(mock_get, valid_sparql_query):
    mock_get.return_value = _mock_get({}, status_code=500)
    result = execute_query(valid_sparql_query)
    assert "error" in result


@patch("src.sparql.execution.requests.get")
def test_execute_and_format_returns_string(mock_get, sparql_json_response, valid_sparql_query):
    mock_get.return_value = _mock_get(sparql_json_response)
    result = execute_and_format(valid_sparql_query)
    assert isinstance(result, str)
    assert len(result) > 0
