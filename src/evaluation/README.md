# `src/evaluation/` — Pipeline Evaluation Framework

## What it does

This module measures how well the KGQA pipeline performs on a gold test set. It runs each test question through the full pipeline, compares the output against gold-standard SPARQL and bindings, and produces a structured diagnostic report. The evaluation is **offline** — it is not part of the live API.

## Files

| File | Role |
|------|------|
| `runner.py` | Top-level orchestrator: runs all gold items through the pipeline and aggregates results |
| `trace.py` | Instrumented pipeline variant that captures first-pass and retry outcomes separately |
| `reporter.py` | Serialises `SuiteResult` to JSON and Markdown summary files under `reports/` |
| `sciqa_prep.py` | Downloads and prepares the SciQA gold test set from HuggingFace |
| `metrics/` | One file per funnel stage metric (see below) |

### `metrics/` sub-module

| File | Metric | What it measures |
|------|--------|-----------------|
| `syntax.py` | **Syntax** (stage 1) | Does the generated SPARQL parse without errors? |
| `executable.py` | **Executable** (stage 2) | Does the query run on the live endpoint without an HTTP/SPARQL error? |
| `execution_match.py` | **Execution Match** (stage 3) | Do the returned bindings match the gold bindings? |
| `algebra.py` | **Algebra Match** (stage 4) | Does the query structure match the gold SPARQL after canonicalisation? |
| `judge.py` | **LLM Judge** (optional) | Does an LLM score the NL answer as correct relative to a reference? |
| `self_correction.py` | **Self-correction lift** | How many invalid first-pass queries were repaired successfully by the retry? |

## The evaluation funnel

```
Gold test set (N questions)
        │
        ▼
  run_linking_pipeline()     ← same linking step as live API
        │
        ▼
  run_with_trace()           ← instrumented SPARQL pipeline (captures first-pass + retry)
        │
        ▼
  Funnel metrics (per item):
    Stage 1: syntax valid?
    Stage 2: query executes without error?
    Stage 3: bindings match gold?
    Stage 4: algebra matches gold SPARQL?
    (optional) LLM judge: NL answer correct?
        │
        ▼
  SuiteResult
    ├── items: tuple[ItemResult, ...]
    ├── funnel: FunnelSummary   ← counts per stage
    ├── self_correction: SelfCorrectionLift
    └── timestamp, config
```

## Running the evaluation

```bash
# Prepare gold test set (SciQA from HuggingFace)
uv run --group evaluation python scripts/evaluate_pipeline.py --prepare

# Run full evaluation (N items, judge disabled)
uv run --group evaluation python scripts/evaluate_pipeline.py

# Run with LLM judge enabled
uv run --group evaluation python scripts/evaluate_pipeline.py --judge
```

Reports are written to `reports/<timestamp>/summary.md` and `summary.json`.

## Design notes

**Serial execution.** Gold items are processed one at a time (not concurrently) to avoid hammering the shared Hactar LLM endpoint and the public ORKG SPARQL endpoint. For a 49-item test set the throughput cost is negligible.

**Instrumented trace.** `trace.py` mirrors `src/sparql/pipeline.py` step-for-step using the same primitives, so the self-correction lift can be measured without modifying the production pipeline. If the production pipeline changes shape (e.g. adds a second retry), `trace.py` must be kept in sync.

**Algebra Match is corroborative, not gating.** Execution Match (do the bindings match?) is the primary quality signal. Algebra Match adds a structural sanity check but is not used to gate success — two structurally different queries can return the same bindings.
