"""Critérios de aceite de HU01.04 (senha), HU01.05 (ativação), HU01.06 (login) e HU01.07 (recuperação)."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.database import agora
from app.models import LogAuditoria, NotificacaoEmail, Sessao, TokenUsuario, Usuario
from app.security import hash_token, validate_password
from app.services import email
from tests.conftest import ALUNO, COORD, SENHA, ativar

LOGIN = "/api/v1/auth/login"


def _usuario(db, endereco=COORD) -> Usuario:
    db.expire_all()
    return db.scalar(select(Usuario).where(Usuario.email == endereco))


# ---------- HU01.04 ----------


@pytest.mark.parametrize(
    ("senha", "faltando"),
    [
        ("abc12345", {"maiuscula", "especial"}),
        ("Senha@2026", set()),
        ("Ab@1", {"tamanho"}),
        ("SenhaForte@", {"numero"}),
        ("siga2026", {"maiuscula", "especial"}),  # CT-01.04-02
        ("Aa1!aaa", {"tamanho"}),  # CT-01.04-03: 7 caracteres
        ("Aa1!aaaa", set()),  # CT-01.04-04: 8 caracteres
    ],
)
def test_hu0104_criterios(senha, faltando):
    assert {c["codigo"] for c in validate_password(senha)} == faltando


def test_hu0104_ca1_ativacao_recusa_senha_fraca_e_lista_criterios(coord, caixa):
    coord.post("/api/v1/alunos", json=ALUNO)
    r = coord.post("/api/v1/auth/ativar", json={"token": caixa[-1]["token"], "senha": "abc12345"})
    assert r.status_code == 422
    assert {c["codigo"] for c in r.json()["criterios"]} == {"maiuscula", "especial"}


def test_hu0104_ca3_senha_gravada_com_bcrypt_e_nunca_devolvida(coord, caixa, db):
    coord.post("/api/v1/alunos", json=ALUNO)
    aluno = ativar(caixa, ALUNO["email"])
    senha_hash = _usuario(db, ALUNO["email"]).senha_hash
    assert senha_hash.startswith("$2b$") and int(senha_hash.split("$")[2]) >= 10
    assert SENHA not in aluno.get("/api/v1/auth/me").text
    assert "senha" not in aluno.get("/api/v1/auth/me").text


# ---------- HU01.05 ----------


def test_hu0105_ca2_link_ativa_a_conta_e_vale_uma_vez(coord, caixa, anonimo, db):
    coord.post("/api/v1/alunos", json=ALUNO)
    token = caixa[-1]["token"]
    # O banco guarda só o hash do token.
    assert db.scalar(select(TokenUsuario).where(TokenUsuario.token_hash == hash_token(token)))
    assert db.scalar(select(TokenUsuario).where(TokenUsuario.token_hash == token)) is None

    validar = {"token": token, "tipo": "ativacao"}
    assert anonimo.post("/api/v1/auth/validar-token", json=validar).json() == {
        "valido": True,
        "motivo": None,
    }
    ativar(caixa, ALUNO["email"])

    r = anonimo.post("/api/v1/auth/ativar", json={"token": token, "senha": SENHA})
    assert (r.status_code, r.json()["motivo"]) == (400, "usado")
    assert anonimo.post("/api/v1/auth/validar-token", json=validar).json()["motivo"] == "usado"


def test_hu0105_ca3_link_expirado(coord, caixa, anonimo, db):
    coord.post("/api/v1/alunos", json=ALUNO)
    registro = db.scalar(select(TokenUsuario))
    assert timedelta(hours=47) < registro.expira_em - agora() <= timedelta(hours=48)
    registro.expira_em = agora() - timedelta(seconds=1)
    db.commit()

    r = anonimo.post("/api/v1/auth/ativar", json={"token": caixa[-1]["token"], "senha": SENHA})
    assert (r.status_code, r.json()["motivo"]) == (400, "expirado")


def test_hu0105_ca4_falha_de_email_nao_desfaz_cadastro_e_permite_reenvio(coord, monkeypatch, db, caixa):
    def falhar(*_):
        raise ConnectionError("servidor de e-mail fora do ar")

    monkeypatch.setattr(email, "entregar", falhar)
    r = coord.post("/api/v1/alunos", json=ALUNO)
    assert r.status_code == 201
    criado = coord.get(f"/api/v1/alunos/{r.json()['id']}").json()
    assert criado["email_ativacao"] == "falha"
    notificacao = db.scalar(select(NotificacaoEmail))
    assert notificacao.tentativas == 1 and "fora do ar" in notificacao.erro

    # Reenvio: gera link novo e o anterior deixa de valer.
    enviados = []
    monkeypatch.setattr(email, "entregar", lambda para, assunto, corpo: enviados.append(corpo))
    r = coord.post(f"/api/v1/usuarios/{criado['id']}/reenviar-ativacao")
    # A resposta sai antes do envio (fila), por isso consultamos de novo.
    assert r.status_code == 200 and r.json()["email_ativacao"] == "pendente"
    assert coord.get(f"/api/v1/alunos/{criado['id']}").json()["email_ativacao"] == "enviado"
    assert len(enviados) == 1 and "/ativar?token=" in enviados[0]


def test_hu0105_reenvio_so_para_quem_aguarda_ativacao(coord):
    eu = coord.get("/api/v1/auth/me").json()
    assert coord.post(f"/api/v1/usuarios/{eu['id']}/reenviar-ativacao").status_code == 409


# ---------- HU01.06 ----------


def test_hu0106_ca1_login_devolve_usuario_e_cookie_httponly(anonimo):
    r = anonimo.post(LOGIN, json={"email": COORD.upper(), "senha": SENHA})
    assert r.status_code == 200
    assert "coordenador" in r.json()["usuario"]["perfis"]
    assert "httponly" in r.headers["set-cookie"].lower()
    assert anonimo.get("/api/v1/auth/me").json()["email"] == COORD


def test_hu0106_ca2_mesma_mensagem_para_email_ou_senha_errados(anonimo):
    senha_errada = anonimo.post(LOGIN, json={"email": COORD, "senha": "Errada@123"})
    email_errado = anonimo.post(LOGIN, json={"email": "ninguem@uea.edu.br", "senha": SENHA})
    assert senha_errada.status_code == email_errado.status_code == 401
    assert senha_errada.json() == email_errado.json()


def test_hu0106_ca3_bloqueio_apos_3_falhas_mesmo_com_senha_correta(anonimo, db):
    for _ in range(2):
        assert anonimo.post(LOGIN, json={"email": COORD, "senha": "Errada@123"}).status_code == 401
    assert anonimo.post(LOGIN, json={"email": COORD, "senha": "Errada@123"}).status_code == 423
    assert anonimo.post(LOGIN, json={"email": COORD, "senha": SENHA}).status_code == 423

    usuario = _usuario(db)
    assert timedelta(minutes=14) < usuario.bloqueado_ate - agora() <= timedelta(minutes=15)
    # Passados os 15 minutos, a senha correta volta a entrar.
    usuario.bloqueado_ate = agora() - timedelta(seconds=1)
    db.commit()
    assert anonimo.post(LOGIN, json={"email": COORD, "senha": SENHA}).status_code == 200


def test_hu0106_sucesso_zera_as_tentativas(anonimo, db):
    for _ in range(2):
        anonimo.post(LOGIN, json={"email": COORD, "senha": "Errada@123"})
    assert anonimo.post(LOGIN, json={"email": COORD, "senha": SENHA}).status_code == 200
    assert _usuario(db).tentativas_falhas == 0


def test_hu0106_ca4_sessao_expira_por_inatividade_e_renova_com_uso(coord, db):
    sessao = db.scalar(select(Sessao))
    sessao.expira_em = agora() + timedelta(minutes=5)
    db.commit()
    assert coord.get("/api/v1/auth/me").status_code == 200
    db.expire_all()
    # O uso empurrou a expiração de volta para 60 minutos.
    assert db.scalar(select(Sessao)).expira_em - agora() > timedelta(minutes=59)

    sessao = db.scalar(select(Sessao))
    sessao.expira_em = agora() - timedelta(seconds=1)
    db.commit()
    assert coord.get("/api/v1/auth/me").status_code == 401


def test_hu0106_ca4_logout_encerra_a_sessao(coord):
    token = coord.cookies.get("siga_sessao")
    assert coord.post("/api/v1/auth/logout").status_code == 200
    assert coord.get("/api/v1/auth/me").status_code == 401
    # O token antigo também não vale mais, mesmo enviado à mão.
    r = coord.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_hu0106_ca5_toda_tentativa_e_registrada(anonimo, db):
    anonimo.post(LOGIN, json={"email": COORD, "senha": "Errada@123"})
    anonimo.post(LOGIN, json={"email": "ninguem@uea.edu.br", "senha": SENHA})
    anonimo.post(LOGIN, json={"email": COORD, "senha": SENHA})
    acoes = db.scalars(select(LogAuditoria.acao).order_by(LogAuditoria.id)).all()
    assert acoes == ["login_falha", "login_falha", "login_sucesso"]


def test_hu0106_ca6_conta_nao_ativada_recebe_a_mesma_mensagem(coord, caixa, anonimo):
    coord.post("/api/v1/alunos", json=ALUNO)
    r = anonimo.post(LOGIN, json={"email": ALUNO["email"], "senha": SENHA})
    assert r.status_code == 401 and r.json()["detail"] == "E-mail ou senha inválidos."


# ---------- HU01.07 ----------


def test_hu0107_ca1_ca2_resposta_igual_e_email_so_para_cadastrado(anonimo, caixa):
    existe = anonimo.post("/api/v1/auth/esqueci-senha", json={"email": COORD})
    nao_existe = anonimo.post("/api/v1/auth/esqueci-senha", json={"email": "ninguem@uea.edu.br"})
    assert existe.status_code == nao_existe.status_code == 202
    assert existe.json() == nao_existe.json()
    assert [m["para"] for m in caixa] == [COORD]


def test_hu0107_ca3_ca4_troca_a_senha_desbloqueia_e_link_nao_se_repete(anonimo, caixa, db):
    for _ in range(3):
        anonimo.post(LOGIN, json={"email": COORD, "senha": "Errada@123"})
    assert _usuario(db).bloqueado_ate is not None

    anonimo.post("/api/v1/auth/esqueci-senha", json={"email": COORD})
    token = caixa[-1]["token"]
    registro = db.scalar(select(TokenUsuario))
    # RBN01.07: o link de recuperação vale 10 minutos.
    assert registro.tipo == "recuperacao" and registro.expira_em - agora() <= timedelta(minutes=10)

    fraca = anonimo.post("/api/v1/auth/redefinir-senha", json={"token": token, "senha": "fraca"})
    assert fraca.status_code == 422

    nova = "Outra#Senha9"
    assert anonimo.post("/api/v1/auth/redefinir-senha", json={"token": token, "senha": nova}).status_code == 200
    usuario = _usuario(db)
    assert usuario.bloqueado_ate is None and usuario.tentativas_falhas == 0
    assert anonimo.post(LOGIN, json={"email": COORD, "senha": nova}).status_code == 200
    assert anonimo.post(LOGIN, json={"email": COORD, "senha": SENHA}).status_code in (401, 423)

    de_novo = anonimo.post("/api/v1/auth/redefinir-senha", json={"token": token, "senha": nova})
    assert (de_novo.status_code, de_novo.json()["motivo"]) == (400, "usado")


def test_hu0107_token_de_ativacao_nao_serve_para_redefinir(coord, caixa, anonimo):
    coord.post("/api/v1/alunos", json=ALUNO)
    r = anonimo.post(
        "/api/v1/auth/redefinir-senha", json={"token": caixa[-1]["token"], "senha": SENHA}
    )
    assert (r.status_code, r.json()["motivo"]) == (400, "invalido")


def test_rbn0107_link_de_recuperacao_vencido_e_recusado(anonimo, caixa, db):
    anonimo.post("/api/v1/auth/esqueci-senha", json={"email": COORD})
    registro = db.scalar(select(TokenUsuario))
    registro.expira_em = agora() - timedelta(seconds=1)  # passaram os 10 minutos
    db.commit()
    r = anonimo.post(
        "/api/v1/auth/redefinir-senha", json={"token": caixa[-1]["token"], "senha": "Outra#Senha9"}
    )
    assert (r.status_code, r.json()["motivo"]) == (400, "expirado")
