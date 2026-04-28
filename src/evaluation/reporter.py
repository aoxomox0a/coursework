"""
Render a SuiteResult to a JSON artifact + a Markdown summary.

  reports/<run-id>/results.json   — canonical machine-readable artifact
  reports/<run-id>/summary.md     — human-readable funnel table + lift + judge

The JSON serialiser walks frozen dataclasses + Enums recursively. Tuples are
unwrapped to lists for JSON compatibility.
"""
import dataclasses
import json
from enum import Enum
from pathlib import Path
from typing import Any

from src.evaluation.runner import ItemResult, SuiteResult


def _to_jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {k: _to_jsonable(v) for k, v in dataclasses.asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    return value


def _pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{100 * numerator / denominator:.1f}%"


def _judge_means(items: list[ItemResult]) -> dict[str, float | None] | None:
    """Average each 1-5 axis over items that have a judge result."""
    judged = [i.judge for i in items if i.judge is not None and i.judge.factual is not None]
    if not judged:
        return None
    n = len(judged)
    return {
        "factual": sum(j.factual for j in judged) / n,
        "completeness": sum(j.completeness for j in judged) / n,
        "fluency": sum(j.fluency for j in judged) / n,
        "hallucination": sum(j.hallucination for j in judged) / n,
        "judged_count": n,
    }


def _render_markdown(suite: SuiteResult) -> str:
    f = suite.funnel
    sc = suite.self_correction
    judge_means = _judge_means(list(suite.items))

    lines: list[str] = []
    lines.append(f"# Evaluation Run {suite.timestamp}")
    lines.append("")
    lines.append("## Configuration")
    if suite.config:
        for key, val in sorted(suite.config.items()):
            lines.append(f"- **{key}**: `{val}`")
    else:
        lines.append("- (no config recorded)")
    lines.append("")

    lines.append("## Funnel")
    lines.append("")
    lines.append("| Stage | Pass | Rate |")
    lines.append("|-------|------|------|")
    lines.append(f"| Syntax valid       | {f.syntax_valid}/{f.total} | {_pct(f.syntax_valid, f.total)} |")
    lines.append(f"| Executable         | {f.executable_ok}/{f.total} | {_pct(f.executable_ok, f.total)} |")
    lines.append(f"| Execution Match    | {f.execution_match}/{f.total} | {_pct(f.execution_match, f.total)} |")
    lines.append(f"| Algebra Match (corroborative) | {f.algebra_match}/{f.total} | {_pct(f.algebra_match, f.total)} |")
    lines.append("")

    lines.append("## Self-correction lift")
    lines.append("")
    lines.append(f"- First-pass syntax valid:  {sc.first_pass_valid_count}/{sc.total}  ({_pct(sc.first_pass_valid_count, sc.total)})")
    lines.append(f"- After fix-prompt retry:   {sc.after_retry_valid_count}/{sc.total}  ({_pct(sc.after_retry_valid_count, sc.total)})")
    lines.append(f"- Delta:                    +{sc.delta * 100:.1f}pp ({sc.recovered_by_retry} queries recovered)")
    lines.append("")

    if judge_means is not None:
        lines.append("## Answer quality (LLM judge, 1-5)")
        lines.append("")
        lines.append(f"- Judged items: {judge_means['judged_count']}/{f.total}")
        lines.append(f"- Factual:        mean = {judge_means['factual']:.2f}")
        lines.append(f"- Completeness:   mean = {judge_means['completeness']:.2f}")
        lines.append(f"- Fluency:        mean = {judge_means['fluency']:.2f}")
        lines.append(f"- Hallucination:  mean = {judge_means['hallucination']:.2f}  (5 = no invention)")
        lines.append("")

    lines.append("## Per-item summary")
    lines.append("")
    lines.append("| ID | Syntax | Exec | EM | Algebra | Used retry |")
    lines.append("|----|--------|------|----|---------|------------|")
    for item in suite.items:
        lines.append(
            f"| {item.gold_id} | "
            f"{'✓' if item.syntax.valid else '✗'} | "
            f"{'✓' if item.trace.bindings is not None else '✗'} | "
            f"{'✓' if item.execution_match.match else '✗'} | "
            f"{'✓' if item.algebra.match else '✗'} | "
            f"{'✓' if item.trace.used_retry else ''} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_report(suite: SuiteResult, out_dir: Path) -> Path:
    """Write results.json and summary.md to ``out_dir`` and return the path."""
    out_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "timestamp": suite.timestamp,
        "config": suite.config,
        "funnel": _to_jsonable(suite.funnel),
        "self_correction": _to_jsonable(suite.self_correction),
        "items": _to_jsonable(list(suite.items)),
    }
    (out_dir / "results.json").write_text(json.dumps(data, indent=2))
    (out_dir / "summary.md").write_text(_render_markdown(suite))
    return out_dir
