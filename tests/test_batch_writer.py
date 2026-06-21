import pytest
from backend.app.batch_writer import BatchWriter

@pytest.mark.asyncio
async def test_batch_writer_queue_buffering():
    writer = BatchWriter()
    
    # Verify starting conditions
    assert writer.queue.empty()
    assert writer.total_searches_received == 0
    assert writer.total_db_writes_performed == 0
    
    # Buffer queries (including duplicate entries)
    writer.push("iphone")
    writer.push("iphone 15")
    writer.push("iphone")  # duplicate
    writer.push("react tutorial")
    
    # Verify in-memory buffer state
    assert writer.queue.qsize() == 4
    assert writer.total_searches_received == 4
    
    # Verify that metrics correctly reflect reduction before flushing
    metrics = writer.get_metrics()
    assert metrics["total_searches_received"] == 4
    assert metrics["buffer_current_size"] == 4
    assert metrics["total_db_writes_performed"] == 0
    assert metrics["write_reduction_percentage"] == 100.0  # 1 - 0/4 = 100% reduction before flush
