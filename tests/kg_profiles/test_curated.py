"""Tests for src/kg_profiles/curated.py — JSON loader for hand-authored one-shots."""
import json

import pytest

from src.kg_profiles import OneShotExample
from src.kg_profiles.curated import (
    CURATED_DIR,
    curated_path_for,
    load_curated_one_shots,
)


def _write_curated(tmp_path, monkeypatch, slug: str, items: list):
    monkeypatch.setattr("src.kg_profiles.curated.CURATED_DIR", tmp_path)
    (tmp_path / f"{slug}.json").write_text(json.dumps(items))


def test_load_returns_empty_when_file_absent(tmp_path, monkeypatch):
    monkeypatch.setattr("src.kg_profiles.curated.CURATED_DIR", tmp_path)
    assert load_curated_one_shots("never-existed") == ()


def test_load_returns_one_shot_examples(tmp_path, monkeypatch):
    _write_curated(
        tmp_path,
        monkeypatch,
        "dbpedia",
        [
            {
                "question": "What is the capital of France?",
                "entity_uris": ["http://dbpedia.org/resource/France"],
                "property_uri": "http://dbpedia.org/ontology/capital",
                "sparql": "SELECT ?capital WHERE { <http://dbpedia.org/resource/France> <http://dbpedia.org/ontology/capital> ?capital }",
                "tags": ["factoid"],
            },
        ],
    )
    examples = load_curated_one_shots("dbpedia")
    assert len(examples) == 1
    ex = examples[0]
    assert isinstance(ex, OneShotExample)
    assert ex.question == "What is the capital of France?"
    assert ex.entity_uris == ("http://dbpedia.org/resource/France",)
    assert ex.property_uri == "http://dbpedia.org/ontology/capital"
    assert "SELECT" in ex.sparql
    assert ex.tags == frozenset({"factoid"})


def test_load_handles_missing_optional_fields(tmp_path, monkeypatch):
    # property_uri and tags are optional; entity_uris can be empty
    _write_curated(
        tmp_path,
        monkeypatch,
        "minimal",
        [
            {
                "question": "q",
                "entity_uris": [],
                "sparql": "ASK { ?s ?p ?o }",
            },
        ],
    )
    examples = load_curated_one_shots("minimal")
    assert examples[0].property_uri is None
    assert examples[0].tags == frozenset()
    assert examples[0].entity_uris == ()


def test_load_multiple_examples_preserves_order(tmp_path, monkeypatch):
    _write_curated(
        tmp_path,
        monkeypatch,
        "multi",
        [
            {"question": "a", "entity_uris": [], "sparql": "ASK {}"},
            {"question": "b", "entity_uris": [], "sparql": "ASK {}"},
            {"question": "c", "entity_uris": [], "sparql": "ASK {}"},
        ],
    )
    examples = load_curated_one_shots("multi")
    assert [e.question for e in examples] == ["a", "b", "c"]


def test_load_raises_on_malformed_json(tmp_path, monkeypatch):
    monkeypatch.setattr("src.kg_profiles.curated.CURATED_DIR", tmp_path)
    (tmp_path / "broken.json").write_text("not json {{{")
    with pytest.raises(ValueError):
        load_curated_one_shots("broken")


def test_load_requires_list_at_root(tmp_path, monkeypatch):
    monkeypatch.setattr("src.kg_profiles.curated.CURATED_DIR", tmp_path)
    (tmp_path / "wrongshape.json").write_text('{"not": "a list"}')
    with pytest.raises(ValueError):
        load_curated_one_shots("wrongshape")


def test_curated_path_for_uses_slug(tmp_path, monkeypatch):
    monkeypatch.setattr("src.kg_profiles.curated.CURATED_DIR", tmp_path)
    assert curated_path_for("orkg") == tmp_path / "orkg.json"


def test_curated_dir_default_is_under_config():
    # Sanity: the shipped curated files live under config/ (not gitignored data/)
    assert "config" in str(CURATED_DIR)
