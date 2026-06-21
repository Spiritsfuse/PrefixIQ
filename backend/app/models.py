from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, func
from .database import Base

class SearchQuery(Base):
    """
    SearchQuery stores the aggregate historical count for search terms.
    Table: queries
    """
    __tablename__ = "queries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(String, unique=True, nullable=False, index=True)
    search_count = Column(Integer, default=1, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# Index optimized for character-by-character prefix matches (e.g. query LIKE 'pref%')
Index(
    "idx_queries_query_pattern",
    SearchQuery.query,
    postgresql_ops={"query": "varchar_pattern_ops"}
)

class SearchLog(Base):
    """
    SearchLog stores individual search events to compute decayed trending popularity.
    Table: search_logs
    """
    __tablename__ = "search_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(Integer, ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, index=True)
    searched_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
