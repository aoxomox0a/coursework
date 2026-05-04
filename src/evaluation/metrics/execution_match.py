"""Funnel stage 3 — relaxed Execution Match between gold and generated bindings.

Each binding row is canonicalised to an unordered ``frozenset`` of
``(type, value)`` cells. This makes the comparison:
  - independent of variable names (gold and generated may use different vars)
  - independent of row ordering (no ORDER BY required to match)

Trade-off: intra-row variable-name structure is discarded. Two rows that bind
the same set of values to differently-named variables compare equal — which
is the desired behaviour for "did the queries return the same answer set?",
but means that re-association across columns within a row is not enforced.

False-positive warnings are emitted for known-coincidental cases:
  - empty gold (any generated query returning empty matches trivially)
  - single-row gold AND single-row generated (a broader generated query may
    accidentally narrow to the same single row)
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionMatchResult:
    match: bool
    score: float                    # Jaccard similarity over canonical row sets, 0..1
    gold_count: int
    generated_count: int
    intersection: int
    false_positive_warning: str     # empty when no coincidence risk identified


def _canonical_row(row: dict) -> frozenset[tuple[str, str]]:
    """Drop variable names; keep only the set of (type, value) cells."""
    return frozenset(
        (cell.get("type", ""), cell.get("value", ""))
        for cell in row.values()
    )


def _false_positive_warning(gold: list[dict], generated: list[dict]) -> str:
    if not gold:
        return (
            "Gold returned no bindings — execution match is trivially "
            "satisfiable by any generated query that also returns empty."
        )
    if len(gold) == 1 and len(generated) == 1:
        return (
            "Both gold and generated returned a single row — high risk of "
            "coincidental match (a broader generated query may accidentally "
            "narrow to the same row)."
        )
    return ""


def evaluate_execution_match(
    gold_bindings: list[dict],
    generated_bindings: list[dict],
) -> ExecutionMatchResult:
    """Compare two binding sets, return match flag, Jaccard score, and warnings."""
    gold_set = {_canonical_row(row) for row in gold_bindings}
    gen_set = {_canonical_row(row) for row in generated_bindings}

    inter = gold_set & gen_set
    union = gold_set | gen_set
    score = len(inter) / len(union) if union else 1.0

    return ExecutionMatchResult(
        match=gold_set == gen_set,
        score=score,
        gold_count=len(gold_bindings),
        generated_count=len(generated_bindings),
        intersection=len(inter),
        false_positive_warning=_false_positive_warning(gold_bindings, generated_bindings),
    )
