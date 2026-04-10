"""Alembic environment configuration.

Integrates with Flask-SQLAlchemy models so that autogenerate and
manual migrations work against the same metadata as the application.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure the backend package is importable when alembic is run from
# the backend/ directory (the standard working directory).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

# ── Alembic config object ───────────────────────────────────────────────────
config = context.config

# Inject the DATABASE_URL from the environment so it overrides whatever
# placeholder is set in alembic.ini (which has no sqlalchemy.url key).
_database_url = os.environ.get("DATABASE_URL", "sqlite:///pipeline_monitor.db")
config.set_main_option("sqlalchemy.url", _database_url)

# Logging setup from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import target metadata ──────────────────────────────────────────────────
# Import extensions.db and all model modules so SQLAlchemy's metadata is
# fully populated before we hand it to Alembic.
from extensions import db  # noqa: E402
import models  # noqa: E402, F401  — side-effect: registers all ORM classes

target_metadata = db.metadata


# ── Migration runners ───────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection required)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (live DB connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()