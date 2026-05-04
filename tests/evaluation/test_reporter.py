"""Tests for src/evaluation/reporter.py — JSON + Markdown output."""
import json

from src.evaluation.metrics.algebra import AlgebraMatchResult, AlgebraMatchStatus
from src.evaluation.metrics.execution_match import ExecutionMatchResult
from src.evaluation.metrics.judge import JudgeResult, JudgeStatus
from src.evaluation.metrics.self_correction import SelfCorrectionLift
from src.evaluation.metrics.syntax import SyntaxResult
from src.evaluation.reporter import write_report
from src.evaluation.runner import FunnelSummary, ItemResult, SuiteResult
from src.evaluation.trace import PipelineTrace


def _suite() -> SuiteResult:
    trace = PipelineTrace(
        question="Q?",
        first_pass_query="SELECT ?x WHERE { ?x ?p ?o }",
        first_pass_valid=True,
        first_pass_error="",
        used_retry=False,
        retry_query=None,
        retry_valid=None,
        retry_error=None,
        final_query="SELECT ?x WHERE { ?x ?p ?o }",
        final_valid=True,
        bindings=[{"x": {"type": "uri", "value": "http://result"}}],
        answer="result",
        status="success",
    )
    item = ItemResult(
        gold_id="AQ001",
        question="Q?",
        gold_sparql="SELECT ?x WHERE { ?x ?p ?o }",
        trace=trace,
        syntax=SyntaxResult(valid=True, error=""),
        execution_match=ExecutionMatchResult(
            match=True, score=1.0, gold_count=1, generated_count=1,
            intersection=1, false_positive_warning="",
        ),
        algebra=AlgebraMatchResult(
            match=True, status=AlgebraMatchStatus.COMPARED, error="", reason="",
        ),
        judge=JudgeResult(
            status=JudgeStatus.OK, factual=5, completeness=4, fluency=5,
            hallucination=5, rationale="great", judge_error="",
        ),
    )
    return SuiteResult(
        items=(item,),
        funnel=FunnelSummary(total=1, syntax_valid=1, executable_ok=1,
                             execution_match=1, algebra_match=1),
        self_correction=SelfCorrectionLift(
            total=1, first_pass_valid_count=1, after_retry_valid_count=1,
            first_pass_rate=1.0, after_retry_rate=1.0, delta=0.0,
            recovered_by_retry=0,
        ),
        timestamp="2026-04-27T12:00:00+00:00",
        config={"endpoint": "https://orkg.org/triplestore", "judge_enabled": True},
    )


def test_write_report_creates_both_files(tmp_path):
    out = write_report(_suite(), tmp_path)
    assert out == tmp_path
    assert (tmp_path / "results.json").exists()
    assert (tmp_path / "summary.md").exists()


def test_results_json_is_valid_and_roundtrips(tmp_path):
    write_report(_suite(), tmp_path)
    data = json.loads((tmp_path / "results.json").read_text())
    assert data["funnel"]["total"] == 1
    assert data["self_correction"]["total"] == 1
    assert data["items"][0]["gold_id"] == "AQ001"
    assert data["items"][0]["judge"]["factual"] == 5
    # Enums must serialise as their string values, not as raw objects
    assert data["items"][0]["algebra"]["status"] == "compared"
    assert data["items"][0]["judge"]["status"] == "ok"


def test_results_json_handles_no_judge(tmp_path):
    suite = _suite()
    items = (
        ItemResult(**{**suite.items[0].__dict__, "judge": None}),
    )
    suite_no_judge = SuiteResult(
        items=items, funnel=suite.funnel, self_correction=suite.self_correction,
        timestamp=suite.timestamp, config=suite.config,
    )
    write_report(suite_no_judge, tmp_path)
    data = json.loads((tmp_path / "results.json").read_text())
    assert data["items"][0]["judge"] is None


def test_summary_markdown_contains_funnel_table(tmp_path):
    write_report(_suite(), tmp_path)
    md = (tmp_path / "summary.md").read_text()
    assert "Funnel" in md
    assert "Syntax" in md or "syntax" in md.lower()
    assert "Execution Match" in md or "execution match" in md.lower()
    assert "Algebra" in md or "algebra" in md.lower()


def test_summary_markdown_includes_self_correction_section(tmp_path):
    write_report(_suite(), tmp_path)
    md = (tmp_path / "summary.md").read_text()
    assert "self-correction" in md.lower() or "self correction" in md.lower()


def test_summary_markdown_includes_judge_section_when_present(tmp_path):
    write_report(_suite(), tmp_path)
    md = (tmp_path / "summary.md").read_text()
    assert "judge" in md.lower() or "factual" in md.lower()


def test_summary_markdown_omits_judge_section_when_absent(tmp_path):
    suite = _suite()
    items = (ItemResult(**{**suite.items[0].__dict__, "judge": None}),)
    suite_no_judge = SuiteResult(
        items=items, funnel=suite.funnel, self_correction=suite.self_correction,
        timestamp=suite.timestamp, config=suite.config,
    )
    write_report(suite_no_judge, tmp_path)
    md = (tmp_path / "summary.md").read_text()
    # Should not crash; should not advertise judge stats
    assert "factual" not in md.lower() or "n/a" in md.lower()


def test_summary_markdown_renders_percentages(tmp_path):
    write_report(_suite(), tmp_path)
    md = (tmp_path / "summary.md").read_text()
    assert "%" in md
    assert "100" in md  # 1/1 → 100%
