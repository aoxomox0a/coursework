"""Tests for src/linking/relation_linking.py — runtime endpoint binding."""
import pytest

from src.linking import relation_linking


@pytest.fixture
def captured_calls(monkeypatch):
    calls: list[dict] = []

    def fake_query_candidates(query_text, collection_name, endpoint, top_k):
        calls.append(
            {
                "query_text": query_text,
                "collection_name": collection_name,
                "endpoint": endpoint,
                "top_k": top_k,
            }
        )
        return [
            {"uri": "http://example.org/p", "label": "predicate", "score": 0.8},
        ]

    monkeypatch.setattr(
        "src.linking.relation_linking.query_candidates", fake_query_candidates
    )
    return calls


def test_find_relation_candidates_uses_runtime_endpoint(monkeypatch, captured_calls):
    monkeypatch.setattr(
        "src.linking.relation_linking.get_endpoint",
        lambda: "http://runtime.example/sparql",
    )
    relation_linking.find_relation_candidates("Who directed Inception?")
    assert captured_calls[0]["endpoint"] == "http://runtime.example/sparql"
    assert captured_calls[0]["collection_name"] == "properties"


def test_find_relation_candidates_passes_top_k(monkeypatch, captured_calls):
    monkeypatch.setattr("src.linking.relation_linking.get_endpoint", lambda: "x")
    relation_linking.find_relation_candidates("q", top_k=7)
    assert captured_calls[0]["top_k"] == 7


def test_select_relation_picks_first_candidate():
    cands = [
        {"uri": "http://example.org/director", "label": "director", "score": 0.9},
        {"uri": "http://example.org/writer", "label": "writer", "score": 0.5},
    ]
    assert relation_linking.select_relation(cands)["uri"] == "http://example.org/director"


def test_select_relation_empty_returns_empty_dict():
    assert relation_linking.select_relation([]) == {}
