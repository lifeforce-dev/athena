"""Alembic migration environment.

Uses a sync engine (standard Alembic pattern) with the database URL from
ATHENA_DATABASE_URL. The async runtime handles the async driver separately.
"""
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Import all ORM models so Alembic's autogenerate can detect them.
from app.database import Base
from app.models import orm as _orm_models  # noqa: F811

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Point autogenerate at our declarative base metadata.
target_metadata = Base.metadata

# Override sqlalchemy.url from env var (sync driver for migrations).
database_url = os.environ.get("ATHENA_DATABASE_URL", "")
if database_url.startswith("postgresql+asyncpg://"):
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
elif not database_url.startswith("postgresql://"):
    # Ensure we have a valid sync PostgreSQL URL.
    pass
config.set_main_option("sqlalchemy.url", database_url)

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
