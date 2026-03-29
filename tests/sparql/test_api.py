"""Tests for api/routes/sparql.py — TDD (RED phase)."""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

PIPELINE_SUCCESS = {
    "status": "success",
    "answer": "1. director: http://dbpedia.org/resource/Christopher_Nolan",
    "sparql_query": "SELECT ?director WHERE { ... }",
    "error_message": None,
}

PIPELINE_ERROR = {
    "status": "error",
    "answer": "",
    "sparql_query": "",
    "error_message": "Failed to generate valid SPARQL query.",
}

LINKING_RESULT = {
    "question": "Who directed Inception?",
    "entities": [{"uri": "http://dbpedia.org/resource/Inception", "confidence": 0.9}],
    "relation": {"uri": "http://dbpedia.org/ontology/director", "label": "director"},
    "relation_candidates": [],
}


@patch("api.routes.sparql.run_sparql_pipeline")
@patch("api.routes.sparql.run_linking_pipeline")
def test_answer_endpoint_success(mock_linking, mock_sparql):
    mock_linking.return_value = LINKING_RESULT
    mock_sparql.return_value = PIPELINE_SUCCESS
    response = client.post("/api/answer", json={"question": "Who directed Inception?"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "answer" in data
    assert data["question"] == "Who directed Inception?"


@patch("api.routes.sparql.run_sparql_pipeline")
@patch("api.routes.sparql.run_linking_pipeline")
def test_answer_endpoint_pipeline_error(mock_linking, mock_sparql):
    mock_linking.return_value = LINKING_RESULT
    mock_sparql.return_value = PIPELINE_ERROR
    response = client.post("/api/answer", json={"question": "Who directed Inception?"})
    assert response.status_code in (200, 422, 500)
    data = response.json()
    assert "status" in data or "detail" in data


def test_answer_endpoint_empty_question():
    response = client.post("/api/answer", json={"question": ""})
    assert response.status_code == 422


def test_answer_endpoint_missing_question():
    response = client.post("/api/answer", json={})
    assert response.status_code == 422


@patch("api.routes.sparql.run_sparql_pipeline")
@patch("api.routes.sparql.run_linking_pipeline")
def test_answer_endpoint_exception_returns_500(mock_linking, mock_sparql):
    mock_linking.side_effect = RuntimeError("Linking service down")
    response = client.post("/api/answer", json={"question": "Who directed Inception?"})
    assert response.status_code == 500
