"""Tests for src/evaluation/runner.py — orchestration + funnel aggregation.

Per-item orchestration is light glue; the bulk of the testable logic is the
pure ``compute_funnel_summary`` aggregator. ``evaluate_item`` is covered by a
mock-based integration test that verifies wiring without touching live endpoints.
"""
from unittest.mock import AsyncMock

import pytest

from src.evaluation.metrics.algebra import AlgebraMatchResult, AlgebraMatchStatus
from src.evaluation.metrics.execution_match import ExecutionMatchResult
from src.evaluation.metrics.judge import JudgeResult, JudgeStatus
from src.evaluation.metrics.syntax import SyntaxResult
from src.evaluation.runner import (
    FunnelSummary,
    ItemResult,
    compute_funnel_summary,
    evaluate_item,
    run_evaluation,
)
from src.evaluation.trace import PipelineTrace


_VALID_SPARQL = "SELECT ?x WHERE { ?x ?p ?o }"


def _trace(*, final_valid: bool, bindings: list[dict] | None) -> PipelineTrace:
    final_q = _VALID_SPARQL if final_valid else "broken {{{"
    return PipelineTrace(
        question="q", first_pass_query=final_q,
        first_pass_valid=final_valid, first_pass_error="",
        used_retry=False, retry_query=None, retry_valid=None, retry_error=None,
        final_query=final_q, final_valid=final_valid,
        bindings=bindings, answer="a" if final_valid else "",
        status="success" if final_valid else "error",
    )


def _item(
    *,
    syntax_valid: bool,
    bindings: list[dict] | None,
    em_match: bool,
    algebra_match: bool,
) -> ItemResult:
    return ItemResult(
        gold_id="x",
        question="q",
        gold_sparql="SELECT ?x WHERE { ?x ?p ?o }",
        trace=_trace(final_valid=syntax_valid, bindings=bindings),
        syntax=SyntaxResult(valid=syntax_valid, error=""),
        execution_match=ExecutionMatchResult(
            match=em_match, score=1.0 if em_match else 0.0,
            gold_count=1, generated_count=1 if bindings else 0,
            intersection=1 if em_match else 0,
            false_positive_warning="",
        ),
        algebra=AlgebraMatchResult(
            match=algebra_match, status=AlgebraMatchStatus.COMPARED,
            error="", reason="",
        ),
        judge=None,
    )


# ---------- compute_funnel_summary ---------------------------------------


def test_funnel_empty_returns_zeros():
    f = compute_funnel_summary([])
    assert f.total == 0
    assert f.syntax_valid == f.executable_ok == f.execution_match == f.algebra_match == 0


def test_funnel_counts_each_stage_independently():
    items = [
        _item(syntax_valid=True, bindings=[{"x": {"type": "uri", "value": "http://a"}}],
              em_match=True, algebra_match=True),
        _item(syntax_valid=True, bindings=[],
              em_match=False, algebra_match=True),
        _item(syntax_valid=True, bindings=None,                                # executable failed
              em_match=False, algebra_match=False),
        _item(syntax_valid=False, bindings=None,
              em_match=False, algebra_match=False),
    ]
    f = compute_funnel_summary(items)
    assert f.total == 4
    assert f.syntax_valid == 3
    assert f.executable_ok == 2  # bindings is not None for items 0 and 1
    assert f.execution_match == 1
    assert f.algebra_match == 2


def test_funnel_summary_is_frozen():
    import dataclasses

    f = FunnelSummary(total=0, syntax_valid=0, executable_ok=0,
                      execution_match=0, algebra_match=0)
    with pytest.raises(dataclasses.FrozenInstanceError):
        f.total = 1  # type: ignore[misc]


# ---------- evaluate_item integration (mocked primitives) ----------------


@pytest.fixture
def patched_orchestration(monkeypatch):
    # Mock the linking pipeline to return a usable result
    def fake_linking(questions):
        return [{
            "question": questions if isinstance(questions, str) else questions[0],
            "entities": [{"uri": "http://e", "label": "E"}],
            "relation": {"uri": "http://r", "label": "R"},
            "relation_candidates": [],
        }]

    monkeypatch.setattr("src.evaluation.runner.run_linking_pipeline", fake_linking)

    # Mock the trace so we don't hit LLM / endpoint
    fake_trace = _trace(
        final_valid=True,
        bindings=[{"x": {"type": "uri", "value": "http://result"}}],
    )
    monkeypatch.setattr(
        "src.evaluation.runner.run_with_trace",
        AsyncMock(return_value=fake_trace),
    )
    return fake_trace


async def test_evaluate_item_wires_funnel_metrics(patched_orchestration):
    gold_item = {
        "id": "AQ001",
        "question": "Who?",
        "gold_sparql": "SELECT ?x WHERE { ?x ?p ?o }",
        "gold_bindings": [{"x": {"type": "uri", "value": "http://result"}}],
        "gold_answer": "result",
    }
    item = await evaluate_item(gold_item, judge_enabled=False)
    assert item.gold_id == "AQ001"
    assert item.question == "Who?"
    assert item.syntax.valid is True
    assert item.execution_match.match is True
    # Algebra: same SPARQL on both sides → match
    assert item.algebra.match is True
    assert item.judge is None


async def test_evaluate_item_with_judge(patched_orchestration, monkeypatch):
    judge_mock = AsyncMock(return_value=JudgeResult(
        status=JudgeStatus.OK, factual=5, completeness=4, fluency=5,
        hallucination=5, rationale="ok", judge_error="",
    ))
    monkeypatch.setattr("src.evaluation.runner.evaluate_answer_with_judge", judge_mock)

    gold_item = {
        "id": "AQ002",
        "question": "Who?",
        "gold_sparql": "SELECT ?x WHERE { ?x ?p ?o }",
        "gold_bindings": [{"x": {"type": "uri", "value": "http://result"}}],
        "gold_answer": "result",
    }
    item = await evaluate_item(gold_item, judge_enabled=True)
    assert item.judge is not None
    assert item.judge.factual == 5
    judge_mock.assert_called_once()


# ---------- run_evaluation end-to-end ------------------------------------


async def test_run_evaluation_aggregates(patched_orchestration):
    gold_items = [
        {"id": f"AQ00{i}", "question": f"Q{i}",
         "gold_sparql": "SELECT ?x WHERE { ?x ?p ?o }",
         "gold_bindings": [{"x": {"type": "uri", "value": "http://result"}}],
         "gold_answer": "result"}
        for i in range(3)
    ]
    suite = await run_evaluation(gold_items, judge_enabled=False, config={"k": "v"})
    assert len(suite.items) == 3
    assert suite.funnel.total == 3
    assert suite.funnel.syntax_valid == 3
    assert suite.funnel.execution_match == 3
    assert suite.config == {"k": "v"}
    assert suite.timestamp  # non-empty ISO timestamp
