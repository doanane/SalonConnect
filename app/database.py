import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Handle database URL
database_url = settings.DATABASE_URL

# In production, require PostgreSQL
if not database_url and os.getenv("RENDER", None):
    raise ValueError("DATABASE_URL must be set in production")

if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Fallback to SQLite only in development
if not database_url:
    database_url = "sqlite:///./salon_connect.db"
    print("🔗 Development: Using SQLite")
else:
    print("🔗 Production: Using PostgreSQL")

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