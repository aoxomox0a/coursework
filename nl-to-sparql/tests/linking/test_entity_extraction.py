"""Tests for pure helpers in src/linking/entity_extraction.py."""
from dataclasses import dataclass

from src.linking.entity_extraction import (
    combine_candidates,
    extract_noun_chunks,
)


# ---------- combine_candidates ---------------------------------------------


def test_combine_candidates_dedups_across_sources():
    entities = [("Paris", "GPE"), ("BERT", "ORG")]
    noun_phrases = ["BERT", "capital"]
    noun_chunks = ["Paris", "the capital"]
    out = combine_candidates(entities, noun_phrases, noun_chunks)
    # Paris and BERT appear once despite being in multiple sources
    assert out.count("Paris") == 1
    assert out.count("BERT") == 1


def test_combine_candidates_preserves_first_occurrence_order():
    entities = [("a", "x")]
    noun_phrases = ["b", "a"]  # 'a' already seen
    noun_chunks = ["c"]
    assert combine_candidates(entities, noun_phrases, noun_chunks) == ["a", "b", "c"]


def test_combine_candidates_handles_all_empty():
    assert combine_candidates([], [], []) == []


def test_combine_candidates_without_chunks_argument():
    # noun_chunks is optional; callers may omit it.
    assert combine_candidates([("x", "ORG")], ["y"]) == ["x", "y"]


def test_combine_candidates_with_none_chunks():
    assert combine_candidates([("x", "ORG")], ["y"], None) == ["x", "y"]


# ---------- extract_noun_chunks --------------------------------------------


@dataclass
class _FakeChunk:
    text: str


@dataclass
class _FakeDoc:
    noun_chunks: list


def test_extract_noun_chunks_returns_text_spans():
    doc = _FakeDoc(noun_chunks=[_FakeChunk("the GAD dataset"), _FakeChunk("a list")])
    assert extract_noun_chunks(doc) == ["the GAD dataset", "a list"]


def test_extract_noun_chunks_empty_doc():
    doc = _FakeDoc(noun_chunks=[])
    assert extract_noun_chunks(doc) == []
