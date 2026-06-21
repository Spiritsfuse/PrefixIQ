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
    prefix: str
    hash_value: str
    assigned_node: str
    cache_hit: bool
    suggestions: List[SuggestionItem]
    ring_distribution: Dict[str, str]  # Physical node to hash-ranges/vnode-counts
