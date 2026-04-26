"""Tests for src/linking/entity_linking.py — runtime endpoint binding + orchestration."""
import pytest

from src.linking import entity_linking


@pytest.fixture
def captured_endpoint(monkeypatch):
    """Capture the endpoint argument passed to query_candidates."""
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
        return []

    monkeypatch.setattr(
        "src.linking.entity_linking.query_candidates", fake_query_candidates
    )
    return calls


def test_link_entities_uses_runtime_endpoint(monkeypatch, captured_endpoint):
    """link_entities must resolve the endpoint at CALL time via get_endpoint(),
    not at module-import time — so endpoint.set_endpoint() actually takes effect.
    """
    monkeypatch.setattr(
        "src.linking.entity_linking.get_endpoint",
        lambda: "http://runtime.example/sparql",
    )
    entity_linking.link_entities(["Paris"])
    assert captured_endpoint[0]["endpoint"] == "http://runtime.example/sparql"


def test_link_entities_picks_up_endpoint_change_between_calls(
    monkeypatch, captured_endpoint
):
    holder = {"value": "http://first.example/sparql"}
    monkeypatch.setattr(
        "src.linking.entity_linking.get_endpoint",
        lambda: holder["value"],
    )
    entity_linking.link_entities(["a"])
    holder["value"] = "http://second.example/sparql"
    entity_linking.link_entities(["b"])
    assert captured_endpoint[0]["endpoint"] == "http://first.example/sparql"
    assert captured_endpoint[1]["endpoint"] == "http://second.example/sparql"


def test_link_entities_empty_input_returns_empty(monkeypatch, captured_endpoint):
    monkeypatch.setattr("src.linking.entity_linking.get_endpoint", lambda: "x")
    assert entity_linking.link_entities([]) == []
    assert captured_endpoint == []


def test_disambiguate_picks_highest_scored_candidate():
    linking_results = [
        {
            "entity": "Paris",
            "candidates": [
                {"uri": "http://dbpedia.org/resource/Paris", "label": "Paris", "score": 0.99},
                {"uri": "http://dbpedia.org/resource/Paris_Hilton", "label": "Paris Hilton", "score": 0.40},
            ],
        }
    ]
    out = entity_linking.disambiguate_entities(linking_results)
    assert out == [
        {
            "entity": "Paris",
            "uri": "http://dbpedia.org/resource/Paris",
            "confidence": 0.99,
        }
    ]


def test_disambiguate_skips_entity_without_candidates():
    linking_results = [{"entity": "Unknown", "candidates": []}]
    assert entity_linking.disambiguate_entities(linking_results) == []
