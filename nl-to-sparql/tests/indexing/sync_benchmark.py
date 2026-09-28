# tests/indexing/test_sync_benchmark.py
import time
import config.settings


config.settings.LIMIT_ENTITIES = 5000
config.settings.BATCH_SIZE = 1000

from src.indexing.pipeline import run_indexing_pipeline


start = time.perf_counter()
result = run_indexing_pipeline()  # No await!
# Stop the timer
end_time = time.perf_counter()
total_time = end_time - start

print("\n--- BENCHMARK RESULTS ---")
print(f"Total Entities Indexed: {result.get('entities', 0)}")
print(f"Total Execution Time:   {total_time:.4f} seconds")

# Calculate throughput for your report
if total_time > 0 and result.get("entities", 0) > 0:
    entities_per_sec = result["entities"] / total_time
    print(f"Throughput:             {entities_per_sec:.2f} entities/second")
