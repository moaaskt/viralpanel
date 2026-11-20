"""Alembic environment configuration with connection injection and dynamic URL support."""

from alembic import context
from sqlalchemy import create_engine

from viralpanel import models  # noqa: F401
from viralpanel.config import get_settings
from viralpanel.database import Base

target_metadata = Base.metadata


def get_url() -> str:
    """Resolve database URL dynamically, prioritizing Alembic config over runtime settings."""
    url = context.config.get_main_option("sqlalchemy.url")
    if not url:
        url = get_settings().database_url
    return str(url)


def do_run_migrations(connection) -> None:
    """Configure Alembic context for the provided active connection and execute migrations."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    """Run migrations in offline mode using dynamically resolved URL."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode, honoring injected connections from tests."""
    connection = context.config.attributes.get("connection", None)
    if connection is not None:
        do_run_migrations(connection)
        return

    connectable = create_engine(get_url())
    try:
        with connectable.connect() as conn:
            do_run_migrations(conn)
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
