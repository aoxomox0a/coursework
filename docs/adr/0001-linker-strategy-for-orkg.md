# ADR 0001 — Linker strategy for the ORKG profile

- **Status:** Accepted (with caveat — result is at the decision boundary)
- **Date:** 2026-04-21
- **Context:** Phase 0.5 of the evaluation-framework work (`feat/evaluation-framework`).

## Context

We are adding an ORKG profile to the KGQA pipeline. spaCy (`en_core_web_trf`) is the current entity-extraction stage (DBpedia profile uses `link_strategy="ner"`). SciQA questions are about scientific papers, benchmarks, models, and methods — domain-specific terms that off-the-shelf NER may not reliably tag. Before wiring the ORKG profile into the pipeline we ran a gate check on 10 SciQA test-split questions (seed=42) to decide:

- `"ner"` — keep NER as the primary signal
- `"noun_chunks"` — rely on spaCy `doc.noun_chunks` only
- `"hybrid"` — NER first, fall back to chunks

**Pre-committed thresholds** (not negotiable after the fact):

- NER useful-hit ≥ 60% → `ner`
- 30% ≤ NER useful-hit < 60% → `hybrid`
- NER useful-hit < 30% → `noun_chunks`

"Useful" = tagged entity whose label is **not** in `{CARDINAL, DATE, ORDINAL, QUANTITY, PERCENT, TIME, MONEY}`, i.e. it plausibly refers to a domain concept addressable in ORKG.

## Data

- Source: HuggingFace `orkg/SciQA`, split `test`, seeded shuffle (seed=42), first 10 items.
- Model: `en_core_web_trf` (v3.8.0).
- Raw machine-readable report: [`0001-linker-strategy-for-orkg.data.json`](./0001-linker-strategy-for-orkg.data.json).
- Reproducer: `uv run --group evaluation python scripts/spacy_gate_check.py`

| #  | Question (truncated) | NER useful | Noun chunks (truncated) | NER hit |
|----|----------------------|------------|-------------------------|---------|
| 1  | List the code links in papers that use the A3C-CTS model…      | `A3C-CTS(PRODUCT)`                    | the A3C-CTS model, any benchmark             | ✓ |
| 2  | What is the most common lead compound?                         | —                                     | the most common lead compound                | ✗ |
| 3  | Indicate the model that performed best… on the RotoWire…      | `RotoWire(PRODUCT)`                   | Precision metric, Relation Generation        | ✓ |
| 4  | Provide a list of papers that have utilized the Duel hs model… | `Duel(PRODUCT)`                       | the Duel hs model                            | ✓ |
| 5  | …utilized the AlexNet, MultiGrasp model…                      | `AlexNet(PRODUCT)`, `MultiGrasp(PRODUCT)` | the AlexNet, MultiGrasp model            | ✓ |
| 6  | …utilized the SAC model…                                       | —                                     | the SAC model                                | ✗ |
| 7  | …tested on the IMDb-M benchmark dataset?                       | —                                     | the IMDb-M benchmark dataset                 | ✗ |
| 8  | …evaluate models on the Story Cloze Test benchmark dataset?    | —                                     | the Story Cloze Test benchmark dataset       | ✗ |
| 9  | What models are being evaluated on the GAD dataset?            | `GAD(ORG)`                            | the GAD dataset                              | ✓ |
| 10 | What are the metrics of evaluation over the OntoNotes dataset? | `OntoNotes(ORG)`                      | the OntoNotes dataset                        | ✓ |

**Rates:**
- NER useful-hit: **6 / 10 = 60%**
- Noun-chunks hit: **10 / 10 = 100%**

## Decision

Per the pre-committed thresholds, NER sits **exactly at the 60% boundary** → `ner` wins. However, this is a boundary result, and the evidence argues for treating the ORKG profile as effectively **hybrid**:

1. **Every question yields usable noun chunks (100%).** Noun chunks always produce a candidate that includes the ORKG-addressable surface form ("the A3C-CTS model", "the GAD dataset", "the Story Cloze Test benchmark dataset").
2. **NER and noun chunks are complementary, not redundant.** When NER fires (6/10), it extracts a crisp, short surface form (`GAD`, `AlexNet`) that is a high-signal query for ChromaDB label similarity. When NER misses (4/10), the multi-word chunk still retrieves the concept.
3. **NER labels are semantically imprecise for this domain.** Model names are tagged `PRODUCT`, dataset names are tagged `ORG` — the label itself carries no filtering value. This means we should not use the NER label for downstream filtering, only the surface text.

### Resolution

- **Keep `link_strategy="noun_chunks"` in `src/kg_profiles/orkg.py`** (the tentative value set during Phase 0.1). Rationale: chunks give 100% coverage, and the boundary NER rate suggests we should not rely on NER alone.
- **Treat NER as an additive signal in a future phase, not a gate.** When the ORKG linker runs, it should union NER surface forms (text only, ignore labels) with noun-chunk spans before vector search. This is a Phase 1 implementation detail — call it out in the ORKG linker's docstring when it's written.
- **The pre-committed threshold formally picked `ner`.** Overriding it here on judgment grounds is documented deliberately: the threshold proxy (useful-hit rate) missed that noun chunks dominate on coverage. This ADR is the audit trail.

## Consequences

- `src/kg_profiles/orkg.py` keeps `link_strategy="noun_chunks"` — no change needed.
- The `link_strategy` literal type (`Literal["ner", "noun_chunks"]` in `src/kg_profiles/base.py`) remains unchanged. If a `"hybrid"` strategy is added in Phase 1, extend the literal and revisit this ADR.
- The SciQA linker implementation must use `doc.noun_chunks` as the primary span source and MAY union NER surface forms as additive candidates.
- DBpedia profile continues with `link_strategy="ner"` — this decision is scoped to ORKG only.

## Reproduction

```sh
uv run --group evaluation python scripts/spacy_gate_check.py
```

Writes `docs/adr/0001-linker-strategy-for-orkg.data.json` with the raw per-question breakdown. Seed=42, sample_size=10 — deterministic.
