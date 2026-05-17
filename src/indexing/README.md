# `src/indexing/` — Knowledge Graph Indexing

## What it does

This module fetches schema data from a SPARQL endpoint and stores it as searchable vector embeddings in ChromaDB. It runs **once per endpoint** (or whenever you want to refresh the index) before questions can be answered.

The index is what allows the linking module to map natural language mentions ("machine learning") to exact graph URIs (`<http://dbpedia.org/resource/Machine_learning>`).

## Files

| File | Role |
|------|------|
| `pipeline.py` | Top-level orchestrator — runs all steps in sequence |
| `endpoint.py` | SPARQL endpoint connection, testing, and endpoint-agnostic discovery |
| `discovery.py` | Probes the endpoint to detect label predicates, typing conventions, and language tag usage |
| `entities.py` | Fetches entities, properties, and classes from the endpoint in paginated batches |
| `embedding.py` | Loads the SentenceTransformer model and generates vector embeddings |
| `chroma_storage.py` | Stores and retrieves embedded data in ChromaDB collections |
| `hybrid_retrieval.py` | Combines dense (embedding) and sparse (BM25) retrieval for better coverage |
| `bm25_index.py` | Sparse BM25 keyword index for entities/properties |
| `indexing_state.py` | Tracks whether indexing is in progress (used by the API to return 202 during background runs) |

## The indexing pipeline (in order)

```
run_indexing_pipeline(endpoint)
        │
        ├─ 1. test_connection()          ← can we reach the endpoint?
        │
        ├─ 2. discover_profile()         ← what label predicates / typing does it use?
        │         (saved to disk for use by kg_profiles/)
        │
        ├─ 3. fetch_properties()         ← all predicates in the graph
        │    fetch_classes()             ← all class URIs
        │    fetch_entities_batch()      ← entities, paginated
        │
        ├─ 4. embed_entities()           ← SentenceTransformer → vectors
        │
        └─ 5. store_entities_in_chroma() ← 3 ChromaDB collections:
                                            "entities", "properties", "classes"
```

## ChromaDB collections

Three separate collections are created per endpoint:

- **entities** — named resources (people, places, papers, …)
- **properties** — predicates / relationships (`dbo:director`, `orkgp:HAS_DATASET`, …)
- **classes** — type hierarchy (`dbo:Film`, `orkgc:Paper`, …)

Each item is stored with its URI, label, and embedding vector. Lookups return the top-k most similar items to a query string.

## Key design decision: endpoint-agnostic discovery

Different endpoints use different conventions:
- DBpedia uses `rdfs:label`; ORKG uses `rdfs:label` too but with different tag requirements
- DBpedia types with `rdf:type`; ORKG uses a different typing predicate

The `discovery.py` module probes the endpoint before indexing to detect these conventions automatically. This is what makes the system work on DBpedia, Wikidata, and ORKG without manual configuration.

See [`docs/adr/0001-linker-strategy-for-orkg.md`](../../docs/adr/0001-linker-strategy-for-orkg.md) for the full design rationale.
