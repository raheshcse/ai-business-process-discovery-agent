import logging
from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)


connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    database = SessionLocal()

    try:
        yield database
    finally:
        database.close()


def ensure_schema() -> None:
    """Create missing tables and backfill missing columns.

    `Base.metadata.create_all` creates missing *tables* but never adds a
    column to a table that already exists, so an existing
    `business_process_discovery.db` would keep an old `documents` table and
    fail at query time once indexing columns were introduced. On SQLite we
    close that gap with idempotent `ALTER TABLE ... ADD COLUMN` statements.

    This is intentionally narrow. Anything beyond additive columns should
    use Alembic, which is already a project dependency.
    """
    from app.models import Base  # Imports all mapped models.

    Base.metadata.create_all(bind=engine)

    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    with engine.begin() as connection:
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            existing = {
                column["name"] for column in inspector.get_columns(table.name)
            }
            for column in table.columns:
                if column.name in existing:
                    continue
                if not (column.nullable or column.server_default is not None):
                    logger.warning(
                        "Cannot add non-nullable column %s.%s without a server "
                        "default; recreate the database to pick it up.",
                        table.name,
                        column.name,
                    )
                    continue
                column_type = column.type.compile(engine.dialect)
                statement = (
                    f'ALTER TABLE "{table.name}" '
                    f'ADD COLUMN "{column.name}" {column_type}'
                )
                if column.server_default is not None:
                    default = column.server_default.arg
                    statement += f" DEFAULT '{default}'"
                logger.info(
                    "Adding missing column %s.%s", table.name, column.name
                )
                connection.execute(text(statement))
