from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Tuple
from .config import settings

def get_suggestions_basic(db: Session, prefix: str, limit: int = 10) -> List[Tuple[str, int, float]]:
    """
    Basic Ranking Engine:
    Orders matching queries in the queries table by lifetime count.
    Uses the query string alphabetically as a tie-breaker for deterministic sorting.
    
    Returns: List of tuples (query, search_count, score)
    """
    normalized_prefix = prefix.strip().lower()
    prefix_pattern = f"{normalized_prefix}%"
    
    sql = text("""
        SELECT query, search_count, CAST(search_count AS FLOAT) as score
        FROM queries
        WHERE query LIKE :pattern
        ORDER BY search_count DESC, query ASC
        LIMIT :limit
    """)
    
    result = db.execute(sql, {"pattern": prefix_pattern, "limit": limit}).fetchall()
    return [(row.query, row.search_count, row.score) for row in result]

def get_suggestions_enhanced(db: Session, prefix: str, limit: int = 10) -> List[Tuple[str, int, float]]:
    """
    Enhanced (Recency-Aware) Ranking Engine:
    Balances long-term historical popularity with short-term traffic spikes.
    
    Scoring Formula:
    Score = 0.8 * LN(historical_count + 1) + 0.2 * SUM( e^(-lambda * dt_seconds) ) 
    for all searches in the last 24 hours.
    
    Tie-breaker is query string alphabetically for deterministic sorting.
    
    For empty prefixes (overall trending), it uses a CTE candidate set (top 1000 by 
    count + active logs) to prevent scanning all 600k+ rows in the queries table.
    """
    normalized_prefix = prefix.strip().lower()
    
    if not normalized_prefix:
        # Optimized query for overall trending (empty prefix) to avoid full table scans
        sql = text("""
            WITH candidates AS (
                (SELECT id, query, search_count 
                 FROM queries 
                 ORDER BY search_count DESC 
                 LIMIT 1000)
                UNION
                (SELECT DISTINCT q.id, q.query, q.search_count 
                 FROM queries q
                 JOIN search_logs l ON q.id = l.query_id 
                 WHERE l.searched_at >= NOW() - INTERVAL '24 hours'
                )
            )
            SELECT c.query, c.search_count,
                   (0.8 * LN(c.search_count + 1) + 0.2 * COALESCE(SUM(EXP(-:decay_rate * EXTRACT(EPOCH FROM (NOW() - l.searched_at)))), 0)) as score
            FROM candidates c
            LEFT JOIN search_logs l ON c.id = l.query_id AND l.searched_at >= NOW() - INTERVAL '24 hours'
            GROUP BY c.id, c.query, c.search_count
            ORDER BY score DESC, c.search_count DESC, c.query ASC
            LIMIT :limit
        """)
        result = db.execute(sql, {
            "decay_rate": settings.DECAY_RATE,
            "limit": limit
        }).fetchall()
    else:
        prefix_pattern = f"{normalized_prefix}%"
        # Standard prefix match with deterministic tie-breaker
        sql = text("""
            SELECT q.query, q.search_count,
                   (0.8 * LN(q.search_count + 1) + 0.2 * COALESCE(SUM(EXP(-:decay_rate * EXTRACT(EPOCH FROM (NOW() - l.searched_at)))), 0)) as score
            FROM queries q
            LEFT JOIN search_logs l ON q.id = l.query_id AND l.searched_at >= NOW() - INTERVAL '24 hours'
            WHERE q.query LIKE :pattern
            GROUP BY q.id, q.query, q.search_count
            ORDER BY score DESC, q.search_count DESC, q.query ASC
            LIMIT :limit
        """)
        result = db.execute(sql, {
            "pattern": prefix_pattern, 
            "decay_rate": settings.DECAY_RATE,
            "limit": limit
        }).fetchall()
        
    return [(row.query, row.search_count, row.score) for row in result]
