"""SQLite engine, session factory and the FastAPI ``get_db`` dependency."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _ensure_parent_dir(path: str) -> None:
    """Create the parent directory of a file path when missing."""
    parent = Path(path).parent
    if str(parent) not in ("", "."):
        parent.mkdir(parents=True, exist_ok=True)


_ensure_parent_dir(settings.database_path)

# ``check_same_thread=False`` lets FastAPI's threadpool use the same engine
engine = create_engine(
    f"sqlite:///{settings.database_path}",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    """FastAPI dependency: yield a database session, always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
