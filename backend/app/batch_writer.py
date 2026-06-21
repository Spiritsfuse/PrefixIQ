import asyncio
import time
import logging
from typing import Dict, List, Set, Optional
from sqlalchemy import text
from .database import SessionLocal
from .models import SearchLog
from .config import settings
from .consistent_hashing import ring

logger = logging.getLogger(__name__)

class BatchWriter:
    def __init__(self):
        """
        Initializes the BatchWriter background service.
        Uses an asyncio Queue to buffer search submissions in-memory.
        """
        self.queue = asyncio.Queue()
        
        # Performance & Operation Metrics
        self.total_searches_received = 0
        self.total_db_writes_performed = 0  # Number of row updates/inserts in queries table
        self.flush_count = 0
        self.total_items_flushed = 0
        
        self.is_running = False
        self._worker_task: Optional[asyncio.Task] = None
        
    def push(self, query: str):
        """
        Pushes a query to the buffer.
        Executed synchronously in O(1) from the request thread.
        """
        normalized_query = query.strip().lower()
        if not normalized_query:
            return
            
        self.queue.put_nowait(normalized_query)
        self.total_searches_received += 1
        
    async def start(self):
        """
        Starts the background worker task.
        """
        if not self.is_running:
            self.is_running = True
            self._worker_task = asyncio.create_task(self._worker_loop())
            logger.info("[BatchWriter] Background worker task started.")
            
    async def stop(self):
        """
        Stops the worker thread and forces a final flush of remaining buffered keys.
        """
        if self.is_running:
            self.is_running = False
            if self._worker_task:
                self._worker_task.cancel()
                try:
                    await self._worker_task
                except asyncio.CancelledError:
                    pass
            # Force final flush of remaining items
            await self.flush()
            logger.info("[BatchWriter] Worker task stopped and queue flushed.")
            
    async def _worker_loop(self):
        """
        Background loop executing periodically to check flush thresholds.
        """
        last_flush = time.time()
        while self.is_running:
            try:
                # Check queue every 500ms
                await asyncio.sleep(0.5)
                
                queue_len = self.queue.qsize()
                time_since_flush = time.time() - last_flush
                
                if queue_len > 0:
                    # Flush if queue exceeds threshold OR elapsed time exceeds flush interval
                    if queue_len >= settings.BATCH_SIZE_THRESHOLD or time_since_flush >= settings.BATCH_FLUSH_INTERVAL:
                        await self.flush()
                        last_flush = time.time()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[BatchWriter] Exception in worker loop: {e}", exc_info=True)
                
    async def flush(self):
        """
        Performs the database updates.
        Aggregates items to reduce write complexity, inserts queries,
        uses SQL RETURNING to map ids, bulk inserts logs, and runs cache invalidation.
        """
        if self.queue.empty():
            return
            
        # Drain the queue
        batch_queries: List[str] = []
        while not self.queue.empty():
            batch_queries.append(await self.queue.get())
            self.queue.task_done()
            
        if not batch_queries:
            return
            
        # Aggregate counts
        aggregated: Dict[str, int] = {}
        for q in batch_queries:
            aggregated[q] = aggregated.get(q, 0) + 1
            
        # Establish DB session
        db = SessionLocal()
        query_ids: Dict[str, int] = {}
        
        try:
            # 1. UPSERT aggregate counts in the queries table, returning the primary key ID.
            # Using RETURNING id lets us map queries to logs in a single relational operation.
            for q, count in aggregated.items():
                res = db.execute(
                    text("""
                        INSERT INTO queries (query, search_count, updated_at)
                        VALUES (:query, :count, NOW())
                        ON CONFLICT (query)
                        DO UPDATE SET 
                            search_count = queries.search_count + EXCLUDED.search_count,
                            updated_at = NOW()
                        RETURNING id
                    """),
                    {"query": q, "count": count}
                ).fetchone()
                
                if res:
                    query_ids[q] = res[0]
            
            # 2. Bulk Insert search logs linked via foreign key query_id
            log_entries = [
                {"query_id": query_ids[q]} 
                for q in batch_queries 
                if q in query_ids
            ]
            
            if log_entries:
                db.bulk_insert_mappings(SearchLog, log_entries)
            
            # Commit atomic database transaction
            db.commit()
            
            # Update metrics
            self.flush_count += 1
            self.total_items_flushed += len(batch_queries)
            self.total_db_writes_performed += len(aggregated)
            
            logger.info(f"[BatchWriter] Flushed {len(batch_queries)} entries in {len(aggregated)} DB writes. Total flushes: {self.flush_count}")
            
            # 3. Active Prefix Cache Invalidation
            # We invalidate prefix keys on the designated Redis node for each updated query.
            # We do this asynchronously to avoid blocking the main worker loop.
            asyncio.create_task(self.invalidate_prefixes_for_batch(aggregated.keys()))
            
        except Exception as e:
            db.rollback()
            logger.error(f"[BatchWriter] Transaction failed during flush: {e}", exc_info=True)
        finally:
            db.close()
            
    async def invalidate_prefixes_for_batch(self, queries: Set[str]):
        """
        Generates and deletes all prefix cache combinations for the flushed batch of queries.
        E.g., "iphone charger" -> deletes "i", "ip", ..., "iphone charger" across the hash ring.
        """
        for query in queries:
            normalized = query.strip().lower()
            if not normalized:
                continue
            
            # Compute all prefixes
            prefixes = [normalized[:i] for i in range(1, len(normalized) + 1)]
            
            for prefix in prefixes:
                for mode in ["basic", "enhanced"]:
                    cache_key = f"suggest:{mode}:{prefix}"
                    try:
                        # Locate correct Redis client using Consistent Hashing
                        client, node, _ = await ring.get_client(prefix)
                        await client.delete(cache_key)
                    except Exception as e:
                        # Log error but continue so other invalidations succeed
                        logger.warning(f"[Cache Invalidate Error] Failed to delete key '{cache_key}': {e}")

    def get_metrics(self) -> dict:
        """
        Calculates batching and write reduction metrics.
        """
        reduction = 0.0
        if self.total_searches_received > 0:
            reduction = 1.0 - (self.total_db_writes_performed / self.total_searches_received)
            
        avg_batch = 0.0
        if self.flush_count > 0:
            avg_batch = self.total_items_flushed / self.flush_count
            
        return {
            "total_searches_received": self.total_searches_received,
            "total_db_writes_performed": self.total_db_writes_performed,
            "flush_count": self.flush_count,
            "average_batch_size": round(avg_batch, 2),
            "buffer_current_size": self.queue.qsize(),
            "write_reduction_percentage": round(reduction * 100, 2)
        }

# Global singleton instance
batch_writer = BatchWriter()
