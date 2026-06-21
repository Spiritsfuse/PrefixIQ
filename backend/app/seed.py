import random
from datetime import datetime, timedelta
from sqlalchemy import text
from .database import SessionLocal, engine, Base
from .models import SearchQuery, SearchLog

def generate_queries():
    """
    Generates 100,000+ unique, realistic-looking search query strings 
    by combining tech, retail, finance, and general subjects with modifiers.
    """
    subjects = [
        "python", "javascript", "java", "c++", "rust", "go", "react", "nextjs", "vue", "angular",
        "node", "fastapi", "django", "flask", "spring boot", "postgresql", "mysql", "mongodb", "redis", "docker",
        "kubernetes", "aws", "gcp", "azure", "ml", "ai", "deep learning", "nlp", "computer vision", "llm",
        "chatgpt", "bard", "gemini", "copilot", "iphone", "ipad", "macbook", "apple watch", "airpods", "vision pro",
        "samsung galaxy", "google pixel", "playstation", "xbox", "nintendo switch", "rtx 4090", "intel core i9", "amd ryzen", "dell xps", "lenovo thinkpad",
        "nike shoes", "adidas ultra boost", "rolex watch", "tesla model 3", "toyota rav4", "honda civic", "ford mustang", "starbucks coffee", "mcdonalds burger", "coca cola",
        "bitcoin", "ethereum", "solana", "cardano", "ripple", "dogecoin", "nvidia stock", "apple stock", "microsoft stock", "google stock",
        "weather in new york", "weather in london", "weather in tokyo", "weather in delhi", "weather in paris", "flights to hawaii", "flights to rome", "flights to bali", "hotels in vegas", "hotels in london",
        "how to learn", "how to build", "how to code", "how to cook", "how to draw", "how to paint", "how to write", "how to read", "how to play", "how to run"
    ]
    
    modifiers = [
        "tutorial", "course", "guide", "documentation", "examples", "best practices", "vulnerabilities", "interviews", "questions", "answers",
        "for beginners", "advanced", "crash course", "cheatsheet", "roadmap", "books", "roadmap 2026", "jobs", "salary", "projects",
        "review", "comparison", "vs", "alternatives", "pros and cons", "specs", "price", "release date", "leaks", "unboxing",
        "troubleshooting", "errors", "bugs", "fixes", "not working", "setup", "installation", "configuration", "optimization", "performance",
        "cheap", "discount", "promo code", "sale", "online", "store", "near me", "delivery", "shipping", "warranty",
        "news", "updates", "trends", "predictions", "analysis", "history", "facts", "statistics", "benefits", "risks"
    ]
    
    queries = set()
    for s in subjects:
        queries.add(s)
        
    while len(queries) < 100000:
        s = random.choice(subjects)
        m1 = random.choice(modifiers)
        query = f"{s} {m1}"
        queries.add(query)
        
        # Inject occasional triple phrase structures for variety: "best python roadmap for beginners"
        if len(queries) < 100000:
            m2 = random.choice(modifiers)
            if m1 != m2:
                prefix = random.choice(["best", "free", "latest", "how to", "where to buy", ""])
                query = f"{prefix} {s} {m1} {m2}".strip()
                # Normalize spacing
                query = " ".join(query.split())
                queries.add(query)
                
    return list(queries)

def seed_db():
    db = SessionLocal()
    try:
        # Check if seeding is already complete
        # Safe table creation check
        Base.metadata.create_all(bind=engine)
        
        query_count = db.query(SearchQuery).count()
        if query_count >= 100000:
            print(f"[Seed] Database already populated with {query_count} queries. Skipping.")
            return

        print("[Seed] Seeding database with 100,000+ queries...")
        unique_queries = generate_queries()
        
        # Shuffle keys to randomize rank assignment
        random.shuffle(unique_queries)
        
        batch_size = 10000
        queries_to_insert = []
        
        for i, q in enumerate(unique_queries):
            # Zipf's Law formula: count = C / (rank ^ s)
            # Setting rank = i + 1, C = 500,000, s = 0.95
            rank = i + 1
            count = int(500000 / (rank ** 0.95))
            if count < 1:
                count = 1
                
            queries_to_insert.append({
                "query": q,
                "search_count": count
            })
            
            if len(queries_to_insert) >= batch_size:
                db.bulk_insert_mappings(SearchQuery, queries_to_insert)
                db.commit()
                queries_to_insert = []
                print(f"[Seed] Inserted {rank} / {len(unique_queries)} queries...")
                
        if queries_to_insert:
            db.bulk_insert_mappings(SearchQuery, queries_to_insert)
            db.commit()
            
        print(f"[Seed] Seeded {len(unique_queries)} baseline queries successfully.")
        
        # Seed trending spikes
        print("[Seed] Seeding concentrated trending spikes...")
        trending_topics = [
            "chatgpt 5 release date",
            "apple vision pro 2 review",
            "room temperature superconductor news",
            "bitcoin price record high",
            "nextjs 15 features"
        ]
        
        # Ensure they are in the database with baseline search counts
        for topic in trending_topics:
            db.execute(text("""
                INSERT INTO search_queries (query, search_count, created_at, updated_at)
                VALUES (:query, 500, NOW(), NOW())
                ON CONFLICT (query) DO UPDATE SET search_count = search_queries.search_count + 500
            """), {"query": topic})
        db.commit()
        
        # Insert recent search log entries for trending topics within the last 2 hours
        logs_to_insert = []
        now = datetime.utcnow()
        
        for topic in trending_topics:
            log_count = random.randint(300, 600)  # Concentrate 300 to 600 searches
            for _ in range(log_count):
                minutes_ago = random.randint(0, 120)  # within 2 hours
                searched_at = now - timedelta(minutes=minutes_ago)
                logs_to_insert.append({
                    "query": topic,
                    "searched_at": searched_at
                })
                
        # Seed baseline log entries for regular searches (scattered, not concentrated)
        baseline_queries = ["iphone", "python tutorial", "weather in new york", "youtube", "netflix"]
        for bq in baseline_queries:
            db.execute(text("""
                INSERT INTO search_queries (query, search_count, created_at, updated_at)
                VALUES (:query, 10000, NOW(), NOW())
                ON CONFLICT (query) DO NOTHING
            """), {"query": bq})
            
            # Logs distributed across 24 hours
            for _ in range(50):
                hours_ago = random.randint(0, 24)
                searched_at = now - timedelta(hours=hours_ago)
                logs_to_insert.append({
                    "query": bq,
                    "searched_at": searched_at
                })
        db.commit()
        
        # Bulk insert logs to the database
        db.bulk_insert_mappings(SearchLog, logs_to_insert)
        db.commit()
        print(f"[Seed] Seeded {len(logs_to_insert)} trending log entries successfully.")
        
    except Exception as e:
        db.rollback()
        print(f"[Seed] Error encountered during database seeding: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
