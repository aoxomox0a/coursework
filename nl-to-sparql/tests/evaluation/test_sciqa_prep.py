"""Tests for src/evaluation/sciqa_prep.py — pure logic only (HTTP loop tested via integration)."""
import pytest

from src.evaluation.sciqa_prep import (
    PREFIX_BLOCK,
    convert_to_gold_item,
    extract_question_text,
    extract_sparql_text,
    extract_uris_from_bindings,
    format_bindings_as_answer,
    has_entity_answer,
    stratified_sample,
)


# ---------- extract_question_text -----------------------------------------


def test_extract_question_text_from_dict():
    assert extract_question_text({"string": "Who directed Inception?"}) == "Who directed Inception?"


def test_extract_question_text_from_plain_string():
    assert extract_question_text("Who directed Inception?") == "Who directed Inception?"


def test_extract_question_text_handles_missing_string_key():
    assert extract_question_text({}) == ""


# ---------- extract_sparql_text -------------------------------------------


def test_extract_sparql_from_dict():
    assert extract_sparql_text({"sparql": "SELECT ?x WHERE { ?x ?p ?o }"}) == "SELECT ?x WHERE { ?x ?p ?o }"


def test_extract_sparql_from_plain_string():
    assert extract_sparql_text("ASK { ?s ?p ?o }") == "ASK { ?s ?p ?o }"


def test_extract_sparql_handles_missing_key():
    assert extract_sparql_text({}) == ""


# ---------- extract_uris_from_bindings ------------------------------------


def test_extract_uris_from_bindings_keeps_uris_drops_literals():
    bindings = [
        {
            "model": {"type": "uri", "value": "http://orkg.org/r1"},
            "name": {"type": "literal", "value": "BERT"},
        },
        {
            "model": {"type": "uri", "value": "http://orkg.org/r2"},
            "name": {"type": "literal", "value": "GPT-3"},
        },
    ]
    uris = extract_uris_from_bindings(bindings)
    assert set(uris) == {"http://orkg.org/r1", "http://orkg.org/r2"}


def test_extract_uris_dedups_across_rows_and_columns():
    bindings = [
        {"a": {"type": "uri", "value": "http://x"}, "b": {"type": "uri", "value": "http://y"}},
        {"a": {"type": "uri", "value": "http://x"}, "b": {"type": "uri", "value": "http://z"}},
    ]
    assert sorted(extract_uris_from_bindings(bindings)) == ["http://x", "http://y", "http://z"]


def test_extract_uris_empty_bindings_returns_empty():
    assert extract_uris_from_bindings([]) == []


def test_extract_uris_skips_bnode_type():
    bindings = [{"x": {"type": "bnode", "value": "_:b1"}}]
    assert extract_uris_from_bindings(bindings) == []


# ---------- has_entity_answer ---------------------------------------------


def test_has_entity_answer_true_when_uris_present():
    bindings = [{"x": {"type": "uri", "value": "http://x"}}]
    assert has_entity_answer(bindings) is True


def test_has_entity_answer_false_when_only_literals():
    bindings = [{"count": {"type": "literal", "value": "42"}}]
    assert has_entity_answer(bindings) is False


def test_has_entity_answer_false_when_empty():
    assert has_entity_answer([]) is False


# ---------- format_bindings_as_answer -------------------------------------


def test_format_bindings_renders_one_row_per_binding():
    bindings = [
        {"model": {"type": "uri", "value": "http://orkg.org/r1"}, "label": {"type": "literal", "value": "BERT"}},
        {"model": {"type": "uri", "value": "http://orkg.org/r2"}, "label": {"type": "literal", "value": "GPT-3"}},
    ]
    out = format_bindings_as_answer(bindings)
    assert "BERT" in out
    assert "GPT-3" in out
    assert "http://orkg.org/r1" in out


def test_format_bindings_empty_returns_no_results_marker():
    assert "no results" in format_bindings_as_answer([]).lower()


# ---------- stratified_sample ---------------------------------------------


def _items(shapes_and_count: dict[str, int]) -> list[dict]:
    items = []
    counter = 0
    for shape, n in shapes_and_count.items():
        for _ in range(n):
            items.append({"id": f"q{counter}", "query_shape": shape})
            counter += 1
    return items


def test_stratified_sample_returns_n_when_pool_is_large_enough():
    items = _items({"Tree": 50, "Star": 50, "Chain": 50})
    sample = stratified_sample(items, n=30, seed=42)
    assert len(sample) == 30


def test_stratified_sample_proportional_per_shape():
    # 90 items, 3 strata of 30, sample 30 → ~10 per stratum
    items = _items({"Tree": 30, "Star": 30, "Chain": 30})
    sample = stratified_sample(items, n=30, seed=42)
    counts = {}
    for item in sample:
        counts[item["query_shape"]] = counts.get(item["query_shape"], 0) + 1
    # Each stratum should get within ±1 of the equal share
    for shape, n in counts.items():
        assert 9 <= n <= 11, f"stratum {shape} got {n} items, expected ~10"


def test_stratified_sample_deterministic_with_same_seed():
    items = _items({"Tree": 50, "Star": 50})
    s1 = stratified_sample(items, n=20, seed=42)
    s2 = stratified_sample(items, n=20, seed=42)
    assert [i["id"] for i in s1] == [i["id"] for i in s2]


def test_stratified_sample_returns_pool_when_n_exceeds_pool():
    items = _items({"Tree": 5})
    sample = stratified_sample(items, n=100, seed=42)
    assert len(sample) == 5


def test_stratified_sample_handles_imbalanced_strata():
    # One stratum dominates; sample should give it more items than tiny strata
    items = _items({"Tree": 100, "Rare": 2})
    sample = stratified_sample(items, n=20, seed=42)
    counts = {}
    for item in sample:
        counts[item["query_shape"]] = counts.get(item["query_shape"], 0) + 1
    # Both strata represented, Tree dominates
    assert counts.get("Rare", 0) >= 1
    assert counts.get("Tree", 0) >= 10


# ---------- convert_to_gold_item ------------------------------------------


def test_convert_to_gold_item_basic_factoid():
    sciqa = {
        "id": "AQ001",
        "query_type": "Factoid",
        "question": {"string": "What is X?"},
        "query": {"sparql": "SELECT ?x WHERE { ?x ?p ?o }"},
        "query_shape": "Tree",
        "template_id": "T01",
    }
    bindings = [{"x": {"type": "uri", "value": "http://orkg.org/r1"}}]
    gold = convert_to_gold_item(sciqa, bindings, executed_at="2026-04-24T12:00:00")
    assert gold["id"] == "AQ001"
    assert gold["question"] == "What is X?"
    assert gold["gold_sparql"] == "SELECT ?x WHERE { ?x ?p ?o }"
    assert gold["expected_entities"] == ["http://orkg.org/r1"]
    assert gold["has_entity_answer"] is True
    assert gold["query_shape"] == "Tree"
    assert gold["template_id"] == "T01"
    assert gold["query_type"] == "Factoid"
    assert gold["gold_executed_at"] == "2026-04-24T12:00:00"


def test_convert_to_gold_item_literal_answer_marks_no_entity():
    sciqa = {
        "id": "AQ002",
        "query_type": "Counting",
        "question": {"string": "How many?"},
        "query": {"sparql": "SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }"},
        "query_shape": "Tree",
        "template_id": "T10",
    }
    bindings = [{"n": {"type": "literal", "value": "42"}}]
    gold = convert_to_gold_item(sciqa, bindings, executed_at="2026-04-24T12:00:00")
    assert gold["has_entity_answer"] is False
    assert gold["expected_entities"] == []


def test_convert_to_gold_item_handles_missing_template_id():
    sciqa = {
        "id": "HQ001",
        "query_type": "Factoid",
        "question": {"string": "q"},
        "query": {"sparql": "ASK {}"},
        "query_shape": "tree",
        # no template_id
    }
    gold = convert_to_gold_item(sciqa, [], executed_at="2026-04-24T12:00:00")
    assert gold["template_id"] is None


# ---------- PREFIX_BLOCK constant -----------------------------------------


def test_prefix_block_contains_orkg_namespaces():
    assert "orkgp:" in PREFIX_BLOCK or "orkg/predicate" in PREFIX_BLOCK
    assert "orkgc:" in PREFIX_BLOCK or "orkg/class" in PREFIX_BLOCK
    assert "rdfs:" in PREFIX_BLOCK or "rdf-schema" in PREFIX_BLOCK
