# `src/sparql/` — SPARQL Generation & Execution

## What it does

This module takes the output of the linking pipeline (entity URIs + relation candidates) and turns it into an executable SPARQL query. It handles LLM prompt construction, query validation with automatic retry, query execution on the target endpoint, and natural language answer synthesis.

## Files

| File | Role |
|------|------|
| `pipeline.py` | Top-level orchestrator — wires prompt → LLM → validate → execute → answer |
| `prompt.py` | LLM prompt templates: legacy template (no profile) and profile-aware template |
| `llm.py` | HTTP client for the Hactar/HuggingFace inference endpoint; extracts SPARQL from fenced responses |
| `validation.py` | SPARQL syntax checker via `rdflib`; returns `(is_valid, error_message)` |
| `execution.py` | Sends validated queries to the SPARQL endpoint; formats raw bindings into readable text |

## The pipeline (in order)

```
question + linking_result + endpoint
          │
          ▼
  _load_profile_or_none()    ← KGProfile if endpoint was indexed, else None
          │
          ▼
  prompt.generate_sparql_prompt()   ← legacy or profile-aware template
          │
          ▼
  llm.call_llm()             ← HTTP call to inference server
  llm.extract_sparql_from_response()
          │
          ▼
  get_required_prefixes()    ← auto-prepend wd:/wdt:/dbo:/dbr: if missing
          │
          ▼
  validation.is_valid_sparql()
      │
      ├─ valid → execute
      │
      └─ invalid → generate_fix_sparql_prompt() → call_llm() → re-validate
                       │
                       ├─ valid → execute
                       └─ invalid → return error
          │
          ▼
  execution.execute_and_format()   ← runs query, formats bindings
          │
          ▼
  prompt.generate_answer_prompt()  ← synthesises NL answer
  llm.call_llm()
          │
          ▼
  SparqlPipelineResult {status, answer, sparql_query, error_message}
```

## Two prompt templates

| Template | When used | Description |
|----------|-----------|-------------|
| `SPARQL_GENERATION_TEMPLATE` | No `KGProfile` available | Generic template with a DBpedia one-shot example; works on any endpoint |
| `SPARQL_PROFILE_TEMPLATE` | `KGProfile` present | Injects endpoint-specific prefixes, style hints, and curated one-shot examples from `kg_profiles/` |

The profile template is more accurate because it shows the LLM concrete examples in the exact SPARQL dialect of the target endpoint (e.g., ORKG uses full URIs and `OPTIONAL` chains that differ from DBpedia style).

## Automatic prefix injection

`get_required_prefixes()` scans the generated query for common prefix aliases (`wd:`, `wdt:`, `dbo:`, `dbr:`, etc.) and prepends their `PREFIX` declarations if they were not declared by the LLM. This catches a common LLM failure mode where the query uses a prefix alias but omits its declaration.

## Self-correction loop

When the first SPARQL attempt fails syntax validation, a second prompt is built with `generate_fix_sparql_prompt()` that includes the invalid query and the parser error. The LLM attempts one repair. If the repaired query is still invalid, the pipeline returns an error rather than executing a broken query.

See [`docs/adr/0001-linker-strategy-for-orkg.md`](../../docs/adr/0001-linker-strategy-for-orkg.md) for the broader context on the ORKG profile design.
