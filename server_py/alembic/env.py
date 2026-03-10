from logging.config import fileConfig
import os

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import text

from app.core.database import Base, engine

load_dotenv()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# importa i modelli così Base.metadata si popola
import app.models  # noqa: F401

target_metadata = Base.metadata

# ✅ schema dedicato (non public)
APP_SCHEMA = os.getenv("DB_SCHEMA", "seatsurfing")


def run_migrations_offline() -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL not set")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema=APP_SCHEMA,     # ✅ alembic_version nello schema seatsurfing
        default_schema_name=APP_SCHEMA,      # ✅ schema di default seatsurfing
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with engine.connect() as connection:
        # ✅ crea schema se non esiste (serve usare un utente che abbia permesso di CREATE SCHEMA)
        #connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {APP_SCHEMA}"))#

        # ✅ forza lo schema di default in sessione
        #connection.execute(text(f"SET search_path TO {APP_SCHEMA}"))#

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table_schema=APP_SCHEMA,  # ✅ alembic_version nello schema seatsurfing
            default_schema_name=APP_SCHEMA,   # ✅ schema di default seatsurfing
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()