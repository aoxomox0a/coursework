import sys
import os
import re
from tqdm.asyncio import tqdm
import random
import logging
import json

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import httpx
import evaluate
from datasets import load_dataset

from src.sparql.pipeline import run_sparql_pipeline
from src.linking.pipeline import run_linking_pipeline

logging.basicConfig(level=logging.WARNING)
logging.getLogger("src.sparql.execution").setLevel(logging.CRITICAL)

CONCURRENTY_LIMIT = 10
TEST_RANGE = 1000

# global client for connection pooling
db_client = httpx.AsyncClient(
    limits=httpx.Limits(max_connections=50, max_keepalive_connections=10)
)


async def execute_sparql_async(
    query, endpoint="https://query.wikidata.org/sparql", max_retries=3
):
    """
    Executes a SPARQL query against Wikidata.
    Updated to handle 'RemoteProtocolError' (Incomplete chunked reads).
    """
    for attempt in range(max_retries):
        try:
            response = await db_client.get(
                endpoint,
                params={"query": query, "format": "json"},
                headers={
                    "User-Agent": "TextToSparqlEval/1.0 (your-email@example.edu)",
                    "Accept": "application/sparql-results+json",
                },
                timeout=45.0,
            )

            if response.status_code == 200:
                if "json" not in response.headers.get("Content-Type", ""):
                    return None
                try:
                    return (
                        json.loads(response.text, strict=False)
                        .get("results", {})
                        .get("bindings", [])
                    )
                except (json.JSONDecodeError, ValueError):
                    logging.error(f"Response Truncated for attempt {attempt + 1}")
                    continue  # Retry on truncation

            elif response.status_code in [429, 503, 504]:
                await asyncio.sleep((1 << attempt) + random.random())
                continue
            else:
                return None

        # 🌟 FIX: Add httpx.RemoteProtocolError here
        except (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.RemoteProtocolError,
        ) as e:
            logging.warning(
                f"Network/Protocol error ({type(e).__name__}) - Retrying..."
            )
            await asyncio.sleep((1 << attempt) + random.random())
            continue

    return None


def calculate_execution_metrics(
    true_data: list, predicted_data: list
) -> tuple[float, float, float]:
    """Calculates Precision, Recall, and F1 score for the execution results."""
    if true_data is None or predicted_data is None:
        return 0.0, 0.0, 0.0

    def extract_row_values(bindings):
        rows = set()
        for row in bindings:
            row_tuple = tuple(sorted((k, v.get("value", "")) for k, v in row.items()))
            rows.add(row_tuple)
        return rows

    true_set = extract_row_values(true_data)
    pred_set = extract_row_values(predicted_data)

    if not true_set and not pred_set:
        return 1.0, 1.0, 1.0

    intersection = true_set.intersection(pred_set)
    precision = len(intersection) / len(pred_set) if pred_set else 0.0
    recall = len(intersection) / len(true_set) if true_set else 0.0
    f1 = (
        (2 * precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return precision, recall, f1


def canonicalize_sparql(query: str) -> str:
    """Normalizes SPARQL queries for SP-BLEU evaluation."""
    if not query:
        return ""

    variables = re.findall(r"\?[a-zA-Z0-9_]+", query)
    var_map = {}
    counter = 0
    for var in variables:
        if var not in var_map:
            var_map[var] = f"?v{counter}"
            counter += 1

    canonical_query = query
    for orig_var, new_var in sorted(
        var_map.items(), key=lambda x: len(x[0]), reverse=True
    ):
        escaped_var = orig_var.replace("?", r"\?")
        canonical_query = re.sub(escaped_var + r"(?!\w)", new_var, canonical_query)

    canonical_query = " ".join(canonical_query.split())
    return canonical_query


async def process_single_question(item, semaphore, index, log_file):
    """Orchestrates the evaluation of a single LC-QuAD 2.0 dataset item."""
    async with semaphore:
        # LC-QuAD 2.0 column names
        question = str(item.get("question", ""))
        true_sparql = str(item.get("sparql_wikidata", ""))

        if not true_sparql or not question:
            return {
                "clean_pred": "",
                "clean_ref": "",
                "precision": 0.0,
                "recall": 0.0,
                "f1": 0.0,
                "valid_ground_truth": False,
            }

        # 1. Entity and relation link
        linking_results_list = run_linking_pipeline(question)
        linking_result = linking_results_list[0] if linking_results_list else {}

        # 2. Generate SPARQL via LLM
        pipeline_result = await run_sparql_pipeline(question, linking_result)
        predicted_sparql = pipeline_result.get("sparql_query", "")

        # 3. Canonicalize queries for SP-BLEU
        clean_pred = canonicalize_sparql(predicted_sparql)
        clean_ref = canonicalize_sparql(true_sparql)

        # 4. Fetch 'true' execution data from Wikidata
        true_data = await execute_sparql_async(true_sparql)

        precision, recall, f1 = 0.0, 0.0, 0.0

        # 5. Fetch 'predicted' execution data and compare F1
        if (
            true_data is not None
            and pipeline_result["status"] == "success"
            and predicted_sparql
        ):
            predicted_data = await execute_sparql_async(predicted_sparql)
            precision, recall, f1 = calculate_execution_metrics(
                true_data, predicted_data
            )

        results = {
            "clean_pred": clean_pred,
            "clean_ref": clean_ref,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "valid_ground_truth": true_data is not None,
        }

        with open(log_file, "a") as f:
            f.write(json.dumps(results) + "\n")

        return results


async def run_evaluation():
    log_file = "logs/lc_quad_2_eval.jsonl"
    if os.path.exists(log_file):
        os.remove(log_file)
        print(f"Cleaned up old {log_file}. Starting fresh!")

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    bleu_metric = evaluate.load("sacrebleu")

    # Load LC-QuAD 2.0 English subset
    print("Downloading LC-QuAD 2.0 dataset...")
    dataset = load_dataset("lc_quad", "v2", split="test")

    subset = dataset.select(range(TEST_RANGE))
    print(f"Evaluating {len(subset)} queries concurrently on Wikidata...")

    semaphore = asyncio.Semaphore(CONCURRENTY_LIMIT)

    tasks = [
        process_single_question(item, semaphore, i + 1, log_file)
        for i, item in enumerate(subset)
    ]

    results = await tqdm.gather(*tasks, desc="Firing tasks")

    valid_results = [res for res in results if res["valid_ground_truth"]]
    total_valid = len(valid_results)

    clean_predictions = [res["clean_pred"] for res in valid_results]
    clean_references = [[res["clean_ref"]] for res in valid_results]

    sp_bleu_results = {"score": 0.0}
    if total_valid > 0 and clean_predictions:
        sp_bleu_results = bleu_metric.compute(
            predictions=clean_predictions, references=clean_references
        )

    if total_valid > 0:
        avg_precision = sum(res["precision"] for res in valid_results) / total_valid
        avg_recall = sum(res["recall"] for res in valid_results) / total_valid
        avg_f1 = sum(res["f1"] for res in valid_results) / total_valid
    else:
        avg_precision = avg_recall = avg_f1 = 0.0

    print("\n======================================")
    print("LC-QUAD 2.0 EVALUATION RESULTS")
    print("======================================")
    print(f"SP-BLEU Score:      {sp_bleu_results['score']:.2f}")
    print(f"Average Precision:  {avg_precision:.4f}")
    print(f"Average Recall:     {avg_recall:.4f}")
    print(f"Macro F1 Score:     {avg_f1:.4f}")
    print(f"Valid Queries Eval: {total_valid}")
    print("======================================")

    await db_client.aclose()


if __name__ == "__main__":
    asyncio.run(run_evaluation())
