# Assignment: Build a Search Typeahead System

## 1. Overview

In this assignment, students will build a search typeahead system similar to the suggestion feature seen in search engines, e-commerce platforms, and content platforms.

The system should:

- Suggest popular search queries while the user is typing.
- Support search submissions.
- Update query popularity.
- Use caching to achieve low-latency reads.

The focus of this assignment is backend data-system design:

- How query-count data is stored.
- How suggestions are served quickly.
- How cache distribution is handled.
- How write pressure is reduced.

---

## 2. Problem Statement

Build a working search typeahead application with the following capabilities:

1. When a user types in the search box, the system should show 10 suggestions sorted by search count.
2. The application should include a UI interface for searching and displaying suggestions.
3. The backend should expose a dummy search API that returns a response such as `"Searched"`.
4. Whenever a search is submitted, the search-query data store should be updated.
5. Students should design how query-count data is stored and how caching is used for low latency.
6. The cache layer should be distributed using consistent hashing.
7. The system should support trending searches.
8. The system should support batch writes for search-count updates.

---

## 3. Dataset Requirement

Students may use any open-source dataset containing search queries, keywords, product names, page titles, or similar text entries.

The dataset should include a count or frequency value for each query.

If the chosen dataset does not already include counts, students may derive counts through aggregation.

### Expected Input Format

| Query | Count |
|---------|---------|
| iphone | 100000 |
| iphone 15 | 85000 |
| iphone charger | 60000 |
| java tutorial | 40000 |

**Minimum expected dataset size:** 100,000 queries.

Larger datasets are encouraged.

---

# 4. Functional Requirements

## 4.1 Typeahead Suggestions

When a user types a prefix in the search box, the system should return suggestions matching that prefix.

Requirements:

- Return at most 10 suggestions.
- Suggestions must start with the typed prefix.
- Suggestions must be sorted by count in descending order.
- Handle empty input, missing input, mixed-case input, and prefixes with no matches gracefully.
- Avoid unnecessary backend calls (e.g., by debouncing).

---

## 4.2 Search Submission

When a user submits a search:

- If the query already exists, its count should increase.
- If the query does not exist, insert it with an initial count.
- The dummy search API should return:

```json
{
  "message": "Searched"
}
```

- Updated counts should eventually be reflected in suggestions and trending searches.

---

# 5. API Expectations

| API | Purpose | Expected Behavior |
|------|----------|------------------|
| GET /suggest?q=<prefix> | Fetch suggestions | Returns up to 10 prefix-matching suggestions sorted by count |
| POST /search | Submit search | Returns "Searched" and records submitted query |
| GET /cache/debug?prefix=<prefix> | Debug cache routing | Shows cache node responsible for prefix and hit/miss |

---

# 6. Data Storage and Caching Expectations

Students must decide how to store search-query data and how to serve suggestions with low latency.

Expected design considerations:

- Maintain query-count data reliably.
- Cache frequently requested suggestions.
- Cache suggestion results for prefixes.
- Support cache expiry/invalidation.
- Distribute cache across multiple logical cache nodes.
- Use consistent hashing to determine cache ownership.

---

# 7. Trending Searches

The basic version (60 marks) should return suggestions sorted by overall popularity.

For the additional 20 marks:

Students should incorporate recency into ranking.

Recently searched queries should receive higher priority instead of relying solely on all-time counts.

Students should explain:

1. How recent searches are tracked.
2. How recent activity affects ranking.
3. How short-term spikes are prevented from permanently dominating rankings.
4. How cache updates or invalidation occur when rankings change.
5. Trade-offs between freshness, latency, and complexity.

### Core API Remains

```http
GET /suggest?q=<prefix>
```

### Basic Version

- Sort matching suggestions by overall count.

### Enhanced Version

- Sort matching suggestions using a recency-aware ranking mechanism.

Students should demonstrate differences between both ranking methods using sample data or logs.

---

# 8. Batch Writes

Students must support batch writes for search-count updates.

Goal:

Avoid writing to the primary database synchronously for every search request.

Requirements:

- Collect search submissions in a buffer, queue, log, or similar mechanism.
- Aggregate repeated queries before writing.
- Periodically flush updates or flush when batch size threshold is reached.
- Demonstrate reduced database writes.
- Discuss failure scenarios and trade-offs.

---

# 9. UI Requirements

The UI should include:

- Search input box.
- Suggestion dropdown updated while typing.
- Search submission using Enter or Search button.
- Display dummy search response.
- Trending searches section.
- Loading and error states.
- Keyboard navigation support.
- Clean and usable layout.

---

# 10. Non-Functional Expectations

- System should be easy to run locally.
- Suggestion API should be optimized for low latency.
- Students should measure and report latency (preferably P95).
- Avoid duplicate reads/writes when possible.
- Include logs or explanations demonstrating consistent hashing.
- Code should be modular, readable, and documented.

---

# 11. Use of AI and Academic Integrity

AI tools are allowed.

However:

Students remain fully responsible for understanding their submission.

After submission, students should be able to explain:

- Data modeling decisions.
- Caching design.
- Consistent hashing.
- Trending search computation.
- Batch-write logic.
- Important code snippets.

If a student cannot explain the implementation during viva/mock interviews, the submission may be treated as plagiarism even if the code runs correctly.

---

# 12. Expected Submission

Submit:

- GitHub repository (or equivalent source-code submission).
- README with setup instructions.
- Dataset source and loading instructions.
- Architecture diagram or architecture explanation.
- API documentation.
- Screenshots or demo video.
- Performance report including:
  - Latency
  - Cache hit rate
  - Write reduction from batching
- Design decisions and trade-offs.

---

# 13. Grading Rubric (100 Marks)

| Component | Marks | Expectation |
|------------|---------|-------------|
| Basic Implementation | 60 | Search UI, suggestions API, search API, query-count updates, distributed cache using consistent hashing |
| Trending Searches | 20 | Working trending-search implementation with ranking explanation |
| Batch Writes | 20 | Batching or sampling, write reduction evidence, trade-off discussion |

---

# 14. Suggested Milestones

1. Load dataset and build suggestion API.
2. Build frontend search box and suggestion dropdown.
3. Add dummy search submission and query-count updates.
4. Add distributed cache with consistent hashing.
5. Add trending searches.
6. Add batch writes.
7. Measure performance and prepare final documentation/demo. 