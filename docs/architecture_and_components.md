# System Architecture & Core Components

This document describes the structural layout, component boundaries, and request flows of the PrefixIQ Search Typeahead System.

---

## 1. Overall System Architecture

The system consists of a Next.js frontend, a FastAPI backend, a PostgreSQL relational database, and three independent Redis instances representing logical cache shards.

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

---

## 2. Request Flows

### 2.1 Suggestion Request Flow (`GET /suggest`)
```mermaid
sequenceDiagram
    autonumber
    actor User as User Browser
    participant FE as Next.js Client
    participant BE as FastAPI Backend
    participant Ring as Hash Ring Router
    participant Redis as Redis Node (Routed)
    participant DB as PostgreSQL DB

    User->>FE: Types character (e.g. 'ip')
    Note over FE: Wait 300ms (Debounce)
    FE->>BE: GET /suggest?q=ip&mode=basic
    BE->>Ring: Map 'ip' to target node
    Ring-->>BE: Returns redis-2 Client
    BE->>Redis: GET suggest:basic:ip
    alt Cache Hit
        Redis-->>BE: Returns cached JSON suggestions
        BE-->>FE: Returns suggestions (source: 'cache')
    else Cache Miss
        BE->>DB: SQL prefix query
        DB-->>BE: Returns top matching records
        BE->>Redis: SETEX suggest:basic:ip 60s JSON
        BE-->>FE: Returns suggestions (source: 'database')
    end
    FE->>User: Displays suggestions dropdown
```

### 2.2 Search Submission & Batch Write Flow
```mermaid
sequenceDiagram
    autonumber
    actor User as User Browser
    participant FE as Next.js Client
    participant BE as FastAPI Backend
    participant Q as Async Queue (BatchWriter)
    participant Worker as Background Task
    participant DB as PostgreSQL DB
    participant Redis as Redis Ring Nodes

    User->>FE: Clicks Search / Press Enter
    FE->>BE: POST /search {query: "iphone"}
    BE->>Q: Pushes "iphone" to Queue
    BE-->>FE: Returns {"message": "Searched"}
    Note over FE: Display simulated search result page instantly

    Note over Worker: Checked every 500ms
    loop Flush Check (Queue Size >= 100 OR Time >= 5s)
        Worker->>Q: Drain all queued searches
        Note over Worker: Aggregate counts (e.g., {"iphone": 5})
        Worker->>DB: SQL UPSERT (queries table)
        Note over DB: ON CONFLICT UPDATE search_count
        DB-->>Worker: Returns Primary Key IDs
        Worker->>DB: Bulk insert logs into search_logs
        Worker->>Redis: Invalidate all prefixes ('i', 'ip', 'iph', etc.)
    end
```

---

## 3. Core Components Detail

### 3.1 Consistent Hash Ring (`consistent_hashing.py`)
- **Key Ring Concept**: Physical Redis servers are positioned on a ring mapped to a 32-bit integer space ($0$ to $2^{32}-1$).
- **Replication**: To ensure uniform distribution, each physical node generates 100 virtual nodes (e.g., `redis-1-replica-0` to `redis-1-replica-99`) on the ring.
- **Routing**: A prefix's SHA-256 hash maps to a point on the ring. The router performs a binary search (`bisect_right`) to find the next available virtual node clockwise, resolving to its physical host.

### 3.2 Relational Database Schema (`models.py`)
Data is stored relationally using two tables:
- **`queries`**: Contains aggregate query counts used for autocomplete suggestion lookups. It features an index optimized for rapid prefix string scans:
  ```sql
  CREATE INDEX idx_queries_query_pattern ON queries(query varchar_pattern_ops);
  ```
- **`search_logs`**: Stores individual timestamped entries of query searches. When a search for a query is flushed, we obtain its mapped `id` from the `queries` table via PostgreSQL `RETURNING id` and bulk-insert an entry in `search_logs`. This supports the recency decay calculations.

### 3.3 Asynchronous Batch Writer (`batch_writer.py`)
The `BatchWriter` buffers search query strings to protect PostgreSQL from concurrent write locks.
- **In-Memory Buffering**: FastAPI endpoints enqueue searches onto an `asyncio.Queue` in $O(1)$ time.
- **Aggregated SQL execution**: The queue is drained and aggregated. Rather than executing $N$ inserts, the worker performs $U$ aggregate updates (where $U$ is the count of unique query strings), executing `INSERT ... ON CONFLICT DO UPDATE`.
- **Active Prefix Cache Invalidation**: To keep cached autocomplete lists accurate, the worker generates all prefixes for each flushed search. For example, for "iphone", it invalidates `"i"`, `"ip"`, `"iph"`, `"ipho"`, `"iphon"`, `"iphone"` across the Redis shards.
