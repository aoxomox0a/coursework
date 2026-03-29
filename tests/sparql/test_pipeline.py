"""Tests for src/sparql/pipeline.py — TDD (RED phase)."""
import pytest
from unittest.mock import patch
from src.sparql.pipeline import run_sparql_pipeline

VALID_FENCED = """```sparql
PREFIX dbo: <http://dbpedia.org/ontology/>
SELECT ?director WHERE {
  <http://dbpedia.org/resource/Inception> dbo:director ?director .
}
```"""

INVALID_FENCED = "```sparql\nSELECT ?x WHERE {{ broken\n```"

FORMATTED_ANSWER = "1. director: http://dbpedia.org/resource/Christopher_Nolan"


@patch("src.sparql.pipeline.execution.execute_and_format")
@patch("src.sparql.pipeline.llm.call_llm")
def test_pipeline_happy_path(mock_llm, mock_execute, sample_linking_result):
    mock_llm.return_value = VALID_FENCED
    mock_execute.return_value = FORMATTED_ANSWER
    result = run_sparql_pipeline("Who directed Inception?", sample_linking_result)
    assert result["status"] == "success"
    assert result["answer"] == FORMATTED_ANSWER
    assert "sparql_query" in result


@patch("src.sparql.pipeline.execution.execute_and_format")
@patch("src.sparql.pipeline.llm.call_llm")
def test_pipeline_retry_on_invalid_syntax(mock_llm, mock_execute, sample_linking_result):
    mock_llm.side_effect = [INVALID_FENCED, VALID_FENCED]
    mock_execute.return_value = FORMATTED_ANSWER
    result = run_sparql_pipeline("Who directed Inception?", sample_linking_result)
    assert result["status"] == "success"
    assert mock_llm.call_count == 2


@patch("src.sparql.pipeline.execution.execute_and_format")
@patch("src.sparql.pipeline.llm.call_llm")
def test_pipeline_fails_after_retry(mock_llm, mock_execute, sample_linking_result):
    mock_llm.return_value = INVALID_FENCED
    mock_execute.return_value = FORMATTED_ANSWER
    result = run_sparql_pipeline("Who directed Inception?", sample_linking_result)
    assert result["status"] == "error"
    assert "error_message" in result


@patch("src.sparql.pipeline.execution.execute_and_format")
@patch("src.sparql.pipeline.llm.call_llm")
def test_pipeline_returns_dict(mock_llm, mock_execute, sample_linking_result):
    mock_llm.return_value = VALID_FENCED
    mock_execute.return_value = FORMATTED_ANSWER
    result = run_sparql_pipeline("Who directed Inception?", sample_linking_result)
    assert isinstance(result, dict)
    assert "status" in result
    assert "answer" in result


def test_pipeline_empty_entities():
    linking_result = {
        "entities": [],
        "relation": {"uri": "http://dbpedia.org/ontology/director"},
        "relation_candidates": [],
    }
    result = run_sparql_pipeline("Who directed Inception?", linking_result)
    assert result["status"] == "error"
