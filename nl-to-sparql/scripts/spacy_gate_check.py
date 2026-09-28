"""Phase 0.5 gate: evaluate spaCy NER vs noun_chunks usefulness on SciQA questions.

Decision thresholds (pre-committed):
- NER useful-hit rate >= 60% -> keep NER for ORKG
- 30% <= NER useful-hit rate < 60% -> hybrid
- NER useful-hit rate < 30% -> noun_chunks only
"""
import json
import random
import sys
from pathlib import Path

import spacy
from datasets import load_dataset

SEED = 42
SAMPLE_SIZE = 10
MODEL = "en_core_web_trf"

# Labels that almost never correspond to ORKG scientific concepts. Treated as
# "not useful" for the hit-rate even when tagged.
GENERIC_NER_LABELS = {"CARDINAL", "DATE", "ORDINAL", "QUANTITY", "PERCENT", "TIME", "MONEY"}


def load_sciqa_sample(seed: int, n: int) -> list[dict]:
    ds = load_dataset("orkg/SciQA", split="test")
    idxs = list(range(len(ds)))
    random.Random(seed).shuffle(idxs)
    return [ds[i] for i in idxs[:n]]


def analyze(nlp, question: str) -> dict:
    doc = nlp(question)
    ents = [{"text": e.text, "label": e.label_} for e in doc.ents]
    useful_ents = [e for e in ents if e["label"] not in GENERIC_NER_LABELS]
    chunks = [c.text for c in doc.noun_chunks]
    return {
        "question": question,
        "ner": ents,
        "ner_useful": useful_ents,
        "noun_chunks": chunks,
        "ner_hit": bool(useful_ents),
        "chunks_hit": bool(chunks),
    }


def main() -> int:
    print(f"Loading SciQA test split (seed={SEED}, n={SAMPLE_SIZE})...", file=sys.stderr)
    items = load_sciqa_sample(SEED, SAMPLE_SIZE)

    print(f"Loading spaCy model '{MODEL}'...", file=sys.stderr)
    nlp = spacy.load(MODEL)

    results = []
    for item in items:
        q = item.get("question") or item.get("paraphrased_question") or ""
        if isinstance(q, dict):
            q = q.get("string") or q.get("text") or next(iter(q.values()), "")
        if not isinstance(q, str):
            q = str(q)
        results.append(analyze(nlp, q))

    ner_hits = sum(1 for r in results if r["ner_hit"])
    chunk_hits = sum(1 for r in results if r["chunks_hit"])
    n = len(results)
    ner_rate = ner_hits / n if n else 0.0
    chunk_rate = chunk_hits / n if n else 0.0

    if ner_rate >= 0.6:
        decision = "ner"
    elif ner_rate >= 0.3:
        decision = "hybrid"
    else:
        decision = "noun_chunks"

    report = {
        "seed": SEED,
        "sample_size": n,
        "model": MODEL,
        "dataset_source": "huggingface:orkg/SciQA:test",
        "ner_useful_hit_rate": f"{ner_hits}/{n}",
        "noun_chunks_hit_rate": f"{chunk_hits}/{n}",
        "decision": decision,
        "items": results,
    }

    out_path = Path("docs/adr/0001-linker-strategy-for-orkg.data.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
