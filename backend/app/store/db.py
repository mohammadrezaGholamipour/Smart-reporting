
from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


# Database configuration
database_url = settings.database_url

if database_url.startswith("sqlite:///"):

    # Extract SQLite file path
    sqlite_path = database_url.removeprefix("sqlite:///")

    # Create parent directory if needed
    if sqlite_path and sqlite_path != ":memory:":
        db_path = Path(sqlite_path)

        db_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    engine = create_engine(
        database_url,
        connect_args={
            "check_same_thread": False,
        },
    )

else:
    # External databases such as PostgreSQL
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
