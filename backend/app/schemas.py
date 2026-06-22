from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class SearchSubmit(BaseModel):
    query: str = Field(..., min_length=1, max_length=255, description="The search query to submit")

class SearchResponse(BaseModel):
    message: str = "Searched"

class SuggestionItem(BaseModel):
    query: str
    count: int
    score: float

class SuggestionResponse(BaseModel):
    suggestions: List[SuggestionItem]
    source: str  # "cache" or "database"

class CacheDebugResponse(BaseModel):
    key: str
    hash: str
    assigned_node: str
    virtual_node: str
    cache_hit: bool
    cache_status: str
    ttl: int
    suggestions: List[SuggestionItem]
    ring_distribution: Dict[str, str]
    hash_distribution_percentage: Dict[str, float]
