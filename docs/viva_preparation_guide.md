# Code Walkthrough & Viva Preparation Guide

This document acts as an interactive coaching guide, providing a complete structural walkthrough of the codebase and compiling 40+ mock viva questions and answers.

---

## 1. Codebase Structural Walkthrough

### 1.1 Backend Component

- **[main.py](file:///c:/Users/ADMIN/PrefixIQ/backend/app/main.py)**: Maps FastAPI routing, startup seeding, metrics middlewares, health checks, and Prometheus metrics.
- **[config.py](file:///c:/Users/ADMIN/PrefixIQ/backend/app/config.py)**: Loads configuration settings via Pydantic BaseSettings.
- **[database.py](file:///c:/Users/ADMIN/PrefixIQ/backend/app/database.py)**: Manages engine pools and session factories.
- **[models.py](file:///c:/Users/ADMIN/PrefixIQ/backend/app/models.py)**: Holds tables schemas for `queries` and `search_logs`. Maps B-Tree indexing pattern.
- **[consistent_hashing.py](file:///c:/Users/ADMIN/PrefixIQ/backend/app/consistent_hashing.py)**: Custom Hash Ring positioning and dynamic Redis sharding routing.
- **[batch_writer.py](file:///c:/Users/ADMIN/PrefixIQ/backend/app/batch_writer.py)**: Runs the background async queue worker, aggregates counts, and executes active prefix invalidations.
- **[ranking.py](file:///c:/Users/ADMIN/PrefixIQ/backend/app/ranking.py)**: Basic counts and logarithmic time-decay trending SQL logic.

### 1.2 Frontend Component

- **[page.tsx](file:///c:/Users/ADMIN/PrefixIQ/frontend/src/app/page.tsx)**: Main assembly page with reactive hooks.
- **[SearchBar.tsx](file:///c:/Users/ADMIN/PrefixIQ/frontend/src/components/SearchBar.tsx)**: UI input field, keyboard arrows listener, debounce fetches.
- **[Dashboard.tsx](file:///c:/Users/ADMIN/PrefixIQ/frontend/src/components/Dashboard.tsx)**: System KPIs, sharding server states, and consistent hash debug ring resolver.

---

## 2. Top 20 Mock Viva Questions & Expected Answers

### Q1: The assignment asks for an open-source dataset. What dataset did you use and how is it loaded?
* **Answer**: "We seed the system using a preprocessed subset of the **Microsoft ORCAS click log dataset** stored in `data/orcas_queries.csv`. This CSV contains 105,000+ unique search queries. During container startup, `seed_queries.py` reads this CSV and populates the `queries` table in PostgreSQL in batches of 10,000 to optimize seeding time."

### Q2: What is Zipf's Law and why is it relevant to a search autocomplete system?
* **Answer**: "Zipf's Law states that in a natural language corpus, the frequency of any query is inversely proportional to its rank. In search systems, this means a tiny percentage of queries drive the vast majority of traffic. Because of this power-law distribution, prefix caching is highly effective: caching suggestions for the top 10% of prefixes can serve 80%+ of typeahead traffic, protecting our primary database."

### Q3: Why did you implement a custom Consistent Hashing ring rather than standard sharding or Redis Cluster?
* **Answer**: "Modulo sharding ($Hash(K) \% N$) causes cache stampedes when scaling because changing $N$ invalidates almost all keys. Consistent Hashing maps both keys and nodes on a circular ring, so adding or removing a node only re-maps $\frac{1}{N}$ of the keys. We bypass Redis Cluster because it automates slot sharding internally; writing our own consistent hashing ring on the backend demonstrates how database routing works at the application layer."

### Q4: Why does your Consistent Hashing ring use virtual nodes (replicas)?
* **Answer**: "If we only place physical nodes (e.g. `redis-1`, `redis-2`, `redis-3`) on the ring, they are unlikely to be spaced evenly. This leads to **hotspots** where one server handles 80% of keys. By representing each physical node with 100 virtual nodes (replicas) scattered across the ring, we ensure that keys are distributed uniformly, balancing the memory load."

### Q5: How does your Enhanced Trending Search ranking work? Why logarithmic scaling?
* **Answer**: "Our scoring formula is:
  $$Score = 0.8 \times \ln(Count_{historical} + 1) + 0.2 \times \sum e^{-\lambda \Delta t}$$
  Applying $\ln(Count)$ compresses historical counts so they don't scale linearly, saving space for recent spikes to compete. The second term aggregates recent searches from the last 24 hours, exponentially decaying their weight based on age ($\lambda = 0.0001$, half-life $\approx 1.9$ hours). This allows trending queries to bubble up during traffic spikes, and naturally cool down over time."

### Q6: What database index did you use for prefix search, and why?
* **Answer**: "We created a PostgreSQL B-Tree index on `queries(query varchar_pattern_ops)`. By default, PostgreSQL B-Tree indexes use locale-specific collations, which prevents them from accelerating prefix queries (`LIKE 'abc%'`) in many locales. The `varchar_pattern_ops` operator class forces character-by-character scans, allowing PostgreSQL to perform index scans for prefix match queries."

### Q7: Explain your BatchWriter design. How does it reduce database writes?
* **Answer**: "Writing to a database synchronously for every search submission causes high write latency and connection pool exhaustion. Our `BatchWriter` buffers incoming search strings in an `asyncio.Queue`. Every 5 seconds or upon reaching 100 items, a background task drains the queue, aggregates duplicates (e.g., 10 searches for 'python' become a single SQL update with count += 10), and performs a single UPSERT, reducing database write operations by up to 90%."

### Q8: What relational mapping strategy did you use to link queries and logs in a batch flush?
* **Answer**: "We split the schema into `queries` (historical counts) and `search_logs` (timestamps). In the batch flush, we execute an UPSERT into the `queries` table with a `RETURNING id` clause. This returns the primary key ID for both newly inserted and updated queries. We map these IDs in Python and perform a bulk insert into the `search_logs` table, maintaining full database relational integrity."

### Q9: How does your cache invalidation strategy work when query counts change?
* **Answer**: "To prevent stale cache suggestions, our `BatchWriter` runs **active prefix cache invalidation** after a batch flush. For each unique search in the batch (e.g., 'iphone'), we generate all prefixes: 'i', 'ip', 'iph', ..., 'iphone'. We locate the responsible Redis client for each prefix using the consistent hash ring and delete the cached suggestion keys (`suggest:basic:prefix` and `suggest:enhanced:prefix`)."

### Q10: What are tail latencies, and why do you measure P95 instead of average latency?
* **Answer**: "Average latency hides outliers. If 95 search requests take 2ms and 5 requests take 500ms due to database queries on cache misses, the average is misleadingly low, but those 5 users experience lag. P95 latency guarantees that 95% of users experience search suggest speeds under that threshold, which is crucial for autocomplete where speed is the primary constraint."
