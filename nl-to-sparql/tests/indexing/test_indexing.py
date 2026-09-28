import time
import asyncio
import config.settings

# 1. Standardize your benchmark parameters
# Set a high enough limit so the network difference becomes obvious
config.settings.LIMIT_ENTITIES = 5000
config.settings.BATCH_SIZE = 1000

from src.indexing.pipeline import run_indexing_pipeline
# from src.indexing.chroma_storage import reset_chroma_database


async def run_benchmark():
    print("--- PREPARING BENCHMARK ENVIRONMENT ---")
    # You MUST wipe the DB before each run, otherwise the second run
    # might skip embedding generation or hit ChromaDB caches.
    # reset_chroma_database()

    print(
        f"\n--- STARTING PIPELINE (Target: {config.settings.LIMIT_ENTITIES} entities) ---"
    )

    # Start the high-resolution timer
    start_time = time.perf_counter()

    # Run the full pipeline
    result = await run_indexing_pipeline()

    # Stop the timer
    end_time = time.perf_counter()
    total_time = end_time - start_time

    print("\n--- BENCHMARK RESULTS ---")
    print(f"Total Entities Indexed: {result.get('entities', 0)}")
    print(f"Total Execution Time:   {total_time:.4f} seconds")

    # Calculate throughput for your report
    if total_time > 0 and result.get("entities", 0) > 0:
        entities_per_sec = result["entities"] / total_time
        print(f"Throughput:             {entities_per_sec:.2f} entities/second")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
