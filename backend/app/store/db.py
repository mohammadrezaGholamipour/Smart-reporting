from sqlalchemy.orm import DeclarativeBase, sessionmaker
from collections.abc import Generator
from app.core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from pathlib import Path



class Base(DeclarativeBase):
    pass


if settings.database_url.startswith("sqlite:///"):
    # Ensure the parent directory exists for a relative or absolute SQLite path.
    sqlite_path = settings.database_url.removeprefix("sqlite:///")
    if sqlite_path and sqlite_path != ":memory:":
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
