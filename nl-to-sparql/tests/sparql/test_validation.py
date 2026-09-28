"""Tests for src/sparql/validation.py — TDD (RED phase)."""
import pytest
from src.sparql.validation import is_valid_sparql, validate_and_get_error


VALID_SELECT = """
PREFIX dbo: <http://dbpedia.org/ontology/>
SELECT ?director WHERE {
  <http://dbpedia.org/resource/Inception> dbo:director ?director .
}
"""

VALID_ASK = """
ASK WHERE {
  <http://dbpedia.org/resource/Inception> a <http://dbpedia.org/ontology/Film> .
}
"""

INVALID_SYNTAX = "SELECT ?x WHERE {{ broken"

EMPTY_QUERY = ""


def test_valid_select_query():
    valid, error = is_valid_sparql(VALID_SELECT)
    assert valid is True
    assert error == ""


def test_valid_ask_query():
    valid, error = is_valid_sparql(VALID_ASK)
    assert valid is True
    assert error == ""


def test_invalid_syntax_returns_false():
    valid, error = is_valid_sparql(INVALID_SYNTAX)
    assert valid is False
    assert len(error) > 0


def test_empty_query_returns_false():
    valid, error = is_valid_sparql(EMPTY_QUERY)
    assert valid is False
    assert len(error) > 0


def test_validate_and_get_error_valid():
    error = validate_and_get_error(VALID_SELECT)
    assert error == ""


def test_validate_and_get_error_invalid():
    error = validate_and_get_error(INVALID_SYNTAX)
    assert len(error) > 0


def test_is_valid_sparql_returns_tuple():
    result = is_valid_sparql(VALID_SELECT)
    assert isinstance(result, tuple)
    assert len(result) == 2
