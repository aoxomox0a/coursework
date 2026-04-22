"""Tests for src/kg_profiles/introspection.py — derive KGProfile from indexed state."""
import pytest

from src.kg_profiles.introspection import (
    WELL_KNOWN_PREFIXES,
    derive_prefixes_from_uris,
    namespace_of,
    profile_from_index,
)


# ---------- namespace_of ---------------------------------------------------


def test_namespace_of_hash_separator():
    assert namespace_of("http://www.w3.org/2000/01/rdf-schema#label") == (
        "http://www.w3.org/2000/01/rdf-schema#"
    )


def test_namespace_of_slash_separator():
    assert namespace_of("http://dbpedia.org/resource/France") == "http://dbpedia.org/resource/"


def test_namespace_of_prefers_hash_over_slash():
    # If both '#' and '/' present, the fragment separator '#' wins.
    assert namespace_of("http://ex.org/ns/foo#bar") == "http://ex.org/ns/foo#"


def test_namespace_of_returns_full_when_no_separator():
    # Edge case: malformed URI with no / or # → return as-is.
    assert namespace_of("urn:lsid:something") == "urn:lsid:something"


# ---------- derive_prefixes_from_uris --------------------------------------


def test_derive_prefixes_uses_well_known_alias():
    uris = ["http://www.w3.org/2000/01/rdf-schema#label"]
    prefixes = derive_prefixes_from_uris(uris)
    # rdfs is a well-known alias for the RDFS namespace
    assert ("rdfs", "http://www.w3.org/2000/01/rdf-schema#") in prefixes


def test_derive_prefixes_generates_numeric_alias_for_unknown():
    uris = [
        "http://unknown-vendor.example/ontology/X",
        "http://unknown-vendor.example/ontology/Y",  # same namespace
    ]
    prefixes = derive_prefixes_from_uris(uris)
    # One prefix emitted for the unknown namespace, aliased ns0
    assert len(prefixes) == 1
    assert prefixes[0][0] == "ns0"
    assert prefixes[0][1] == "http://unknown-vendor.example/ontology/"


def test_derive_prefixes_numeric_aliases_are_stable_by_first_occurrence():
    uris = [
        "http://first.example/a/x",
        "http://second.example/b/y",
    ]
    prefixes = derive_prefixes_from_uris(uris)
    aliases = {p[0] for p in prefixes}
    assert aliases == {"ns0", "ns1"}
    # First-occurrence ordering: ns0 for first.example
    assert dict(prefixes)["ns0"] == "http://first.example/a/"
    assert dict(prefixes)["ns1"] == "http://second.example/b/"


def test_derive_prefixes_deduplicates_namespaces():
    uris = [
        "http://dbpedia.org/ontology/director",
        "http://dbpedia.org/ontology/writer",
        "http://dbpedia.org/ontology/actor",
    ]
    prefixes = derive_prefixes_from_uris(uris)
    # One prefix for dbpedia ontology, regardless of how many URIs share it
    namespaces = [p[1] for p in prefixes]
    assert namespaces.count("http://dbpedia.org/ontology/") == 1


def test_derive_prefixes_mixes_well_known_and_unknown():
    uris = [
        "http://www.w3.org/2000/01/rdf-schema#label",  # rdfs (well-known)
        "http://custom.example/ns/foo",                 # unknown → ns0
    ]
    prefixes = derive_prefixes_from_uris(uris)
    aliases = {p[0] for p in prefixes}
    assert "rdfs" in aliases
    assert "ns0" in aliases


def test_derive_prefixes_empty_input_returns_empty():
    assert derive_prefixes_from_uris([]) == ()


def test_well_known_prefixes_contains_rdfs():
    assert ("rdfs", "http://www.w3.org/2000/01/rdf-schema#") in WELL_KNOWN_PREFIXES.items()


def test_well_known_prefixes_contains_orkg():
    # We seed ORKG namespaces so ORKG profiles auto-use orkgr/orkgp/orkgc aliases
    # rather than opaque ns0/ns1/ns2 when those are the only unknown namespaces.
    assert WELL_KNOWN_PREFIXES.get("orkgp") == "http://orkg.org/orkg/predicate/"


# ---------- profile_from_index --------------------------------------------


def _write_sidecar(tmp_path, monkeypatch, slug, payload):
    """Helper: persist a discovery sidecar JSON for tests."""
    import json

    monkeypatch.setattr("src.indexing.discovery.PROFILES_DIR", tmp_path)
    (tmp_path / f"{slug}.json").write_text(json.dumps(payload))


def test_profile_from_index_uses_sidecar_fields(tmp_path, monkeypatch):
    _write_sidecar(
        tmp_path,
        monkeypatch,
        slug="orkg",
        payload={
            "endpoint_url": "https://orkg.org/triplestore",
            "slug": "orkg",
            "label_predicate": "http://www.w3.org/2000/01/rdf-schema#label",
            "property_typing": "untyped_fallback",
            "class_typing": "rdfs_class",
            "has_language_tags": False,
            "probed_at": "2026-04-22T12:00:00",
        },
    )
    monkeypatch.setattr(
        "src.kg_profiles.introspection._fetch_uris_from_chroma",
        lambda collection, endpoint: [
            "http://orkg.org/orkg/predicate/P31",
            "http://orkg.org/orkg/predicate/P32",
        ],
    )
    profile = profile_from_index("https://orkg.org/triplestore")
    assert profile.slug == "orkg"
    assert profile.label_predicate == "rdfs:label"  # rendered as short form via prefixes
    assert ("orkgp", "http://orkg.org/orkg/predicate/") in profile.prefixes
    assert profile.endpoint_url == "https://orkg.org/triplestore"


def test_profile_from_index_raises_when_sidecar_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("src.indexing.discovery.PROFILES_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        profile_from_index("http://never-indexed.example/sparql")


def test_profile_from_index_carries_link_strategy_default(tmp_path, monkeypatch):
    _write_sidecar(
        tmp_path,
        monkeypatch,
        slug="dbpedia",
        payload={
            "endpoint_url": "http://dbpedia.org/sparql",
            "slug": "dbpedia",
            "label_predicate": "http://www.w3.org/2000/01/rdf-schema#label",
            "property_typing": "rdf_property",
            "class_typing": "rdfs_class",
            "has_language_tags": True,
            "probed_at": "2026-04-22T12:00:00",
        },
    )
    monkeypatch.setattr(
        "src.kg_profiles.introspection._fetch_uris_from_chroma",
        lambda collection, endpoint: [
            "http://dbpedia.org/ontology/director",
        ],
    )
    profile = profile_from_index("http://dbpedia.org/sparql")
    # Default link strategy is "ner" (per KGProfile base); introspection doesn't
    # override it unless caller specifies.
    assert profile.link_strategy == "ner"
