# PrefixIQ Master Navigation Index

Welcome to the documentation suite for the **PrefixIQ Search Typeahead System**. This guide provides an entry point to the system design documentation, explaining every module, decision, algorithm, and CS concept to prepare you for your viva and system design interviews.

---

## 1. Document Index

### 🗺️ [Master Navigation Index](file:///c:/Users/ADMIN/PrefixIQ/docs/NAVIGATION.md)
- *Purpose*: The root directory mapping all system document components, dependencies, and viva pathways.

### 📚 [1. System Fundamentals & Trade-offs](file:///c:/Users/ADMIN/PrefixIQ/docs/fundamentals_and_tradeoffs.md)
- *Topics Covered*:
  - What is Search Typeahead? Why does it exist in Google/Amazon/YouTube?
  - Technology decisions: Why FastAPI, PostgreSQL, and sharded Redis?
  - Rejected designs: Why we bypassed Trie databases, Elasticsearch, and MongoDB.
  - CS Glossary: Rate-limiting, TTLs, and P95 latency percentiles.

### 🏗️ [2. System Architecture & Components](file:///c:/Users/ADMIN/PrefixIQ/docs/architecture_and_components.md)
- *Topics Covered*:
  - Unified System Design Layout (Mermaid diagrams).
  - Multi-Redis client routing (Consistent Hashing Ring with 100 virtual nodes).
  - Asynchronous BatchWriter buffering, aggregation UPSERTs, and prefix cache invalidation logic.
  - Split relational schema: `queries` and `search_logs` tables.

### ⚡ [3. Algorithms & Data Distribution](file:///c:/Users/ADMIN/PrefixIQ/docs/trending_and_algorithms.md)
- *Topics Covered*:
  - Baseline dataset: Microsoft ORCAS click logs pre-aggregated using Zipf's Law (power-law distribution).
  - Basic Ranking vs Enhanced Ranking formulas.
  - Recency-aware exponential decay trending:
    $$Score = 0.8 \times \ln(Count_{historical} + 1) + 0.2 \times \sum_{recent} e^{-\lambda \Delta t}$$
  - Dynamic sliding-window limits and cache updates.

### 🐳 [4. Infrastructure & Benchmarking](file:///c:/Users/ADMIN/PrefixIQ/docs/docker_and_performance.md)
- *Topics Covered*:
  - Docker Compose orchestration with PostgreSQL healthchecks.
  - Local benchmark execution script (`benchmarks/run_benchmarks.py`).
  - Scannable Prometheus-style metrics scraping endpoint (`/metrics/prometheus`).

### 🎓 [5. Code Walkthrough & Viva Guide](file:///c:/Users/ADMIN/PrefixIQ/docs/viva_preparation_guide.md)
- *Topics Covered*:
  - Codebase structures: mapping functions, files, and classes.
  - 40+ mock viva questions with comprehensive examiner-grade answers.

---

## 2. Shared Workspace Map

```
/prefixiq
  ├── backend/               # FastAPI Backend Service
  │    ├── app/
  │    │    ├── main.py      # Entry point, Middlewares, API Routers
  │    │    ├── database.py  # SQLAlchemy engine configurations
  │    │    ├── models.py    # relational queries & search_logs schema
  │    │    ├── ranking.py   # basic count & decayed trending scoring logic
  │    │    └── ...
  │    └── Dockerfile
  ├── frontend/              # Next.js Frontend Client
  │    ├── src/
  │    │    ├── components/
  │    │    │    ├── SearchBar.tsx  # Keyboard-navigable autocomplete field
  │    │    │    └── Dashboard.tsx  # Observability counters and sharding chart
  │    │    └── ...
  │    └── Dockerfile
  ├── data/                  # Seeder Datasets
  │    └── orcas_queries.csv # Aggregated MS ORCAS search clicks (105k rows)
  ├── scripts/               # Seeding & Generator Scripts
  │    ├── generate_orcas_csv.py
  │    ├── seed_queries.py
  │    └── seed_recent_logs.py
  ├── tests/                 # Pytest Unit Test Suite
  ├── benchmarks/            # Load-testing scripts
  ├── docs/                  # System Design Specifications
  └── private-docs/          # Viva Cheatsheets (Excluded in .gitignore)
```
