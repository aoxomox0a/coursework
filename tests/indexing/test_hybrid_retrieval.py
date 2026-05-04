"""Unit tests for src/indexing/hybrid_retrieval.py — pure function, no I/O."""
from src.indexing.hybrid_retrieval import reciprocal_rank_fusion, FusedHit


def test_rrf_empty_input_returns_empty():
    assert reciprocal_rank_fusion([]) == []
    assert reciprocal_rank_fusion([[], []]) == []


def test_rrf_single_list_preserves_order():
    docs = [("a", "A"), ("b", "B"), ("c", "C")]
    fused = reciprocal_rank_fusion([docs])
    assert [h.uri for h in fused] == ["a", "b", "c"]


def test_rrf_item_in_both_lists_outranks_item_in_one():
    """Classic RRF guarantee: appearing in both rankers beats appearing in one."""
    dense = [("a", "A"), ("b", "B"), ("c", "C")]
    lexical = [("c", "C"), ("d", "D")]
    fused = reciprocal_rank_fusion([dense, lexical])
    uris = [h.uri for h in fused]
    # 'c' is in both: dense rank 3 → 1/63, lexical rank 1 → 1/61. Sum ~ 0.0322
    # 'a' only in dense rank 1 → 1/61. 'b' only dense rank 2 → 1/62. 'd' only
    # lexical rank 2 → 1/62.
    # So expected order: c (~0.0322), a (~0.0164), b (~0.0161), d (~0.0161).
    assert uris[0] == "c"


def test_rrf_score_uses_k_60_default():
    """Single item, single list, rank 1 → score = 1/(60+1)."""
    fused = reciprocal_rank_fusion([[("a", "A")]])
    assert len(fused) == 1
    assert abs(fused[0].score - 1 / 61) < 1e-12


def test_rrf_keeps_first_nonempty_label():
    """Dense often carries the label; BM25 path may pass empty. RRF must
    surface the non-empty one regardless of input order."""
    dense = [("uri:1", "the label")]
    lexical = [("uri:1", "")]
    fused = reciprocal_rank_fusion([lexical, dense])
    assert fused[0].label == "the label"


def test_rrf_skips_empty_uri():
    docs = [("", "X"), ("a", "A")]
    fused = reciprocal_rank_fusion([docs])
    assert [h.uri for h in fused] == ["a"]


def test_rrf_returns_fused_hits():
    fused = reciprocal_rank_fusion([[("a", "A")]])
    assert isinstance(fused[0], FusedHit)
