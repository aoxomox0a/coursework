"""Tests for src/evaluation/metrics/self_correction.py — pure aggregation over traces."""
from src.evaluation.metrics.self_correction import (
    SelfCorrectionLift,
    compute_self_correction_lift,
)
from src.evaluation.trace import PipelineTrace


def _trace(*, first_valid: bool, used_retry: bool, retry_valid: bool | None) -> PipelineTrace:
    final_valid = first_valid or (used_retry and bool(retry_valid))
    return PipelineTrace(
        question="q",
        first_pass_query="q1",
        first_pass_valid=first_valid,
        first_pass_error="" if first_valid else "syntax",
        used_retry=used_retry,
        retry_query="q2" if used_retry else None,
        retry_valid=retry_valid,
        retry_error="" if (retry_valid is None or retry_valid) else "still bad",
        final_query="q2" if (used_retry and retry_valid) else "q1",
        final_valid=final_valid,
        bindings=[] if final_valid else None,
        answer="a" if final_valid else "",
        status="success" if final_valid else "error",
    )


def test_empty_traces_returns_zeroed_lift():
    r = compute_self_correction_lift([])
    assert r.total == 0
    assert r.first_pass_rate == 0.0
    assert r.after_retry_rate == 0.0
    assert r.delta == 0.0
    assert r.recovered_by_retry == 0


def test_all_first_pass_valid_no_lift():
    traces = [_trace(first_valid=True, used_retry=False, retry_valid=None)] * 5
    r = compute_self_correction_lift(traces)
    assert r.total == 5
    assert r.first_pass_valid_count == 5
    assert r.after_retry_valid_count == 5
    assert r.first_pass_rate == 1.0
    assert r.after_retry_rate == 1.0
    assert r.delta == 0.0
    assert r.recovered_by_retry == 0


def test_all_first_pass_invalid_all_recovered():
    traces = [_trace(first_valid=False, used_retry=True, retry_valid=True)] * 4
    r = compute_self_correction_lift(traces)
    assert r.total == 4
    assert r.first_pass_valid_count == 0
    assert r.after_retry_valid_count == 4
    assert r.first_pass_rate == 0.0
    assert r.after_retry_rate == 1.0
    assert r.delta == 1.0
    assert r.recovered_by_retry == 4


def test_mixed_partial_recovery():
    traces = [
        _trace(first_valid=True, used_retry=False, retry_valid=None),   # success no retry
        _trace(first_valid=True, used_retry=False, retry_valid=None),   # success no retry
        _trace(first_valid=False, used_retry=True, retry_valid=True),   # recovered
        _trace(first_valid=False, used_retry=True, retry_valid=False),  # not recovered
        _trace(first_valid=False, used_retry=True, retry_valid=False),  # not recovered
    ]
    r = compute_self_correction_lift(traces)
    assert r.total == 5
    assert r.first_pass_valid_count == 2
    assert r.after_retry_valid_count == 3  # 2 first-valid + 1 recovered
    assert abs(r.first_pass_rate - 0.4) < 1e-9
    assert abs(r.after_retry_rate - 0.6) < 1e-9
    assert abs(r.delta - 0.2) < 1e-9
    assert r.recovered_by_retry == 1


def test_lift_result_is_frozen():
    import dataclasses

    import pytest

    r = SelfCorrectionLift(
        total=0, first_pass_valid_count=0, after_retry_valid_count=0,
        first_pass_rate=0.0, after_retry_rate=0.0, delta=0.0,
        recovered_by_retry=0,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.total = 1  # type: ignore[misc]
