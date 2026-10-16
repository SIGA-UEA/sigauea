"""Liga o Alembic às tabelas da API (app/models.py) e ao banco de DATABASE_URL."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app import config as config_api
from app import models  # noqa: F401  (registra as tabelas em Base.metadata)
from app.database import Base

config = context.config
if config.config_file_name is not None and config.attributes.get("configurar_log", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
# Quem chama pode passar outro endereço (os testes usam um banco temporário).
url = config.attributes.get("url") or config_api.DATABASE_URL
# SQLite não altera colunas no lugar; "batch" recria a tabela quando preciso.
render_as_batch = url.startswith("sqlite")


def run_migrations_offline() -> None:
    """Gera o SQL sem conectar (alembic upgrade head --sql)."""
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=render_as_batch,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(url)
    with engine.connect() as conexao:
        context.configure(
            connection=conexao, target_metadata=target_metadata, render_as_batch=render_as_batch
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
