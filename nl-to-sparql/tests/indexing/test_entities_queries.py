"""Tests that entities.py emits the right SPARQL for each param combination.

We intercept `src.indexing.endpoint.query_sparql` / `query_sparql_custom` so the
tests don't touch a real endpoint; we only assert the query STRING we emit.
"""
from unittest.mock import AsyncMock

import pytest

from src.indexing import entities


@pytest.fixture
def captured_queries(monkeypatch):
    """Patch query_sparql to capture the SPARQL string and return an empty result."""
    captured: list[str] = []

    async def fake(query: str, format: str = "json") -> dict:
        captured.append(query)
        return {"results": {"bindings": []}}

    monkeypatch.setattr("src.indexing.endpoint.query_sparql", fake)
    # entities.py imports query_sparql at the top — patch the already-imported reference too
    monkeypatch.setattr("src.indexing.entities.query_sparql", fake)
    return captured


@pytest.mark.asyncio
async def test_fetch_entities_default_keeps_legacy_behavior(captured_queries):
    await entities.fetch_entities(limit=10)
    q = captured_queries[-1]
    assert "rdfs:label" in q or "rdf-schema#label" in q
    assert "lang(?label) = 'en'" in q


@pytest.mark.asyncio
async def test_fetch_entities_custom_label_predicate(captured_queries):
    await entities.fetch_entities(
        limit=10,
        label_predicate="http://www.w3.org/2004/02/skos/core#prefLabel",
    )
    q = captured_queries[-1]
    assert "skos/core#prefLabel" in q


@pytest.mark.asyncio
async def test_fetch_entities_drops_lang_filter_when_required_false(captured_queries):
    await entities.fetch_entities(limit=10, require_lang_en=False)
    q = captured_queries[-1]
    assert "lang(" not in q.lower()


@pytest.mark.asyncio
async def test_fetch_properties_default_uses_rdf_property_typing(captured_queries):
    await entities.fetch_properties(limit=5)
    q = captured_queries[-1]
    assert "rdf:Property" in q or "22-rdf-syntax-ns#Property" in q


@pytest.mark.asyncio
async def test_fetch_properties_untyped_fallback_uses_spo_scan(captured_queries):
    await entities.fetch_properties(limit=5, property_type_uri=None)
    q = captured_queries[-1]
    # Untyped fallback: scan subject-predicate-object patterns rather than rdf:Property
    assert "rdf:Property" not in q
    assert "22-rdf-syntax-ns#Property" not in q
    assert "?s ?property ?o" in q or "?property ?o" in q


@pytest.mark.asyncio
async def test_fetch_properties_owl_object_property_typing(captured_queries):
    await entities.fetch_properties(
        limit=5,
        property_type_uri="http://www.w3.org/2002/07/owl#ObjectProperty",
    )
    q = captured_queries[-1]
    assert "owl#ObjectProperty" in q


@pytest.mark.asyncio
async def test_fetch_classes_default_uses_rdfs_class(captured_queries):
    await entities.fetch_classes(limit=5)
    q = captured_queries[-1]
    assert "rdfs:Class" in q or "rdf-schema#Class" in q


@pytest.mark.asyncio
async def test_fetch_classes_owl_class_typing(captured_queries):
    await entities.fetch_classes(
        limit=5,
        class_type_uri="http://www.w3.org/2002/07/owl#Class",
    )
    q = captured_queries[-1]
    assert "owl#Class" in q


@pytest.mark.asyncio
async def test_fetch_classes_untyped_fallback(captured_queries):
    await entities.fetch_classes(limit=5, class_type_uri=None)
    q = captured_queries[-1]
    assert "rdfs:Class" not in q
    assert "owl#Class" not in q
    # Untyped fallback pulls the class from ?s a ?class patterns
    assert "a ?class" in q or "rdf:type ?class" in q
