"""
Evaluate SPARQL → Natural Language generation using LC-QuAD dataset in reverse.

For each sample:
  - Input: gold SPARQL query (sparql_dbpedia18)
  - Gold target: original question
  - Model output: generated natural language question via /generate-nl endpoint
  - Metrics: semantic similarity, BLEU, ROUGE, optional LLM judge

Usage:
  uv run --group evaluation python scripts/evaluate_sparql_to_nl.py
  uv run --group evaluation python scripts/evaluate_sparql_to_nl.py --limit 10
  uv run --group evaluation python scripts/evaluate_sparql_to_nl.py --judge
  uv run --group evaluation python scripts/evaluate_sparql_to_nl.py -v
"""

import sys
import os
import json
import logging
import argparse
import re
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from dataclasses import dataclass
from typing import Optional

import httpx
import evaluate
from tqdm.asyncio import tqdm
from datasets import load_dataset

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("evaluate_sparql_to_nl")

# Configuration
GENERATE_NL_ENDPOINT = "http://localhost:8000/api/sparql/generate-nl"
CONCURRENCY_LIMIT = 10
TEST_RANGE = 50  # Number of queries to evaluate
LOG_DIR = Path("logs")
EVAL_LOG_FILE = LOG_DIR / "sparql_to_nl_eval.jsonl"
SUMMARY_FILE = LOG_DIR / "sparql_to_nl_summary.json"

# Load metrics once
bleu_metric = evaluate.load("sacrebleu")
rouge_metric = evaluate.load("rouge")


@dataclass
class SampleResult:
    """Result for a single SPARQL→NL sample."""
    sample_id: int
    gold_sparql: str
    gold_question: str
    generated_question: Optional[str]
    generation_error: Optional[str]
    bleu_score: Optional[float]
    rouge1_score: Optional[float]
    rouge2_score: Optional[float]
    rougeL_score: Optional[float]
    semantic_similarity: Optional[float]
    judge_score: Optional[dict]
    is_valid: bool


def canonicalize_nl(text: str) -> str:
    """
    Canonicalize natural language text for fair metric comparison.
    - Lowercase
    - Remove punctuation
    - Normalize whitespace
    """
    if not text:
        return ""
    
    # Lowercase
    text = text.lower()
    
    # Remove punctuation
    text = re.sub(r"[^a-z0-9\s]", "", text)
    
    # Normalize whitespace
    text = " ".join(text.split())
    
    return text


def compute_metrics(
    generated: str,
    gold: str,
) -> dict:
    """
    Compute lexical and semantic metrics for SPARQL→NL evaluation.
    
    Args:
        generated: Generated natural language question
        gold: Gold natural language question
    
    Returns:
        Dictionary with BLEU, ROUGE scores
    """
    metrics = {
        "bleu": None,
        "rouge1": None,
        "rouge2": None,
        "rougeL": None,
    }
    
    if not generated or not gold:
        return metrics
    
    try:
        # Canonicalize both texts
        gen_canonical = canonicalize_nl(generated)
        gold_canonical = canonicalize_nl(gold)
        
        if not gen_canonical or not gold_canonical:
            return metrics
        
        # Compute BLEU
        bleu_result = bleu_metric.compute(
            predictions=[gen_canonical],
            references=[[gold_canonical]],
        )
        metrics["bleu"] = bleu_result.get("score", 0.0) / 100.0  # Normalize to 0-1
        
        # Compute ROUGE
        rouge_result = rouge_metric.compute(
            predictions=[gen_canonical],
            references=[gold_canonical],
        )
        metrics["rouge1"] = rouge_result.get("rouge1", 0.0)
        metrics["rouge2"] = rouge_result.get("rouge2", 0.0)
        metrics["rougeL"] = rouge_result.get("rougeL", 0.0)
        
    except Exception as exc:
        logger.warning(f"Metric computation error: {str(exc)[:100]}")
    
    return metrics


def load_lc_quad_reversed(split: str = "test", limit: Optional[int] = None) -> list[dict]:
    """
    Load LC-QuAD dataset and reverse the mapping for SPARQL→NL evaluation.
    
    Args:
        split: Dataset split ("test", "train")
        limit: Max samples to load (None = all)
    
    Returns:
        List of reversed samples with keys:
        - sample_id: unique identifier
        - gold_sparql: sparql_dbpedia18 from original
        - gold_question: question from original
    """
    logger.info(f"Loading LC-QuAD {split} split...")
    dataset = load_dataset("lc_quad", split=split, trust_remote_code=True)
    
    if limit is not None:
        dataset = dataset.select(range(min(limit, len(dataset))))
    
    reversed_samples = []
    for idx, item in enumerate(dataset):
        sparql = item.get("sparql_dbpedia18", "")
        question = item.get("question", "")
        
        # Skip invalid samples
        if not sparql or not question:
            logger.debug(f"Skipping sample {idx}: missing SPARQL or question")
            continue
        
        reversed_samples.append({
            "sample_id": idx,
            "gold_sparql": sparql,
            "gold_question": question,
        })
    
    logger.info(f"Loaded {len(reversed_samples)} valid samples for SPARQL→NL evaluation")
    return reversed_samples


def create_judge_prompt(gold_sparql: str, generated_question: str, gold_question: str) -> str:
    """
    Create a prompt for LLM to evaluate faithfulness of generated question to SPARQL.
    
    Args:
        gold_sparql: Original SPARQL query
        generated_question: Generated natural language question
        gold_question: Gold natural language question (for reference)
    
    Returns:
        Judge prompt string
    """
    prompt = f"""Evaluate how well this generated natural language question represents the given SPARQL query.

SPARQL Query:
{gold_sparql}

Gold Reference Question:
{gold_question}

Generated Question:
{generated_question}

Assess semantic faithfulness: Does the generated question accurately capture what the SPARQL query does?

Provide your judgment as: CORRECT (question accurately represents the query), PARTIAL (some aspects are correct but may be incomplete or have minor issues), or INCORRECT (question misrepresents the query's intent).

Judgment:"""
    return prompt


async def evaluate_with_judge(gold_sparql: str, generated_question: str, gold_question: str) -> dict:
    """
    Use LLM judge to evaluate semantic faithfulness of generated question.
    
    Args:
        gold_sparql: Original SPARQL query
        generated_question: Generated natural language question
        gold_question: Gold natural language question
    
    Returns:
        Dictionary with judge_verdict and raw_response
    """
    judge_result = {
        "judge_verdict": None,
        "raw_response": None,
        "judge_error": None,
    }
    
    try:
        prompt = create_judge_prompt(gold_sparql, generated_question, gold_question)
        response = await call_llm(prompt)
        
        if not response:
            judge_result["judge_error"] = "LLM returned empty response"
            return judge_result
        
        judge_result["raw_response"] = response.strip()
        
        # Parse verdict from response
        response_upper = response.upper()
        if "CORRECT" in response_upper:
            judge_result["judge_verdict"] = "correct"
        elif "PARTIAL" in response_upper:
            judge_result["judge_verdict"] = "partial"
        elif "INCORRECT" in response_upper:
            judge_result["judge_verdict"] = "incorrect"
        else:
            judge_result["judge_verdict"] = "unknown"
            
    except Exception as exc:
        judge_result["judge_error"] = f"Judge error: {type(exc).__name__}: {str(exc)[:100]}"
        logger.warning(f"Judge evaluation failed: {judge_result['judge_error']}")
    
    return judge_result


async def process_single_sample(
    sample: dict,
    semaphore: asyncio.Semaphore,
    judge_enabled: bool = False,
) -> SampleResult:
    """
    Process a single SPARQL→NL sample and generate metrics.
    """
    async with semaphore:
        sample_id = sample["sample_id"]
        gold_sparql = sample["gold_sparql"]
        gold_question = sample["gold_question"]
        
        # Step 1: Generate NL from SPARQL via /generate-nl endpoint
        generated_question = None
        generation_error = None
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    GENERATE_NL_ENDPOINT,
                    json={"sparql_query": gold_sparql},
                )
                response.raise_for_status()
                
                result = response.json()
                
                if result.get("status") == "success":
                    generated_question = result.get("question", "").strip()
                    if not generated_question:
                        generation_error = "LLM returned empty question"
                        logger.warning(f"Sample {sample_id}: {generation_error}")
                else:
                    generation_error = result.get("error", "Unknown API error")
                    logger.warning(f"Sample {sample_id}: {generation_error}")
                    
        except httpx.TimeoutException:
            generation_error = "API timeout"
            logger.warning(f"Sample {sample_id}: {generation_error}")
        except httpx.HTTPError as exc:
            generation_error = f"HTTP error: {str(exc)[:100]}"
            logger.warning(f"Sample {sample_id}: {generation_error}")
        except Exception as exc:
            generation_error = f"Error: {type(exc).__name__}: {str(exc)[:100]}"
            logger.warning(f"Sample {sample_id}: {generation_error}")
        
        # Determine validity: no generation errors
        is_valid = generation_error is None and generated_question is not None
        
        # Compute metrics for valid samples
        bleu_score = None
        rouge1_score = None
        rouge2_score = None
        rougeL_score = None
        semantic_similarity = None
        
        if is_valid:
            metrics = compute_metrics(generated_question, gold_question)
            bleu_score = metrics["bleu"]
            rouge1_score = metrics["rouge1"]
            rouge2_score = metrics["rouge2"]
            rougeL_score = metrics["rougeL"]
        
        # LLM judge evaluation (optional, if enabled)
        judge_score = None
        if is_valid and judge_enabled:
            judge_result = await evaluate_with_judge(
                gold_sparql, generated_question, gold_question
            )
            judge_score = judge_result
        
        result = SampleResult(
            sample_id=sample_id,
            gold_sparql=gold_sparql,
            gold_question=gold_question,
            generated_question=generated_question,
            generation_error=generation_error,
            bleu_score=bleu_score,
            rouge1_score=rouge1_score,
            rouge2_score=rouge2_score,
            rougeL_score=rougeL_score,
            semantic_similarity=semantic_similarity,
            judge_score=judge_score,
            is_valid=is_valid,
        )
        
        return result


async def run_evaluation(
    samples: list[dict],
    judge_enabled: bool = False,
) -> list[SampleResult]:
    """
    Run SPARQL→NL evaluation on all samples concurrently.
    
    Args:
        samples: List of reversed LC-QuAD samples
        judge_enabled: Whether to use LLM judge (costly)
    
    Returns:
        List of SampleResult objects
    """
    logger.info(f"Evaluating {len(samples)} SPARQL→NL samples (judge={judge_enabled})")
    
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    tasks = [
        process_single_sample(sample, semaphore, judge_enabled)
        for sample in samples
    ]
    
    logger.info("Starting evaluation...")
    results = await tqdm.gather(*tasks, desc="Processing samples")
    
    return results


def save_evaluation_results(results: list[SampleResult]) -> None:
    """
    Save per-sample results to JSONL and aggregated summary to JSON.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Saving results to {EVAL_LOG_FILE} and {SUMMARY_FILE}")
    
    # Per-sample JSONL (one result per line)
    with open(EVAL_LOG_FILE, "w") as f:
        for result in results:
            # Convert SampleResult to dict for JSON serialization
            result_dict = {
                "sample_id": result.sample_id,
                "gold_sparql": result.gold_sparql,
                "gold_question": result.gold_question,
                "generated_question": result.generated_question,
                "generation_error": result.generation_error,
                "metrics": {
                    "bleu": result.bleu_score,
                    "rouge1": result.rouge1_score,
                    "rouge2": result.rouge2_score,
                    "rougeL": result.rougeL_score,
                    "semantic_similarity": result.semantic_similarity,
                },
                "judge": result.judge_score,
                "is_valid": result.is_valid,
            }
            f.write(json.dumps(result_dict) + "\n")
    
    # Aggregate metrics for summary
    valid_results = [r for r in results if r.is_valid]
    total = len(results)
    valid_count = len(valid_results)
    failed_count = total - valid_count
    
    # Compute metric averages
    bleu_scores = [r.bleu_score for r in valid_results if r.bleu_score is not None]
    rouge1_scores = [r.rouge1_score for r in valid_results if r.rouge1_score is not None]
    rouge2_scores = [r.rouge2_score for r in valid_results if r.rouge2_score is not None]
    rougeL_scores = [r.rougeL_score for r in valid_results if r.rougeL_score is not None]
    
    bleu_avg = sum(bleu_scores) / len(bleu_scores) if bleu_scores else None
    rouge1_avg = sum(rouge1_scores) / len(rouge1_scores) if rouge1_scores else None
    rouge2_avg = sum(rouge2_scores) / len(rouge2_scores) if rouge2_scores else None
    rougeL_avg = sum(rougeL_scores) / len(rougeL_scores) if rougeL_scores else None
    
    # Compute judge statistics
    judge_results = [r.judge_score for r in valid_results if r.judge_score is not None]
    judge_verdicts = {}
    if judge_results:
        verdicts = [j.get("judge_verdict") for j in judge_results]
        judge_verdicts = {
            "correct": verdicts.count("correct"),
            "partial": verdicts.count("partial"),
            "incorrect": verdicts.count("incorrect"),
            "unknown": verdicts.count("unknown"),
            "total_judged": len(verdicts),
        }
    
    # Compute error breakdown
    error_breakdown = {}
    for r in results:
        if r.generation_error:
            error_type = r.generation_error.split(":")[0]
            error_breakdown[error_type] = error_breakdown.get(error_type, 0) + 1
    
    # Build summary JSON
    summary = {
        "metadata": {
            "total_samples": total,
            "valid_samples": valid_count,
            "failed_samples": failed_count,
            "success_rate": valid_count / total if total > 0 else 0.0,
        },
        "metrics": {
            "bleu": {
                "average": bleu_avg,
                "count": len(bleu_scores),
            },
            "rouge": {
                "rouge1": {
                    "average": rouge1_avg,
                    "count": len(rouge1_scores),
                },
                "rouge2": {
                    "average": rouge2_avg,
                    "count": len(rouge2_scores),
                },
                "rougeL": {
                    "average": rougeL_avg,
                    "count": len(rougeL_scores),
                },
            },
            "semantic_similarity": {
                "average": None,  # Not computed yet
                "count": 0,
            },
        },
        "judge": judge_verdicts if judge_verdicts else None,
        "error_breakdown": error_breakdown,
    }
    
    with open(SUMMARY_FILE, "w") as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Results saved to {EVAL_LOG_FILE}")
    logger.info(f"Summary saved to {SUMMARY_FILE}")


def print_summary(results: list[SampleResult]) -> None:
    """Print evaluation summary to console."""
    valid_results = [r for r in results if r.is_valid]
    total = len(results)
    valid_count = len(valid_results)
    failed_count = total - valid_count
    
    print("\n" + "=" * 70)
    print("SPARQL → NL EVALUATION COMPLETE")
    print("=" * 70)
    print(f"Total samples:              {total}")
    print(f"Successfully generated:     {valid_count}/{total} ({100*valid_count/total:.1f}%)")
    print(f"Generation failed:          {failed_count}")
    print()
    
    # Group errors by type
    error_types = {}
    for r in results:
        if r.generation_error:
            error_msg = r.generation_error.split(":")[0]
            error_types[error_msg] = error_types.get(error_msg, 0) + 1
    
    if error_types:
        print("Error breakdown:")
        for error_type, count in sorted(error_types.items(), key=lambda x: -x[1]):
            print(f"  {error_type}: {count}")
        print()
    
    # Compute aggregated metrics
    if valid_results:
        bleu_scores = [r.bleu_score for r in valid_results if r.bleu_score is not None]
        rouge1_scores = [r.rouge1_score for r in valid_results if r.rouge1_score is not None]
        rouge2_scores = [r.rouge2_score for r in valid_results if r.rouge2_score is not None]
        rougeL_scores = [r.rougeL_score for r in valid_results if r.rougeL_score is not None]
        
        print("Lexical Metrics:")
        if bleu_scores:
            print(f"  BLEU:                   {sum(bleu_scores)/len(bleu_scores):.4f}")
        if rouge1_scores:
            print(f"  ROUGE-1:                {sum(rouge1_scores)/len(rouge1_scores):.4f}")
        if rouge2_scores:
            print(f"  ROUGE-2:                {sum(rouge2_scores)/len(rouge2_scores):.4f}")
        if rougeL_scores:
            print(f"  ROUGE-L:                {sum(rougeL_scores)/len(rougeL_scores):.4f}")
        
        # Judge statistics (if any)
        judge_results = [r.judge_score for r in valid_results if r.judge_score is not None]
        if judge_results:
            verdicts = [j.get("judge_verdict") for j in judge_results]
            correct_count = verdicts.count("correct")
            partial_count = verdicts.count("partial")
            incorrect_count = verdicts.count("incorrect")
            unknown_count = verdicts.count("unknown")
            
            print()
            print("Semantic Faithfulness (LLM Judge):")
            print(f"  Correct:                {correct_count}/{len(verdicts)} ({100*correct_count/len(verdicts):.1f}%)")
            if partial_count > 0:
                print(f"  Partially Correct:      {partial_count}/{len(verdicts)} ({100*partial_count/len(verdicts):.1f}%)")
            if incorrect_count > 0:
                print(f"  Incorrect:              {incorrect_count}/{len(verdicts)} ({100*incorrect_count/len(verdicts):.1f}%)")
            if unknown_count > 0:
                print(f"  Unknown:                {unknown_count}/{len(verdicts)} ({100*unknown_count/len(verdicts):.1f}%)")
    
    print()
    print("Output Files:")
    print(f"  Per-sample:             {EVAL_LOG_FILE}")
    print(f"  Aggregated summary:     {SUMMARY_FILE}")
    print("=" * 70)


async def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluate SPARQL → Natural Language generation on LC-QuAD"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=TEST_RANGE,
        help=f"Number of samples to evaluate (default: {TEST_RANGE})",
    )
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Enable LLM judge for faithfulness scoring (cost-sensitive)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose logging",
    )
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logging.getLogger("src").setLevel(logging.DEBUG)
    
    # Load reversed LC-QuAD dataset
    samples = load_lc_quad_reversed(split="test", limit=args.limit)
    
    if not samples:
        logger.error("No valid samples loaded. Exiting.")
        return 1
    
    # Run evaluation
    results = await run_evaluation(samples, judge_enabled=args.judge)
    
    # Save results
    save_evaluation_results(results)
    
    # Print summary
    print_summary(results)
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
