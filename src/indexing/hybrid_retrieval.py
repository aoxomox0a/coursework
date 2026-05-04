"""Hybrid retrieval = dense embedding (Chroma) ⊕ lexical BM25, fused via RRF.

Reciprocal Rank Fusion (Cormack et al. 2009) is the standard rank-aggregation
choice when the underlying scorers live on incomparable scales — here cosine
similarity vs. BM25's tf-idf-derived score. RRF needs only ranks, not raw
scores, so no normalisation/calibration step is required.

Public surface is ``hybrid_query``: takes dense + lexical hit lists and
returns the fused top-K. Pure function, no I/O — call sites in
``chroma_storage`` provide the per-collection dense + BM25 results.
"""
from __future__ import annotations

from dataclasses import dataclass


# RRF k=60 is the constant from the original paper; widely used as a sane
# default. Larger k flattens the curve (less weight on top ranks); smaller k
# steepens it. 60 has held up well in IR benchmarks.
_RRF_K = 60


@dataclass(frozen=True)
class FusedHit:
    uri: str
    label: str
    score: float  # RRF score (higher = better)


def reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[str, str]]],
    k: int = _RRF_K,
) -> list[FusedHit]:
    """Fuse multiple ranked lists of (uri, label) tuples by RRF.

    Each input list is in best→worst order. Items absent from a given list
    contribute nothing from that scorer. Ties broken by URI for determinism.

    Args:
        ranked_lists: List of ranked (uri, label) sequences from independent
            scorers. Order within each inner list = rank, best first.
        k: RRF constant. Default 60 (paper).

    Returns:
        Fused hits in descending RRF score order.
    """
    accumulator: dict[str, dict] = {}  # uri -> {label, score}

    for ranked in ranked_lists:
        for rank, (uri, label) in enumerate(ranked, start=1):
            if not uri:
                continue
            entry = accumulator.setdefault(uri, {"label": label, "score": 0.0})
            entry["score"] += 1.0 / (k + rank)
            # Keep the first non-empty label seen (dense usually has it).
            if not entry["label"] and label:
                entry["label"] = label

    fused = [
        FusedHit(uri=uri, label=entry["label"], score=entry["score"])
        for uri, entry in accumulator.items()
    ]
    fused.sort(key=lambda h: (-h.score, h.uri))
    return fused
