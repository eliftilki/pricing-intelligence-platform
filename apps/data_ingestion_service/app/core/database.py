from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


engine = create_engine(
    settings.database_url,
    pool_pre_ping=settings.db_pool_pre_ping,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def init_db():
    raise RuntimeError(
        "Data ingestion service does not manage database schema. "
        "Create or migrate tables from the owning API/database migration layer."
    )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
