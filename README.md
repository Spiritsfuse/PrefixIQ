# PrefixIQ — Search Typeahead & Distributed Caching System

[![Docker Compose](https://img.shields.io/badge/Docker%20Compose-v3.8-blue?logo=docker&logoColor=white)](https://docs.docker.com/)
[![Next.js](https://img.shields.io/badge/Next.js-v15.0-black?logo=next.js&logoColor=white)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-v0.111-emerald?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-v15.0-blue?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-v7.0-red?logo=redis&logoColor=white)](https://redis.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

PrefixIQ is a complete, production-inspired search suggestion and autocomplete engine designed to showcase core distributed systems, database sharding, write buffering, and recency-decay algorithms.

---

## 🏗️ System Architecture

```mermaid
graph TD
    User["User Browser"]
    Frontend["Next.js Web Client (Port 3000)"]
    Backend["FastAPI Backend Server (Port 8000)"]
    DB[("PostgreSQL DB (Port 5432)")]
    
    subgraph Caching Layer
        Ring["Consistent Hash Ring Router"]
        Redis1[("Redis Node 1 (Port 6379)")]
        Redis2[("Redis Node 2 (Port 6380)")]
        Redis3[("Redis Node 3 (Port 6381)")]
    end

    User -->|Queries & Submits| Frontend
    Frontend -->|GET /suggest & POST /search| Backend
    Backend -->|Key Hash Mapping| Ring
    Ring -->|Route to redis-1| Redis1
    Ring -->|Route to redis-2| Redis2
    Ring -->|Route to redis-3| Redis3
    
    Backend -->|Asynchronous Batch UPSERT| DB
    Backend -->|Direct SQL Fallback| DB
```

### Architectural Component Interaction
- **Autocomplete Suggestions**: The Next.js frontend client debounces inputs (300ms) and queries `GET /suggest`. The backend maps the query prefix onto a consistent hashing ring, checks the assigned Redis instance, and falls back to PostgreSQL on a cache miss, caching the result back in Redis.
- **Asynchronous Batching**: User search submissions trigger a non-blocking `POST /search`. The backend enqueues the search string into an in-memory queue. A background task aggregates counts, runs bulk database UPSERTs, maps relational search log timestamps, and invalidates prefix keys across the Redis shards.

---

## 🚀 Quick Start & Setup Instructions

Ensure you have **Docker** and **Docker Compose** installed.

### 1. Launch the Cluster
Run the following single command in the project root:
```bash
docker compose up --build
```
This starts the PostgreSQL database, three independent Redis cache instances, the FastAPI backend, and the Next.js web client. 

### 2. Access the Applications
- **Frontend Dashboard & Search Box**: http://localhost:3000
- **API Swagger Documentation**: http://localhost:8000/docs
- **Prometheus Metrics Scraper**: http://localhost:8000/metrics/prometheus

---

## 📂 Dataset Source & Loading

PrefixIQ uses a preprocessed query frequency CSV (`data/orcas_queries.csv`) modeled on the **Microsoft ORCAS click log dataset**, consisting of 105,000+ unique search terms distributed according to **Zipf's Law** (Power-Law Distribution). 

The database seeding is fully automated and runs sequentially during backend startup:
1. **Queries Seeder**: `seed_queries.py` reads `data/orcas_queries.csv` in chunks of 10,000 and executes bulk inserts into the `queries` table.
2. **Logs Seeder**: `seed_recent_logs.py` populates the `search_logs` table with synthetic timestamped logs (in the last 2 hours) for 5 specific trending queries to showcase the recency-decay sorting.

To trigger database seeding manually:
```bash
# Seed queries
docker compose exec backend python -m app.seed_queries

# Seed recent trending activity logs
docker compose exec backend python -m app.seed_recent_logs
```

---

## 🔌 API Documentation

### 1. `GET /suggest?q=<prefix>&mode=<basic|enhanced>`
Fetches autocomplete suggestions matching the prefix.
- **Parameters**:
  - `q` (string): Search query prefix (case-insensitive).
  - `mode` (string): `basic` (all-time count sorting) or `enhanced` (decay trending scoring).
- **Response (`200 OK`)**:
  ```json
  {
    "suggestions": [{"query": "iphone charger", "count": 60000, "score": 60000.0}],
    "source": "cache"
  }
  ```

### 2. `POST /search`
Records a search query submission, buffering it to the BatchWriter queue.
- **Payload**: `{"query": "nextjs 15 features"}`
- **Response (`200 OK`)**: `{"message": "Searched"}`

### 3. `GET /cache/debug?prefix=<prefix>&mode=<basic|enhanced>`
Exposes Consistent Hashing routing mapping, virtual nodes, TTL, and uniformity metrics.
- **Response (`200 OK`)**:
  ```json
  {
    "key": "suggest:basic:iph",
    "hash": "8ef4a1b0",
    "assigned_node": "redis-2:6379",
    "virtual_node": "redis-2-replica-43",
    "cache_hit": true,
    "cache_status": "HIT",
    "ttl": 58,
    "suggestions": [...],
    "ring_distribution": {
      "redis-1:6379": "100 virtual nodes",
      "redis-2:6379": "100 virtual nodes",
      "redis-3:6379": "100 virtual nodes"
    },
    "hash_distribution_percentage": {
      "redis-1:6379": 33.42,
      "redis-2:6379": 33.28,
      "redis-3:6379": 33.30
    }
  }
  ```

### 4. `GET /health`
Returns connection status and metrics for all services along with system uptime.
- **Response (`200 OK`)**:
  ```json
  {
    "status": "healthy",
    "services": {
      "postgres": "healthy",
      "redis": {
        "connected": 3,
        "total": 3
      },
      "batch_writer": "running"
    },
    "uptime_seconds": 123.45
  }
  ```

---

## 🛠️ Design Decisions & Trade-offs

- **PostgreSQL B-Tree Operator Class (`varchar_pattern_ops`)**: Standard database indexes utilize locale-specific collation, rendering index range scans useless for character prefix searches (`LIKE 'prefix%'`). We specify a `varchar_pattern_ops` B-Tree index on `queries(query)`, forcing character-by-character scans and enabling fast index range scanning.
- **Application-Managed Redis Sharding**: We sharded keys across 3 independent Redis nodes using consistent hashing with 100 virtual nodes per instance. This prevents cache stampedes when adding/removing nodes by remapping only $\frac{1}{N}$ keys.
- **Logarithmic + Exponential Decay Trending**: The scoring formula balances long-term popularity with recent spikes:
  $$Score = 0.8 \times \ln(Count_{historical} + 1) + 0.2 \times \sum e^{-\lambda \Delta t}$$
  Using the natural logarithm ($\ln$) compresses lifetime counts so they don't scale linearly, allowing recent trends to compete.

---

## 📊 Performance Report

The following performance profile was evaluated under a comparative load of 150 simulated requests running inside the backend container using `benchmarks/run_benchmarks.py`:

| Scenario | Average Latency | P50 (Median) | P95 Latency | Success Rate |
| :--- | :---: | :---: | :---: | :---: |
| **DB Only (Cache Bypassed)** | 34.00 ms | 21.03 ms | 27.81 ms | 150/150 |
| **Cold Redis (Cache Miss)**  | 23.49 ms | 23.08 ms | 29.80 ms | 150/150 |
| **Warm Redis (Cache Hit)**   | 12.35 ms | 12.37 ms | 15.92 ms | 150/150 |

### Batching Write Reduction (Under Load)
- **Total Searches Received**: 150
- **Database Write Statements Executed**: 8 flushes
- **PostgreSQL Write Reduction Factor**: **94.7%**
- **Average Batch Flush Size**: 18.75 searches

---

## 🧪 Verification & Testing
Execute the Pytest unit testing suite inside the backend container:
```bash
docker compose exec backend pytest
```

---

## 🖼️ Media & Demonstration
Screenshots and visual assets demonstrating the Next.js visual dashboard, sharded nodes, and active queue flush animations are compiled in the `/screenshots` directory.

