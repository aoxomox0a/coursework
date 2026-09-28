"""Tests for src/sparql/prompt.py — TDD (RED phase)."""
import pytest
from src.sparql.prompt import generate_sparql_prompt, generate_fix_sparql_prompt


def test_generate_sparql_prompt_contains_question(sample_question, sample_entity_uris, sample_property_uri):
    prompt = generate_sparql_prompt(sample_question, sample_entity_uris, sample_property_uri)
    assert sample_question in prompt


def test_generate_sparql_prompt_contains_entity_uris(sample_question, sample_entity_uris, sample_property_uri):
    prompt = generate_sparql_prompt(sample_question, sample_entity_uris, sample_property_uri)
    for uri in sample_entity_uris:
        assert uri in prompt


def test_generate_sparql_prompt_contains_property_uri(sample_question, sample_entity_uris, sample_property_uri):
    prompt = generate_sparql_prompt(sample_question, sample_entity_uris, sample_property_uri)
    assert sample_property_uri in prompt


def test_generate_sparql_prompt_requests_fenced_output(sample_question, sample_entity_uris, sample_property_uri):
    prompt = generate_sparql_prompt(sample_question, sample_entity_uris, sample_property_uri)
    assert "```sparql" in prompt


def test_generate_sparql_prompt_contains_one_shot_example(sample_question, sample_entity_uris, sample_property_uri):
    prompt = generate_sparql_prompt(sample_question, sample_entity_uris, sample_property_uri)
    # Must have a concrete SPARQL example (SELECT and WHERE present in a non-placeholder block)
    assert "SELECT" in prompt
    assert "WHERE" in prompt


def test_generate_sparql_prompt_uri_only_constraint(sample_question, sample_entity_uris, sample_property_uri):
    prompt = generate_sparql_prompt(sample_question, sample_entity_uris, sample_property_uri)
    assert "ONLY" in prompt.upper()


def test_generate_sparql_prompt_handles_empty_related(sample_question, sample_entity_uris, sample_property_uri):
    prompt = generate_sparql_prompt(sample_question, sample_entity_uris, sample_property_uri, related_properties=None)
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_generate_sparql_prompt_includes_related_properties(
    sample_question, sample_entity_uris, sample_property_uri, sample_related_properties
):
    prompt = generate_sparql_prompt(
        sample_question, sample_entity_uris, sample_property_uri, sample_related_properties
    )
    for prop in sample_related_properties:
        assert prop in prompt


def test_generate_fix_sparql_prompt_contains_error(sample_question, invalid_sparql_query):
    error = "Missing WHERE clause"
    prompt = generate_fix_sparql_prompt(sample_question, invalid_sparql_query, error)
    assert error in prompt


def test_generate_fix_sparql_prompt_contains_original_query(sample_question, invalid_sparql_query):
    error = "Unbalanced braces"
    prompt = generate_fix_sparql_prompt(sample_question, invalid_sparql_query, error)
    assert invalid_sparql_query in prompt


def test_generate_fix_sparql_prompt_requests_fenced_output(sample_question, invalid_sparql_query):
    prompt = generate_fix_sparql_prompt(sample_question, invalid_sparql_query, "some error")
    assert "```sparql" in prompt


def test_generate_fix_sparql_prompt_contains_question(sample_question, invalid_sparql_query):
    prompt = generate_fix_sparql_prompt(sample_question, invalid_sparql_query, "some error")
    assert sample_question in prompt
