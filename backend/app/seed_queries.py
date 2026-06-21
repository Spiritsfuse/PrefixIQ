import os
import csv
import sys
from sqlalchemy.orm import Session
from .database import SessionLocal, engine, Base
from .models import SearchQuery

def seed_historical_queries():
    """
    Seeds the PostgreSQL database with the preprocessed ORCAS historical queries 
    from the CSV file, preserving the Zipfian distribution counts.
    """
    db = SessionLocal()
    try:
        # Create all tables if they don't exist
        Base.metadata.create_all(bind=engine)
        
        # Check if already seeded
        queries_count = db.query(SearchQuery).count()
        if queries_count >= 100000:
            print(f"[Seed Queries] Database already seeded with {queries_count} queries. Skipping.")
            return
            
        possible_paths = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "orcas_queries.csv")), # local dev path relative to seed_queries.py
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "orcas_queries.csv")),       # Docker path relative to backend app
            os.path.abspath(os.path.join(os.getcwd(), "data", "orcas_queries.csv")),                            # CWD/data/
            "/app/data/orcas_queries.csv",                                                                     # Docker absolute path
        ]
        
        csv_path = None
        for p in possible_paths:
            if os.path.exists(p):
                csv_path = p
                break
                
        if not csv_path:
            print(f"[Seed Queries] ERROR: CSV dataset not found in any expected location: {possible_paths}")
            sys.exit(1)
            
        print(f"[Seed Queries] Seeding queries from {csv_path}...")
        
        batch_size = 10000
        queries_batch = []
        
        with open(csv_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            count = 0
            
            for row in reader:
                queries_batch.append({
                    "query": row["query"],
                    "search_count": int(row["count"])
                })
                
                if len(queries_batch) >= batch_size:
                    db.bulk_insert_mappings(SearchQuery, queries_batch)
                    db.commit()
                    count += len(queries_batch)
                    print(f"[Seed Queries] Seeded {count} queries...")
                    queries_batch = []
                    
            if queries_batch:
                db.bulk_insert_mappings(SearchQuery, queries_batch)
                db.commit()
                count += len(queries_batch)
                print(f"[Seed Queries] Seeded {count} queries...")
                
        print(f"[Seed Queries] SUCCESS: Seeding of {count} historical queries complete.")
    except Exception as e:
        db.rollback()
        print(f"[Seed Queries] ERROR during seeding: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    seed_historical_queries()
