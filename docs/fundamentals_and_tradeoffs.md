# System Fundamentals & Architecture Trade-offs

This document details the computer science fundamentals, engineering decisions, and trade-offs made in the **PrefixIQ Search Typeahead System**.

---

## 1. What is Search Typeahead?

### 1.1 Definition & Context
**Search Typeahead** (also known as Autocomplete or Search Suggestions) is a system feature that predicts and displays matching search queries in real-time as a user types characters into a search input. 

### 1.2 Why Does It Exist?
- **User Experience (UX)**: Saves keystrokes, prevents typos, and guides the user toward queries that are known to produce search results.
- **Search Optimization**: Steers search traffic toward popular, pre-indexed queries, maximizing database search caches and reducing search engine query load.

### 1.3 How Big Tech Implements Similar Systems
- **Google Search**: Processes billions of queries daily. The suggestions are pre-computed offline from historical logs, stored in massive distributed key-value stores, and cached globally at edge nodes (CDNs).
- **Amazon Search**: Autocomplete is heavily focused on product discovery and purchasing intent. Rankings are influenced by search frequency, product categories, and personal purchase history.

---

## 2. Core CS Concepts Explained

### 2.1 Latency Percentiles (P50 vs. P95 vs. P99)
- **Definition**: Percentiles divide a set of sorted latencies into percentage bands. 
  - **P50 (Median)**: 50% of requests are faster than this latency.
  - **P95**: 95% of requests are faster than this latency. Only 5% of requests are slower.
- **Intuition**: In a search system, the average latency is a deceptive metric. If 99 requests take 2ms and 1 request takes 2000ms, the average is 22ms. P50 is 2ms, but P95 represents the "tail latency" experienced by users with slower routing or cache misses. We optimize for P95 latency because search suggestions must feel instant to *everyone*.

### 2.2 Debouncing
- **Definition**: A programming pattern that delays invoking a function (like an API fetch) until a specified silent period has elapsed since the last event.
- **Example**: If a user types "iphone" in 600ms, debouncing with a 300ms delay fires only *one* API call after they stop typing, rather than firing 6 separate API calls (`i`, `ip`, `iph`, `ipho`, `iphon`, `iphone`). This reduces network traffic by up to 80%.

### 2.3 Modulo Sharding vs. Consistent Hashing
- **Modulo Sharding**: Routes key `K` using `Hash(K) % N`, where `N` is the number of cache servers.
  - **The Problem**: If `N` changes (a server crashes or is added), almost all keys map to different servers. This triggers a **cache stampede** as thousands of cache misses hit the primary database simultaneously.
- **Consistent Hashing**: Maps both keys and cache servers onto a circular hash ring. Keys are routed clockwise to the nearest server.
  - **The Advantage**: If a server is added or removed, only a small fraction ($\frac{1}{N}$) of keys are re-mapped. This protects the primary database from sudden overload.

---

## 3. Design Decision Matrix

| Technology | Selected | Alternatives | Why Bypassed / Rejected |
|:---|:---|:---|:---|
| **Backend Framework** | **FastAPI** | Express.js, Django, Spring Boot | FastAPI is asynchronous by default, matches Next.js performance, has automatic OpenAPI doc generation, and simplifies writing background tasks. |
| **Primary Database** | **PostgreSQL** | MongoDB, MySQL, Elasticsearch | PostgreSQL supports ACID compliance, relational joins for logs, and a B-Tree index with `varchar_pattern_ops` for fast prefix queries. Elasticsearch was bypassed as over-engineering for a 100k query project. |
| **Distributed Caching** | **Application-Managed Redis** | Memcached, Redis Cluster | We deploy 3 independent Redis instances and manage routing on the backend via Consistent Hashing. We bypass standard "Redis Cluster" because it automates slot sharding, which defeats the academic purpose of implementing our own hash ring. |
| **Prefix Indexing** | **B-Tree Pattern Ops** | In-Memory Python Trie | An in-memory Trie cannot scale horizontally across multiple backend container processes, consumes significant RAM, and does not persist query counts reliably. |
| **Dataset** | **Microsoft ORCAS** | Synthetic Generation | Seeding from a subset of a real open-source corpus (ORCAS) is academically defensible and mimics actual search distributions, unlike 100% synthetic query files. |

---

## 4. Why We Bypassed a Custom Python Trie in Production
A common academic suggestion is: "Why not build a Trie in Python memory?"
During a viva, defend our SQL + Redis architecture using these points:
1. **Horizontal Scalability**: A Trie in Python memory is local to a single process. If we run 4 backend container replicas behind a load balancer, they cannot easily synchronize write increments.
2. **Memory Efficiency**: In-memory Tries consume large amounts of memory due to object overhead. PostgreSQL and Redis manage memory in highly optimized C-based structures.
3. **Persistency and ACID**: A python-implemented Trie must write to disk to prevent data loss on crashes. Using PostgreSQL guarantees transactional safety and crash durability.
4. **Production Standard**: Large search platforms do not build custom in-memory Tries for global search indexes. They use pre-computed index tables (like PostgreSQL B-Tree) and distribute matches using cache keys.
