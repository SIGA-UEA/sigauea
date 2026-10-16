"""Preparação dos testes: banco temporário, carga base e um coordenador ativo.

Por padrão os testes usam um SQLite temporário. Para rodar contra o PostgreSQL,
aponte TEST_DATABASE_URL para um banco vazio (ele é apagado a cada teste):
    TEST_DATABASE_URL=postgresql+psycopg://usuario:senha@localhost:5432/siga_teste
"""

import os
import re
import tempfile

# Precisa vir antes de importar a aplicação, que lê a configuração ao ser importada.
os.environ["DATABASE_URL"] = (
    os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tempfile.mkdtemp()}/teste.db"
)
os.environ["BCRYPT_CUSTO"] = "10"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.security import gerar_hash_senha
from app.seed import carregar_base, criar_coordenador
from app.services import email

SENHA = "Senha@2026"
COORD = "coord@uea.edu.br"
_HASH = gerar_hash_senha(SENHA)


@pytest.fixture(autouse=True)
def banco():
    """Cada teste começa com o banco limpo e a carga base."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        nucleo = carregar_base(db)
        coordenador = criar_coordenador(db, nucleo, "Coordenadora Teste", COORD)
        coordenador.senha_hash = _HASH
        coordenador.ativo = True
        db.commit()
    yield


@pytest.fixture
def db():
    with SessionLocal() as sessao:
        yield sessao


@pytest.fixture
def caixa(monkeypatch):
    """E-mails "enviados" durante o teste, no lugar do envio real."""
    enviados: list[dict] = []

    def entregar(destinatario, assunto, corpo):
        token = re.search(r"token=(\S+)", corpo)
        enviados.append({"para": destinatario, "assunto": assunto, "token": token and token[1]})

    monkeypatch.setattr(email, "entregar", entregar)
    return enviados


@pytest.fixture
def anonimo():
    return TestClient(app)


@pytest.fixture
def coord():
    """Cliente já autenticado como coordenador."""
    cliente = TestClient(app)
    resposta = cliente.post("/api/v1/auth/login", json={"email": COORD, "senha": SENHA})
    assert resposta.status_code == 200
    return cliente


DOCENTE = {
    "nome": "Ricardo Alves",
    "email": "ricardo@uea.edu.br",
    "cargo": "orientador",
    "curso_id": 1,
    "perfis": ["orientador"],
}
ALUNO = {"nome": "Ana Ribeiro", "email": "ana@uea.edu.br", "matricula": "24150001", "curso_id": 1}


def ativar(caixa, email_destino: str, senha: str = SENHA) -> TestClient:
    """Ativa a conta pelo link recebido e devolve um cliente logado como essa pessoa."""
    token = next(m["token"] for m in reversed(caixa) if m["para"] == email_destino)
    cliente = TestClient(app)
    assert cliente.post("/api/v1/auth/ativar", json={"token": token, "senha": senha}).status_code == 200
    assert cliente.post("/api/v1/auth/login", json={"email": email_destino, "senha": senha}).status_code == 200
    return cliente
