"""SCRUM-88 (RBN13.01) e SCRUM-89 (RBN13.02): indicadores por perfil, situação dos TCCs e orientações (RN18 ·
DS-FL08-D, TEL16).

Cada teste cita o caso de teste da ficha (CT-13.01-xx e CT-13.02-xx). Cenário: a fixture `banca` (período 2026/2
vigente, turma TCC1 de EC do Paulo, TCC da Ana aprovado e orientado pela Olga) e TCCs extras gravados direto no
banco, para ter todas as situações, as duas etapas e dois cursos.
"""

import json

import pytest
from sqlalchemy import select

from app.models import Orientacao, Perfil, PeriodoLetivo, Tcc, Turma, UsuarioPerfil
from tests.test_defesas_banca import banca  # noqa: F401  (fixture)
from tests.test_tcc import cenario  # noqa: F401  (fixture usada por banca)

URL = "/api/v1/indicadores"


def _aluno(coord, n: int, curso: int = 1) -> int:
    r = coord.post("/api/v1/alunos", json={"nome": f"Aluno Indicador {n}", "email": f"ind{n}@uea.edu.br",
                                           "matricula": f"2599{n:04d}", "curso_id": curso})
    assert r.status_code == 201, r.json()
    return r.json()["id"]


def _turma(db, b, disciplina: str, professor: str, curso: int = 1) -> int:
    t = Turma(codigo=f"{disciplina}-{curso}-{professor}", disciplina=disciplina, curso_id=curso,
              periodo_id=b["periodo"]["id"], professor_id=b["ids"][professor])
    db.add(t)
    db.commit()
    return t.id


def _tcc(db, b, aluno_id: int, situacao: str, etapa: str = "TCC1", orientador: str | None = "olga",
         turma_id: int | None = None, periodo_id: int | None = None) -> int:
    t = Tcc(aluno_id=aluno_id, turma_id=turma_id or b["turma"]["id"], periodo_id=periodo_id or b["periodo"]["id"],
            etapa=etapa, modalidade="MONOGRAFIA", titulo=f"TCC {situacao}", resumo="Resumo.",
            area_id=b["area"]["id"], situacao=situacao)
    db.add(t)
    db.flush()
    if orientador:
        db.add(Orientacao(tcc_id=t.id, professor_id=b["ids"][orientador], papel="ORIENTADOR", status="ACEITA"))
    db.commit()
    return t.id


def _contagem(corpo) -> dict:
    return {s["situacao"]: (s["total"]["TCC1"], s["total"]["TCC2"]) for s in corpo["situacoes"]}


def _orientacoes(corpo) -> dict:
    return {o["orientador"]["nome"]: (o["total"]["TCC1"], o["total"]["TCC2"]) for o in corpo["orientacoes"]}


@pytest.fixture
def ind(banca, coord, db):
    """Além do TCC da Ana (TCC1, aprovado, Olga): TCC1 nas outras situações, dois TCC2 da Olga, um do Otto e um TCC
    de outro curso (LC, curso 2) na turma de outro professor (o Otto)."""
    turma_tcc2 = _turma(db, banca, "TCC2", "paulo")
    turma_lc = _turma(db, banca, "TCC1", "otto", curso=2)
    for n, sit in enumerate(("RASCUNHO", "EM_ANALISE", "DEVOLVIDO", "REPROVADO", "DESISTENCIA"), start=1):
        _tcc(db, banca, _aluno(coord, n), sit)
    _tcc(db, banca, _aluno(coord, 6), "APROVADO", "TCC2", turma_id=turma_tcc2)
    _tcc(db, banca, _aluno(coord, 7), "EM_ANALISE", "TCC2", turma_id=turma_tcc2)
    _tcc(db, banca, _aluno(coord, 8), "APROVADO", "TCC2", orientador="otto", turma_id=turma_tcc2)
    _tcc(db, banca, _aluno(coord, 9, curso=2), "APROVADO", orientador="otto", turma_id=turma_lc)
    return {**banca, "coord": coord, "turma_tcc2": turma_tcc2, "turma_lc": turma_lc}


# ---------------------------------------------------------------- SCRUM-88 · RBN13.01 escopo por perfil


def test_ct_13_01_01_coordenacao_ve_os_dois_cursos(ind):
    corpo = ind["coord"].get(f"{URL}/situacao").json()
    assert (corpo["total"]["TCC1"], corpo["total"]["TCC2"]) == (7, 3)  # 6 de EC e 1 de LC; 3 em TCC2
    assert {c["sigla"] for c in ind["coord"].get(f"{URL}/escopo").json()["cursos"]} >= {"EC", "LC"}


def test_ct_13_01_02_professor_ve_so_as_suas_turmas(ind):
    """O Paulo é professor das turmas TCC1 e TCC2 de EC; o TCC de LC (turma do Otto) fica de fora."""
    corpo = ind["paulo"].get(f"{URL}/situacao").json()
    assert (corpo["total"]["TCC1"], corpo["total"]["TCC2"]) == (6, 3)
    escopo = ind["paulo"].get(f"{URL}/escopo").json()
    assert {t["id"] for t in escopo["turmas"]} == {ind["turma"]["id"], ind["turma_tcc2"]}


def test_ct_13_01_03_orientador_ve_so_os_orientandos(ind):
    """A Olga orienta 6 em TCC1 e 2 em TCC2."""
    corpo = ind["olga"].get(f"{URL}/situacao").json()
    assert (corpo["total"]["TCC1"], corpo["total"]["TCC2"]) == (6, 2)


def test_ct_13_01_04_dois_perfis_somam_escopos_sem_duplicar(ind, db):
    """O Otto passa a professor da turma de LC (já é) e orientador: soma a turma de LC com os 2 orientandos dele,
    e o TCC de LC, que é das duas coisas, conta uma vez."""
    perfil = db.scalar(select(Perfil).where(Perfil.codigo == "professor_disciplina"))
    db.add(UsuarioPerfil(usuario_id=ind["ids"]["otto"], perfil_id=perfil.id))
    db.commit()
    corpo = ind["otto"].get(f"{URL}/situacao").json()
    assert (corpo["total"]["TCC1"], corpo["total"]["TCC2"]) == (1, 1)
    assert ind["otto"].get(f"{URL}/escopo").json()["filtros"]["turma"] is True


def test_ct_13_01_05_nenhuma_resposta_traz_nome_de_aluno(ind):
    for cliente in (ind["coord"], ind["paulo"], ind["olga"]):
        for rota in ("escopo", "situacao"):
            texto = json.dumps(cliente.get(f"{URL}/{rota}").json(), ensure_ascii=False)
            assert "Aluno Indicador" not in texto and "Ana Ribeiro" not in texto


def test_ct_13_01_06_orientador_nao_ve_a_distribuicao_de_outros(ind):
    """Visão exclusiva da coordenação: filtrar por outro orientador é negado (403), mesmo pela URL."""
    r = ind["olga"].get(f"{URL}/situacao?orientador={ind['ids']['otto']}")
    assert r.status_code == 403 and r.json()["campo"] == "orientador"
    assert ind["paulo"].get(f"{URL}/situacao?orientador={ind['ids']['olga']}").status_code == 403


def test_aluno_nao_abre_os_indicadores(ind):
    assert ind["aluno"].get(f"{URL}/escopo").status_code == 403
    assert ind["aluno"].get(f"{URL}/situacao").status_code == 403


# ---------------------------------------------------------------- SCRUM-89 · RBN13.02 situação e orientações


def test_ct_13_02_01_contagem_por_situacao_e_etapa(ind):
    c = _contagem(ind["coord"].get(f"{URL}/situacao").json())
    assert c["RASCUNHO"] == (1, 0) and c["EM_ANALISE"] == (1, 1) and c["DEVOLVIDO"] == (1, 0)
    assert c["REPROVADO"] == (1, 0) and c["DESISTENCIA"] == (1, 0)
    assert c["APROVADO"] == (2, 2)  # Ana e o de LC em TCC1; dois em TCC2


def test_ct_13_02_02_tcc_com_banca_conta_uma_vez(ind):
    """O TCC da Ana tem banca de 3 e ainda assim conta 1 vez entre os aprovados de EC em TCC1."""
    c = _contagem(ind["coord"].get(f"{URL}/situacao?curso=1").json())
    assert c["APROVADO"] == (1, 2)


def test_ct_13_02_03_orientacoes_separadas_por_etapa(ind):
    o = _orientacoes(ind["coord"].get(f"{URL}/situacao").json())
    assert o["Olga Orientadora"] == (6, 2) and o["Otto Orientador"] == (1, 1)


def test_ct_13_02_04_coordenacao_filtra_curso_periodo_etapa_e_orientador(ind):
    c = ind["coord"]
    assert c.get(f"{URL}/situacao?curso=2").json()["total"] == {"TCC1": 1, "TCC2": 0}
    assert c.get(f"{URL}/situacao?etapa=TCC2").json()["total"] == {"TCC1": 0, "TCC2": 3}
    assert c.get(f"{URL}/situacao?orientador={ind['ids']['otto']}").json()["total"] == {"TCC1": 1, "TCC2": 1}
    filtros = c.get(f"{URL}/escopo").json()["filtros"]
    # a coordenadora da carga inicial também é professora da disciplina, mas sem turma: o escopo vazio não soma filtro
    assert filtros == {"periodo": True, "curso": True, "etapa": True, "turma": False, "orientador": True}
    assert [p for p, _ in c.get(f"{URL}/escopo").json()["descricao"]] == ["Coordenação"]


def test_ct_13_02_05_professor_so_tem_periodo_e_turma(ind):
    filtros = ind["paulo"].get(f"{URL}/escopo").json()["filtros"]
    assert filtros == {"periodo": True, "curso": False, "etapa": False, "turma": True, "orientador": False}
    assert ind["paulo"].get(f"{URL}/situacao?turma={ind['turma_tcc2']}").json()["total"] == {"TCC1": 0, "TCC2": 3}
    assert ind["paulo"].get(f"{URL}/situacao?curso=1").status_code == 403
    assert ind["paulo"].get(f"{URL}/situacao?turma={ind['turma_lc']}").status_code == 403  # turma de outro


def test_ct_13_02_06_periodo_vigente_vem_marcado(ind, db):
    db.add(PeriodoLetivo(codigo="2026/1", inicio=__import__("datetime").date(2026, 2, 1),
                         fim=__import__("datetime").date(2026, 7, 15)))
    db.commit()
    escopo = ind["coord"].get(f"{URL}/escopo").json()
    assert escopo["periodo_vigente_id"] == ind["periodo"]["id"]
    assert [p["codigo"] for p in escopo["periodos"] if p["vigente"]] == ["2026/2"]
    assert ind["coord"].get(f"{URL}/situacao").json()["periodo_id"] == ind["periodo"]["id"]


def test_ct_13_02_07_orientador_ve_so_o_proprio_total(ind):
    corpo = ind["olga"].get(f"{URL}/situacao").json()
    assert _orientacoes(corpo) == {"Olga Orientadora": (6, 2)}


def test_ct_13_02_08_filtro_sem_dados_zera_e_avisa(ind, db):
    p = PeriodoLetivo(codigo="2025/2", inicio=__import__("datetime").date(2025, 8, 1),
                      fim=__import__("datetime").date(2025, 12, 20))
    db.add(p)
    db.commit()
    corpo = ind["coord"].get(f"{URL}/situacao?periodo={p.id}").json()
    assert corpo["sem_dados"] is True and corpo["total"] == {"TCC1": 0, "TCC2": 0}
    assert all(s["total"] == {"TCC1": 0, "TCC2": 0} for s in corpo["situacoes"])


def test_professor_ve_os_orientadores_dos_alunos_das_suas_turmas(ind):
    o = _orientacoes(ind["paulo"].get(f"{URL}/situacao").json())
    assert o == {"Olga Orientadora": (6, 2), "Otto Orientador": (0, 1)}  # o TCC de LC não é do Paulo


# ---------------------------------------------------------------- SCRUM-90 a 92 · filtros de cada indicador


def _filtros_de(cliente) -> dict:
    """Os filtros ligados de cada indicador, para comparar sem repetir os desligados."""
    por_indicador = cliente.get(f"{URL}/escopo").json()["filtros_indicadores"]
    return {nome: {f for f, ligado in filtros.items() if ligado} for nome, filtros in por_indicador.items()}


def test_ct_13_04_05_cada_perfil_tem_os_filtros_da_ficha(ind):
    """CT-13.04-05 (e CA-04 do RBN13.03, CA-03 e CA-04 do RBN13.05): cada indicador traz só os filtros do perfil."""
    assert _filtros_de(ind["coord"]) == {
        "situacao": {"periodo", "curso", "etapa", "orientador"},
        "producao": {"periodo", "curso"},
        "desistencias": {"periodo", "curso", "etapa", "intervalo"},
        "bancas": {"periodo", "curso", "professor", "papel"},
    }
    assert _filtros_de(ind["paulo"]) == {
        "situacao": {"periodo", "turma"},
        "producao": {"periodo", "turma"},
        "desistencias": {"periodo", "turma"},
        "bancas": {"periodo", "papel"},
    }
    assert _filtros_de(ind["olga"]) == {
        "situacao": {"periodo", "curso", "etapa"},
        "producao": {"periodo", "curso"},
        "desistencias": {"periodo"},
        "bancas": {"periodo", "papel"},
    }


def test_filtros_de_quem_tem_dois_perfis_somam(ind, db):
    """CA-04 do RBN13.01: o Otto, orientador e professor da turma de LC, tem os filtros dos dois perfis."""
    perfil = db.scalar(select(Perfil).where(Perfil.codigo == "professor_disciplina"))
    db.add(UsuarioPerfil(usuario_id=ind["ids"]["otto"], perfil_id=perfil.id))
    db.commit()
    filtros = _filtros_de(ind["otto"])
    assert filtros["producao"] == {"periodo", "curso", "turma"}
    assert filtros["desistencias"] == {"periodo", "turma"}  # evolução e etapa continuam só da coordenação


def test_so_a_coordenacao_recebe_a_lista_de_professores_das_bancas(ind):
    """RBN13.05: o filtro "professor" é só da coordenação; os demais perfis não recebem a lista."""
    nomes = {p["nome"] for p in ind["coord"].get(f"{URL}/escopo").json()["professores"]}
    assert {"Olga Orientadora", "Otto Orientador"} <= nomes
    assert ind["paulo"].get(f"{URL}/escopo").json()["professores"] == []
    assert ind["olga"].get(f"{URL}/escopo").json()["professores"] == []
