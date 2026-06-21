# Search Suggestions & Recency-Decay Algorithms

This document details the data distribution modeling, baseline seeding corpus, and the ranking algorithms of the PrefixIQ system.

---

## 1. Dataset & Frequency Distribution

### 1.1 Dataset Source (Microsoft ORCAS)
PrefixIQ is seeded with a 105,000-row preprocessed query corpus `data/orcas_queries.csv` modeled on the **Microsoft ORCAS click log dataset**. It contains two columns:
- `query` (search term phrase)
- `count` (historical search frequency)

### 1.2 Zipf's Law (Power-Law Distribution)
Real-world search query distributions follow **Zipf's Law**, which states that the frequency of any query is inversely proportional to its rank in the frequency table.
- **Count Formula**: 
  $$Count(r) = \frac{C}{r^s}$$
  where $r$ is the query rank, $C$ is a scaling constant ($500,000$), and $s \approx 0.92$.
- **Implication**: The top 1% of queries (e.g. "google", "weather") account for a massive percentage of total search traffic, while a long tail of 90%+ queries have very low, sparse frequencies. This is why prefix caches are highly effective: caching the top 10% of prefixes can serve 80%+ of typeahead traffic.

---

## 2. Suggestion Ranking Algorithms

### 2.1 Basic Ranking Engine
Basic ranking queries matches starting with the prefix, sorted purely by lifetime aggregate counts.
- **SQL Execution**:
  ```sql
  SELECT query, search_count
  FROM queries
  WHERE query LIKE 'prefix%'
  ORDER BY search_count DESC
  LIMIT 10;
  ```
- **Limitation**: Highly popular queries (e.g., "iphone" with 500,000 searches) can never be overtaken by newer queries (e.g., "nextjs 15 features" with 5,000 searches), even if the new query has a sudden burst of popularity today.

### 2.2 Enhanced (Recency-Aware) Ranking Engine
To capture trending spikes, the enhanced engine balances historical popularity with recent activity using a time-decay algorithm.
- **Scoring Formula**:
  $$Score(q) = 0.8 \times \ln(Count_{historical} + 1) + 0.2 \times \sum_{i \in \text{recent\_logs}} e^{-\lambda(t_{now} - t_i)}$$
- **Mathematical Rationale**:
  1. **Stable Historical Base**: $0.8 \times \ln(Count + 1)$ compresses the scale. A count of 100,000 gives a score of $\approx 9.2$, while a count of 500,000 gives a score of $\approx 10.5$. This prevents large numbers from scaling linearly, allowing recent trends to compete.
  2. **Exponential Recency Decay**: Each recent search log entry (in the last 24 hours) is decayed exponentially based on age in seconds: $e^{-\lambda \Delta t}$.
     - We set $\lambda = 0.0001$.
     - Half-life of a search log: $t_{1/2} = \frac{\ln(2)}{\lambda} \approx 6,931 \text{ seconds} \approx 1.92 \text{ hours}$.
     - A search from 10 minutes ago ($\Delta t = 600$s) adds $e^{-0.06} \approx 0.94$ to the score.
     - A search from 6 hours ago ($\Delta t = 21,600$s) adds $e^{-2.16} \approx 0.11$ to the score.
     - A search from 24 hours ago ($\Delta t = 86,400$s) adds $e^{-8.64} \approx 0.00017$ (virtually zero).

- **SQL Execution**:
  ```sql
  SELECT q.query, q.search_count,
         (0.8 * LN(q.search_count + 1) + 0.2 * COALESCE(SUM(EXP(-:decay_rate * EXTRACT(EPOCH FROM (NOW() - l.searched_at)))), 0)) as score
  FROM queries q
  LEFT JOIN search_logs l ON q.id = l.query_id AND l.searched_at >= NOW() - INTERVAL '24 hours'
  WHERE q.query LIKE :pattern
  GROUP BY q.id, q.query, q.search_count
  ORDER BY score DESC, q.search_count DESC
  LIMIT 10;
  ```

---

## 3. Comparative Ranking Scenario

Suppose the database contains the following records, and we search for prefixes matching `"ch"`:

| Query | Historical Count | Recent Log entries (Last 2 hours) |
|:---|:---|:---|
| **charger** | 60,000 | 0 |
| **chatgpt 5 release date** | 500 | 450 |

### Basic Mode Output (Overall Popularity)
Basic ranking orders purely by historical counts:
1. **charger** (Count: 60,000, Score: 60,000.0)
2. **chatgpt 5 release date** (Count: 500, Score: 500.0)

### Enhanced Mode Output (Recency-decay)
1. **chatgpt 5 release date**
   - Historical Log Term: $0.8 \times \ln(501) \approx 0.8 \times 6.2 \approx 4.96$
   - Recent Decay Term: $450 \text{ logs} \times \approx 0.9 \text{ avg decay} = 405 \text{ decay score}$. Multiply by $0.2 \approx 81.0$.
   - **Total Score**: $4.96 + 81.0 = \mathbf{85.96}$
2. **charger**
   - Historical Log Term: $0.8 \times \ln(60001) \approx 0.8 \times 11.0 \approx 8.8$
   - Recent Decay Term: $0$ (no recent logs).
   - **Total Score**: $8.8 + 0.0 = \mathbf{8.8}$

**Result**: In Enhanced mode, `chatgpt 5 release date` leaps to position #1 because its sudden, concentrated burst of activity overrides the stable historical popularity of `charger`. Over the next few hours, if no new searches occur, the decay score will return to $0$, and `charger` will automatically reclaim the #1 spot.
