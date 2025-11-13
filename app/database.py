import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
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
else:
    print(" Production: Using PostgreSQL")

print(f" Final database URL: {database_url.split('@')[1] if '@' in database_url else 'SQLite'}")

engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()