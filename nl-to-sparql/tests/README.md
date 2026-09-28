# `tests/` — Test Suite

## Structure

The test tree mirrors `src/` and `api/`, with one folder per module:

```
tests/
├── indexing/        # ChromaDB storage, discovery, BM25, hybrid retrieval
├── linking/         # Entity extraction, entity linking, relation linking
├── sparql/          # Prompt generation, LLM extraction, validation, execution, API
├── evaluation/      # Runner, trace, reporter, SciQA preparation, metrics
└── kg_profiles/     # Profile base dataclasses, curated loader, introspection
```

## Running the tests

```bash
# Full suite
uv run pytest

# Single module
uv run pytest tests/sparql/

# With coverage report
uv run pytest --cov=src --cov-report=term-missing

# Evaluation-group tests (heavier, require HuggingFace access)
uv run --group evaluation pytest tests/evaluation/
```

## Test categories

| Module | What is tested |
|--------|---------------|
| `indexing/` | BM25 index build/search, ChromaDB storage operations, endpoint discovery queries, hybrid retrieval score fusion |
| `linking/` | NER extraction, noun-chunk extraction, ChromaDB entity lookup, relation candidate selection |
| `sparql/` | Prompt template rendering (legacy + profile), SPARQL extraction from LLM output, syntax validation, query execution formatting, full API endpoint integration |
| `evaluation/` | Funnel metric computation (syntax, execution match, algebra match, judge), trace capture, report serialisation, SciQA dataset preparation |
| `kg_profiles/` | `KGProfile` and `OneShotExample` frozen-dataclass invariants, curated JSON loading, profile introspection from ChromaDB |

## Test philosophy

- Tests use **mocks** for external I/O (LLM HTTP calls, SPARQL endpoint calls, ChromaDB). Real network calls are not made in CI.
- Evaluation tests that require live endpoints or HuggingFace downloads are guarded by a `--group evaluation` marker and excluded from the default `pytest` run.
- Each test file is co-located with a matching `conftest.py` (where fixtures are needed) to keep fixture scope local.
