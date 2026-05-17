# `src/kg_profiles/` — Knowledge Graph Profiles

## What it does

This module provides **endpoint-specific configuration** that is injected into the SPARQL generation prompt. Each knowledge graph (DBpedia, ORKG, Wikidata, …) uses different prefix conventions, has different query style requirements, and benefits from different few-shot examples. Rather than hard-coding these differences in the prompt module, they are encapsulated in a `KGProfile` dataclass that is derived at runtime from the indexed state.

## Files

| File | Role |
|------|------|
| `base.py` | Frozen dataclasses: `KGProfile` and `OneShotExample` |
| `curated.py` | Loads hand-authored one-shot examples from `config/curated_oneshots/<slug>.json` |
| `introspection.py` | Derives prefix conventions and style hints from the ChromaDB index (i.e. what the indexing pipeline discovered about the endpoint) |
| `__init__.py` | Public entry point: `profile_from_index(endpoint)` assembles the full `KGProfile` |

## Data model

```python
KGProfile
├── slug            # e.g. "dbpedia", "orkg"
├── label           # Human-readable name
├── endpoint_url    # Full SPARQL endpoint URL
├── prefixes        # Tuple of (alias, namespace_uri) pairs
├── one_shot_examples  # Curated Q/SPARQL pairs shown to the LLM
├── label_predicate # e.g. "rdfs:label"
├── link_strategy   # "ner" or "noun_chunks" (how the linker extracts mentions)
└── query_style_hints  # Free-form strings added to the system prompt
```

## How a profile is assembled

```
profile_from_index(endpoint_url)
        │
        ├─ introspection.py   ← reads the ChromaDB index for this endpoint
        │     prefixes discovered during indexing (rdf:, rdfs:, owl:, …)
        │     label_predicate detected by discovery.py
        │
        └─ curated.py         ← reads config/curated_oneshots/<slug>.json
              hand-authored one-shot Q/SPARQL examples (verified against live endpoint)

        → merged into a frozen KGProfile
```

The profile is built on demand each time `run_sparql_pipeline()` is called. If no index exists for the endpoint (i.e. indexing has not been run yet), `profile_from_index` raises `FileNotFoundError` and the SPARQL pipeline falls back to the legacy generic prompt.

## Curated one-shot examples

One-shot examples live in [`config/curated_oneshots/`](../../config/curated_oneshots/README.md). Each file is a JSON array of `{question, entity_uris, property_uri, sparql, tags}` objects. The `tags` field may include `"placeholder"` to mark examples whose URIs have not been verified against the live endpoint.

## Link strategy

The `link_strategy` field tells the linking pipeline which extraction method to use for a given endpoint:

| Value | Method | Best for |
|-------|--------|---------|
| `"ner"` | spaCy named entity recognition | General KGs like DBpedia where NER tags are semantically meaningful |
| `"noun_chunks"` | spaCy noun chunk extraction | Scientific KGs like ORKG where NER coverage is limited (~60%) |

See [`docs/adr/0001-linker-strategy-for-orkg.md`](../../docs/adr/0001-linker-strategy-for-orkg.md) for the empirical analysis behind this choice.
