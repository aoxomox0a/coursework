"""
Evaluate the KGQA pipeline against the SciQA gold set.

For each gold item:
  1. Run the linking pipeline (NER + noun chunks + ChromaDB).
  2. Run the instrumented SPARQL pipeline (first pass + fix-prompt retry).
  3. Score the final query against gold via the four funnel metrics:
     syntax → executable → execution match → algebra match.
  4. Optionally call the LLM-as-a-Judge over the formatted answer.

Aggregates into reports/<run-id>/results.json and summary.md.

Usage:
  uv run --group evaluation python scripts/evaluate_pipeline.py
  uv run --group evaluation python scripts/evaluate_pipeline.py --limit 5
  uv run --group evaluation python scripts/evaluate_pipeline.py --judge
"""
import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make src/ importable when this script is invoked from anywhere.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.evaluation.reporter import write_report
from src.evaluation.runner import run_evaluation

logger = logging.getLogger("evaluate_pipeline")

DEFAULT_GOLD = Path("data/gold/orkg_sciqa.jsonl")


def _load_gold(path: Path) -> list[dict]:
    items: list[dict] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line:
            items.append(json.loads(line))
    return items


def _print_summary(suite) -> None:
    f = suite.funnel
    sc = suite.self_correction
    print()
    print("=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"Total items: {f.total}")
    print()
    print("Funnel:")
    print(f"  Syntax valid       {f.syntax_valid}/{f.total}")
    print(f"  Executable         {f.executable_ok}/{f.total}")
    print(f"  Execution match    {f.execution_match}/{f.total}")
    print(f"  Algebra match      {f.algebra_match}/{f.total}  (corroborative)")
    print()
    print("Self-correction lift:")
    print(f"  First-pass valid   {sc.first_pass_valid_count}/{sc.total}  ({sc.first_pass_rate*100:.1f}%)")
    print(f"  After retry        {sc.after_retry_valid_count}/{sc.total}  ({sc.after_retry_rate*100:.1f}%)")
    print(f"  Recovered by retry {sc.recovered_by_retry}")
    print("=" * 60)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, default=DEFAULT_GOLD,
                        help="Path to the gold-set JSONL")
    parser.add_argument("--limit", type=int, default=None,
                        help="Evaluate only the first N items (for smoke testing)")
    parser.add_argument("--judge", action="store_true",
                        help="Run the LLM-as-a-Judge over each answer (cost-sensitive)")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="Where to write results.json + summary.md "
                             "(default: reports/<UTC-timestamp>)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    if not args.verbose:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)

    if not args.gold.exists():
        logger.error("Gold set not found at %s — run scripts/prepare_sciqa_gold.py first.", args.gold)
        return 1

    items = _load_gold(args.gold)
    if args.limit is not None:
        items = items[: args.limit]
    logger.info("Evaluating %d items (judge=%s)", len(items), args.judge)

    if args.out_dir is None:
        run_id = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S")
        args.out_dir = Path("reports") / run_id

    config = {
        "gold_path": str(args.gold),
        "item_count": len(items),
        "judge_enabled": args.judge,
    }
    suite = await run_evaluation(items, judge_enabled=args.judge, config=config)

    write_report(suite, args.out_dir)
    logger.info("Wrote report to %s", args.out_dir)
    _print_summary(suite)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
