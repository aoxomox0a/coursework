# `src/` — Core Application Logic

This folder contains all the Python packages that implement the pipeline. Each subfolder is an independent module with a single responsibility.

## Modules

| Folder | What it does |
|--------|--------------|
| [`indexing/`](indexing/README.md) | Connects to a SPARQL endpoint, fetches entities/properties/classes, generates embeddings, and stores them in ChromaDB |
| [`linking/`](linking/README.md) | Extracts entity mentions and relations from a natural language question, then maps them to URIs in the index |
| [`sparql/`](sparql/README.md) | Builds LLM prompts, calls the LLM to generate SPARQL, validates syntax, executes queries, and synthesises NL answers |
| [`evaluation/`](evaluation/README.md) | 4-stage diagnostic evaluation funnel for measuring pipeline quality on a gold test set |
| [`kg_profiles/`](kg_profiles/README.md) | Per-endpoint knowledge graph profiles: registered prefixes, one-shot examples, query style hints |

## How the modules connect

```
Question (NL)
     │
     ▼
  linking/          ← extracts entities + relations, returns URIs
     │
     ▼
  sparql/           ← builds prompt from URIs, calls LLM, validates, executes
     │
     ▼
  Answer (NL)

  indexing/         ← run once per endpoint to build the ChromaDB index
  kg_profiles/      ← provides endpoint-specific metadata to sparql/ at prompt time
  evaluation/       ← run offline to score the pipeline against a gold test set
```
