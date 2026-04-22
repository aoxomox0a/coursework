"""Tests for src/indexing/discovery.py — probe logic, serialization, and sidecar persistence."""
import json
from pathlib import Path

import pytest

from src.indexing.discovery import (
    DiscoveredProfile,
    LABEL_PREDICATES,
    CLASS_TYPINGS,
    PROPERTY_TYPINGS,
    load_profile,
    probe_class_typing,
    probe_has_language_tags,
    probe_label_predicate,
    probe_property_typing,
    profile_path_for,
    save_profile,
)


# ---------- Query mocks ---------------------------------------------------


def _mock_query(counts: dict[str, int]):
    """
    Build a mock query_fn that returns a COUNT response based on a (substring -> count) map.
    The key is a substring expected to appear in the query; first match wins.
    """

    async def fake_query(query: str, endpoint: str | None = None) -> dict:
        for needle, count in counts.items():
            if needle in query:
                return {"results": {"bindings": [{"n": {"value": str(count)}}]}}
        return {"results": {"bindings": [{"n": {"value": "0"}}]}}

    return fake_query


def _mock_ask(truthy_substrings: set[str]):
    """Mock query_fn for ASK queries: returns boolean=True iff query contains a truthy needle."""

    async def fake_query(query: str, endpoint: str | None = None) -> dict:
        for needle in truthy_substrings:
            if needle in query:
                return {"boolean": True}
        return {"boolean": False}

    return fake_query


# ---------- probe_label_predicate -----------------------------------------


@pytest.mark.asyncio
async def test_probe_label_predicate_picks_highest_count():
    query_fn = _mock_query(
        {
            "rdf-schema#label": 100,
            "skos/core#prefLabel": 50,
            "foaf/0.1/name": 10,
        }
    )
    winner = await probe_label_predicate("http://x/sparql", query_fn=query_fn)
    assert winner == "http://www.w3.org/2000/01/rdf-schema#label"


@pytest.mark.asyncio
async def test_probe_label_predicate_picks_second_when_first_zero():
    query_fn = _mock_query(
        {
            "rdf-schema#label": 0,
            "skos/core#prefLabel": 42,
        }
    )
    winner = await probe_label_predicate("http://x/sparql", query_fn=query_fn)
    assert winner == "http://www.w3.org/2004/02/skos/core#prefLabel"


@pytest.mark.asyncio
async def test_probe_label_predicate_falls_back_to_rdfs_label_when_all_zero():
    query_fn = _mock_query({})  # no key matches → all zero
    winner = await probe_label_predicate("http://x/sparql", query_fn=query_fn)
    assert winner == "http://www.w3.org/2000/01/rdf-schema#label"


@pytest.mark.asyncio
async def test_probe_label_predicate_handles_query_errors_gracefully():
    async def erroring_query(query: str, endpoint: str | None = None) -> dict:
        raise ConnectionError("boom")

    winner = await probe_label_predicate("http://x/sparql", query_fn=erroring_query)
    assert winner == "http://www.w3.org/2000/01/rdf-schema#label"


# ---------- probe_property_typing -----------------------------------------


@pytest.mark.asyncio
async def test_probe_property_typing_picks_rdf_property_when_present():
    query_fn = _mock_ask({"rdf-syntax-ns#Property"})
    typing = await probe_property_typing("http://x/sparql", query_fn=query_fn)
    assert typing == "rdf_property"


@pytest.mark.asyncio
async def test_probe_property_typing_falls_through_to_untyped_when_none_tagged():
    query_fn = _mock_ask(set())  # ASK always false
    typing = await probe_property_typing("http://x/sparql", query_fn=query_fn)
    assert typing == "untyped_fallback"


@pytest.mark.asyncio
async def test_probe_property_typing_prefers_rdf_property_over_owl():
    query_fn = _mock_ask({"rdf-syntax-ns#Property", "owl#ObjectProperty"})
    typing = await probe_property_typing("http://x/sparql", query_fn=query_fn)
    assert typing == "rdf_property"


# ---------- probe_class_typing --------------------------------------------


@pytest.mark.asyncio
async def test_probe_class_typing_rdfs_class():
    query_fn = _mock_ask({"rdf-schema#Class"})
    typing = await probe_class_typing("http://x/sparql", query_fn=query_fn)
    assert typing == "rdfs_class"


@pytest.mark.asyncio
async def test_probe_class_typing_owl_class_fallback():
    query_fn = _mock_ask({"owl#Class"})
    typing = await probe_class_typing("http://x/sparql", query_fn=query_fn)
    assert typing == "owl_class"


@pytest.mark.asyncio
async def test_probe_class_typing_falls_through_to_untyped():
    query_fn = _mock_ask(set())
    typing = await probe_class_typing("http://x/sparql", query_fn=query_fn)
    assert typing == "untyped_fallback"


# ---------- probe_has_language_tags ---------------------------------------


@pytest.mark.asyncio
async def test_probe_language_tags_true_when_en_found():
    query_fn = _mock_ask({'lang(?l) = "en"'})
    assert await probe_has_language_tags(
        "http://x/sparql",
        "http://www.w3.org/2000/01/rdf-schema#label",
        query_fn=query_fn,
    ) is True


@pytest.mark.asyncio
async def test_probe_language_tags_false_when_untagged():
    query_fn = _mock_ask(set())
    assert await probe_has_language_tags(
        "http://x/sparql",
        "http://www.w3.org/2000/01/rdf-schema#label",
        query_fn=query_fn,
    ) is False


# ---------- DiscoveredProfile dataclass ------------------------------------


def test_discovered_profile_is_frozen():
    p = DiscoveredProfile(
        endpoint_url="http://x/sparql",
        slug="x",
        label_predicate="http://www.w3.org/2000/01/rdf-schema#label",
        property_typing="rdf_property",
        class_typing="rdfs_class",
        has_language_tags=True,
        probed_at="2026-04-22T12:00:00",
    )
    import dataclasses

    with pytest.raises(dataclasses.FrozenInstanceError):
        p.slug = "mutated"  # type: ignore[misc]


# ---------- save / load / path ---------------------------------------------


def test_profile_path_for_uses_slug(tmp_path, monkeypatch):
    monkeypatch.setattr("src.indexing.discovery.PROFILES_DIR", tmp_path)
    # get_endpoint_slug maps dbpedia.org → "dbpedia"
    path = profile_path_for("http://dbpedia.org/sparql")
    assert path == tmp_path / "dbpedia.json"


def test_save_and_load_profile_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr("src.indexing.discovery.PROFILES_DIR", tmp_path)
    original = DiscoveredProfile(
        endpoint_url="https://orkg.org/triplestore",
        slug="orkg",
        label_predicate="http://www.w3.org/2000/01/rdf-schema#label",
        property_typing="untyped_fallback",
        class_typing="rdfs_class",
        has_language_tags=False,
        probed_at="2026-04-22T12:00:00",
    )
    save_profile(original)

    loaded = load_profile("https://orkg.org/triplestore")
    assert loaded == original


def test_load_profile_returns_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("src.indexing.discovery.PROFILES_DIR", tmp_path)
    assert load_profile("http://never-indexed.example/sparql") is None


def test_save_profile_writes_valid_json(tmp_path, monkeypatch):
    monkeypatch.setattr("src.indexing.discovery.PROFILES_DIR", tmp_path)
    profile = DiscoveredProfile(
        endpoint_url="http://x/sparql",
        slug="x",
        label_predicate="http://www.w3.org/2000/01/rdf-schema#label",
        property_typing="rdf_property",
        class_typing="rdfs_class",
        has_language_tags=True,
        probed_at="2026-04-22T12:00:00",
    )
    save_profile(profile)
    raw = json.loads((tmp_path / "x.json").read_text())
    assert raw["endpoint_url"] == "http://x/sparql"
    assert raw["label_predicate"] == "http://www.w3.org/2000/01/rdf-schema#label"


# ---------- Constants sanity -----------------------------------------------


def test_label_predicates_ranked_list_non_empty():
    assert len(LABEL_PREDICATES) >= 3
    assert LABEL_PREDICATES[0] == "http://www.w3.org/2000/01/rdf-schema#label"


def test_property_typings_has_untyped_fallback_last():
    assert PROPERTY_TYPINGS[-1] == "untyped_fallback"


def test_class_typings_has_untyped_fallback_last():
    assert CLASS_TYPINGS[-1] == "untyped_fallback"
