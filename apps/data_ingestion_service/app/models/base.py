from sqlalchemy.orm import DeclarativeBase


def _schema_management_disabled(*args, **kwargs):
    raise RuntimeError(
        """
        Schema management is disabled in this service.

        This service is a database consumer only.

        Use:
        - API Service migrations
        - Alembic migrations
        - Supabase SQL migrations

        to create or modify database schema.
        """
    )


class Base(DeclarativeBase):
    pass


Base.metadata.create_all = _schema_management_disabled
Base.metadata.drop_all = _schema_management_disabled
