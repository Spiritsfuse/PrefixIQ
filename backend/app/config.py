from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/prefixiq"
    # Comma-separated list of Redis node addresses
    REDIS_NODES: str = "redis-1:6379,redis-2:6379,redis-3:6379"
    # Batch writer settings
    BATCH_FLUSH_INTERVAL: float = 5.0  # seconds
    BATCH_SIZE_THRESHOLD: int = 100
    # Decaying parameter lambda for trending queries scoring: Score = Score * exp(-lambda * dt_seconds)
    # 0.0001 means a half life of about 6931 seconds (~1.9 hours)
    DECAY_RATE: float = 0.0001
    
    @property
    def redis_node_list(self) -> List[str]:
        return [node.strip() for node in self.REDIS_NODES.split(",") if node.strip()]

    class Config:
        env_file = ".env"

settings = Settings()
