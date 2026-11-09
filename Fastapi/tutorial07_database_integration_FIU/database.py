import os
from collections.abc import Iterator

from sqlalchemy import create_engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./students.db")
database_url = make_url(DATABASE_URL)

# FastAPI runs sync handlers in worker threads. This option is SQLite-specific.
connect_args = (
    {"check_same_thread": False} if database_url.get_backend_name() == "sqlite" else {}
)
engine = create_engine(database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    """Collect the table definitions from our ORM models."""


def get_db() -> Iterator[Session]:
    """Open one session per request and close it when the request is done."""
    with SessionLocal() as session:
        yield session
