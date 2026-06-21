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
MOCK_QUERIES = [
    "iphone charger", "python tutorial", "weather in new york", "bitcoin price",
    "nextjs 15 features", "c++ roadmap", "docker config", "chatgpt 5 leaks",
    "tesla stock", "apple watch review", "macbook pro buy", "google flights"
]

async def benchmark_suggest(client: httpx.AsyncClient, mode: str) -> float:
    """Sends a single suggest query and returns latency in milliseconds."""
    prefix = random.choice(MOCK_PREFIXES)
    start = time.time()
    try:
        res = await client.get(f"{API_URL}/suggest?q={prefix}&mode={mode}")
        latency = (time.time() - start) * 1000  # Convert to ms
        if res.status_code == 200:
            return latency
        else:
            return -1.0
    except Exception:
        return -2.0

async def benchmark_search(client: httpx.AsyncClient) -> float:
    """Sends a single search query and returns latency in milliseconds."""
    query = random.choice(MOCK_QUERIES)
    start = time.time()
    try:
        res = await client.post(f"{API_URL}/search", json={"query": query})
        latency = (time.time() - start) * 1000  # Convert to ms
        if res.status_code == 200:
            return latency
        else:
            return -1.0
    except Exception:
        return -2.0

async def run_benchmark_suite(num_requests: int = 200, concurrency: int = 10):
    print("=" * 60)
    print("         PREFIXIQ SYSTEM BENCHMARK PERFORMANCE SUITE         ")
    print("=" * 60)
    print(f"Target API Endpoint: {API_URL}")
    print(f"Total Requests: {num_requests} | Concurrency: {concurrency}")
    print("-" * 60)

    limits = httpx.Limits(max_keepalive_connections=concurrency, max_connections=concurrency)
    async with httpx.AsyncClient(limits=limits, timeout=5.0) as client:
        
        # 1. Benchmark Autocomplete GET /suggest (Basic Mode)
        print("Warmup: Warming up caches...")
        # Send a few warm-up queries
        await asyncio.gather(*[benchmark_suggest(client, "basic") for _ in range(20)])
        
        print("Benchmarking Autocomplete GET /suggest (Basic)...")
        suggest_basic_latencies = []
        # Run in concurrent chunks
        for i in range(0, num_requests, concurrency):
            tasks = [benchmark_suggest(client, "basic") for _ in range(concurrency)]
            results = await asyncio.gather(*tasks)
            suggest_basic_latencies.extend([r for r in results if r > 0])
            
        # 2. Benchmark Autocomplete GET /suggest (Enhanced Mode)
        print("Benchmarking Autocomplete GET /suggest (Enhanced)...")
        suggest_enhanced_latencies = []
        for i in range(0, num_requests, concurrency):
            tasks = [benchmark_suggest(client, "enhanced") for _ in range(concurrency)]
            results = await asyncio.gather(*tasks)
            suggest_enhanced_latencies.extend([r for r in results if r > 0])

        # 3. Benchmark Search POST /search (Batch Writer buffer)
        print("Benchmarking Search Submit POST /search...")
        search_latencies = []
        for i in range(0, num_requests, concurrency):
            tasks = [benchmark_search(client) for _ in range(concurrency)]
            results = await asyncio.gather(*tasks)
            search_latencies.extend([r for r in results if r > 0])

        def print_stats(name: str, latencies: list):
            if not latencies:
                print(f"Error: No successful requests recorded for {name}.")
                return
            avg = sum(latencies) / len(latencies)
            p50 = statistics.median(latencies)
            # Calculate P95
            sorted_lats = sorted(latencies)
            p95 = sorted_lats[int(len(sorted_lats) * 0.95)]
            
            print(f"\nStats for {name}:")
            print(f"  Success Rate : {len(latencies)} / {num_requests} ({round(len(latencies)/num_requests*100, 1)}%)")
            print(f"  Average Lat  : {round(avg, 2)} ms")
            print(f"  P50 Latency  : {round(p50, 2)} ms")
            print(f"  P95 Latency  : {round(p95, 2)} ms (Scrape/Scrub standard)")
            print("-" * 60)

        print_stats("GET /suggest (Basic, Cache sharded)", suggest_basic_latencies)
        print_stats("GET /suggest (Enhanced, Recency-aware)", suggest_enhanced_latencies)
        print_stats("POST /search (Batch Writer queue buffer)", search_latencies)
        
        # Check active batch writer write metrics
        try:
            res = await client.get(f"{API_URL}/metrics")
            if res.status_code == 200:
                m = res.json()
                reduction = m["database_metrics"]["batch_write_reduction_percentage"]
                total_rec = m["database_metrics"]["db_reads"] + m["database_metrics"]["db_writes"]
                print(f"Batching Effectiveness:")
                print(f"  Write Reduction Factor: {reduction}%")
                print(f"  Avg Flush Batch Size  : {m['database_metrics']['average_batch_size']}")
                print(f"  DB Writes Performed   : {m['database_metrics']['db_writes']} flushes")
        except Exception:
            pass

if __name__ == "__main__":
    # Check if backend is running
    try:
        import socket
        s = socket.socket()
        # Parse host and port
        s.settimeout(1.0)
        s.connect(("localhost", 8000))
        s.close()
    except Exception:
        print("ERROR: Backend service is not running on localhost:8000.")
        print("Please run `docker compose up` before running benchmarks.")
        sys.exit(1)

    asyncio.run(run_benchmark_suite())
