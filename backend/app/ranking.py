from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Tuple
from .config import settings

def get_suggestions_basic(db: Session, prefix: str, limit: int = 10) -> List[Tuple[str, int, float]]:
    """
    Basic Ranking Engine:
    Orders matching queries in the queries table by lifetime count.
    
    Returns: List of tuples (query, search_count, score)
    """
    normalized_prefix = prefix.strip().lower()
    prefix_pattern = f"{normalized_prefix}%"
    
    sql = text("""
        SELECT query, search_count, CAST(search_count AS FLOAT) as score
        FROM queries
        WHERE query LIKE :pattern
        ORDER BY search_count DESC
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
    
    This ensures historical counts remain stable and do not decay to zero,
    while sudden bursts of recent search traffic generate a temporary boost.
    """
    normalized_prefix = prefix.strip().lower()
    prefix_pattern = f"{normalized_prefix}%"
    
    # Left join queries with search_logs by query_id filtered to the last 24 hours.
    # Group by queries.id to aggregate decay scores.
    sql = text("""
        SELECT q.query, q.search_count,
               (0.8 * LN(q.search_count + 1) + 0.2 * COALESCE(SUM(EXP(-:decay_rate * EXTRACT(EPOCH FROM (NOW() - l.searched_at)))), 0)) as score
        FROM queries q
        LEFT JOIN search_logs l ON q.id = l.query_id AND l.searched_at >= NOW() - INTERVAL '24 hours'
        WHERE q.query LIKE :pattern
        GROUP BY q.id, q.query, q.search_count
        ORDER BY score DESC, q.search_count DESC
        LIMIT :limit
    """)
    
    result = db.execute(sql, {
        "pattern": prefix_pattern, 
        "decay_rate": settings.DECAY_RATE,
        "limit": limit
    }).fetchall()
    return [(row.query, row.search_count, row.score) for row in result]
