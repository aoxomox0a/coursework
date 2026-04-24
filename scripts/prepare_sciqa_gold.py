"""
Prepare the SciQA gold-set for ORKG evaluation.

Workflow:
  1. Load SciQA test split from HuggingFace.
  2. Execute each gold SPARQL against the live ORKG endpoint (caching responses
     on disk so re-runs are cheap).
  3. Filter to items that returned at least one binding.
  4. Stratified random sample by ``query_shape`` to hit the target size.
  5. Write the gold JSONL + a manifest documenting the snapshot.

Usage:
  uv run --group evaluation python scripts/prepare_sciqa_gold.py
  uv run --group evaluation python scripts/prepare_sciqa_gold.py --limit 50  # smoke test
  uv run --group evaluation python scripts/prepare_sciqa_gold.py --target-size 60 --seed 42
"""
import argparse
import asyncio
import hashlib
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Make src/ importable when this script is invoked from anywhere.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from datasets import load_dataset

from src.evaluation.sciqa_prep import (
    PREFIX_BLOCK,
    convert_to_gold_item,
    extract_sparql_text,
    stratified_sample,
)
from src.sparql.execution import execute_query

logger = logging.getLogger("prepare_sciqa_gold")

DEFAULT_ENDPOINT = "https://orkg.org/triplestore"
DEFAULT_OUT = Path("data/gold/orkg_sciqa.jsonl")
DEFAULT_MANIFEST = Path("data/gold/orkg_sciqa.manifest.json")
DEFAULT_CACHE_DIR = Path("data/gold/.cache")


def _cache_path(cache_dir: Path, item_id: str, sparql_hash: str) -> Path:
    return cache_dir / f"{item_id}_{sparql_hash[:8]}.json"


def _hash_sparql(sparql: str) -> str:
    return hashlib.sha256(sparql.encode()).hexdigest()


def _load_cached(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        logger.warning("cache miss (corrupt at %s): %s", path, exc)
        return None


def _save_cached(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


async def _execute_with_cache(
    item: dict,
    endpoint: str,
    cache_dir: Path,
    use_cache: bool,
    rate_limit_sec: float,
) -> tuple[list[dict] | None, str]:
    """Execute a SciQA item's gold query (with cache + PREFIX prepend).

    Returns (bindings, status) — bindings is None on error, [] for empty results.
    """
    sparql_raw = extract_sparql_text(item.get("query"))
    if not sparql_raw:
        return None, "missing_sparql"

    full_query = PREFIX_BLOCK + sparql_raw
    cache_path = _cache_path(cache_dir, item["id"], _hash_sparql(full_query))

    if use_cache:
        cached = _load_cached(cache_path)
        if cached is not None:
            if "error" in cached:
                return None, "error_cached"
            bindings = cached.get("results", {}).get("bindings", [])
            return bindings, "ok_cached"

    response = await execute_query(full_query, endpoint_url=endpoint)
    _save_cached(cache_path, response)
    if rate_limit_sec > 0:
        await asyncio.sleep(rate_limit_sec)

    if "error" in response:
        return None, f"error:{response['error']}"
    bindings = response.get("results", {}).get("bindings", [])
    return bindings, "ok"


async def _scan_items(
    items: list[dict],
    endpoint: str,
    cache_dir: Path,
    use_cache: bool,
    rate_limit_sec: float,
) -> tuple[list[tuple[dict, list[dict]]], dict]:
    """Execute every item, return (successful_pairs, stats).

    successful_pairs: list of (sciqa_item, bindings) where bindings is non-empty.
    stats: counts (total, ok_nonempty, ok_empty, errors).
    """
    successful: list[tuple[dict, list[dict]]] = []
    stats = {"total": len(items), "ok_nonempty": 0, "ok_empty": 0, "errors": 0}

    for i, item in enumerate(items, 1):
        bindings, status = await _execute_with_cache(
            item, endpoint, cache_dir, use_cache, rate_limit_sec
        )
        if bindings is None:
            stats["errors"] += 1
        elif bindings:
            stats["ok_nonempty"] += 1
            successful.append((item, bindings))
        else:
            stats["ok_empty"] += 1

        if i % 50 == 0 or i == len(items):
            logger.info(
                "scanned %d/%d  ok_nonempty=%d  ok_empty=%d  errors=%d",
                i,
                len(items),
                stats["ok_nonempty"],
                stats["ok_empty"],
                stats["errors"],
            )

    return successful, stats


def _build_manifest(
    *,
    target_size: int,
    actual_size: int,
    scan_stats: dict,
    seed: int,
    endpoint: str,
    snapshot_date: str,
    stratum_distribution: dict[str, int],
) -> dict:
    return {
        "source": "huggingface:orkg/SciQA",
        "split": "test",
        "endpoint": endpoint,
        "snapshot_date": snapshot_date,
        "seed": seed,
        "target_size": target_size,
        "actual_size": actual_size,
        "scan_total": scan_stats["total"],
        "scan_successful_nonempty": scan_stats["ok_nonempty"],
        "scan_successful_empty": scan_stats["ok_empty"],
        "scan_errors": scan_stats["errors"],
        "stratum_distribution": stratum_distribution,
        "drift_note": (
            f"Of {scan_stats['total']} SciQA test gold queries, "
            f"{scan_stats['ok_nonempty']} ({100*scan_stats['ok_nonempty']/max(1,scan_stats['total']):.1f}%) "
            "returned at least one binding on the live ORKG endpoint at snapshot time. "
            "The remainder reflects data-level drift: predicates still exist but the specific "
            "scientific entities (papers, datasets, models) referenced by the gold queries "
            "have been removed or never imported into the public endpoint. The sampled gold "
            "set is therefore biased toward whichever subset of ORKG remains queryable."
        ),
    }


def _stratum_counts(items: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = item.get("query_shape") or "unknown"
        counts[key] = counts.get(key, 0) + 1
    return counts


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--limit", type=int, default=None,
                        help="Scan only the first N items (for smoke testing)")
    parser.add_argument("--target-size", type=int, default=60,
                        help="Number of items in the final gold sample")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--no-cache", action="store_true",
                        help="Always re-fetch, ignoring on-disk cache")
    parser.add_argument("--rate-limit-sec", type=float, default=0.3)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    # Silence httpx per-request chatter unless --verbose.
    if not args.verbose:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)

    logger.info("Loading SciQA test split from HuggingFace…")
    ds = load_dataset("orkg/SciQA", split="test")
    items = list(ds)
    if args.limit is not None:
        items = items[: args.limit]
    logger.info("Scanning %d items against %s", len(items), args.endpoint)

    t0 = time.time()
    successful, stats = await _scan_items(
        items,
        endpoint=args.endpoint,
        cache_dir=args.cache_dir,
        use_cache=not args.no_cache,
        rate_limit_sec=args.rate_limit_sec,
    )
    elapsed = time.time() - t0
    logger.info("Scan done in %.1fs. Pool of %d non-empty items.", elapsed, len(successful))

    if not successful:
        logger.error("No items returned non-empty bindings — cannot build a gold set.")
        return 1

    sampled = stratified_sample(
        items=[item for item, _ in successful],
        n=args.target_size,
        seed=args.seed,
    )
    sampled_ids = {item["id"] for item in sampled}
    sampled_with_bindings = [(item, bindings) for item, bindings in successful if item["id"] in sampled_ids]
    sampled_with_bindings.sort(key=lambda pair: pair[0]["id"])

    snapshot = datetime.now(tz=timezone.utc).isoformat()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as f:
        for sciqa_item, bindings in sampled_with_bindings:
            gold = convert_to_gold_item(sciqa_item, bindings, executed_at=snapshot)
            f.write(json.dumps(gold) + "\n")
    logger.info("Wrote %d gold items to %s", len(sampled_with_bindings), args.out)

    manifest = _build_manifest(
        target_size=args.target_size,
        actual_size=len(sampled_with_bindings),
        scan_stats=stats,
        seed=args.seed,
        endpoint=args.endpoint,
        snapshot_date=snapshot,
        stratum_distribution=_stratum_counts([item for item, _ in sampled_with_bindings]),
    )
    args.manifest.write_text(json.dumps(manifest, indent=2))
    logger.info("Wrote manifest to %s", args.manifest)

    print(json.dumps({"actual_size": manifest["actual_size"],
                      "scan_successful_nonempty": stats["ok_nonempty"],
                      "scan_total": stats["total"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
