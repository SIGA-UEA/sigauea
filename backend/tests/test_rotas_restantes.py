"""Rotas do contrato da API que nenhum outro teste chamava (HT03, CA-01: toda operação com rota testada).

O levantamento veio do registrador de status (docs/arquitetura/coleta_status.py): estas eram as
operações sem nenhuma resposta observada na suíte.
"""

from tests.conftest import DOCENTE
from tests.test_perfil import JPG
from tests.test_tcc import _rascunho, cenario  # noqa: F401  (cenario é fixture)


def test_health_responde_sem_login(anonimo):
    r = anonimo.get("/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_catalogo_de_cursos_e_perfis_exige_login(coord, anonimo):
    cursos = coord.get("/api/v1/cursos").json()
    assert {c["sigla"] for c in cursos} == {"EC", "LC", "SI"}  # RN01
    perfis = {p["codigo"] for p in coord.get("/api/v1/perfis").json()}
    assert perfis == {"aluno", "orientador", "professor_disciplina", "coordenador", "membro_banca"}  # RN07
    assert anonimo.get("/api/v1/cursos").status_code == 401
    assert anonimo.get("/api/v1/perfis").status_code == 401


def test_lista_de_periodos_e_de_turmas(cenario, coord):
    periodos = coord.get("/api/v1/periodos").json()
    assert [p["codigo"] for p in periodos] == ["2026/2"]
    turmas = coord.get("/api/v1/turmas").json()
    assert [t["codigo"] for t in turmas] == ["TCC1-EC-2026/2-1"]
    filtradas = coord.get(f"/api/v1/turmas?periodo={cenario['periodo']['id']}").json()
    assert len(filtradas) == 1
    # a lista completa de turmas é só da coordenação; o aluno usa /turmas/minhas
    assert cenario["aluno"].get("/api/v1/turmas").status_code == 403
    assert cenario["aluno"].get("/api/v1/periodos").status_code == 200  # qualquer usuário logado


def test_orientador_abre_a_solicitacao_e_outro_docente_nao(cenario):
    _rascunho(cenario)
    [pedido] = cenario["olga"].get("/api/v1/orientacoes?status=PENDENTE").json()
    r = cenario["olga"].get(f"/api/v1/orientacoes/{pedido['id']}")
    assert r.status_code == 200 and r.json()["status"] == "PENDENTE"
    assert r.json()["tcc"]["titulo"].startswith("Detecção de fraudes")
    # RN07: quem não é o orientador pedido não vê a solicitação (404, sem revelar que existe)
    assert cenario["otto"].get(f"/api/v1/orientacoes/{pedido['id']}").status_code == 404


def test_coordenacao_remove_a_foto_do_docente(coord, caixa):
    docente = coord.post("/api/v1/docentes", json=DOCENTE).json()
    coord.put(f"/api/v1/usuarios/{docente['id']}/foto", files={"foto": ("f.jpg", JPG)})
    r = coord.delete(f"/api/v1/usuarios/{docente['id']}/foto")
    assert r.status_code == 200 and r.json()["foto_versao"] is None
    assert coord.get(f"/api/v1/usuarios/{docente['id']}/foto").status_code == 404


def test_so_a_coordenacao_remove_foto_de_outra_pessoa(cenario):
    alvo = cenario["orientador"]["id"]
    assert cenario["aluno"].delete(f"/api/v1/usuarios/{alvo}/foto").status_code == 403
    assert cenario["otto"].delete(f"/api/v1/usuarios/{alvo}/foto").status_code == 403


def test_rnf06_foto_alterada_no_banco_nao_e_entregue(coord, caixa, db):
    """RNF06: o checksum SHA-256 é conferido no envio e também na leitura."""
    from app.models import FotoUsuario

    docente = coord.post("/api/v1/docentes", json=DOCENTE).json()
    coord.put(f"/api/v1/usuarios/{docente['id']}/foto", files={"foto": ("f.jpg", JPG)})
    assert coord.get(f"/api/v1/usuarios/{docente['id']}/foto").content == JPG
    foto = db.get(FotoUsuario, docente["id"])
    foto.conteudo = JPG + b"corrompido"
    db.commit()
    r = coord.get(f"/api/v1/usuarios/{docente['id']}/foto")
    assert r.status_code == 500 and "não confere" in r.json()["detail"]
