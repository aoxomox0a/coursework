"""Tests for src/evaluation/metrics/algebra.py — funnel stage 4 (corroborative).

The test matrix is split into "must match" pairs and "must NOT match" pairs to
catch silent canonicalisation regressions in both directions. Property paths
and aggregates are handled by the rdflib parser; we only assert that the
metric doesn't crash on them, since deep canonicalisation of those is out
of scope (planner Section 4 rated them medium/low confidence).
"""
import pytest

from src.evaluation.metrics.algebra import AlgebraMatchStatus, evaluate_algebra_match


# ---------- MUST MATCH ----------------------------------------------------


def test_identical_queries_match():
    q = "SELECT ?x WHERE { ?x <http://p> <http://o> }"
    r = evaluate_algebra_match(q, q)
    assert r.match is True
    assert r.status == AlgebraMatchStatus.COMPARED


def test_alpha_equivalent_queries_match():
    # Same structure, renamed variables.
    gold = "SELECT ?director WHERE { <http://film> <http://director> ?director }"
    gen = "SELECT ?d WHERE { <http://film> <http://director> ?d }"
    r = evaluate_algebra_match(gold, gen)
    assert r.match is True


def test_bgp_triple_reorder_matches():
    # Triple order inside a BGP shouldn't matter.
    gold = """SELECT ?d WHERE {
        ?film <http://director> ?d .
        ?film <http://name> "Inception" .
    }"""
    gen = """SELECT ?d WHERE {
        ?film <http://name> "Inception" .
        ?film <http://director> ?d .
    }"""
    r = evaluate_algebra_match(gold, gen)
    assert r.match is True


def test_alpha_plus_bgp_reorder_matches():
    gold = """SELECT ?director WHERE {
        ?film <http://director> ?director .
        ?film <http://name> "Inception" .
    }"""
    gen = """SELECT ?d WHERE {
        ?f <http://name> "Inception" .
        ?f <http://director> ?d .
    }"""
    r = evaluate_algebra_match(gold, gen)
    assert r.match is True


# ---------- MUST NOT MATCH -----------------------------------------------


def test_different_predicate_no_match():
    gold = "SELECT ?x WHERE { <http://s> <http://p1> ?x }"
    gen = "SELECT ?x WHERE { <http://s> <http://p2> ?x }"
    r = evaluate_algebra_match(gold, gen)
    assert r.match is False
    assert r.status == AlgebraMatchStatus.COMPARED


def test_added_filter_no_match():
    gold = "SELECT ?x WHERE { ?x <http://p> ?o }"
    gen = "SELECT ?x WHERE { ?x <http://p> ?o . FILTER(?x != <http://blocked>) }"
    r = evaluate_algebra_match(gold, gen)
    assert r.match is False


def test_added_extra_triple_no_match():
    gold = "SELECT ?x WHERE { ?x <http://p1> ?o }"
    gen = "SELECT ?x WHERE { ?x <http://p1> ?o . ?x <http://p2> ?other }"
    r = evaluate_algebra_match(gold, gen)
    assert r.match is False


def test_different_query_form_no_match():
    # SELECT vs ASK
    gold = "SELECT ?x WHERE { ?x <http://p> ?o }"
    gen = "ASK { ?x <http://p> ?o }"
    r = evaluate_algebra_match(gold, gen)
    assert r.match is False


def test_different_subject_no_match():
    gold = "SELECT ?x WHERE { <http://s1> <http://p> ?x }"
    gen = "SELECT ?x WHERE { <http://s2> <http://p> ?x }"
    r = evaluate_algebra_match(gold, gen)
    assert r.match is False


# ---------- PARSE ERRORS / GRACEFUL DEGRADATION --------------------------


def test_invalid_gold_returns_error_status():
    r = evaluate_algebra_match("SELECT ?x WHERE { broken {{{", "SELECT ?x WHERE { ?x ?p ?o }")
    assert r.match is False
    assert r.status == AlgebraMatchStatus.GOLD_PARSE_ERROR
    assert r.error  # error message present


def test_invalid_generated_returns_error_status():
    r = evaluate_algebra_match("SELECT ?x WHERE { ?x ?p ?o }", "SELECT ?x WHERE { broken {{{")
    assert r.match is False
    assert r.status == AlgebraMatchStatus.GENERATED_PARSE_ERROR


def test_both_invalid_returns_gold_error_first():
    r = evaluate_algebra_match("SELECT ?x WHERE { broken", "SELECT ?x WHERE { also broken")
    assert r.match is False
    # Gold error takes precedence so the reporter can deprioritise tests with bad gold.
    assert r.status == AlgebraMatchStatus.GOLD_PARSE_ERROR


# ---------- HARD FEATURES handled without crashing -----------------------


def test_property_paths_do_not_crash():
    # rdflib's translateQuery handles property paths; we just verify our
    # canonicaliser doesn't raise on the resulting algebra nodes.
    gold = "SELECT ?x WHERE { <http://s> <http://p1>/<http://p2> ?x }"
    gen = "SELECT ?y WHERE { <http://s> <http://p1>/<http://p2> ?y }"
    r = evaluate_algebra_match(gold, gen)
    # Match or no match — either is acceptable; what matters is no exception.
    assert r.status in {AlgebraMatchStatus.COMPARED, AlgebraMatchStatus.PARSE_LIMITATION}


def test_aggregates_do_not_crash():
    gold = "SELECT (COUNT(?x) AS ?n) WHERE { ?x <http://p> ?o }"
    gen = "SELECT (COUNT(?y) AS ?n) WHERE { ?y <http://p> ?o }"
    r = evaluate_algebra_match(gold, gen)
    assert r.status in {AlgebraMatchStatus.COMPARED, AlgebraMatchStatus.PARSE_LIMITATION}


def test_optional_block_handled():
    gold = "SELECT ?x WHERE { ?x <http://p> ?o . OPTIONAL { ?x <http://q> ?o2 } }"
    gen = "SELECT ?y WHERE { ?y <http://p> ?o . OPTIONAL { ?y <http://q> ?o2 } }"
    r = evaluate_algebra_match(gold, gen)
    assert r.status == AlgebraMatchStatus.COMPARED


# ---------- result invariants --------------------------------------------


def test_result_is_frozen():
    import dataclasses

    r = evaluate_algebra_match("SELECT ?x WHERE { ?x ?p ?o }", "SELECT ?x WHERE { ?x ?p ?o }")
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.match = False  # type: ignore[misc]
