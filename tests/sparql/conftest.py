"""Shared fixtures for sparql module tests."""
import pytest


@pytest.fixture
def sample_question():
    return "Who directed Inception?"


@pytest.fixture
def sample_entity_uris():
    return [
        "http://dbpedia.org/resource/Inception",
        "http://dbpedia.org/resource/Christopher_Nolan",
    ]


@pytest.fixture
def sample_property_uri():
    return "http://dbpedia.org/ontology/director"


@pytest.fixture
def sample_related_properties():
    return [
        "http://dbpedia.org/ontology/producer",
        "http://dbpedia.org/ontology/writer",
    ]


@pytest.fixture
def valid_sparql_query():
    return """PREFIX dbo: <http://dbpedia.org/ontology/>
SELECT ?director WHERE {
  <http://dbpedia.org/resource/Inception> dbo:director ?director .
}"""


@pytest.fixture
def invalid_sparql_query():
    return "SELECT ?x WHERE { broken syntax {{{"


@pytest.fixture
def fenced_llm_response(valid_sparql_query):
    return f"Here is the query:\n```sparql\n{valid_sparql_query}\n```\nThis query retrieves the director."


@pytest.fixture
def sample_linking_result(sample_entity_uris, sample_property_uri, sample_related_properties):
    return {
        "question": "Who directed Inception?",
        "entities": [
            {"uri": sample_entity_uris[0], "label": "Inception", "confidence": 0.95},
        ],
        "relation": {"uri": sample_property_uri, "label": "director"},
        "relation_candidates": [
            {"uri": p, "label": p.split("/")[-1]} for p in sample_related_properties
        ],
    }


@pytest.fixture
def sparql_json_response():
    return {
        "results": {
            "bindings": [
                {"director": {"type": "uri", "value": "http://dbpedia.org/resource/Christopher_Nolan"}},
            ]
        }
    }
