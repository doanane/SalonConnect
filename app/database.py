import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings

# Handle database URL
database_url = settings.DATABASE_URL

print(f" DEBUG: DATABASE_URL exists: {bool(database_url)}")

# Fix legacy postgres:// URL if present
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Initialize engine arguments
engine_args = {
    "echo": settings.DEBUG,
}

if database_url:
    print(" Production: Using PostgreSQL")
    
    # CRITICAL FIXES FOR RENDER:
    # 1. NullPool: Disables connection pooling completely. 
    #    Every request opens a new, fresh connection and closes it immediately.
    engine_args["poolclass"] = NullPool
    
    # 2. SSL Mode: Pass directly to the underlying driver (psycopg2)
    #    This is safer than appending "?sslmode=require" to the string
    engine_args["connect_args"] = {"sslmode": "require"}
    
else:
    # Fallback to SQLite for local testing if no URL provided
    database_url = "sqlite:///./salon_connect.db"
    print(" Development: Using SQLite")
    engine_args["connect_args"] = {"check_same_thread": False}

# Create the engine
engine = create_engine(database_url, **engine_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()