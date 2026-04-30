"""Lazy in-memory BM25 index over a ChromaDB collection's labels.

Used as the lexical half of a hybrid retrieval (BM25 + dense embeddings, fused
via RRF) — this compensates for MiniLM's weakness on terse vs verbose labels,
which is what was masking ORKG's canonical SciQA predicates (HAS_DATASET,
HAS_BENCHMARK, HAS_METRIC, …) under a flood of empty-label / system-noise
entries in the dense ranking.

Index build is lazy: the first query against a (scoped) collection pulls all
``(uri, label)`` pairs from ChromaDB, drops entries with empty label (they
carry no lexical signal and only add noise), tokenises labels, and builds a
``BM25Okapi``. Result is cached for the process lifetime.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from rank_bm25 import BM25Okapi


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase + alphanumeric word split. Empty string → empty list."""
    if not text:
        return []
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]


@dataclass(frozen=True)
class BM25Hit:
    uri: str
    label: str
    score: float
    rank: int  # 1-based


class BM25Index:
    """In-memory BM25 over a list of (uri, label) docs.

    Docs with empty label are filtered out at build time — pure URI fragments
    aren't natural language and only pollute IDF. Their dense-embedding rank
    still reaches the fusion layer.
    """

    def __init__(self, docs: Iterable[tuple[str, str]]) -> None:
        kept = [(u, l) for u, l in docs if l]
        self._uris: list[str] = [u for u, _ in kept]
        self._labels: list[str] = [l for _, l in kept]
        self._tokenised: list[list[str]] = [tokenize(l) for l in self._labels]
        # rank_bm25 chokes on an empty corpus — guard with a sentinel doc that
        # can never match a real query (no alphanumerics).
        if not self._tokenised:
            self._tokenised = [["__empty__"]]
            self._uris = [""]
            self._labels = [""]
        self._bm25 = BM25Okapi(self._tokenised)

    @property
    def size(self) -> int:
        return len(self._uris) if self._uris != [""] else 0

    def query(self, text: str, top_n: int = 20) -> list[BM25Hit]:
        """Return up to ``top_n`` hits ranked by BM25 score (descending).

        Hits with score == 0 are dropped — they carry no lexical signal.
        """
        tokens = tokenize(text)
        if not tokens or self.size == 0:
            return []

        scores = self._bm25.get_scores(tokens)
        indexed = [(i, s) for i, s in enumerate(scores) if s > 0]
        indexed.sort(key=lambda x: x[1], reverse=True)

        hits: list[BM25Hit] = []
        for rank, (i, score) in enumerate(indexed[:top_n], start=1):
            hits.append(
                BM25Hit(uri=self._uris[i], label=self._labels[i], score=float(score), rank=rank)
            )
        return hits


# --- Lazy per-collection cache ------------------------------------------------

_INDEX_CACHE: dict[str, BM25Index] = {}


def _load_docs_from_chroma(scoped_collection_name: str) -> list[tuple[str, str]]:
    """Pull (uri, label) tuples from a ChromaDB collection. Lazy import keeps
    this module testable without a live ChromaDB."""
    from src.indexing.chroma_storage import _get_client  # local import

    client = _get_client()
    collection = client.get_collection(scoped_collection_name)
    raw = collection.get(include=["metadatas"])
    metadatas = raw.get("metadatas") or []
    return [
        (m.get("uri", ""), m.get("label", ""))
        for m in metadatas
        if isinstance(m, dict)
    ]


def get_bm25_index(scoped_collection_name: str) -> BM25Index:
    """Return (and cache) the BM25 index for a scoped ChromaDB collection."""
    cached = _INDEX_CACHE.get(scoped_collection_name)
    if cached is not None:
        return cached
    docs = _load_docs_from_chroma(scoped_collection_name)
    index = BM25Index(docs)
    _INDEX_CACHE[scoped_collection_name] = index
    return index


def clear_cache() -> None:
    """Drop all cached BM25 indices. Test-only helper."""
    _INDEX_CACHE.clear()
