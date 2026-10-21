"""Aplica as migrações do Alembic (pasta migrations/) a partir do Python.

Usado pelo seed e pelos testes. Pela linha de comando: alembic upgrade head.
"""

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app import config

_INI = config.BASE_DIR / "alembic.ini"


def _config(url: str) -> Config:
    cfg = Config(str(_INI))
    cfg.attributes["url"] = url
    cfg.attributes["configurar_log"] = False
    return cfg


def atualizar_banco(url: str | None = None) -> None:
    url = url or config.DATABASE_URL
    cfg = _config(url)

    engine = create_engine(url)
    tabelas = set(inspect(engine).get_table_names())
    engine.dispose()
    # Banco criado antes das migrações (create_all): já tem o esquema da 0001.
    if "usuario" in tabelas and "alembic_version" not in tabelas:
        command.stamp(cfg, "0001")

    command.upgrade(cfg, "head")
