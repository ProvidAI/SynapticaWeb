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
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return url
    path_part = url[len(prefix):]
    if path_part.startswith("/"):
        return url
    absolute = (PROJECT_ROOT / path_part).resolve()
    return f"{prefix}{absolute}"


raw_database_url = os.getenv("DATABASE_URL")
if raw_database_url:
    DATABASE_URL = _normalize_sqlite_url(raw_database_url)
else:
    default_path = PROJECT_ROOT / "hedera_marketplace.db"
    DATABASE_URL = f"sqlite:///{default_path}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
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
