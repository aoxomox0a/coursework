"""
LLM-as-a-Judge metric for the natural-language answer (Task #4).

Reuses ``src/sparql/llm.call_llm`` directly — no new dependency, no new
HTTP client. Asks the same model (or a configured judge model) to score
the generated answer against the gold reference on four axes, returning
strict JSON.

Bias caveat: when the judge and generator are the same model, scores are
known to inflate by ~10–15% (self-preference bias). The current pipeline
ships with one model on Hactar so we accept this and document it in the
final report. To mitigate, the CLI in Task #6 will expose a ``--judge-model``
flag once a second model becomes available.

Two-pass parse: malformed JSON triggers exactly one retry with a stricter
"return ONLY JSON" reminder. A second failure is recorded as PARSE_ERROR
with a populated ``judge_error`` field — the run never crashes on a bad
judge response.
"""
import json
import logging
import re
from dataclasses import dataclass
from enum import Enum

from src.sparql.llm import call_llm

logger = logging.getLogger(__name__)

REQUIRED_SCORES = ("factual", "completeness", "fluency", "hallucination")

JUDGE_PROMPT_TEMPLATE = """\
You are an evaluator scoring an AI-generated natural-language answer against
a gold reference. Score the generated answer on four axes from 1 (worst) to
5 (best):

  - factual:        are the entities, values and facts correct?
  - completeness:   are all parts of the question addressed?
  - fluency:        is the answer readable, well-formed English?
  - hallucination:  5 means no invented information; 1 means heavy invention.

Output EXACTLY one JSON object with these five keys and nothing else:
{{"factual": <int 1-5>, "completeness": <int 1-5>, "fluency": <int 1-5>,
"hallucination": <int 1-5>, "rationale": "<one-sentence justification>"}}

Question: {question}
Gold answer: {gold_answer}
Generated answer: {generated_answer}
SPARQL result bindings (context, may be empty): {bindings}

JSON:
"""

JUDGE_RETRY_REMINDER = (
    "\n\nReminder: your previous output was not a parseable JSON object. "
    "Return ONLY a single JSON object with the five keys factual, "
    "completeness, fluency, hallucination, rationale — no prose, no fences."
)


class JudgeStatus(str, Enum):
    OK = "ok"
    PARSE_ERROR = "parse_error"


@dataclass(frozen=True)
class JudgeResult:
    status: JudgeStatus
    factual: int | None
    completeness: int | None
    fluency: int | None
    hallucination: int | None
    rationale: str
    judge_error: str


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json_from_response(raw: str) -> dict | None:
    """Pull the first JSON object out of an LLM response (tolerates fences + prose)."""
    if not raw:
        return None
    match = _JSON_OBJECT_RE.search(raw)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _clamp(value, lo: int = 1, hi: int = 5) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return lo
    return max(lo, min(hi, n))


def _parse_judge_payload(payload: dict) -> JudgeResult | str:
    """Convert a parsed JSON payload to a JudgeResult, or return an error message."""
    missing = [k for k in REQUIRED_SCORES if k not in payload]
    if missing:
        return f"missing required keys: {', '.join(missing)}"
    return JudgeResult(
        status=JudgeStatus.OK,
        factual=_clamp(payload["factual"]),
        completeness=_clamp(payload["completeness"]),
        fluency=_clamp(payload["fluency"]),
        hallucination=_clamp(payload["hallucination"]),
        rationale=str(payload.get("rationale", "")),
        judge_error="",
    )


def _build_prompt(question: str, gold_answer: str, generated_answer: str, bindings_text: str) -> str:
    return JUDGE_PROMPT_TEMPLATE.format(
        question=question,
        gold_answer=gold_answer,
        generated_answer=generated_answer,
        bindings=bindings_text,
    )


async def evaluate_answer_with_judge(
    question: str,
    gold_answer: str,
    generated_answer: str,
    sparql_bindings_text: str = "",
) -> JudgeResult:
    """Run the LLM-as-a-Judge over a single (gold, generated) answer pair."""
    base_prompt = _build_prompt(question, gold_answer, generated_answer, sparql_bindings_text)

    raw = await call_llm(base_prompt)
    payload = extract_json_from_response(raw)
    if payload is not None:
        result_or_error = _parse_judge_payload(payload)
        if isinstance(result_or_error, JudgeResult):
            return result_or_error
        # Schema-shaped JSON but missing keys — treat as parse error (no retry,
        # the LLM understood "JSON" but not the schema; another retry is unlikely
        # to help and burns tokens).
        return JudgeResult(
            status=JudgeStatus.PARSE_ERROR,
            factual=None, completeness=None, fluency=None, hallucination=None,
            rationale="",
            judge_error=result_or_error,
        )

    # First pass not parseable — retry once with stricter reminder.
    logger.info("judge: first pass returned non-JSON, retrying")
    raw_retry = await call_llm(base_prompt + JUDGE_RETRY_REMINDER)
    payload = extract_json_from_response(raw_retry)
    if payload is not None:
        result_or_error = _parse_judge_payload(payload)
        if isinstance(result_or_error, JudgeResult):
            return result_or_error
        return JudgeResult(
            status=JudgeStatus.PARSE_ERROR,
            factual=None, completeness=None, fluency=None, hallucination=None,
            rationale="",
            judge_error=result_or_error,
        )

    return JudgeResult(
        status=JudgeStatus.PARSE_ERROR,
        factual=None, completeness=None, fluency=None, hallucination=None,
        rationale="",
        judge_error="judge returned unparseable output on both attempts",
    )
