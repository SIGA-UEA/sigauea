"""Sprint S04 · SCRUM-94 (RBN14.01) e SCRUM-97 (RBN14.04): agenda de apresentações (TEL17).

A remarcação e o cancelamento ainda não têm história própria (SCRUM-65 e SCRUM-66); os testes
alteram a defesa direto no banco, que é o que essas histórias vão fazer.
"""

from datetime import date, time, timedelta

import pytest

from app.models import Defesa, Tcc, Usuario
from tests.test_defesas_banca import _agendar, banca  # noqa: F401  (fixture)
from tests.test_tcc import cenario  # noqa: F401  (fixture usada por banca)


def _outro_tcc(banca, db, coord, n, titulo):
    """Mais um TCC aprovado na mesma turma, com outro aluno, sem vínculo de orientação."""
    aluno = coord.post(
        "/api/v1/alunos",
        json={"nome": f"Aluno {n}", "email": f"aluno{n}@uea.edu.br", "matricula": f"2415010{n}", "curso_id": 1},
    ).json()
    base = db.get(Tcc, banca["tcc"]["id"])
    tcc = Tcc(
        aluno_id=aluno["id"], turma_id=base.turma_id, periodo_id=base.periodo_id, etapa=base.etapa,
        modalidade=base.modalidade, titulo=titulo, resumo="Resumo.", area_id=base.area_id, situacao="APROVADO",
    )
    db.add(tcc)
    db.commit()
    return tcc.id


def _defesa(db, banca, tcc_id, dia, inicio, **campos):
    d = Defesa(
        tcc_id=tcc_id, formato="REMOTO", data=date.fromisoformat(dia), inicio=time.fromisoformat(inicio),
        fim=time.fromisoformat(inicio).replace(minute=50), link="https://meet.exemplo.com/x",
        responsavel_id=banca["ids"]["olga"], **campos,
    )
    db.add(d)
    db.commit()
    return d.id


def dia(n):
    """Data daqui a n dias: a agenda "próximos" não pode depender do calendário de hoje."""
    return (date.today() + timedelta(days=n)).isoformat()


def _agenda(cliente, periodo="proximos"):
    r = cliente.get(f"/api/v1/agenda?periodo={periodo}")
    assert r.status_code == 200, r.json()
    return r.json()


# ---------------------------------------------------------------- RBN14.01


def test_ct_14_01_01_ordem_cronologica(banca, coord, db):
    """CT-14.01-01 / CA-01: três defesas em datas e horas distintas saem em ordem crescente."""
    a, b = _outro_tcc(banca, db, coord, 1, "Segundo"), _outro_tcc(banca, db, coord, 2, "Terceiro")
    _defesa(db, banca, banca["tcc"]["id"], dia(5), "09:00")
    _defesa(db, banca, a, dia(3), "15:00")
    _defesa(db, banca, b, dia(3), "08:00")
    titulos = [i["titulo"] for i in _agenda(banca["aluno"])]
    assert titulos == ["Terceiro", "Segundo", banca["tcc"]["titulo"]]


def test_ct_14_01_02_campos_exibidos(banca):
    """CA-02: título, autor, orientador, curso, formato, horário e local ou link."""
    assert _agendar(banca, data=dia(3)).status_code == 201
    item = _agenda(banca["otto"])[0]
    assert item["titulo"] == banca["tcc"]["titulo"]
    assert item["autor"] == "Ana Ribeiro" and item["orientador"]
    assert item["curso"]["sigla"] == "EC" and item["formato"] == "REMOTO"
    assert (item["data"], item["inicio"][:5], item["fim"][:5]) == (dia(3), "14:00", "14:20")
    assert item["remarcada"] is False


def test_ct_14_01_03_agenda_vazia(banca):
    """CA-03: sem defesa agendada a lista vem vazia, e a tela mostra a ausência de programação."""
    assert _agenda(banca["aluno"]) == []


def test_ct_14_01_04_sem_dados_sensiveis(banca):
    """CA-04: nada de matrícula, e-mail, contato, nota, PDF nem banca na resposta."""
    assert _agendar(banca, data=dia(3)).status_code == 201
    corpo = banca["aluno"].get("/api/v1/agenda").text.lower()
    for proibido in ("matricula", "24150001", "@uea.edu.br", "email", "nota", "membros", "telefone"):
        assert proibido not in corpo


def test_ct_14_01_05_link_so_quando_autorizado(banca, db, coord):
    """CA-05: o link da defesa remota só aparece quando a defesa autoriza divulgar."""
    assert _agendar(banca, data=dia(3)).status_code == 201
    assert _agenda(banca["aluno"])[0]["link"] is None
    defesa = db.query(Defesa).one()
    defesa.divulgar_link = True
    db.commit()
    assert _agenda(banca["aluno"])[0]["link"] == "https://meet.exemplo.com/defesa"


def test_agenda_exige_login(anonimo):
    assert anonimo.get("/api/v1/agenda").status_code == 401


# ---------------------------------------------------------------- RBN14.04


def test_ct_14_04_01_remarcacao_mostra_so_o_novo_horario(banca, db):
    """CA-01 e CA-05: depois de remarcar, a agenda traz só a nova data e hora, já reordenada."""
    assert _agendar(banca, data=dia(3)).status_code == 201
    defesa = db.query(Defesa).one()
    defesa.data, defesa.inicio, defesa.fim, defesa.situacao = date.today() + timedelta(days=6), time(16), time(16, 20), "REMARCADA"
    db.commit()
    itens = _agenda(banca["aluno"])
    assert len(itens) == 1
    assert (itens[0]["data"], itens[0]["inicio"][:5]) == (dia(6), "16:00")
    assert itens[0]["remarcada"] is True


def test_ct_14_04_02_mudanca_de_local(banca, db):
    """CA-02: o novo link ou local aparece na agenda."""
    assert _agendar(banca, data=dia(3)).status_code == 201
    defesa = db.query(Defesa).one()
    defesa.link, defesa.divulgar_link = "https://meet.exemplo.com/novo", True
    db.commit()
    assert _agenda(banca["aluno"])[0]["link"] == "https://meet.exemplo.com/novo"


def test_ct_14_04_03_cancelada_sai_da_agenda(banca, db):
    """CA-03: defesa cancelada não aparece."""
    assert _agendar(banca, data=dia(3)).status_code == 201
    db.query(Defesa).one().situacao = "CANCELADA"
    db.commit()
    assert _agenda(banca["aluno"]) == []


def test_ct_14_04_04_reagendar_depois_de_cancelar(banca, db):
    """CA-04: só a defesa vigente vale; a cancelada fica fora e a nova entra."""
    assert _agendar(banca, data=dia(3)).status_code == 201
    db.query(Defesa).one().situacao = "CANCELADA"
    db.commit()
    assert _agendar(banca, data=dia(10)).status_code == 201
    itens = _agenda(banca["aluno"])
    assert [i["data"] for i in itens] == [dia(10)]


def test_periodo_proximos_ignora_defesa_passada(banca, db):
    """DS-FL05-A passo 2: "próximos" começa hoje; "todas" traz também as que já passaram."""
    assert _agendar(banca, data=dia(3)).status_code == 201
    db.query(Defesa).one().data = date.today() - timedelta(days=2)
    db.commit()
    assert _agenda(banca["aluno"]) == []
    assert len(_agenda(banca["aluno"], "todas")) == 1
