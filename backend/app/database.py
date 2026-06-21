from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

# Create PostgreSQL database engine
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# Create sessionmaker factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base class for models
Base = declarative_base()

# Dependency utility for retrieving DB sessions in endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
