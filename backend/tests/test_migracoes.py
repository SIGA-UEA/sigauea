"""As migrações (migrations/) criam exatamente as tabelas de app/models.py.

Se este teste falhar, alguém mudou models.py sem criar a migração:
    alembic revision --autogenerate -m "o que mudou"
"""

import tempfile

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.database import Base
from app.migracoes import atualizar_banco


def _url() -> str:
    return f"sqlite:///{tempfile.mkdtemp()}/migracoes.db"


def test_migracoes_batem_com_os_modelos():
    url = _url()
    atualizar_banco(url)
    engine = create_engine(url)
    with engine.connect() as conexao:
        diferencas = compare_metadata(MigrationContext.configure(conexao), Base.metadata)
    engine.dispose()
    assert diferencas == []


def test_banco_recusa_email_repetido_com_outras_maiusculas():
    url = _url()
    atualizar_banco(url)
    engine = create_engine(url)
    inserir = text(
        "INSERT INTO usuario (nome, email, ativo, tentativas_falhas, criado_em) "
        "VALUES ('Ana', :email, false, 0, CURRENT_TIMESTAMP)"
    )
    with engine.begin() as conexao:
        conexao.execute(inserir, {"email": "ana@uea.edu.br"})
    with pytest.raises(IntegrityError), engine.begin() as conexao:
        conexao.execute(inserir, {"email": "ANA@uea.edu.br"})
    engine.dispose()


def test_banco_antigo_sem_alembic_e_reconhecido_e_atualizado():
    """O siga_dev.db de quem rodou o seed antes das migrações continua servindo."""
    url = _url()
    # Um banco da época do create_all tem o esquema da 0001 e não tem alembic_version.
    from alembic import command

    from app.migracoes import _config

    command.upgrade(_config(url), "0001")
    engine = create_engine(url)
    with engine.begin() as conexao:
        conexao.execute(text("DROP TABLE alembic_version"))
    engine.dispose()

    atualizar_banco(url)

    engine = create_engine(url)
    tabelas = set(inspect(engine).get_table_names())
    engine.dispose()
    assert {"foto_usuario", "alembic_version"} <= tabelas


def test_ct_ht07_02_log_de_auditoria_nao_pode_ser_alterado_nem_apagado():
    url = _url()
    atualizar_banco(url)
    engine = create_engine(url)
    with engine.begin() as conexao:
        conexao.execute(
            text(
                "INSERT INTO log_auditoria (acao, entidade, criado_em) "
                "VALUES ('teste', 'usuario', CURRENT_TIMESTAMP)"
            )
        )
    for comando in ("UPDATE log_auditoria SET acao = 'outra'", "DELETE FROM log_auditoria"):
        with pytest.raises(DBAPIError), engine.begin() as conexao:
            conexao.execute(text(comando))
    with engine.connect() as conexao:
        assert conexao.execute(text("SELECT acao FROM log_auditoria")).scalar() == "teste"
    engine.dispose()


def test_ct_ht08_02_carga_inicial_repetida_nao_duplica():
    from sqlalchemy.orm import Session

    from app.models import AreaInteresse, Curso, Perfil, Usuario
    from app.seed import CONTAS_DEMO, carregar_base, criar_contas_demo, criar_coordenador

    url = _url()
    atualizar_banco(url)
    engine = create_engine(url)
    for _ in range(2):
        with Session(engine) as db:
            nucleo = carregar_base(db)
            if not db.scalar(select(Usuario).where(Usuario.email == "coord@exemplo.com")):
                criar_coordenador(db, nucleo, "Coordenação", "coord@exemplo.com")
            criar_contas_demo(db, nucleo)
            db.commit()
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(Curso)) == 3
        assert db.scalar(select(func.count()).select_from(Perfil)) == 5
        assert db.scalar(select(func.count()).select_from(AreaInteresse)) == 6
        assert db.scalar(select(func.count()).select_from(Usuario)) == 1 + len(CONTAS_DEMO)
    engine.dispose()
