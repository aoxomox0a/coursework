"""Aggregate per-item PipelineTrace records into the self-correction lift metric.

The lift quantifies how much value the fix-prompt retry adds versus a hypothetical
single-shot pipeline:
  - first_pass_rate: fraction of items where the first LLM call already produced
    a syntactically valid SPARQL query.
  - after_retry_rate: fraction of items where the FINAL query (post-retry if used)
    was syntactically valid.
  - delta: after_retry_rate − first_pass_rate. Strictly ≥ 0 by construction.
  - recovered_by_retry: count of items where first pass failed but retry succeeded.
"""
from dataclasses import dataclass

from src.evaluation.trace import PipelineTrace


@dataclass(frozen=True)
class SelfCorrectionLift:
    total: int
    first_pass_valid_count: int
    after_retry_valid_count: int
    first_pass_rate: float
    after_retry_rate: float
    delta: float
    recovered_by_retry: int


def compute_self_correction_lift(traces: list[PipelineTrace]) -> SelfCorrectionLift:
    """Aggregate a list of traces into the per-funnel lift summary."""
    total = len(traces)
    if total == 0:
        return SelfCorrectionLift(
            total=0,
            first_pass_valid_count=0,
            after_retry_valid_count=0,
            first_pass_rate=0.0,
            after_retry_rate=0.0,
            delta=0.0,
            recovered_by_retry=0,
        )

    first_valid = sum(1 for t in traces if t.first_pass_valid)
    after_retry = sum(1 for t in traces if t.final_valid)
    recovered = sum(
        1 for t in traces if (not t.first_pass_valid) and t.used_retry and t.retry_valid
    )

    first_rate = first_valid / total
    after_rate = after_retry / total

    return SelfCorrectionLift(
        total=total,
        first_pass_valid_count=first_valid,
        after_retry_valid_count=after_retry,
        first_pass_rate=first_rate,
        after_retry_rate=after_rate,
        delta=after_rate - first_rate,
        recovered_by_retry=recovered,
    )
