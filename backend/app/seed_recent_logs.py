import random
import sys
from datetime import datetime, timedelta
from sqlalchemy import text
from .database import SessionLocal
from .models import SearchQuery, SearchLog

def seed_recent_activity():
    """
    Seeds the search_logs table with concentrated search log timestamps 
    in the last 2 hours for specific trending queries. This demonstrates 
    the recency-aware (exponential time-decay) ranking engine.
    """
    db = SessionLocal()
    try:
        # Check if logs table is already seeded
        logs_count = db.query(SearchLog).count()
        if logs_count > 0:
            print(f"[Seed Logs] Database already populated with {logs_count} log entries. Skipping.")
            return
            
        print("[Seed Logs] Seeding trending search spikes...")
        
        # 5 target topics representing recent spikes
        trending_topics = [
            "chatgpt 5 release date",
            "apple vision pro 2 review",
            "room temperature superconductor news",
            "bitcoin price record high",
            "nextjs 15 features"
        ]
        
        topic_ids = {}
        # 1. Ensure target topics exist in queries table and fetch their ids
        for topic in trending_topics:
            # Check if query already exists
            query_row = db.query(SearchQuery).filter(SearchQuery.query == topic).first()
            if not query_row:
                # Insert with baseline historical count
                new_q = SearchQuery(query=topic, search_count=500)
                db.add(new_q)
                db.flush()  # Populates new_q.id
                topic_ids[topic] = new_q.id
            else:
                topic_ids[topic] = query_row.id
                
        # Also select a few baseline popular queries to scatter logs for comparison
        baseline_queries = ["iphone", "python tutorial", "weather in new york", "youtube", "netflix"]
        for bq in baseline_queries:
            query_row = db.query(SearchQuery).filter(SearchQuery.query == bq).first()
            if not query_row:
                new_q = SearchQuery(query=bq, search_count=10000)
                db.add(new_q)
                db.flush()
                topic_ids[bq] = new_q.id
            else:
                topic_ids[bq] = query_row.id
                
        db.commit()
        
        # 2. Generate search log mappings
        logs_to_insert = []
        now = datetime.utcnow()
        
        # Concentrated logs in the last 2 hours for trending topics
        for topic in trending_topics:
            query_id = topic_ids[topic]
            log_count = random.randint(300, 600)
            for _ in range(log_count):
                minutes_ago = random.randint(0, 120)  # within 2 hours
                searched_at = now - timedelta(minutes=minutes_ago)
                logs_to_insert.append({
                    "query_id": query_id,
                    "searched_at": searched_at
                })
                
        # Distributed logs in the last 24 hours for baseline queries
        for bq in baseline_queries:
            query_id = topic_ids[bq]
            log_count = 50  # spread out logs
            for _ in range(log_count):
                hours_ago = random.randint(0, 24)
                searched_at = now - timedelta(hours=hours_ago)
                logs_to_insert.append({
                    "query_id": query_id,
                    "searched_at": searched_at
                })
                
        # 3. Bulk insert log entries
        db.bulk_insert_mappings(SearchLog, logs_to_insert)
        db.commit()
        
        # Output summary info
        print(f"[Seed Logs] SUCCESS: Seeded {len(logs_to_insert)} search log entries for trending query spikes.")
    except Exception as e:
        db.rollback()
        print(f"[Seed Logs] ERROR: Seeding recent activity logs failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    seed_activity = seed_recent_activity()
