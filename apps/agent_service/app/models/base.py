from sqlalchemy.orm import DeclarativeBase


def _schema_management_disabled(*args, **kwargs):
    raise RuntimeError(
        "Agent service must not create or drop database schema from ORM metadata. "
        "Use API service Alembic migrations or Supabase SQL migrations instead."
    )


class Base(DeclarativeBase):
    pass


Base.metadata.create_all = _schema_management_disabled
Base.metadata.drop_all = _schema_management_disabled
