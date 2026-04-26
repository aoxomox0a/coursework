"""
Pure logic for the SciQA gold-set preparation pipeline.

The HTTP-bound parts (executing gold queries against ORKG, on-disk caching) live
in `scripts/prepare_sciqa_gold.py`; this module exposes only deterministic
functions so they can be unit-tested without network or fixtures.
"""
import random
from collections import defaultdict
from typing import Any, Iterable

# Prefix block prepended to every SciQA gold query. The dataset's SPARQL strings
# rely on these aliases without declaring them, and the ORKG endpoint does not
# inject defaults — without this prefix block every query returns an error.
PREFIX_BLOCK = """\
PREFIX orkgr: <http://orkg.org/orkg/resource/>
PREFIX orkgp: <http://orkg.org/orkg/predicate/>
PREFIX orkgc: <http://orkg.org/orkg/class/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

"""


def extract_question_text(question_field: Any) -> str:
    """Pull the question string out of SciQA's `question` field (dict or plain str)."""
    if isinstance(question_field, dict):
        return question_field.get("string", "")
    if isinstance(question_field, str):
        return question_field
    return ""


def extract_sparql_text(query_field: Any) -> str:
    """Pull the SPARQL string out of SciQA's `query` field (dict or plain str)."""
    if isinstance(query_field, dict):
        return query_field.get("sparql", "")
    if isinstance(query_field, str):
        return query_field
    return ""


def extract_uris_from_bindings(bindings: list[dict]) -> list[str]:
    """Return all distinct URIs across all bindings, preserving first-occurrence order."""
    seen: list[str] = []
    seen_set: set[str] = set()
    for row in bindings:
        for cell in row.values():
            if cell.get("type") == "uri":
                uri = cell.get("value", "")
                if uri and uri not in seen_set:
                    seen.append(uri)
                    seen_set.add(uri)
    return seen


def has_entity_answer(bindings: list[dict]) -> bool:
    """True iff at least one binding cell carries a URI value."""
    return bool(extract_uris_from_bindings(bindings))


def format_bindings_as_answer(bindings: list[dict]) -> str:
    """Human-readable rendering of result bindings — used as the canonical gold_answer text."""
    if not bindings:
        return "(no results)"
    lines = []
    for i, row in enumerate(bindings, 1):
        cells = [f"{var}={cell.get('value', '')}" for var, cell in row.items()]
        lines.append(f"{i}. " + ", ".join(cells))
    return "\n".join(lines)


def stratified_sample(
    items: list[dict],
    n: int,
    seed: int,
    stratum_key: str = "query_shape",
) -> list[dict]:
    """Return a stratified random sample of size ``n`` (or fewer if pool is smaller).

    Strata are buckets by ``stratum_key``. Each stratum gets a share proportional
    to its pool fraction, with at least 1 item per stratum that has any items.
    Selection within a stratum is uniform random under ``seed``.
    """
    if not items:
        return []
    if n >= len(items):
        return list(items)

    rng = random.Random(seed)
    by_stratum: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        by_stratum[item.get(stratum_key, "")].append(item)

    strata = sorted(by_stratum.keys())
    total = len(items)

    # First pass: allocate proportional shares (floor), guaranteeing at least 1 per stratum.
    allocations: dict[str, int] = {}
    for stratum in strata:
        share = int(n * len(by_stratum[stratum]) / total)
        allocations[stratum] = max(1, share)

    # Distribute / trim to hit exactly n.
    diff = n - sum(allocations.values())
    sorted_by_pool = sorted(strata, key=lambda s: -len(by_stratum[s]))
    i = 0
    while diff != 0:
        s = sorted_by_pool[i % len(sorted_by_pool)]
        if diff > 0 and allocations[s] < len(by_stratum[s]):
            allocations[s] += 1
            diff -= 1
        elif diff < 0 and allocations[s] > 1:
            allocations[s] -= 1
            diff += 1
        i += 1
        if i > 10 * n:  # safety guard against pathological input
            break

    sampled: list[dict] = []
    for stratum in strata:
        pool = by_stratum[stratum]
        k = min(allocations[stratum], len(pool))
        sampled.extend(rng.sample(pool, k))
    return sampled


def convert_to_gold_item(
    sciqa_item: dict,
    bindings: list[dict],
    executed_at: str,
) -> dict:
    """Transform a SciQA test item + its executed bindings into our gold-set schema."""
    return {
        "id": sciqa_item.get("id", ""),
        "question": extract_question_text(sciqa_item.get("question")),
        "gold_sparql": extract_sparql_text(sciqa_item.get("query")),
        "gold_bindings": bindings,
        "gold_answer": format_bindings_as_answer(bindings),
        "expected_entities": extract_uris_from_bindings(bindings),
        "has_entity_answer": has_entity_answer(bindings),
        "query_shape": sciqa_item.get("query_shape"),
        "template_id": sciqa_item.get("template_id"),
        "query_type": sciqa_item.get("query_type"),
        "gold_executed_at": executed_at,
    }
