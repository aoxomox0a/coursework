import sys
import os
import re
from tqdm.asyncio import tqdm
import random
import logging

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
TEST_RANGE = 300

# global client for connection pooling
db_client = httpx.AsyncClient(
    limits=httpx.Limits(max_connections=50, max_keepalive_connections=10)
)


async def execute_sparql_async(
    query, endpoint="https://dbpedia.org/sparql", max_retries=3
):
    """
    Executes a SPARQL query against the DBpedia endpoint.
    Fetches and returns the bindings list for comparison.
    """
    for attempt in range(max_retries):
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
                return response.json().get("results", {}).get("bindings", [])
            elif response.status_code in [429, 503, 504, 500]:
                # Server is overwhelmed, use exponential backoff to calcualte waiting time
                base_wait = 1 << attempt
                # add jitter so concurrent reqs dont hit server at same time
                wait_time = base_wait + random.random()

                logging.warning(
                    f"DBpedia {response.status_code} - Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
                continue
            else:
                return None  # Bad query syntax, don't retry

        except (httpx.ReadTimeout, httpx.ConnectError) as e:
            wait_time = 2**attempt
            logging.warning(f"Connection error. Retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)

    return None  # Failed after all retries


def calculate_execution_metrics(
    true_data: list, predicted_data: list
) -> tuple[float, float, float]:
    """
    Calculates Precision, Recall, and F1 score for the execution results.
    Converts JSON bindings into sets of tuples to perform set math.
    """
    if true_data is None or predicted_data is None:
        return 0.0, 0.0, 0.0

    def extract_row_values(bindings):
        rows = set()
        for row in bindings:
            # Sort by key to ensure tuple order is consistent across dicts
            row_tuple = tuple(sorted((k, v.get("value", "")) for k, v in row.items()))
            rows.add(row_tuple)
        return rows

    true_set = extract_row_values(true_data)
    pred_set = extract_row_values(predicted_data)

    if not true_set and not pred_set:
        return 1.0, 1.0, 1.0  # Both correctly returned empty results

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
    """
    Normalizes SPARQL queries for SP-BLEU evaluation.
    1. Replaces all variables with ?v0, ?v1, ?v2...
    2. Normalizes all whitespace.
    """
    if not query:
        return ""

    # Find all variables (e.g., ?actor, ?movie)
    variables = re.findall(r"\?[a-zA-Z0-9_]+", query)

    # Create a mapping of original variables to ?v0, ?v1
    var_map = {}
    counter = 0
    for var in variables:
        if var not in var_map:
            var_map[var] = f"?v{counter}"
            counter += 1

    canonical_query = query

    # Replace variables in the query (sort by length descending)
    for orig_var, new_var in sorted(
        var_map.items(), key=lambda x: len(x[0]), reverse=True
    ):
        escaped_var = orig_var.replace("?", r"\?")
        canonical_query = re.sub(escaped_var + r"(?!\w)", new_var, canonical_query)

    # Normalize all formatting, tabs, and line breaks into single spaces
    canonical_query = " ".join(canonical_query.split())

    return canonical_query


async def process_single_question(item, semaphore, index, log_file):
    """
    Orchestrates the evaluation of a single dataset item.
    """
    async with semaphore:
        question = item["question"]
        true_sparql = item["sparql_dbpedia18"]

        # print(f"Starting Query {index}: {question[:50]}...")

        # 1. Entity and relation link
        linking_results_list = run_linking_pipeline(question)
        linking_result = linking_results_list[0] if linking_results_list else {}

        # 2. Generate SPARQL via LLM
        pipeline_result = await run_sparql_pipeline(question, linking_result)
        predicted_sparql = pipeline_result.get("sparql_query", "")

        # 3. Canonicalize queries for SP-BLEU string comparison
        clean_pred = canonicalize_sparql(predicted_sparql)
        clean_ref = canonicalize_sparql(true_sparql)

        # 4. Fetch 'true' execution data
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

        # print(f"Finished Query {index} | F1: {f1:.2f}")

        results = {
            "clean_pred": clean_pred,
            "clean_ref": clean_ref,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "valid_ground_truth": true_data is not None,
        }

        import json

        with open(log_file, "a") as f:
            f.write(json.dumps(results) + "\n")

        return results


async def run_evaluation():
    # Load SP-BLEU string metric
    log_file = "logs/lc_quad_eval.jsonl"
    if os.path.exists(log_file):
        os.remove(log_file)
        print(f"Cleaned up old {log_file}. Starting fresh!")

    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    bleu_metric = evaluate.load("sacrebleu")
    print("Downloading dataset...")
    dataset = load_dataset("lc_quad", split="test")

    subset = dataset.select(range(TEST_RANGE))
    print(f"Evaluating {len(subset)} queries concurrently...")

    semaphore = asyncio.Semaphore(CONCURRENTY_LIMIT)

    tasks = [
        process_single_question(item, semaphore, i + 1, log_file)
        for i, item in enumerate(subset)
    ]

    print("Firing off tasks...")
    results = await tqdm.gather(*tasks, desc="Firing tasks")

    # Filter out queries where the DBpedia endpoint failed on the ground truth
    valid_results = [res for res in results if res["valid_ground_truth"]]
    total_valid = len(valid_results)

    # Extract clean strings for SP-BLEU evaluation
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
    print("SCIENTIFIC EVALUATION RESULTS")
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
