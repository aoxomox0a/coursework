"""Tests for src/evaluation/metrics/judge.py — LLM-as-a-Judge over the NL answer."""
from unittest.mock import AsyncMock

import pytest

from src.evaluation.metrics.judge import (
    JudgeResult,
    JudgeStatus,
    extract_json_from_response,
    evaluate_answer_with_judge,
)


# ---------- JSON extraction (pure) ---------------------------------------


def test_extract_json_from_plain_object():
    raw = '{"factual": 5, "completeness": 4, "fluency": 5, "hallucination": 5, "rationale": "ok"}'
    assert extract_json_from_response(raw) == {
        "factual": 5, "completeness": 4, "fluency": 5, "hallucination": 5, "rationale": "ok",
    }


def test_extract_json_strips_fenced_block():
    raw = 'Here is my judgement:\n```json\n{"factual": 4, "completeness": 4, "fluency": 5, "hallucination": 5, "rationale": "fine"}\n```\nDone.'
    out = extract_json_from_response(raw)
    assert out["factual"] == 4
    assert out["rationale"] == "fine"


def test_extract_json_handles_unfenced_with_prose():
    raw = 'Sure thing! {"factual": 3, "completeness": 2, "fluency": 4, "hallucination": 5, "rationale": "partial"} hope this helps'
    out = extract_json_from_response(raw)
    assert out["factual"] == 3


def test_extract_json_returns_none_on_garbage():
    assert extract_json_from_response("no json here") is None


def test_extract_json_returns_none_on_empty():
    assert extract_json_from_response("") is None


# ---------- evaluate_answer_with_judge -----------------------------------


@pytest.fixture
def patched_llm(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr("src.evaluation.metrics.judge.call_llm", mock)
    return mock


async def test_judge_returns_scores_on_valid_json(patched_llm):
    patched_llm.return_value = (
        '{"factual": 5, "completeness": 4, "fluency": 5, "hallucination": 5, "rationale": "great"}'
    )
    r = await evaluate_answer_with_judge(
        question="Q?",
        gold_answer="42",
        generated_answer="42",
        sparql_bindings_text="?n=42",
    )
    assert r.status == JudgeStatus.OK
    assert r.factual == 5
    assert r.completeness == 4
    assert r.fluency == 5
    assert r.hallucination == 5
    assert r.rationale == "great"
    assert r.judge_error == ""


async def test_judge_retries_once_on_malformed_then_succeeds(patched_llm):
    patched_llm.side_effect = [
        "I'm thinking… not JSON yet",
        '{"factual": 3, "completeness": 3, "fluency": 4, "hallucination": 4, "rationale": "ok"}',
    ]
    r = await evaluate_answer_with_judge("Q?", "g", "x", "")
    assert r.status == JudgeStatus.OK
    assert patched_llm.call_count == 2


async def test_judge_returns_error_after_two_failures(patched_llm):
    patched_llm.side_effect = ["not json", "still not json"]
    r = await evaluate_answer_with_judge("Q?", "g", "x", "")
    assert r.status == JudgeStatus.PARSE_ERROR
    assert r.factual is None
    assert r.judge_error  # populated


async def test_judge_clamps_out_of_range_scores(patched_llm):
    patched_llm.return_value = (
        '{"factual": 9, "completeness": 0, "fluency": -3, "hallucination": 7, "rationale": "weird"}'
    )
    r = await evaluate_answer_with_judge("Q?", "g", "x", "")
    assert r.status == JudgeStatus.OK
    assert 1 <= r.factual <= 5
    assert 1 <= r.completeness <= 5
    assert 1 <= r.fluency <= 5
    assert 1 <= r.hallucination <= 5


async def test_judge_handles_missing_score_field(patched_llm):
    patched_llm.return_value = '{"factual": 5, "rationale": "missing keys"}'
    r = await evaluate_answer_with_judge("Q?", "g", "x", "")
    assert r.status == JudgeStatus.PARSE_ERROR
    assert "missing" in r.judge_error.lower() or "key" in r.judge_error.lower()


async def test_judge_includes_question_and_answers_in_prompt(patched_llm):
    patched_llm.return_value = (
        '{"factual": 5, "completeness": 5, "fluency": 5, "hallucination": 5, "rationale": "x"}'
    )
    await evaluate_answer_with_judge(
        question="Who directed Inception?",
        gold_answer="Christopher Nolan",
        generated_answer="Nolan",
        sparql_bindings_text="?d=http://nolan",
    )
    prompt = patched_llm.call_args_list[0].args[0]
    assert "Who directed Inception?" in prompt
    assert "Christopher Nolan" in prompt
    assert "Nolan" in prompt


async def test_judge_routes_to_judge_llm_model(patched_llm, monkeypatch):
    """The judge must pass JUDGE_LLM_MODEL to call_llm so users can route to a
    different model on Hactar (mitigating self-preference bias)."""
    monkeypatch.setattr("src.evaluation.metrics.judge.JUDGE_LLM_MODEL", "judge-model-xyz")
    patched_llm.return_value = (
        '{"factual": 5, "completeness": 5, "fluency": 5, "hallucination": 5, "rationale": "x"}'
    )
    await evaluate_answer_with_judge("Q?", "g", "x", "")
    # call_llm receives model as a keyword argument
    assert patched_llm.call_args_list[0].kwargs.get("model") == "judge-model-xyz"


async def test_judge_routes_retry_to_same_model(patched_llm, monkeypatch):
    """When the first parse fails and we retry, the retry call must also use
    JUDGE_LLM_MODEL — not silently fall back to the generator."""
    monkeypatch.setattr("src.evaluation.metrics.judge.JUDGE_LLM_MODEL", "judge-model-xyz")
    patched_llm.side_effect = [
        "not json",
        '{"factual": 3, "completeness": 3, "fluency": 4, "hallucination": 4, "rationale": "ok"}',
    ]
    await evaluate_answer_with_judge("Q?", "g", "x", "")
    assert patched_llm.call_count == 2
    assert patched_llm.call_args_list[0].kwargs.get("model") == "judge-model-xyz"
    assert patched_llm.call_args_list[1].kwargs.get("model") == "judge-model-xyz"


# ---------- result invariants --------------------------------------------


async def test_judge_result_is_frozen(patched_llm):
    import dataclasses

    patched_llm.return_value = (
        '{"factual": 5, "completeness": 5, "fluency": 5, "hallucination": 5, "rationale": "x"}'
    )
    r = await evaluate_answer_with_judge("Q?", "g", "x", "")
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.factual = 1  # type: ignore[misc]
