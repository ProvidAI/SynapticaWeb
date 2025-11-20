"""Database configuration and session management."""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _normalize_sqlite_url(url: str) -> str:
    """Normalize SQLite URL to use absolute paths."""
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return url
    path_part = url[len(prefix):]
    if path_part.startswith("/"):
        return url
    absolute = (PROJECT_ROOT / path_part).resolve()
    return f"{prefix}{absolute}"


def get_database_url() -> str:
    """Get database URL with proper configuration for environment."""
    raw_database_url = os.getenv("DATABASE_URL")

    if raw_database_url:
        # Fix Render's postgres:// to postgresql://
        if raw_database_url.startswith("postgres://"):
            raw_database_url = raw_database_url.replace("postgres://", "postgresql://", 1)

        # Normalize SQLite paths if needed
        if raw_database_url.startswith("sqlite"):
            return _normalize_sqlite_url(raw_database_url)

        return raw_database_url

    # Default to SQLite for local development
    default_path = PROJECT_ROOT / "hedera_marketplace.db"
    return f"sqlite:///{default_path}"


DATABASE_URL = get_database_url()
print(f"Database: {DATABASE_URL.split('@')[0].split('//')[0]}://*****")  # Hide credentials in logs

# Configure engine based on database type
if DATABASE_URL.startswith("sqlite"):
    # SQLite configuration
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
else:
    # PostgreSQL configuration
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=0,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
