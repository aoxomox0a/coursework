"""Tests for src/evaluation/metrics/syntax.py — funnel stage 1."""
from src.evaluation.metrics.syntax import SyntaxResult, evaluate_syntax


def test_valid_select_query_returns_valid():
    r = evaluate_syntax("SELECT ?x WHERE { ?x ?p ?o }")
    assert r.valid is True
    assert r.error == ""


def test_invalid_query_returns_error_message():
    r = evaluate_syntax("SELECT ?x WHERE broken {{{")
    assert r.valid is False
    assert r.error  # non-empty error message


def test_empty_query_invalid():
    r = evaluate_syntax("")
    assert r.valid is False


def test_result_is_frozen_dataclass():
    import dataclasses

    r = evaluate_syntax("SELECT ?x WHERE { ?x ?p ?o }")
    with pytest_raises():
        r.valid = False  # type: ignore[misc]


def pytest_raises():
    """Local helper to avoid an extra import; mirrors pytest.raises semantics."""
    import dataclasses
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        try:
            yield
            raise AssertionError("Expected FrozenInstanceError")
        except dataclasses.FrozenInstanceError:
            pass

    return _ctx()
