"""Tests for src/evaluation/metrics/execution_match.py — funnel stage 3.

Relaxed Execution Match: set equality of binding rows ignoring variable names
and row ordering. Trade-off documented in the module: each row becomes the
unordered set of (type, value) cells — intra-row variable-name structure is
discarded so that gold and generated queries with different ?varNames still
compare equal when they bind the same values.
"""
from src.evaluation.metrics.execution_match import (
    ExecutionMatchResult,
    evaluate_execution_match,
)


def _row(*pairs: tuple[str, str, str]) -> dict:
    """Helper: build a binding row from (var, type, value) triples."""
    return {var: {"type": typ, "value": val} for var, typ, val in pairs}


# ---------- exact match ---------------------------------------------------


def test_identical_bindings_same_var_names_match():
    g = [_row(("x", "uri", "http://a"))]
    r = evaluate_execution_match(g, g)
    assert r.match is True
    assert r.score == 1.0
    assert r.gold_count == r.generated_count == 1


def test_identical_bindings_different_var_names_still_match():
    gold = [_row(("director", "uri", "http://nolan"))]
    gen = [_row(("d", "uri", "http://nolan"))]
    r = evaluate_execution_match(gold, gen)
    assert r.match is True
    assert r.score == 1.0


def test_row_order_does_not_matter():
    gold = [_row(("x", "uri", "http://a")), _row(("x", "uri", "http://b"))]
    gen = [_row(("x", "uri", "http://b")), _row(("x", "uri", "http://a"))]
    r = evaluate_execution_match(gold, gen)
    assert r.match is True


# ---------- partial / no match --------------------------------------------


def test_partial_overlap_gives_jaccard_score():
    gold = [_row(("x", "uri", "http://a")), _row(("x", "uri", "http://b"))]
    gen = [_row(("x", "uri", "http://b")), _row(("x", "uri", "http://c"))]
    r = evaluate_execution_match(gold, gen)
    # |intersection|=1, |union|=3 → Jaccard = 1/3
    assert r.match is False
    assert abs(r.score - 1 / 3) < 1e-9
    assert r.intersection == 1


def test_disjoint_bindings_score_zero():
    gold = [_row(("x", "uri", "http://a"))]
    gen = [_row(("x", "uri", "http://z"))]
    r = evaluate_execution_match(gold, gen)
    assert r.match is False
    assert r.score == 0.0


def test_gold_nonempty_generated_empty_no_match():
    gold = [_row(("x", "uri", "http://a"))]
    r = evaluate_execution_match(gold, [])
    assert r.match is False
    assert r.score == 0.0
    assert r.gold_count == 1
    assert r.generated_count == 0


# ---------- empty edge cases ----------------------------------------------


def test_both_empty_match_with_warning():
    r = evaluate_execution_match([], [])
    assert r.match is True
    assert r.score == 1.0  # vacuously equal
    # Empty-gold is the prime false-positive case — must be flagged.
    assert "empty" in r.false_positive_warning.lower() or "trivial" in r.false_positive_warning.lower()


def test_empty_gold_warning_even_when_generated_also_empty():
    r = evaluate_execution_match([], [])
    assert r.false_positive_warning != ""


# ---------- false-positive warnings ---------------------------------------


def test_single_row_match_warns_high_coincidence():
    gold = [_row(("x", "uri", "http://a"))]
    gen = [_row(("x", "uri", "http://a"))]
    r = evaluate_execution_match(gold, gen)
    assert r.match is True
    # Single-row matches are also flagged because a broader query may
    # accidentally narrow to the same single row.
    assert r.false_positive_warning != ""


def test_multi_row_match_no_warning():
    gold = [
        _row(("x", "uri", "http://a")),
        _row(("x", "uri", "http://b")),
        _row(("x", "uri", "http://c")),
    ]
    r = evaluate_execution_match(gold, gold)
    assert r.match is True
    # 3+ rows match = strong signal, no false-positive warning needed.
    assert r.false_positive_warning == ""


# ---------- multi-cell rows ----------------------------------------------


def test_multi_cell_rows_compared_as_value_sets():
    gold = [_row(("model", "uri", "http://m"), ("score", "literal", "0.9"))]
    gen = [_row(("m", "uri", "http://m"), ("s", "literal", "0.9"))]
    r = evaluate_execution_match(gold, gen)
    assert r.match is True


def test_different_values_in_same_row_no_match():
    gold = [_row(("model", "uri", "http://m"), ("score", "literal", "0.9"))]
    gen = [_row(("model", "uri", "http://m"), ("score", "literal", "0.8"))]
    r = evaluate_execution_match(gold, gen)
    assert r.match is False


# ---------- result invariants --------------------------------------------


def test_result_is_frozen():
    import dataclasses

    r = ExecutionMatchResult(
        match=True, score=1.0, gold_count=0, generated_count=0,
        intersection=0, false_positive_warning="",
    )
    with __import__("pytest").raises(dataclasses.FrozenInstanceError):
        r.match = False  # type: ignore[misc]
