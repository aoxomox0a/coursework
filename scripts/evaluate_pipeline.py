import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import httpx
import evaluate
from datasets import load_dataset

from src.sparql.pipeline import run_sparql_pipeline
from src.linking.pipeline import run_linking_pipeline

CONCURRENTY_LIMIT = 10
TEST_RANGE = 100


# global client for connection pooling
db_client = httpx.AsyncClient(
    limits=httpx.Limits(max_connections=50, max_keepalive_connections=10)
)


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


def compare_execution_results(true_data, predicted_data):
    # performs a semantic comparison of query results
    # checks if both queries returned the exact same data rows
    if true_data is None or predicted_data is None:
        return False
    if len(true_data) != len(predicted_data):
        return False
    return true_data == predicted_data


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
    )

    print("\n======================================")
    print("EVALUATION RESULTS")
    print("======================================")
    print(f"BLEU Score:         {bleu_results['score']:.2f}")
    print(
        f"Execution Accuracy: {execution_accuracy:.2f}% ({execution_correct}/{total_valid_queries})"
    )
    print("======================================")

    await db_client.aclose()


if __name__ == "__main__":
    asyncio.run(run_evaluation())
