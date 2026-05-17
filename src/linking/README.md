# `src/linking/` — Entity & Relation Linking

## What it does

Given a natural language question, this module identifies **which entities and relations** are mentioned, then maps them to exact URIs in the ChromaDB index. Its output is the input to the SPARQL generation step.

Example:
```
Question: "Who directed Inception?"
→ Entities:  [<http://dbpedia.org/resource/Inception>]
→ Relation:  <http://dbpedia.org/ontology/director>
→ Candidates: [director, producer, writer, ...]
```

## Files

| File | Role |
|------|------|
| `pipeline.py` | Top-level function `run_linking_pipeline(questions, endpoint)` — orchestrates all steps |
| `entity_extraction.py` | Extracts candidate mentions from text using NER, noun phrases, and noun chunks |
| `entity_linking.py` | Maps extracted mentions to URIs by querying ChromaDB embeddings |
| `relation_linking.py` | Finds the most likely graph predicates for the question using hybrid retrieval |
| `spacy_setup.py` | Loads and caches the spaCy language model |

## The linking pipeline

```
question (string)
      │
      ▼
  spaCy parse (spacy_setup.py)
      │
      ├─ entity_extraction.py
      │     extract_entities()      ← standard NER (persons, orgs, locations)
      │     extract_noun_phrases()  ← noun phrases (e.g. "open research knowledge graph")
      │     extract_noun_chunks()   ← noun chunks (broader coverage)
      │     combine_candidates()    ← union of all three, deduplicated
      │
      ├─ entity_linking.py
      │     link_entities()         ← query ChromaDB "entities" collection
      │     disambiguate_entities() ← pick the best URI per mention
      │
      └─ relation_linking.py
            find_relation_candidates()  ← top-10 from "properties" collection
            select_relation()           ← pick the single best predicate

Output: {"question": ..., "entities": [...], "relation": {...}, "relation_candidates": [...]}
```

## Why three extraction strategies?

NER alone only covers ~60% of relevant entities on ORKG-style questions (e.g. "What datasets benchmark transformer models?" has no named entities in the NER sense). Noun phrases and noun chunks add broad coverage as a fallback. All three are unioned and deduplicated — so a phrase caught by NER doesn't appear twice.

## Why top-10 relation candidates?

Predicates with short or technical labels (e.g. `HAS_DATASET`, `P32`) tend to rank lower under embedding similarity because they're harder to match to natural language. Keeping 10 candidates rather than just the top 1 ensures these don't get dropped. The LLM receives all 10 and picks the most relevant one when generating the SPARQL query.

See [`docs/adr/0001-linker-strategy-for-orkg.md`](../../docs/adr/0001-linker-strategy-for-orkg.md) for the full strategy decision record.
