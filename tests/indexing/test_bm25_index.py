"""Unit tests for src/indexing/bm25_index.py — pure in-memory, no ChromaDB."""
from src.indexing.bm25_index import BM25Index, BM25Hit, tokenize


def test_tokenize_lowercases_and_splits_on_non_alnum():
    assert tokenize("Has Dataset!") == ["has", "dataset"]
    assert tokenize("URI/with-Punct.123") == ["uri", "with", "punct", "123"]
    assert tokenize("") == []
    assert tokenize("   ") == []


def test_bm25index_returns_empty_on_empty_corpus():
    idx = BM25Index([])
    assert idx.size == 0
    assert idx.query("anything") == []


def test_bm25index_ignores_empty_label_docs():
    docs = [
        ("uri:1", ""),
        ("uri:2", "has dataset"),
        ("uri:3", ""),
    ]
    idx = BM25Index(docs)
    assert idx.size == 1


def test_bm25index_ranks_lexical_overlap_first():
    """The label with the most overlap with the query wins."""
    docs = [
        ("uri:dataset", "has dataset"),
        ("uri:benchmark", "has benchmark"),
        ("uri:other", "model name"),
    ]
    idx = BM25Index(docs)
    hits = idx.query("dataset", top_n=3)
    assert len(hits) >= 1
    assert hits[0].uri == "uri:dataset"
    assert hits[0].rank == 1
    assert hits[0].score > 0


def test_bm25index_drops_zero_score_hits():
    """A query with no token overlap returns no hits at all."""
    docs = [("uri:1", "has dataset"), ("uri:2", "has benchmark")]
    idx = BM25Index(docs)
    hits = idx.query("xylophone", top_n=10)
    assert hits == []


def test_bm25index_returns_at_most_top_n():
    docs = [(f"uri:{i}", f"dataset entry {i}") for i in range(20)]
    idx = BM25Index(docs)
    hits = idx.query("dataset", top_n=5)
    assert len(hits) == 5
    assert all(isinstance(h, BM25Hit) for h in hits)


def test_bm25index_surfaces_target_predicate_in_realistic_question():
    """The exact case that was broken on the live ORKG endpoint:
    'has dataset' must surface for a long question containing 'dataset'."""
    docs = [
        ("uri:HAS_DATASET", "has dataset"),
        ("uri:HAS_BENCHMARK", "has benchmark"),
        ("uri:HAS_MODEL", "has model"),
        ("uri:P123004", "benchmarked datasets"),
        ("uri:P105016", "model name"),
        # noise
        ("uri:noise1", "ownerUser"),
        ("uri:noise2", "qmfBoolTmpl"),
    ]
    idx = BM25Index(docs)
    hits = idx.query(
        "What models are being evaluated on the FTD dataset?", top_n=5
    )
    uris = [h.uri for h in hits]
    # Token overlap: "dataset" ∈ query → HAS_DATASET ranks. "models" doesn't
    # stem-match "model" without a stemmer, so HAS_MODEL/P105016 may not
    # surface — that's fine, it's BM25's job to do exact lexical, not stemmed.
    assert "uri:HAS_DATASET" in uris
    assert hits[0].uri == "uri:HAS_DATASET"
