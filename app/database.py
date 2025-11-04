import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Handle database URL for both development and production
database_url = settings.DATABASE_URL

if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# No print statements - cleaner production logs
engine = create_engine(
    database_url if database_url else "sqlite:///./salon_connect.db",
    connect_args={"check_same_thread": False} if not database_url or database_url.startswith("sqlite") else {},
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