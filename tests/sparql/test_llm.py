"""Tests for src/sparql/llm.py — TDD (RED phase)."""
import pytest
from unittest.mock import patch, MagicMock
from src.sparql.llm import call_llm, extract_sparql_from_response


# --- extract_sparql_from_response ---

def test_extract_sparql_fenced(valid_sparql_query, fenced_llm_response):
    result = extract_sparql_from_response(fenced_llm_response)
    assert "SELECT" in result
    assert "WHERE" in result


def test_extract_sparql_fenced_exact(valid_sparql_query):
    response = f"```sparql\n{valid_sparql_query}\n```"
    result = extract_sparql_from_response(response)
    assert result.strip() == valid_sparql_query.strip()


def test_extract_sparql_fenced_no_language_tag(valid_sparql_query):
    response = f"```\n{valid_sparql_query}\n```"
    result = extract_sparql_from_response(response)
    assert "SELECT" in result


def test_extract_sparql_fallback_keyword_scan():
    response = "Sure! SELECT ?x WHERE { ?x ?p ?o . }"
    result = extract_sparql_from_response(response)
    assert "SELECT" in result


def test_extract_sparql_empty_response():
    result = extract_sparql_from_response("")
    assert result == ""


def test_extract_sparql_no_sparql_content():
    result = extract_sparql_from_response("Hello, I cannot generate a query for this.")
    assert result == ""


# --- call_llm ---

def _mock_response(content: str, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    return mock


@patch("src.sparql.llm.requests.post")
def test_call_llm_success(mock_post, fenced_llm_response):
    mock_post.return_value = _mock_response(fenced_llm_response)
    result = call_llm("some prompt")
    assert isinstance(result, str)
    assert len(result) > 0


@patch("src.sparql.llm.requests.post")
def test_call_llm_sends_chat_completions_format(mock_post, fenced_llm_response):
    mock_post.return_value = _mock_response(fenced_llm_response)
    call_llm("test prompt")
    _, kwargs = mock_post.call_args
    payload = kwargs.get("json", mock_post.call_args[0][1] if len(mock_post.call_args[0]) > 1 else {})
    # Accept both positional and keyword argument styles
    call_kwargs = mock_post.call_args
    json_payload = call_kwargs.kwargs.get("json") or (call_kwargs.args[1] if len(call_kwargs.args) > 1 else None)
    assert json_payload is not None
    assert "messages" in json_payload
    assert json_payload["messages"][0]["role"] == "user"
    assert json_payload["messages"][0]["content"] == "test prompt"


@patch("src.sparql.llm.requests.post")
def test_call_llm_uses_bearer_auth(mock_post, fenced_llm_response):
    mock_post.return_value = _mock_response(fenced_llm_response)
    call_llm("test prompt")
    call_kwargs = mock_post.call_args
    headers = call_kwargs.kwargs.get("headers") or call_kwargs.args[1] if len(call_kwargs.args) > 1 else {}
    headers = call_kwargs.kwargs.get("headers", {})
    assert "Authorization" in headers
    assert headers["Authorization"].startswith("Bearer ")


@patch("src.sparql.llm.requests.post")
def test_call_llm_non_200_returns_empty(mock_post):
    mock_post.return_value = _mock_response("", status_code=500)
    mock_post.return_value.json.return_value = {"error": "Internal server error"}
    result = call_llm("some prompt")
    assert result == ""


@patch("src.sparql.llm.requests.post")
def test_call_llm_timeout_returns_empty(mock_post):
    import requests as req
    mock_post.side_effect = req.exceptions.Timeout()
    result = call_llm("some prompt")
    assert result == ""


@patch("src.sparql.llm.requests.post")
def test_call_llm_low_temperature(mock_post, fenced_llm_response):
    mock_post.return_value = _mock_response(fenced_llm_response)
    call_llm("test prompt")
    call_kwargs = mock_post.call_args
    json_payload = call_kwargs.kwargs.get("json")
    assert json_payload["temperature"] <= 0.2
