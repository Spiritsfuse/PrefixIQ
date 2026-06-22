import time
import httpx
import asyncio
import statistics
import sys
import random

# Target API URL
API_URL = "http://localhost:8000"

# Mock prefixes and queries to simulate real user behavior
MOCK_PREFIXES = ["iph", "py", "wea", "bit", "next", "c++", "dock", "chat", "ten", "app", "mac", "gold", "goog"]

async def measure_request(client: httpx.AsyncClient, method: str, url: str, json_data=None) -> float:
    """Sends a request and returns latency in milliseconds. Returns -1.0 on failure."""
    start = time.time()
    try:
        if method == "GET":
            res = await client.get(url)
        else:
            res = await client.post(url, json=json_data)
        latency = (time.time() - start) * 1000
        if res.status_code == 200:
            return latency
        return -1.0
    except Exception:
        return -2.0

async def run_benchmark_suite(num_requests: int = 150, concurrency: int = 5):
    print("=" * 60)
    print("         PREFIXIQ SYSTEM COMPARATIVE BENCHMARK SUITE         ")
    print("=" * 60)
    print(f"Target API Endpoint: {API_URL}")
    print(f"Total Cycles: {num_requests} | Concurrency: {concurrency}")
    print("-" * 60)

    limits = httpx.Limits(max_keepalive_connections=concurrency, max_connections=concurrency)
    
    db_only_latencies = []
    cold_cache_latencies = []
    warm_cache_latencies = []

    async with httpx.AsyncClient(limits=limits, timeout=10.0) as client:
        # We process in small concurrent chunks to simulate concurrent traffic
        for i in range(0, num_requests, concurrency):
            prefixes_chunk = [random.choice(MOCK_PREFIXES) for _ in range(concurrency)]

            # 1. DB ONLY (Bypassing Redis Caching via /internal/db-suggest)
            db_tasks = [
                measure_request(client, "GET", f"{API_URL}/internal/db-suggest?q={pref}&mode=basic")
                for pref in prefixes_chunk
            ]
            db_results = await asyncio.gather(*db_tasks)
            db_only_latencies.extend([r for r in db_results if r > 0])

            # 2. COLD REDIS CACHE (Clear key first, then query autocomplete suggest)
            # Clear keys in parallel
            clear_tasks = [
                measure_request(client, "POST", f"{API_URL}/internal/cache/clear?prefix={pref}")
                for pref in prefixes_chunk
            ]
            await asyncio.gather(*clear_tasks)
            
            # Query suggest (will miss, query DB, and write-back to cache)
            cold_tasks = [
                measure_request(client, "GET", f"{API_URL}/suggest?q={pref}&mode=basic")
                for pref in prefixes_chunk
            ]
            cold_results = await asyncio.gather(*cold_tasks)
            cold_cache_latencies.extend([r for r in cold_results if r > 0])

            # 3. WARM REDIS CACHE (Query suggest immediately again -> guaranteed cache hit)
            warm_tasks = [
                measure_request(client, "GET", f"{API_URL}/suggest?q={pref}&mode=basic")
                for pref in prefixes_chunk
            ]
            warm_results = await asyncio.gather(*warm_tasks)
            warm_cache_latencies.extend([r for r in warm_results if r > 0])

        def compute_percentiles(latencies: list) -> tuple:
            if not latencies:
                return (0.0, 0.0, 0.0)
            avg = sum(latencies) / len(latencies)
            p50 = statistics.median(latencies)
            sorted_lats = sorted(latencies)
            p95 = sorted_lats[int(len(sorted_lats) * 0.95)] if len(sorted_lats) > 1 else avg
            return avg, p50, p95

        db_avg, db_p50, db_p95 = compute_percentiles(db_only_latencies)
        cold_avg, cold_p50, cold_p95 = compute_percentiles(cold_cache_latencies)
        warm_avg, warm_p50, warm_p95 = compute_percentiles(warm_cache_latencies)

        print("\n### Caching Performance Comparison Table")
        print("\n| Scenario | Avg Latency | P50 (Median) | P95 Latency | Success Rate |")
        print("| :--- | :---: | :---: | :---: | :---: |")
        print(f"| **DB Only (Cache Bypassed)** | {db_avg:.2f} ms | {db_p50:.2f} ms | {db_p95:.2f} ms | {len(db_only_latencies)}/{num_requests} |")
        print(f"| **Cold Redis (Cache Miss)**  | {cold_avg:.2f} ms | {cold_p50:.2f} ms | {cold_p95:.2f} ms | {len(cold_cache_latencies)}/{num_requests} |")
        print(f"| **Warm Redis (Cache Hit)**   | {warm_avg:.2f} ms | {warm_p50:.2f} ms | {warm_p95:.2f} ms | {len(warm_cache_latencies)}/{num_requests} |")
        print("\n" + "=" * 60)

if __name__ == "__main__":
    # Check if backend is running on localhost:8000
    try:
        import socket
        s = socket.socket()
        s.settimeout(1.0)
        s.connect(("localhost", 8000))
        s.close()
    except Exception:
        print("ERROR: Backend service is not running on localhost:8000.")
        print("Please run `docker compose up` before running benchmarks.")
        sys.exit(1)

    asyncio.run(run_benchmark_suite())
