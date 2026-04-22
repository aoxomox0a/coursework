"""Tests for src/kg_profiles/base.py — TDD RED phase."""
import dataclasses

import pytest

from src.kg_profiles import KGProfile, OneShotExample


def _sample_example() -> OneShotExample:
    return OneShotExample(
        question="q",
        entity_uris=("http://example.org/x",),
        property_uri="http://example.org/p",
        sparql="SELECT ?x WHERE { ?x ?p ?o }",
    )


def _sample_profile() -> KGProfile:
    return KGProfile(
        slug="sample",
        label="Sample",
        endpoint_url="http://example.org/sparql",
        prefixes=(("ex", "http://example.org/"),),
        one_shot_examples=(_sample_example(),),
    )


def test_kg_profile_is_frozen():
    profile = _sample_profile()
    with pytest.raises(dataclasses.FrozenInstanceError):
        profile.slug = "mutated"  # type: ignore[misc]


def test_kg_profile_is_hashable():
    assert {_sample_profile()} == {_sample_profile()}


def test_one_shot_example_is_frozen():
    example = _sample_example()
    with pytest.raises(dataclasses.FrozenInstanceError):
        example.question = "mutated"  # type: ignore[misc]


def test_default_link_strategy_is_ner():
    assert _sample_profile().link_strategy == "ner"


def test_default_label_predicate_is_rdfs_label():
    assert _sample_profile().label_predicate == "rdfs:label"


def test_default_query_style_hints_is_empty_tuple():
    assert _sample_profile().query_style_hints == ()


def test_one_shot_example_default_tags_is_empty_frozenset():
    assert _sample_example().tags == frozenset()
