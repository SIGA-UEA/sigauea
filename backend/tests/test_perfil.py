"""RBN01.02 (áreas de interesse), RBN01.09 e RBN01.10 (meu perfil), foto e troca de senha."""

from sqlalchemy import select

from app.models import AreaInteresse, DocenteArea, LogAuditoria
from tests.conftest import ALUNO, COORD, DOCENTE, SENHA, ativar

# Menores arquivos válidos de cada formato: o que importa são os bytes iniciais.
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 32


def _orientador(coord, caixa, **extra):
    coord.post("/api/v1/docentes", json={**DOCENTE, **extra})
    return ativar(caixa, DOCENTE["email"])


def _aluno(coord, caixa):
    coord.post("/api/v1/alunos", json=ALUNO)
    return ativar(caixa, ALUNO["email"])


# ---------- RBN01.02: áreas de interesse ----------


def test_rbn0102_coordenador_cria_renomeia_e_exclui_area(coord, db):
    r = coord.post("/api/v1/areas", json={"nome": "Computação Gráfica"})
    assert r.status_code == 201
    area = r.json()
    assert area["docentes"] == 0

    r = coord.put(f"/api/v1/areas/{area['id']}", json={"nome": "Computação Visual"})
    assert r.status_code == 200 and r.json()["nome"] == "Computação Visual"

    assert coord.delete(f"/api/v1/areas/{area['id']}").status_code == 204
    nomes = [a["nome"] for a in coord.get("/api/v1/areas").json()]
    assert "Computação Visual" not in nomes

    acoes = db.scalars(
        select(LogAuditoria.acao).where(LogAuditoria.entidade == "area_interesse")
    ).all()
    assert {"criar_area", "editar_area", "excluir_area"} <= set(acoes)


def test_rbn0102_nome_repetido_ignora_maiusculas(coord):
    r = coord.post("/api/v1/areas", json={"nome": "engenharia de software"})
    assert r.status_code == 409 and r.json()["campo"] == "nome"


def test_rbn0102_excluir_area_em_uso_desvincula_docentes(coord, caixa, db):
    area_id = coord.get("/api/v1/areas").json()[0]["id"]
    docente = coord.post("/api/v1/docentes", json={**DOCENTE, "areas": [area_id]}).json()
    uso = {a["id"]: a["docentes"] for a in coord.get("/api/v1/areas/gestao").json()}
    assert uso[area_id] == 1

    assert coord.delete(f"/api/v1/areas/{area_id}").status_code == 204
    assert coord.get(f"/api/v1/docentes/{docente['id']}").json()["areas"] == []
    assert db.get(AreaInteresse, area_id) is None
    assert db.scalar(select(DocenteArea).where(DocenteArea.area_id == area_id)) is None


def test_rbn0102_so_coordenador_gerencia_areas(coord, caixa):
    orientador = _orientador(coord, caixa)
    assert orientador.post("/api/v1/areas", json={"nome": "Robótica"}).status_code == 403
    assert orientador.get("/api/v1/areas/gestao").status_code == 403
    assert orientador.get("/api/v1/areas").status_code == 200  # a lista simples continua aberta


# ---------- RBN01.10: docente edita os próprios dados ----------


def test_rbn0110_docente_edita_telefone_curso_e_areas(coord, caixa, db):
    orientador = _orientador(coord, caixa)
    areas = [a["id"] for a in coord.get("/api/v1/areas").json()[:2]]
    r = orientador.put(
        "/api/v1/usuarios/me", json={"telefone": "(92) 98888-0000", "curso_id": 2, "areas": areas}
    )
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["telefone"] == "(92) 98888-0000"
    assert corpo["curso"]["id"] == 2
    assert sorted(a["id"] for a in corpo["areas"]) == sorted(areas)

    campos = db.scalars(
        select(LogAuditoria.campo).where(LogAuditoria.acao == "editar_meu_perfil")
    ).all()
    assert set(campos) == {"telefone", "curso", "areas"}


def test_rbn0110_nome_e_email_so_a_coordenacao_altera(coord, caixa):
    orientador = _orientador(coord, caixa)
    r = orientador.put("/api/v1/usuarios/me", json={"nome": "Outro Nome"})
    assert r.status_code == 400
    r = orientador.put("/api/v1/usuarios/me", json={"email": "outro@uea.edu.br"})
    assert r.status_code == 400
    assert orientador.get("/api/v1/usuarios/me").json()["nome"] == DOCENTE["nome"]


def test_rbn0110_membro_da_banca_nao_escolhe_areas(coord, caixa):
    banca = _orientador(coord, caixa, perfis=["membro_banca"])
    r = banca.put("/api/v1/usuarios/me", json={"areas": [1]})
    assert r.status_code == 403


# ---------- RBN01.09: aluno edita telefone e foto ----------


def test_rbn0109_aluno_edita_telefone_mas_nao_o_curso(coord, caixa):
    aluno = _aluno(coord, caixa)
    assert aluno.put("/api/v1/usuarios/me", json={"telefone": "92999990000"}).status_code == 200
    assert aluno.put("/api/v1/usuarios/me", json={"curso_id": 2}).status_code == 403
    assert aluno.put("/api/v1/usuarios/me", json={"matricula": "99999999"}).status_code == 400
    assert aluno.put("/api/v1/usuarios/me", json={"areas": [1]}).status_code == 403


# ---------- foto ----------


def test_foto_aceita_jpg_png_webp_e_pode_ser_removida(coord, caixa):
    aluno = _aluno(coord, caixa)
    for conteudo in (JPG, PNG, WEBP):
        r = aluno.put("/api/v1/usuarios/me/foto", files={"foto": ("x.img", conteudo)})
        assert r.status_code == 200
    eu = r.json()
    assert eu["foto_versao"]

    # Qualquer pessoa logada vê a foto; quem não está logado, não.
    r = coord.get(f"/api/v1/usuarios/{eu['id']}/foto")
    assert r.status_code == 200 and r.headers["content-type"] == "image/webp"
    assert r.content == WEBP

    assert aluno.delete("/api/v1/usuarios/me/foto").json()["foto_versao"] is None
    assert coord.get(f"/api/v1/usuarios/{eu['id']}/foto").status_code == 404


def test_foto_recusa_arquivo_que_nao_e_imagem_mesmo_com_extensao_certa(coord, caixa):
    aluno = _aluno(coord, caixa)
    falso = aluno.put("/api/v1/usuarios/me/foto", files={"foto": ("foto.png", b"MZ\x90\x00")})
    assert falso.status_code == 415
    vazio = aluno.put("/api/v1/usuarios/me/foto", files={"foto": ("foto.png", b"")})
    assert vazio.status_code == 400


def test_foto_acima_de_5_mb_e_recusada(coord, caixa):
    aluno = _aluno(coord, caixa)
    grande = PNG + b"\x00" * (5 * 1024 * 1024)
    r = aluno.put("/api/v1/usuarios/me/foto", files={"foto": ("foto.png", grande)})
    assert r.status_code == 413


def test_rbn0101_coordenacao_inclui_foto_do_docente(coord, caixa, anonimo):
    docente = coord.post("/api/v1/docentes", json=DOCENTE).json()
    r = coord.put(f"/api/v1/usuarios/{docente['id']}/foto", files={"foto": ("f.jpg", JPG)})
    assert r.status_code == 200 and r.json()["foto_versao"]
    assert anonimo.get(f"/api/v1/usuarios/{docente['id']}/foto").status_code == 401


# ---------- troca de senha pelo próprio usuário (RBN01.04) ----------


def test_rbn0104_troca_de_senha_exige_a_atual_e_a_regra_de_complexidade(coord, caixa, anonimo):
    aluno = _aluno(coord, caixa)
    r = aluno.post("/api/v1/usuarios/me/senha", json={"senha_atual": "errada", "nova_senha": "x"})
    assert r.status_code == 400 and "senha_atual" in r.json()["campos"]

    r = aluno.post("/api/v1/usuarios/me/senha", json={"senha_atual": SENHA, "nova_senha": "fraca"})
    assert r.status_code == 422 and r.json()["criterios"]

    r = aluno.post(
        "/api/v1/usuarios/me/senha", json={"senha_atual": SENHA, "nova_senha": "Nova@Senha9"}
    )
    assert r.status_code == 200
    assert aluno.get("/api/v1/usuarios/me").status_code == 200  # esta sessão continua

    login = {"email": ALUNO["email"], "senha": SENHA}
    assert anonimo.post("/api/v1/auth/login", json=login).status_code == 401
    login["senha"] = "Nova@Senha9"
    assert anonimo.post("/api/v1/auth/login", json=login).status_code == 200


def test_rbn0104_troca_de_senha_encerra_as_outras_sessoes(coord, caixa, anonimo):
    from fastapi.testclient import TestClient

    from app.main import app

    outra = TestClient(app)
    assert outra.post("/api/v1/auth/login", json={"email": COORD, "senha": SENHA}).status_code == 200
    r = coord.post(
        "/api/v1/usuarios/me/senha", json={"senha_atual": SENHA, "nova_senha": "Nova@Senha9"}
    )
    assert r.status_code == 200
    assert coord.get("/api/v1/usuarios/me").status_code == 200
    assert outra.get("/api/v1/usuarios/me").status_code == 401


# ---------- casos de teste das fichas SCRUM-29 e SCRUM-30 ----------


def test_ct_01_09_03_foto_recusada_mantem_a_anterior(coord, caixa):
    aluno = _aluno(coord, caixa)
    versao = aluno.put("/api/v1/usuarios/me/foto", files={"foto": ("f.png", PNG)}).json()
    r = aluno.put("/api/v1/usuarios/me/foto", files={"foto": ("virus.exe", b"MZ\x90\x00")})
    assert r.status_code == 415
    assert aluno.get("/api/v1/usuarios/me").json()["foto_versao"] == versao["foto_versao"]


def test_ct_01_09_04_aluno_nao_exclui_a_propria_conta(coord, caixa):
    aluno = _aluno(coord, caixa)
    assert aluno.delete("/api/v1/usuarios/me").status_code in (403, 405)
    assert aluno.get("/api/v1/usuarios/me").status_code == 200


def test_ct_01_09_05_e_01_10_05_ninguem_edita_o_perfil_de_outro(coord, caixa):
    aluno = _aluno(coord, caixa)
    outro = coord.post("/api/v1/docentes", json=DOCENTE).json()
    r = aluno.put(f"/api/v1/usuarios/{outro['id']}", json={"telefone": "92999990000"})
    assert r.status_code == 403
    r = aluno.put(f"/api/v1/usuarios/{outro['id']}/foto", files={"foto": ("f.png", PNG)})
    assert r.status_code == 403


def test_scrum30_coordenador_nao_edita_curso(coord):
    r = coord.put("/api/v1/usuarios/me", json={"curso_id": 1})
    assert r.status_code == 403
    assert coord.put("/api/v1/usuarios/me", json={"telefone": "92999990000"}).status_code == 200
