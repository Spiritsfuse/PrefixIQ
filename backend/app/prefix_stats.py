import sys
from sqlalchemy import text
from .database import SessionLocal

def analyze_prefixes():
    prefixes = ["a", "ap", "iph", "java", "python", "data", "machine"]
    db = SessionLocal()
    try:
        total_queries = db.execute(text("SELECT COUNT(*) FROM queries")).scalar()
        print(f"Total queries in database: {total_queries}")
        print("-" * 50)
        print(f"{'Prefix':<10} | {'Total Matches':<15} | {'Suggestions Returned':<20}")
        print("-" * 50)
        for prefix in prefixes:
            pattern = f"{prefix}%"
            # Total matches
            total_matches = db.execute(
                text("SELECT COUNT(*) FROM queries WHERE query LIKE :pattern"),
                {"pattern": pattern}
            ).scalar()
            
            # Limit 10 count
            suggestions_returned = db.execute(
                text("SELECT COUNT(*) FROM (SELECT id FROM queries WHERE query LIKE :pattern LIMIT 10) sub"),
                {"pattern": pattern}
            ).scalar()
            
            print(f"{prefix:<10} | {total_matches:<15} | {suggestions_returned:<20}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    analyze_prefixes()
