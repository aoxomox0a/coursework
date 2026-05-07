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


async def execute_sparql_async(query, endpoint):
    # executes sparql query against dbpedia endpoint
    # fetches and returns the bindings list for comparions
    try:
        response = await db_client.get(
            endpoint,
            params={"query": query, "format": "json"},
            headers={
                "User-Agent": "NL-to-SPARQL-Eval/1.0",
                "Accept": "application/sparql-results+json",
            },
            timeout=30.0,
        )

        if response.status_code == 200:
            # we extract the 'bindings' list specifically for comparison
            return response.json().get("results", {}).get("bindings", [])

        print(f"DBpedia returned {response.status_code} for query")
        return None

    except Exception as e:
        print(f"DBpedia Connection Error: {e}")
        return None

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

async def process_single_question(item, semaphore, index, endpoint):
    # orchestrates the evaluation of a single dataset item.
    # uses a semaphore to regulate the number of parallel tasks.
    async with semaphore:
        question = item["question"]
        true_sparql = item["sparql_dbpedia18"]

        print(f"Starting Query {index}: {question[:50]}...")

        # entity and relation link
        linking_results_list = run_linking_pipeline(question, endpoint)
        linking_result = linking_results_list[0] if linking_results_list else {}

        # generate sparql via llm
        pipeline_result = await run_sparql_pipeline(question, linking_result)
        predicted_sparql = pipeline_result.get("sparql_query", "")

        # fetch "true" data
        true_data = await execute_sparql_async(true_sparql, endpoint)
        is_match = False

        # fetch "predicted" data and compare
        if (
            true_data is not None
            and pipeline_result["status"] == "success"
            and predicted_sparql
        ):
            predicted_data = await execute_sparql_async(predicted_sparql, endpoint)
            is_match = compare_execution_results(true_data, predicted_data)

        print(f"Finished Query {index} | Match: {is_match}")

        return {
            "prediction": predicted_sparql,
            "reference": true_sparql,
            "is_match": is_match,
            "valid_ground_truth": true_data is not None,
        }


async def run_evaluation():
    endpoint = "https://dbpedia.org/sparql"
    # main evaluation loop
    # load data, run tasks concurrently
    # compute final BLEU and accuracy metrics
    bleu_metric = evaluate.load("sacrebleu")

    print("Downloading dataset...")
    dataset = load_dataset("lc_quad", split="test")

    subset = dataset.select(range(TEST_RANGE))
    print(f"Evaluating {len(subset)} queries concurrently...")

    # set concurrency limit
    semaphore = asyncio.Semaphore(CONCURRENTY_LIMIT)

    # create a list of async tasks
    tasks = [
        process_single_question(item, semaphore, i + 1, endpoint)
        for i, item in enumerate(subset)
    ]

    # fire all off at once
    print("Firing off tasks...")
    results = await asyncio.gather(*tasks)

    # sum up results
    predictions = [res["prediction"] for res in results]
    references = [[res["reference"]] for res in results]

    execution_correct = sum(1 for res in results if res["is_match"])
    total_valid_queries = sum(1 for res in results if res["valid_ground_truth"])

    print("\nComputing final metrics...")
    bleu_results = bleu_metric.compute(predictions=predictions, references=references)
    execution_accuracy = (
        (execution_correct / total_valid_queries) * 100
        if total_valid_queries > 0
        else 0
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
