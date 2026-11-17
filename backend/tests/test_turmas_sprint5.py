"""Sprint S05 · turmas: pré-preencher o TCC2 com o TCC1 (SCRUM-45, RBN08.04) e encerrar a turma
(SCRUM-46, RBN08.05, DS-FL11-D).

Cada teste cita o caso de teste (CT) da ficha que confere. O cenário é montado pela API.
"""

import pytest
from sqlalchemy import select

from app.models import LogAuditoria, Tcc
from tests.conftest import ALUNO, ativar

ORIENTADOR = {"nome": "Olga Orientadora", "email": "olga@exemplo.com", "cargo": "orientador",
              "curso_id": 1, "perfis": ["orientador"]}
OUTRO_ORIENTADOR = {**ORIENTADOR, "nome": "Otto Orientador", "email": "otto@exemplo.com"}
PROFESSOR = {"nome": "Paulo Professor", "email": "paulo@exemplo.com", "cargo": "professor",
             "curso_id": 1, "perfis": ["professor_disciplina"]}
OUTRO_PROFESSOR = {**PROFESSOR, "nome": "Pedro Professor", "email": "pedro@exemplo.com"}


def _turma(coord, disciplina, periodo_id, professor_id):
    r = coord.post("/api/v1/turmas", json={"disciplina": disciplina, "curso_id": 1,
                                           "periodo_id": periodo_id, "professor_id": professor_id})
    assert r.status_code == 201, r.text
    return r.json()


def _matricular(coord, turma_id, aluno_id):
    r = coord.post(f"/api/v1/turmas/{turma_id}/alunos", json={"aluno_id": aluno_id})
    assert r.status_code == 201, r.text
    return next(a for a in r.json()["alunos"] if a["aluno"]["id"] == aluno_id)


def _situacao(coord, turma_id, matricula_id, situacao):
    r = coord.patch(f"/api/v1/turmas/{turma_id}/alunos/{matricula_id}", json={"situacao": situacao})
    assert r.status_code == 200, r.text
    return r


# =================================================================== SCRUM-45 · RBN08.04


@pytest.fixture
def tcc1(coord, caixa):
    """A aluna fez o TCC1 em 2026/1 com a Olga (orientação aceita) e foi aprovada."""
    p1 = coord.post("/api/v1/periodos", json={"codigo": "2026/1", "inicio": "2026-02-01",
                                              "fim": "2026-07-15"}).json()
    professor = coord.post("/api/v1/docentes", json=PROFESSOR).json()
    olga = coord.post("/api/v1/docentes", json=ORIENTADOR).json()
    otto = coord.post("/api/v1/docentes", json=OUTRO_ORIENTADOR).json()
    aluno = coord.post("/api/v1/alunos", json=ALUNO).json()
    turma1 = _turma(coord, "TCC1", p1["id"], professor["id"])
    m1 = _matricular(coord, turma1["id"], aluno["id"])
    area = coord.get("/api/v1/areas").json()[1]
    ana = ativar(caixa, ALUNO["email"])
    olga_c = ativar(caixa, ORIENTADOR["email"])
    ativar(caixa, OUTRO_ORIENTADOR["email"])
    r = ana.post("/api/v1/tccs", json={
        "titulo": "Detecção de fraudes com aprendizado de máquina", "resumo": "Resumo do TCC1.",
        "palavras_chave": ["IA"], "area_id": area["id"], "modalidade": "MONOGRAFIA",
        "orientador_id": olga["id"]})
    assert r.status_code == 201, r.text
    pedido = olga_c.get("/api/v1/orientacoes?status=PENDENTE").json()[0]
    assert olga_c.post(f"/api/v1/orientacoes/{pedido['id']}/resposta",
                       json={"decisao": "ACEITAR"}).status_code == 200
    _situacao(coord, turma1["id"], m1["id"], "APROVADO")
    # TCC2 em 2026/2 (período em curso), na turma da orientadora (RN26)
    p2 = coord.post("/api/v1/periodos", json={"codigo": "2026/2", "inicio": "2026-08-01",
                                              "fim": "2026-12-20"}).json()
    turma2 = _turma(coord, "TCC2", p2["id"], olga["id"])
    return {"tcc1": r.json(), "aluno": aluno, "ana": ana, "olga": olga, "otto": otto, "area": area,
            "turma2": turma2, "p2": p2}


def test_ct_08_04_01_formulario_do_tcc2_traz_titulo_area_e_orientador_do_tcc1(coord, tcc1):
    _matricular(coord, tcc1["turma2"]["id"], tcc1["aluno"]["id"])
    form = tcc1["ana"].get("/api/v1/tccs/formulario").json()
    assert form["turma"]["disciplina"] == "TCC2" and form["tcc"] is None
    origem = form["origem"]
    assert origem["tcc_origem_id"] == tcc1["tcc1"]["id"]
    assert origem["titulo"] == "Detecção de fraudes com aprendizado de máquina"
    assert origem["area_id"] == tcc1["area"]["id"]
    assert origem["orientador_id"] == tcc1["olga"]["id"]


def test_ct_08_04_02_e_08_04_05_tcc2_com_novo_titulo_e_novo_cadastro_sem_alterar_o_tcc1(coord, tcc1, db):
    _matricular(coord, tcc1["turma2"]["id"], tcc1["aluno"]["id"])
    outra_area = coord.get("/api/v1/areas").json()[0]
    r = tcc1["ana"].post("/api/v1/tccs", json={
        "titulo": "Detecção de fraudes em tempo real com aprendizado de máquina",
        "resumo": "Agora com metodologia e resultados esperados.", "palavras_chave": ["IA", "fraude"],
        "area_id": outra_area["id"], "modalidade": "MONOGRAFIA", "orientador_id": tcc1["olga"]["id"]})
    assert r.status_code == 201, r.text
    tcc2 = r.json()
    assert tcc2["id"] != tcc1["tcc1"]["id"] and tcc2["etapa"] == "TCC2"
    assert tcc2["tcc_origem_id"] == tcc1["tcc1"]["id"]
    assert tcc2["titulo"].startswith("Detecção de fraudes em tempo real")
    antigo = db.get(Tcc, tcc1["tcc1"]["id"])
    assert antigo.titulo == "Detecção de fraudes com aprendizado de máquina"
    assert antigo.area_id == tcc1["area"]["id"] and antigo.etapa == "TCC1"
    # CT-08.04-05: o TCC2 terá protocolo próprio; o rascunho ainda não tem e o TCC1 não ganha outro
    assert tcc2["protocolo"] is None and antigo.protocolo == tcc1["tcc1"]["protocolo"]


def test_ct_08_04_03_trocar_o_orientador_segue_o_fluxo_de_indicacao(coord, tcc1, caixa):
    """CA-03: o orientador do TCC1 não é imposto; indicar outro gera um pedido novo (RAN06)."""
    _matricular(coord, tcc1["turma2"]["id"], tcc1["aluno"]["id"])
    r = tcc1["ana"].post("/api/v1/tccs", json={
        "titulo": "Outro tema", "resumo": "", "palavras_chave": [], "area_id": tcc1["area"]["id"],
        "modalidade": "MONOGRAFIA", "orientador_id": tcc1["otto"]["id"]})
    assert r.status_code == 201, r.text
    assert r.json()["orientador"]["professor"]["id"] == tcc1["otto"]["id"]
    assert r.json()["orientador"]["status"] == "PENDENTE"
    assert any(m["para"] == OUTRO_ORIENTADOR["email"] for m in caixa)


def test_ct_08_04_04_aluno_de_tcc2_sem_tcc1_abre_o_formulario_em_branco(coord, caixa):
    p2 = coord.post("/api/v1/periodos", json={"codigo": "2026/2", "inicio": "2026-08-01",
                                              "fim": "2026-12-20"}).json()
    olga = coord.post("/api/v1/docentes", json=ORIENTADOR).json()
    aluno = coord.post("/api/v1/alunos", json=ALUNO).json()
    turma2 = _turma(coord, "TCC2", p2["id"], olga["id"])
    _matricular(coord, turma2["id"], aluno["id"])
    r = ativar(caixa, ALUNO["email"]).get("/api/v1/tccs/formulario")
    assert r.status_code == 200 and r.json()["origem"] is None


def test_rbn0804_a2_orientacao_do_tcc1_nao_aceita_nao_preenche_o_orientador(coord, caixa):
    p1 = coord.post("/api/v1/periodos", json={"codigo": "2026/1", "inicio": "2026-02-01",
                                              "fim": "2026-07-15"}).json()
    professor = coord.post("/api/v1/docentes", json=PROFESSOR).json()
    olga = coord.post("/api/v1/docentes", json=ORIENTADOR).json()
    aluno = coord.post("/api/v1/alunos", json=ALUNO).json()
    turma1 = _turma(coord, "TCC1", p1["id"], professor["id"])
    _matricular(coord, turma1["id"], aluno["id"])
    ana = ativar(caixa, ALUNO["email"])
    ativar(caixa, ORIENTADOR["email"])
    area = coord.get("/api/v1/areas").json()[0]
    assert ana.post("/api/v1/tccs", json={"titulo": "Tema do TCC1", "resumo": "", "palavras_chave": [],
                                   "area_id": area["id"], "modalidade": "ARTIGO",
                                   "orientador_id": olga["id"]}).status_code == 201  # pedido fica PENDENTE
    p2 = coord.post("/api/v1/periodos", json={"codigo": "2026/2", "inicio": "2026-08-01",
                                              "fim": "2026-12-20"}).json()
    turma2 = _turma(coord, "TCC2", p2["id"], olga["id"])
    _matricular(coord, turma2["id"], aluno["id"])
    origem = ana.get("/api/v1/tccs/formulario").json()["origem"]
    assert origem["titulo"] == "Tema do TCC1" and origem["modalidade"] == "ARTIGO"
    assert origem["orientador_id"] is None


def test_rbn0804_e1_aluno_sem_matricula_matriculado_nao_abre_o_tcc2(coord, tcc1):
    m = _matricular(coord, tcc1["turma2"]["id"], tcc1["aluno"]["id"])
    _situacao(coord, tcc1["turma2"]["id"], m["id"], "DESISTENTE")
    r = tcc1["ana"].get("/api/v1/tccs/formulario")
    assert r.status_code == 403 and r.json()["motivo"] == "sem_matricula"


def test_rbn0804_tcc1_nao_tem_origem(tcc1):
    assert tcc1["tcc1"]["tcc_origem_id"] is None


# =================================================================== SCRUM-46 · RBN08.05


@pytest.fixture
def turma(coord, caixa):
    """Turma de TCC1 2026/2 do Paulo com três alunos, todos Matriculados."""
    p = coord.post("/api/v1/periodos", json={"codigo": "2026/2", "inicio": "2026-08-01",
                                             "fim": "2026-12-20"}).json()
    paulo = coord.post("/api/v1/docentes", json=PROFESSOR).json()
    coord.post("/api/v1/docentes", json=OUTRO_PROFESSOR)
    t = _turma(coord, "TCC1", p["id"], paulo["id"])
    matriculas = []
    for i, nome in enumerate(("Ana Ribeiro", "Bruno Lima", "Carla Souza")):
        a = coord.post("/api/v1/alunos", json={"nome": nome, "email": f"aluno{i}@uea.edu.br",
                                               "matricula": f"2415000{i}", "curso_id": 1}).json()
        matriculas.append(_matricular(coord, t["id"], a["id"]))
    return {"turma": t, "matriculas": matriculas, "paulo": ativar(caixa, PROFESSOR["email"]),
            "pedro": ativar(caixa, OUTRO_PROFESSOR["email"]), "periodo": p}


def _encerrar(cliente, turma_id):
    return cliente.post(f"/api/v1/turmas/{turma_id}/encerramento")


def test_ct_08_05_01_turma_sem_matriculados_e_encerrada_com_data(coord, turma):
    tid = turma["turma"]["id"]
    for m, s in zip(turma["matriculas"], ("APROVADO", "REPROVADO", "DESISTENTE")):
        _situacao(coord, tid, m["id"], s)
    assert turma["paulo"].get(f"/api/v1/turmas/{tid}").json()["pode_encerrar"] is True
    r = _encerrar(turma["paulo"], tid)
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["encerrada"] is True and corpo["encerrada_em"] and corpo["pode_encerrar"] is False
    cartao = turma["paulo"].get("/api/v1/turmas/minhas").json()[0]
    assert cartao["encerrada"] is True


def test_ct_08_05_02_com_matriculados_bloqueia_e_lista_os_pendentes(coord, turma):
    tid = turma["turma"]["id"]
    _situacao(coord, tid, turma["matriculas"][0]["id"], "APROVADO")
    r = _encerrar(turma["paulo"], tid)
    assert r.status_code == 422
    assert [p["aluno"] for p in r.json()["pendentes"]] == ["Bruno Lima", "Carla Souza"]
    assert turma["paulo"].get(f"/api/v1/turmas/{tid}").json()["encerrada"] is False


def _encerrada(coord, turma):
    tid = turma["turma"]["id"]
    for m in turma["matriculas"]:
        _situacao(coord, tid, m["id"], "APROVADO")
    assert _encerrar(turma["paulo"], tid).status_code == 200
    return tid


def test_ct_08_05_03_turma_encerrada_nao_aceita_aluno(coord, turma):
    tid = _encerrada(coord, turma)
    novo = coord.post("/api/v1/alunos", json={"nome": "Davi Novo", "email": "davi@uea.edu.br",
                                              "matricula": "24159999", "curso_id": 1}).json()
    r = coord.post(f"/api/v1/turmas/{tid}/alunos", json={"aluno_id": novo["id"]})
    assert r.status_code == 409


def test_ct_08_05_04_turma_encerrada_nao_aceita_mudanca_de_situacao(coord, turma):
    tid = _encerrada(coord, turma)
    r = coord.patch(f"/api/v1/turmas/{tid}/alunos/{turma['matriculas'][0]['id']}",
                    json={"situacao": "REPROVADO"})
    assert r.status_code == 409


def test_rbn0805_e2_encerrar_de_novo_responde_409(coord, turma):
    tid = _encerrada(coord, turma)
    r = _encerrar(turma["paulo"], tid)
    assert r.status_code == 409 and r.json()["detail"] == "Turma já encerrada."


def test_ct_08_05_05_so_o_professor_responsavel_encerra(coord, turma):
    tid = turma["turma"]["id"]
    for m in turma["matriculas"]:
        _situacao(coord, tid, m["id"], "APROVADO")
    for cliente in (turma["pedro"], coord):  # outro professor e a coordenação: 404 (RN24)
        r = _encerrar(cliente, tid)
        assert r.status_code == 404 and r.json()["detail"] == "Turma não encontrada."
    assert _encerrar(turma["paulo"], 9999).status_code == 404
    # a coordenação vê a turma, mas não tem o botão
    assert coord.get(f"/api/v1/turmas/{tid}").json()["pode_encerrar"] is False


def test_ct_08_05_06_encerramento_fica_no_log(coord, turma, db):
    tid = _encerrada(coord, turma)
    log = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "encerrar_turma"))
    paulo_id = turma["turma"]["professor"]["id"]
    assert (log.usuario_id, log.entidade, log.entidade_id) == (paulo_id, "turma", tid)
    assert (log.valor_anterior, log.valor_novo) == ("ABERTA", "ENCERRADA") and log.criado_em


def test_rbn0805_encerrar_turma_nao_conclui_tcc(coord, turma, caixa, db):
    """RBN08.05: encerrar a turma é passo distinto de concluir o TCC (RBN11.04)."""
    tid = turma["turma"]["id"]
    olga = coord.post("/api/v1/docentes", json=ORIENTADOR).json()
    ativar(caixa, ORIENTADOR["email"])
    ana = ativar(caixa, "aluno0@uea.edu.br")
    area = coord.get("/api/v1/areas").json()[0]
    tcc = ana.post("/api/v1/tccs", json={"titulo": "Tema", "resumo": "", "palavras_chave": [],
                                         "area_id": area["id"], "modalidade": "MONOGRAFIA",
                                         "orientador_id": olga["id"]}).json()
    assert turma["paulo"].get(f"/api/v1/turmas/{tid}").json()["alunos"][0]["tcc"]["id"] == tcc["id"]
    _encerrada(coord, turma)
    db.expire_all()
    assert db.get(Tcc, tcc["id"]).situacao == "RASCUNHO" and db.get(Tcc, tcc["id"]).concluido_em is None
