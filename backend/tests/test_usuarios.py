"""Critérios de aceite de HU01.01 (docentes), HU01.03 (alunos) e HU01.08 (editar e inativar)."""

from sqlalchemy import select

from app.models import LogAuditoria, Usuario
from tests.conftest import ALUNO, COORD, DOCENTE, SENHA, ativar

# ---------- HU01.01 ----------


def test_ct_01_01_01_docente_nasce_inativo_e_sem_senha(coord, caixa, db):
    """CT-01.01-01."""
    r = coord.post("/api/v1/docentes", json=DOCENTE)
    assert r.status_code == 201
    corpo = r.json()
    assert corpo["situacao"] == "aguardando_ativacao"
    assert corpo["perfis"] == ["orientador"]
    assert "senha" not in str(corpo).lower()

    usuario = db.scalar(select(Usuario).where(Usuario.email == DOCENTE["email"]))
    assert usuario.senha_hash is None and usuario.ativo is False
    assert usuario.vinculos_perfil[0].atribuido_por is not None


def test_ct_01_01_03_email_duplicado_ignora_maiusculas(coord, caixa):
    """CT-01.01-03."""
    coord.post("/api/v1/docentes", json=DOCENTE)
    r = coord.post("/api/v1/docentes", json={**DOCENTE, "email": "RICARDO@uea.edu.br"})
    assert r.status_code == 409
    assert r.json()["campo"] == "email"


def test_ct_01_01_05_coordenador_nao_exige_curso(coord, caixa):
    """CT-01.01-05."""
    dados = {**DOCENTE, "curso_id": None, "cargo": "coordenador", "perfis": ["coordenador"]}
    assert coord.post("/api/v1/docentes", json=dados).status_code == 201

    sem_curso = {**DOCENTE, "email": "outro@uea.edu.br", "curso_id": None}
    r = coord.post("/api/v1/docentes", json=sem_curso)
    assert r.status_code == 400
    assert "curso_id" in r.json()["campos"]


def test_ct_01_01_06_quem_nao_e_coordenador_recebe_403(coord, caixa, anonimo, db):
    """CT-01.01-06."""
    coord.post("/api/v1/docentes", json=DOCENTE)
    orientador = ativar(caixa, DOCENTE["email"])
    novo = {**DOCENTE, "email": "novo@uea.edu.br"}

    assert orientador.post("/api/v1/docentes", json=novo).status_code == 403
    assert orientador.get("/api/v1/docentes").status_code == 403
    assert anonimo.post("/api/v1/docentes", json=novo).status_code == 401
    assert db.scalar(select(Usuario).where(Usuario.email == "novo@uea.edu.br")) is None


def test_ct_01_01_07_criacao_fica_no_log(coord, caixa, db):
    """CT-01.01-07."""
    criado = coord.post("/api/v1/docentes", json=DOCENTE).json()
    linhas = db.scalars(
        select(LogAuditoria).where(
            LogAuditoria.acao == "criar_docente", LogAuditoria.entidade_id == criado["id"]
        )
    ).all()
    campos = {linha.campo: linha.valor_novo for linha in linhas}
    assert campos["email"] == DOCENTE["email"]
    assert campos["perfis"] == "orientador"
    assert all(linha.usuario_id and linha.criado_em for linha in linhas)


def test_hu0101_ca6_ninguem_altera_os_proprios_perfis(coord, caixa):
    eu = coord.get("/api/v1/auth/me").json()
    r = coord.put(f"/api/v1/usuarios/{eu['id']}", json={"perfis": ["coordenador", "orientador"]})
    assert r.status_code == 403

    # Docente sem perfil coordenador também não consegue (cai no 403 da rota).
    coord.post("/api/v1/docentes", json=DOCENTE)
    orientador = ativar(caixa, DOCENTE["email"])
    eu = orientador.get("/api/v1/auth/me").json()
    r = orientador.put(f"/api/v1/usuarios/{eu['id']}", json={"perfis": ["coordenador"]})
    assert r.status_code == 403


def test_ct_01_01_02_campo_obrigatorio_vazio_responde_400(coord):
    """CT-01.01-02."""
    r = coord.post("/api/v1/docentes", json={"nome": "", "cargo": "professor", "perfis": []})
    assert r.status_code == 400
    assert {"nome", "email", "perfis"} <= set(r.json()["campos"])


# ---------- HU01.03 ----------


def test_ct_01_03_01_aluno_nasce_sem_senha_com_perfil_aluno(coord, caixa):
    """CT-01.03-01."""
    r = coord.post("/api/v1/alunos", json=ALUNO)
    assert r.status_code == 201
    corpo = r.json()
    assert corpo["perfis"] == ["aluno"]
    assert corpo["situacao"] == "aguardando_ativacao"
    assert corpo["curso"]["sigla"] == "EC"


def test_ct_01_03_03_indica_o_campo_duplicado(coord, caixa):
    """CT-01.03-03."""
    coord.post("/api/v1/alunos", json=ALUNO)
    r = coord.post("/api/v1/alunos", json={**ALUNO, "email": "outra@uea.edu.br"})
    assert (r.status_code, r.json()["campo"]) == (409, "matricula")
    r = coord.post("/api/v1/alunos", json={**ALUNO, "matricula": "24150099"})
    assert (r.status_code, r.json()["campo"]) == (409, "email")


def test_ct_01_03_06_e_01_05_01_enfileira_ativacao_e_audita(coord, caixa, db):
    """CT-01.03-06, CT-01.05-01."""
    criado = coord.post("/api/v1/alunos", json=ALUNO).json()
    assert caixa[-1]["para"] == ALUNO["email"] and caixa[-1]["token"]
    assert coord.get(f"/api/v1/alunos/{criado['id']}").json()["email_ativacao"] == "enviado"
    assert db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "criar_aluno"))


def test_hu0103_e1_curso_fora_dos_contemplados(coord):
    r = coord.post("/api/v1/alunos", json={**ALUNO, "curso_id": 999})
    assert r.status_code == 400 and "curso_id" in r.json()["campos"]


def test_hu0103_busca_e_filtro_por_curso(coord, caixa):
    coord.post("/api/v1/alunos", json=ALUNO)
    coord.post(
        "/api/v1/alunos",
        json={"nome": "Caio Martins", "email": "caio@uea.edu.br", "matricula": "24310021", "curso_id": 3},
    )
    assert len(coord.get("/api/v1/alunos").json()) == 2
    assert [a["nome"] for a in coord.get("/api/v1/alunos?busca=2431").json()] == ["Caio Martins"]
    assert [a["nome"] for a in coord.get("/api/v1/alunos?curso=1").json()] == ["Ana Ribeiro"]


# ---------- HU01.08 ----------


def test_ct_01_08_01_e_01_08_06_edicao_auditada_com_valor_anterior_e_novo(coord, caixa, db):
    """CT-01.08-01, CT-01.08-06."""
    criado = coord.post("/api/v1/alunos", json=ALUNO).json()
    r = coord.put(
        f"/api/v1/usuarios/{criado['id']}",
        json={"telefone": "(92) 99999-0000", "curso_id": 3, "email": "ana.nova@uea.edu.br"},
    )
    assert r.status_code == 200
    assert r.json()["curso"]["sigla"] == "SI" and r.json()["telefone"] == "(92) 99999-0000"

    linhas = db.scalars(select(LogAuditoria).where(LogAuditoria.acao == "editar_usuario")).all()
    log = {linha.campo: (linha.valor_anterior, linha.valor_novo) for linha in linhas}
    assert log["email"] == ("ana@uea.edu.br", "ana.nova@uea.edu.br")
    assert log["curso"] == ("Engenharia de Computação", "Sistemas de Informação")
    assert log["telefone"] == (None, "(92) 99999-0000")


def test_ct_01_08_02_email_ou_matricula_de_outra_pessoa(coord, caixa):
    """CT-01.08-02."""
    ana = coord.post("/api/v1/alunos", json=ALUNO).json()
    coord.post("/api/v1/docentes", json=DOCENTE)
    r = coord.put(f"/api/v1/usuarios/{ana['id']}", json={"email": DOCENTE["email"]})
    assert (r.status_code, r.json()["campo"]) == (409, "email")


def test_ct_01_08_03_e_01_08_04_inativado_nao_entra_e_reativado_volta(coord, caixa, anonimo):
    """CT-01.08-03, CT-01.08-04, CT-01.06-08."""
    criado = coord.post("/api/v1/docentes", json=DOCENTE).json()
    orientador = ativar(caixa, DOCENTE["email"])

    r = coord.patch(f"/api/v1/usuarios/{criado['id']}/inativar")
    assert r.json()["situacao"] == "inativo"
    # A sessão aberta cai na hora e um novo login é negado com a mensagem genérica.
    assert orientador.get("/api/v1/auth/me").status_code == 401
    r = anonimo.post("/api/v1/auth/login", json={"email": DOCENTE["email"], "senha": SENHA})
    assert r.status_code == 401 and r.json()["detail"] == "E-mail ou senha inválidos."
    # O cadastro não é excluído.
    assert coord.get(f"/api/v1/docentes/{criado['id']}").status_code == 200

    assert coord.patch(f"/api/v1/usuarios/{criado['id']}/reativar").json()["situacao"] == "ativo"
    r = anonimo.post("/api/v1/auth/login", json={"email": DOCENTE["email"], "senha": SENHA})
    assert r.status_code == 200


def test_hu0108_ca4_nao_existe_rota_de_exclusao(coord, caixa):
    criado = coord.post("/api/v1/alunos", json=ALUNO).json()
    assert coord.delete(f"/api/v1/usuarios/{criado['id']}").status_code == 405


def test_hu0108_coordenador_nao_inativa_a_si_mesmo(coord):
    eu = coord.get("/api/v1/auth/me").json()
    assert eu["email"] == COORD
    assert coord.patch(f"/api/v1/usuarios/{eu['id']}/inativar").status_code == 409
