"""Conexão com o banco e sessão do SQLAlchemy."""

from collections.abc import Iterator
from datetime import datetime, timezone

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app import config

_sqlite = config.DATABASE_URL.startswith("sqlite")

engine = create_engine(
    config.DATABASE_URL,
    # O SQLite só aceita uso em outra thread com esta opção; o PostgreSQL não precisa.
    connect_args={"check_same_thread": False} if _sqlite else {},
)

if _sqlite:

    @event.listens_for(engine, "connect")
    def _ligar_chaves_estrangeiras(conexao, _registro) -> None:
        # No SQLite as chaves estrangeiras vêm desligadas por padrão.
        conexao.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    """Dependência do FastAPI: abre uma sessão por requisição e fecha no fim."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def agora() -> datetime:
    """Data e hora atuais em UTC, sem fuso (é assim que gravamos no banco).

    A conversão para America/Manaus (RNF03) é feita na exibição.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
