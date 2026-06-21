import time
import json
import asyncio
from typing import List, Dict, Optional
from fastapi import FastAPI, Depends, Query, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import redis.asyncio as async_redis

from .config import settings
from .database import get_db, engine, Base
from .models import SearchQuery
from .schemas import SearchSubmit, SearchResponse, SuggestionResponse, SuggestionItem, CacheDebugResponse
from .consistent_hashing import ring
from .batch_writer import batch_writer
from .ranking import get_suggestions_basic, get_suggestions_enhanced
from .seed_queries import seed_historical_queries
from .seed_recent_logs import seed_recent_activity

# Initialize FastAPI application
app = FastAPI(
    title="PrefixIQ Backend",
    description="PrefixIQ Search Typeahead System with Consistent Hashing, Decayed Trending, and Asynchronous Batching",
    version="1.0.0"
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global metrics tracking (in-memory request times for P50/P95 computations)
METRICS = {
    "suggest_calls": 0,
    "suggest_hits": 0,
    "suggest_misses": 0,
    "suggest_latencies": [],  # List of floating-point seconds (sliding window)
    "search_calls": 0,
    "search_latencies": [],
    "db_reads": 0
}
metrics_lock = asyncio.Lock()

# Custom middleware to log request latency for dynamic P50/P95 computations
@app.middleware("http")
async def latency_tracker_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    latency = time.time() - start_time
    
    path = request.url.path
    async with metrics_lock:
        if path == "/suggest":
            METRICS["suggest_calls"] += 1
            METRICS["suggest_latencies"].append(latency)
            if len(METRICS["suggest_latencies"]) > 1000:
                METRICS["suggest_latencies"].pop(0)
        elif path == "/search":
            METRICS["search_calls"] += 1
            METRICS["search_latencies"].append(latency)
            if len(METRICS["search_latencies"]) > 1000:
                METRICS["search_latencies"].pop(0)
                
    return response

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    # 1. Initialize SQL schemas and seed DB if empty
    # Seeding is sequential: historical queries first, then trending activity log
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, seed_historical_queries)
    await loop.run_in_executor(None, seed_recent_activity)
    
    # 2. Warm up/verify Redis connections
    for node, client in ring.redis_clients.items():
        try:
            await client.ping()
            print(f"[Startup] Connected to Redis node: {node}")
        except Exception as e:
            print(f"[Startup] WARNING: Could not connect to Redis node {node}: {e}")
            
    # 3. Start batch writing worker loop
    await batch_writer.start()
    print("[Startup] App initialization complete.")

@app.on_event("shutdown")
async def shutdown_event():
    # Stop batch writer worker and perform final flush
    await batch_writer.stop()
    
    # Close Redis client connections
    for client in ring.redis_clients.values():
        await client.aclose()
    print("[Shutdown] Closed connections and cleaned up.")


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Simulates a production health check.
    Validates connection to PostgreSQL database and at least one Redis node.
    """
    health_status = {
        "status": "healthy",
        "database": "unhealthy",
        "redis_nodes": {}
    }
    
    # Check Database connection
    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = "healthy"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["database"] = f"unhealthy: {str(e)}"
        
    # Check Redis nodes connection status
    healthy_redis_count = 0
    for node, client in ring.redis_clients.items():
        try:
            await client.ping()
            health_status["redis_nodes"][node] = "healthy"
            healthy_redis_count += 1
        except Exception as e:
            health_status["redis_nodes"][node] = f"unreachable: {str(e)}"
            
    if healthy_redis_count == 0:
        health_status["status"] = "unhealthy"
        
    if health_status["status"] != "healthy":
        raise HTTPException(status_code=503, detail=health_status)
        
    return health_status


@app.get("/suggest", response_model=SuggestionResponse)
async def suggest(
    q: str = Query("", description="The prefix string to match suggestions"),
    mode: str = Query("basic", description="Ranking engine mode: 'basic' or 'enhanced'"),
    db: Session = Depends(get_db)
):
    """
    Retrieves matching typeahead suggestions.
    Checks the consistent hashing ring for a cached list.
    Falls back to PostgreSQL database on a cache miss.
    """
    normalized_prefix = q.strip().lower()
    
    # If query prefix is empty, return empty list (or trending defaults handled separately)
    if not normalized_prefix:
        return SuggestionResponse(suggestions=[], source="database")
        
    cache_key = f"suggest:{mode}:{normalized_prefix}"
    
    # 1. Consistent hashing lookup to identify target Redis client
    redis_client = None
    node_name = "unknown"
    try:
        redis_client, node_name, _ = await ring.get_client(normalized_prefix)
        # Attempt to retrieve from Redis
        cached_data = await redis_client.get(cache_key)
        if cached_data:
            async with metrics_lock:
                METRICS["suggest_hits"] += 1
            suggestions_list = json.loads(cached_data)
            return SuggestionResponse(
                suggestions=[SuggestionItem(**item) for item in suggestions_list],
                source="cache"
            )
    except Exception as e:
        print(f"[Redis Cache Error] Could not connect or query node {node_name}: {e}")
        
    # 2. Cache Miss or Redis Offline -> Query primary SQL database
    async with metrics_lock:
        METRICS["suggest_misses"] += 1
        METRICS["db_reads"] += 1
        
    if mode == "enhanced":
        raw_suggestions = get_suggestions_enhanced(db, normalized_prefix, limit=10)
    else:
        raw_suggestions = get_suggestions_basic(db, normalized_prefix, limit=10)
        
    suggestions = [
        SuggestionItem(query=item[0], count=item[1], score=item[2])
        for item in raw_suggestions
    ]
    
    # 3. Cache the results back to the designated Redis node for 60 seconds
    if redis_client:
        try:
            serialized = json.dumps([item.dict() for item in suggestions])
            await redis_client.setex(cache_key, 60, serialized)
        except Exception as e:
            print(f"[Redis Write Error] Could not write cache to node {node_name}: {e}")
            
    return SuggestionResponse(suggestions=suggestions, source="database")


@app.post("/search", response_model=SearchResponse)
async def search(payload: SearchSubmit):
    """
    Records a search submission.
    Pushes the query into the batch writer queue to buffer updates.
    Returns immediately to ensure low write latency.
    """
    query = payload.query.strip().lower()
    if not query:
        raise HTTPException(status_code=400, detail="Search query cannot be empty")
        
    # Push query into memory buffer
    batch_writer.push(query)
    return SearchResponse()


@app.get("/cache/debug", response_model=CacheDebugResponse)
async def cache_debug(
    prefix: str = Query(..., description="Prefix to look up"),
    mode: str = Query("basic", description="Ranking engine mode: 'basic' or 'enhanced'")
):
    """
    Debugs cache routing.
    Shows the physical node assigned to the prefix on the hash ring, key hash, 
    and hit/miss status.
    """
    normalized_prefix = prefix.strip().lower()
    cache_key = f"suggest:{mode}:{normalized_prefix}"
    
    try:
        # Determine node assignment
        redis_client, node_name, key_hash = await ring.get_client(normalized_prefix)
        
        # Check cache hit status
        cached_data = await redis_client.get(cache_key)
        hit = cached_data is not None
        
        suggestions = []
        if hit:
            suggestions_list = json.loads(cached_data)
            suggestions = [SuggestionItem(**item) for item in suggestions_list]
            
        # Get hash ring node replicas count
        stats = ring.get_ring_distribution()
        distribution = {node: f"{count} virtual nodes" for node, count in stats.items()}
        
        return CacheDebugResponse(
            prefix=normalized_prefix,
            hash_value=key_hash,
            assigned_node=node_name,
            cache_hit=hit,
            suggestions=suggestions,
            ring_distribution=distribution
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache debug inspection failed: {str(e)}")


@app.get("/trending", response_model=SuggestionResponse)
async def trending(
    mode: str = Query("basic", description="Mode of ranking: 'basic' or 'enhanced'"),
    db: Session = Depends(get_db)
):
    """
    Returns the top 10 overall search queries.
    Basic: Top 10 by overall historical counts.
    Enhanced: Top 10 by decay trending score in the last 24 hours.
    """
    async with metrics_lock:
        METRICS["db_reads"] += 1
        
    # We query basic/enhanced with empty prefix to grab overall top queries
    if mode == "enhanced":
        raw = get_suggestions_enhanced(db, "", limit=10)
    else:
        raw = get_suggestions_basic(db, "", limit=10)
        
    suggestions = [
        SuggestionItem(query=item[0], count=item[1], score=item[2])
        for item in raw
    ]
    return SuggestionResponse(suggestions=suggestions, source="database")


@app.get("/metrics")
async def get_system_metrics(db: Session = Depends(get_db)):
    """
    Gathers real-time performance statistics, latency averages (P50, P95),
    cache efficiency, queue length, and database write reduction factor.
    """
    async with metrics_lock:
        suggest_lats = METRICS["suggest_latencies"]
        search_lats = METRICS["search_latencies"]
        hits = METRICS["suggest_hits"]
        misses = METRICS["suggest_misses"]
        db_reads = METRICS["db_reads"]
        
    def calculate_percentiles(latencies: List[float]) -> Dict[str, float]:
        if not latencies:
            return {"avg": 0.0, "p50": 0.0, "p95": 0.0}
        sorted_lats = sorted(latencies)
        n = len(sorted_lats)
        p50 = sorted_lats[int(n * 0.5)]
        p95 = sorted_lats[int(n * 0.95)]
        avg = sum(sorted_lats) / n
        return {
            "avg": round(avg * 1000, 2),   # Milliseconds
            "p50": round(p50 * 1000, 2),
            "p95": round(p95 * 1000, 2)
        }
        
    suggest_perf = calculate_percentiles(suggest_lats)
    search_perf = calculate_percentiles(search_lats)
    
    total_suggests = hits + misses
    hit_rate = round((hits / total_suggests * 100), 2) if total_suggests > 0 else 0.0
    
    batch_stats = batch_writer.get_metrics()
    
    # Retrieve Redis physical node connection status and cached keys size
    redis_status = {}
    redis_keys_count = 0
    for node, client in ring.redis_clients.items():
        try:
            await client.ping()
            keys_size = await client.dbsize()
            redis_status[node] = {
                "status": "healthy",
                "cached_keys": keys_size
            }
            redis_keys_count += keys_size
        except:
            redis_status[node] = {
                "status": "unreachable",
                "cached_keys": 0
            }
            
    # Database total queries count
    try:
        total_queries_count = db.query(SearchQuery).count()
    except:
        total_queries_count = 0
            
    return {
        "suggest_metrics": {
            "total_calls": total_suggests,
            "cache_hits": hits,
            "cache_misses": misses,
            "cache_hit_rate_percentage": hit_rate,
            "latency_ms": suggest_perf
        },
        "search_metrics": {
            "total_calls": batch_stats["total_searches_received"],
            "latency_ms": search_perf
        },
        "database_metrics": {
            "total_queries_in_db": total_queries_count,
            "db_reads": db_reads,
            "db_writes": batch_stats["total_db_writes_performed"],
            "flush_count": batch_stats["flush_count"],
            "average_batch_size": batch_stats["average_batch_size"],
            "batch_write_reduction_percentage": batch_stats["write_reduction_percentage"]
        },
        "redis_metrics": {
            "total_cached_keys": redis_keys_count,
            "nodes_health": redis_status,
            "ring_distribution": ring.get_ring_distribution()
        },
        "queue_metrics": {
            "background_queue_length": batch_stats["buffer_current_size"]
        }
    }


@app.get("/metrics/prometheus")
async def prometheus_metrics(db: Session = Depends(get_db)):
    """
    Exposes simulated/formatted Prometheus text metrics.
    Fits production deployments for scraping.
    """
    async with metrics_lock:
        hits = METRICS["suggest_hits"]
        misses = METRICS["suggest_misses"]
        reads = METRICS["db_reads"]
        suggest_lats = METRICS["suggest_latencies"]
        
    avg_lat_ms = (sum(suggest_lats) / len(suggest_lats) * 1000) if suggest_lats else 0.0
    batch_stats = batch_writer.get_metrics()
    
    try:
        db_queries = db.query(SearchQuery).count()
    except:
        db_queries = 0
        
    prometheus_data = [
        "# HELP prefixiq_suggest_requests_total Total autocomplete suggestions requests.",
        "# TYPE prefixiq_suggest_requests_total counter",
        f"prefixiq_suggest_requests_total {hits + misses}",
        
        "# HELP prefixiq_cache_hits_total Total suggestions successfully served from Redis cache.",
        "# TYPE prefixiq_cache_hits_total counter",
        f"prefixiq_cache_hits_total {hits}",
        
        "# HELP prefixiq_cache_misses_total Total suggestions that missed Redis cache and fell back to DB.",
        "# TYPE prefixiq_cache_misses_total counter",
        f"prefixiq_cache_misses_total {misses}",
        
        "# HELP prefixiq_suggest_latency_average_ms Average autocomplete API latency in milliseconds.",
        "# TYPE prefixiq_suggest_latency_average_ms gauge",
        f"prefixiq_suggest_latency_average_ms {round(avg_lat_ms, 3)}",
        
        "# HELP prefixiq_searches_submitted_total Total searches submitted by users.",
        "# TYPE prefixiq_searches_submitted_total counter",
        f"prefixiq_searches_submitted_total {batch_stats['total_searches_received']}",
        
        "# HELP prefixiq_db_writes_total Total write statements executed on PostgreSQL database.",
        "# TYPE prefixiq_db_writes_total counter",
        f"prefixiq_db_writes_total {batch_stats['total_db_writes_performed']}",
        
        "# HELP prefixiq_db_reads_total Total read queries executed on PostgreSQL database.",
        "# TYPE prefixiq_db_reads_total counter",
        f"prefixiq_db_reads_total {reads}",
        
        "# HELP prefixiq_db_queries_count Total search keywords registered in queries table.",
        "# TYPE prefixiq_db_queries_count gauge",
        f"prefixiq_db_queries_count {db_queries}",
        
        "# HELP prefixiq_batch_writer_flushes_total Total times batch writer has flushed queue to database.",
        "# TYPE prefixiq_batch_writer_flushes_total counter",
        f"prefixiq_batch_writer_flushes_total {batch_stats['flush_count']}",
        
        "# HELP prefixiq_batch_queue_length Current size of the in-memory batch write buffer.",
        "# TYPE prefixiq_batch_queue_length gauge",
        f"prefixiq_batch_queue_length {batch_stats['buffer_current_size']}"
    ]
    
    return Response(content="\n".join(prometheus_data) + "\n", media_type="text/plain")
