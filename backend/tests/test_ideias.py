"""SCRUM-34 (RBN02.01) e SCRUM-35 (RBN02.02): ideias de TCC (RN07, RN25 · DS-FL12 e DS-FL12-A).

Cada teste cita o caso de teste da ficha (CT-02.01-xx e CT-02.02-xx) ou o fluxo de exceção. Pessoas: Ana
(aluna), Olga e Otto (orientadores), Paulo (professor da disciplina) e a coordenação. O CT-02.01-06 (tela de
360 px sem rolagem horizontal) é conferido no navegador, não aqui.
"""

import pytest
from sqlalchemy import select

from app.models import AreaInteresse, DocenteArea, LogAuditoria, Proposta, Tcc
from tests.test_defesas_banca import banca  # noqa: F401  (fixture: cenario + Paulo e Ricardo ativos)
from tests.test_tcc import cenario  # noqa: F401  (fixture usada por banca)

URL = "/api/v1/ideias"


@pytest.fixture
def ideias(banca, db):
    """A Olga é vinculada à área do cenário; o Otto não (RN25)."""
    db.add(DocenteArea(docente_id=banca["ids"]["olga"], area_id=banca["area"]["id"]))
    db.commit()
    return banca


def _proposta(d, destino="PROFESSORES", professores=("olga",), **extra):
    corpo = {"titulo": "Detecção de fake news com grafos", "descricao": "Usar redes de propagação para detectar.",
             "area_id": d["area"]["id"], "destino": destino,
             "professores_ids": [d["ids"][p] for p in professores] if destino == "PROFESSORES" else [], **extra}
    return d["aluno"].post(URL, json=corpo)


def _ids(r) -> list[int]:
    return [p["id"] for p in r.json()]


# ---------------------------------------------------------------- RBN02.01 · cadastrar proposta


def test_ct_02_01_01_proposta_para_um_professor_tem_autor_e_data_e_sem_protocolo(ideias, db):
    """CA-01: criada com autor e data registrados; não gera protocolo nem cadastro de TCC."""
    tccs_antes = len(db.scalars(select(Tcc)).all())
    r = _proposta(ideias)
    assert r.status_code == 201, r.json()
    p = r.json()
    assert p["autor"]["id"] == ideias["aluno"].get("/api/v1/auth/me").json()["id"] and p["criado_em"]
    assert (p["destino"], [x["id"] for x in p["professores"]]) == ("PROFESSORES", [ideias["ids"]["olga"]])
    assert "protocolo" not in p and len(db.scalars(select(Tcc)).all()) == tccs_antes
    log = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "criar_ideia"))
    assert log.entidade_id == p["id"] and "Olga Orientadora" in log.valor_novo


def test_ct_02_01_02_sem_destinatario_destaca_o_campo(ideias, db):
    """CA-02 / E1: sem destinatário (e sem os demais campos) nada é criado e os campos voltam destacados."""
    r = _proposta(ideias, professores=())
    assert r.status_code == 400 and set(r.json()["campos"]) == {"professores_ids"}
    r = ideias["aluno"].post(URL, json={"titulo": "  ", "descricao": "", "area_id": None, "destino": None})
    assert r.status_code == 400 and set(r.json()["campos"]) == {"titulo", "descricao", "area_id", "destino"}
    assert db.scalar(select(Proposta)) is None


def test_ct_02_01_03_professor_nao_nomeado_nao_ve(ideias):
    """CA-03: proposta para Olga e Otto não aparece para o Paulo, nem abre (403)."""
    pid = _proposta(ideias, professores=("olga", "otto")).json()["id"]
    assert pid in _ids(ideias["olga"].get(URL)) and pid in _ids(ideias["otto"].get(URL))
    assert pid not in _ids(ideias["paulo"].get(URL))
    assert ideias["paulo"].get(f"{URL}/{pid}").status_code == 403


def test_ct_02_01_04_por_area_so_os_vinculados_veem(ideias):
    """CA-04 / RN25: direcionada à área, a Olga (vinculada) vê; o Otto (não vinculado) não."""
    r = _proposta(ideias, destino="AREA")
    assert r.status_code == 201 and r.json()["area"]["id"] == ideias["area"]["id"] and r.json()["professores"] == []
    pid = r.json()["id"]
    assert pid in _ids(ideias["olga"].get(URL))
    assert pid not in _ids(ideias["otto"].get(URL))
    assert ideias["otto"].get(f"{URL}/{pid}").status_code == 403


def test_ct_02_01_05_professor_nao_cadastra_proposta(ideias, coord):
    """CA-05 / E2: outro perfil recebe 403, inclusive no formulário."""
    corpo = {"titulo": "x", "descricao": "y", "area_id": ideias["area"]["id"], "destino": "AREA"}
    assert ideias["olga"].post(URL, json=corpo).status_code == 403
    assert coord.post(URL, json=corpo).status_code == 403
    assert ideias["olga"].get(f"{URL}/formulario").status_code == 403


def test_formulario_traz_areas_e_so_professores_e_orientadores_ativos(ideias, db):
    """DS-FL12 mensagens 2 a 4: áreas e docentes elegíveis (a coordenadora do teste também é professora da
    disciplina, pela carga inicial); aluno não é destinatário."""
    f = ideias["aluno"].get(f"{URL}/formulario").json()
    assert {a["id"] for a in f["areas"]} == {a.id for a in db.scalars(select(AreaInteresse))}
    nomes = {d["nome"] for d in f["docentes"]}
    assert {"Olga Orientadora", "Otto Orientador", "Paulo Professor"} <= nomes
    assert "Ana Ribeiro" not in nomes


def test_professor_que_nao_e_elegivel_e_recusado(ideias):
    """verificarPerfil(idsProfessores): só professores da disciplina e orientadores ativos."""
    r = ideias["aluno"].post(URL, json={"titulo": "T", "descricao": "D", "area_id": ideias["area"]["id"],
                                         "destino": "PROFESSORES", "professores_ids": [999]})
    assert r.status_code == 400 and "professores_ids" in r.json()["campos"]


def test_aluno_ve_so_as_proprias_propostas(ideias, caixa, coord):
    from tests.conftest import ativar

    outro = {"nome": "Bruno Batista", "email": "bruno@uea.edu.br", "matricula": "24150002", "curso_id": 1}
    assert coord.post("/api/v1/alunos", json=outro).status_code == 201
    bruno = ativar(caixa, outro["email"])
    pid = _proposta(ideias).json()["id"]
    assert _ids(ideias["aluno"].get(URL)) == [pid]
    assert _ids(bruno.get(URL)) == []
    assert bruno.get(f"{URL}/{pid}").status_code == 403


# ---------------------------------------------------------------- RBN02.02 · consultar e comentar


def test_ct_02_02_01_destinatario_ve_autor_data_e_texto(ideias):
    """CA-01: autor, data, texto e a discussão (ainda vazia)."""
    pid = _proposta(ideias).json()["id"]
    p = ideias["olga"].get(f"{URL}/{pid}").json()
    assert (p["autor"]["nome"], p["descricao"]) == ("Ana Ribeiro", "Usar redes de propagação para detectar.")
    assert p["criado_em"] and p["discussao"] == [] and p["pode_comentar"] is True


def test_ct_02_02_02_comentario_salvo_com_autor_e_data(ideias, db):
    """CA-02: salvo com autor e data/hora e exibido na discussão; fica no log."""
    pid = _proposta(ideias).json()["id"]
    r = ideias["olga"].post(f"{URL}/{pid}/comentarios", json={"texto": "Tema relevante; detalhe a metodologia"})
    assert r.status_code == 201, r.json()
    [c] = r.json()["discussao"]
    assert (c["autor"]["id"], c["texto"]) == (ideias["ids"]["olga"], "Tema relevante; detalhe a metodologia")
    assert c["criado_em"] and r.json()["comentarios"] == 1
    assert db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "comentar_ideia")).entidade_id == c["id"]


@pytest.mark.parametrize("texto", ["", "   "], ids=["ct_02_02_03_vazio", "ct_02_02_04_so_espacos"])
def test_ct_02_02_03_e_04_comentario_vazio_e_bloqueado(ideias, texto):
    """CA-03 / E2: vazio ou só espaços não é aceito."""
    pid = _proposta(ideias).json()["id"]
    r = ideias["olga"].post(f"{URL}/{pid}/comentarios", json={"texto": texto})
    assert r.status_code == 400 and "texto" in r.json()["campos"]
    assert ideias["olga"].get(f"{URL}/{pid}").json()["discussao"] == []


def test_ct_02_02_05_professor_nao_destinatario_nao_comenta(ideias):
    """CA-04: proposta de outro professor → 403 no comentário pela API."""
    pid = _proposta(ideias, professores=("otto",)).json()["id"]
    assert ideias["olga"].post(f"{URL}/{pid}/comentarios", json={"texto": "Posso orientar."}).status_code == 403


def test_ct_02_02_06_aluno_autor_ve_o_comentario(ideias):
    """CA-05: o aluno autor vê o comentário ao abrir a proposta, sem poder comentar."""
    pid = _proposta(ideias, destino="AREA").json()["id"]
    ideias["olga"].post(f"{URL}/{pid}/comentarios", json={"texto": "Tema relevante; detalhe a metodologia"})
    p = ideias["aluno"].get(f"{URL}/{pid}").json()
    assert [c["texto"] for c in p["discussao"]] == ["Tema relevante; detalhe a metodologia"]
    assert p["pode_comentar"] is False
    assert ideias["aluno"].post(f"{URL}/{pid}/comentarios", json={"texto": "Obrigada!"}).status_code == 403


def test_proposta_inexistente_e_404(ideias):
    assert ideias["olga"].get(f"{URL}/999").status_code == 404
