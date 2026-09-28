"""
End-to-end evaluation runner: per-item orchestration + suite-level aggregation.

Per item:
  1. Run the linking pipeline (NER + noun chunks + ChromaDB lookup) via
     ``src.linking.pipeline.run_linking_pipeline``.
  2. Run the instrumented SPARQL pipeline (``src.evaluation.trace.run_with_trace``)
     to produce a PipelineTrace with first-pass and retry artifacts.
  3. Compute the funnel metrics on the final query (syntax, execution match
     against gold bindings, algebra match against gold SPARQL).
  4. Optionally call the LLM-as-a-Judge over the formatted answer.

Suite aggregation:
  - Funnel summary: counts per stage.
  - Self-correction lift: aggregated over the per-item PipelineTraces.
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from src.evaluation.metrics.algebra import (
    AlgebraMatchResult,
    evaluate_algebra_match,
)
from src.evaluation.metrics.execution_match import (
    ExecutionMatchResult,
    evaluate_execution_match,
)
from src.evaluation.metrics.judge import (
    JudgeResult,
    evaluate_answer_with_judge,
)
from src.evaluation.metrics.self_correction import (
    SelfCorrectionLift,
    compute_self_correction_lift,
)
from src.evaluation.metrics.syntax import SyntaxResult, evaluate_syntax
from src.evaluation.trace import PipelineTrace, run_with_trace
from src.linking.pipeline import run_linking_pipeline


@dataclass(frozen=True)
class FunnelSummary:
    total: int
    syntax_valid: int
    executable_ok: int
    execution_match: int
    algebra_match: int


@dataclass(frozen=True)
class ItemResult:
    gold_id: str
    question: str
    gold_sparql: str
    trace: PipelineTrace
    syntax: SyntaxResult
    execution_match: ExecutionMatchResult
    algebra: AlgebraMatchResult
    judge: JudgeResult | None


@dataclass(frozen=True)
class SuiteResult:
    items: tuple[ItemResult, ...]
    funnel: FunnelSummary
    self_correction: SelfCorrectionLift
    timestamp: str
    config: dict


def compute_funnel_summary(items: list[ItemResult]) -> FunnelSummary:
    """Pure aggregation: count items passing each funnel stage."""
    return FunnelSummary(
        total=len(items),
        syntax_valid=sum(1 for i in items if i.syntax.valid),
        executable_ok=sum(1 for i in items if i.trace.bindings is not None),
        execution_match=sum(1 for i in items if i.execution_match.match),
        algebra_match=sum(1 for i in items if i.algebra.match),
    )


async def evaluate_item(gold_item: dict, judge_enabled: bool) -> ItemResult:
    """Evaluate one gold item through the full pipeline + funnel."""
    question = gold_item["question"]

    # Linking is synchronous (loads spaCy, does ChromaDB lookups) — offload it.
    linking_results = await asyncio.to_thread(run_linking_pipeline, question)
    linking_result = linking_results[0] if linking_results else {
        "entities": [], "relation": {}, "relation_candidates": [],
    }

    trace = await run_with_trace(question, linking_result)

    syntax = evaluate_syntax(trace.final_query) if trace.final_query else SyntaxResult(
        valid=False, error="no query produced",
    )
    execution_match = evaluate_execution_match(
        gold_item.get("gold_bindings", []),
        trace.bindings if trace.bindings is not None else [],
    )
    algebra = evaluate_algebra_match(
        gold_item.get("gold_sparql", ""),
        trace.final_query,
    )

    judge: JudgeResult | None = None
    if judge_enabled and trace.status == "success":
        judge = await evaluate_answer_with_judge(
            question=question,
            gold_answer=gold_item.get("gold_answer", ""),
            generated_answer=trace.answer,
            sparql_bindings_text="",
        )

    return ItemResult(
        gold_id=gold_item.get("id", ""),
        question=question,
        gold_sparql=gold_item.get("gold_sparql", ""),
        trace=trace,
        syntax=syntax,
        execution_match=execution_match,
        algebra=algebra,
        judge=judge,
    )


async def run_evaluation(
    gold_items: list[dict],
    judge_enabled: bool = False,
    config: dict | None = None,
) -> SuiteResult:
    """Evaluate every gold item and return the aggregated SuiteResult.

    Items are processed serially to be a polite citizen of public endpoints
    (ORKG) and the shared LLM endpoint (Hactar). Concurrency would only buy
    a small speedup for a 49-item suite and risks throttling.
    """
    items: list[ItemResult] = []
    for gi in gold_items:
        items.append(await evaluate_item(gi, judge_enabled))

    return SuiteResult(
        items=tuple(items),
        funnel=compute_funnel_summary(items),
        self_correction=compute_self_correction_lift([i.trace for i in items]),
        timestamp=datetime.now(tz=timezone.utc).isoformat(),
        config=dict(config or {}),
    )
