import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool  # <--- IMPORT THIS
from app.core.config import settings

# Handle database URL
database_url = settings.DATABASE_URL

# Debug: Check if we're in Render
print(f" DEBUG: DATABASE_URL exists: {bool(database_url)}")
print(f" DEBUG: RENDER environment: {os.getenv('RENDER', 'Not set')}")

if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Fallback to SQLite if no DATABASE_URL
if not database_url:
    database_url = "sqlite:///./salon_connect.db"
    print(" Development: Using SQLite")
    connect_args = {"check_same_thread": False}
    pool_class = None
else:
    print(" Production: Using PostgreSQL")
    # Force SSL mode for PostgreSQL
    if "?" not in database_url:
        database_url += "?sslmode=require"
    
    connect_args = {}
    pool_class = NullPool  # <--- DISABLE POOLING FOR RENDER

print(f" Final database URL: {database_url.split('@')[1] if '@' in database_url else 'SQLite'}")

# Create engine with robust settings
engine_args = {
    "echo": settings.DEBUG,
    "connect_args": connect_args,
    "pool_pre_ping": True,  # Check connection validity before using
}

# Only add poolclass if we are using PostgreSQL (NullPool)
if pool_class:
    engine_args["poolclass"] = pool_class
else:
    # Default settings for SQLite
    engine_args["pool_recycle"] = 300

engine = create_engine(database_url, **engine_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()