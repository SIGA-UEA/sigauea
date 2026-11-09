"""Sprint S04 · SCRUM-65 (RBN09.07, remarcar), SCRUM-66 (RBN09.08, cancelar) e SCRUM-67 (RBN09.09, suplente).

Cada teste cita o caso de teste da ficha (CT-09.0x-yy) ou o fluxo de exceção. A banca é a da SCRUM-59
(Olga orienta; Otto e Paulo avaliam; o Ricardo entra como suplente quando o teste precisa). Os e-mails
não saem de verdade: a fixture `cartas` guarda destinatário, assunto e corpo.
"""

from datetime import date, datetime, time, timedelta

import pytest
from sqlalchemy import select

from app.models import Avaliacao, Defesa, HistoricoDefesa, LocalDefesa, LogAuditoria, Tcc
from app.services import avaliacao as servico_avaliacao
from app.services import email
from tests.test_agenda import _agenda
from tests.test_defesas_agendamento import _outra_defesa
from tests.test_defesas_banca import DIA, _agendar, _membros, banca  # noqa: F401  (banca é fixture)
from tests.test_tcc import cenario  # noqa: F401  (fixture usada por banca)

NOVO_DIA = (date.fromisoformat(DIA) + timedelta(days=2)).isoformat()
NOVO = {"formato": "REMOTO", "data": DIA, "inicio": "16:00", "fim": "16:20",
        "link": "https://meet.exemplo.com/defesa", "motivo": "Sala indisponível no horário original."}


@pytest.fixture
def cartas(banca, monkeypatch):
    enviados: list[dict] = []
    monkeypatch.setattr(email, "entregar",
                        lambda para, assunto, corpo: enviados.append({"para": para, "assunto": assunto, "corpo": corpo}))
    return enviados


@pytest.fixture
def defesa(banca, cartas):
    """Defesa agendada (DIA, 14:00 às 14:20) com o Ricardo de suplente; os convites já saíram."""
    r = _agendar(banca, membros=_membros(banca, suplente="ricardo"))
    assert r.status_code == 201, r.json()
    cartas.clear()
    return r.json()


def _post(b, quem, defesa_id, acao, corpo):
    return b[quem].post(f"/api/v1/defesas/{defesa_id}/{acao}", json=corpo)


def _membro(defesa, banca, quem):
    return next(m for m in defesa["membros"] if m["pessoa"]["id"] == banca["ids"][quem])


def _ontem(db, defesa_id):
    """A defesa passa a ter acontecido ontem (realizada pela regra de horário)."""
    d = db.get(Defesa, defesa_id)
    d.data = date.today() - timedelta(days=2)
    db.commit()


# ================================================================ SCRUM-65 · RBN09.07 · remarcar


def test_ct_09_07_01_remarcar_para_16h_guarda_as_14h_e_avisa(banca, defesa, cartas, db):
    r = _post(banca, "olga", defesa["id"], "remarcacao", NOVO)
    assert r.status_code == 200, r.json()
    nova = r.json()
    assert (nova["id"], nova["situacao"], nova["inicio"][:5]) == (defesa["id"], "REMARCADA", "16:00")
    evento = nova["historico"][0]
    assert evento["evento"] == "REMARCACAO" and evento["motivo"] == NOVO["motivo"]
    assert evento["valores_anteriores"]["inicio"] == "14:00"
    # banca (com o suplente) e aluno, uma vez cada
    assert len([c for c in cartas if c["assunto"].startswith("Defesa de TCC remarcada")]) == 5
    corpo = cartas[0]["corpo"]
    assert "das 14:00 às 14:20" in corpo and "16:00 às 16:20" in corpo and NOVO["motivo"] in corpo


def test_ct_09_07_02_remarcar_sem_motivo_e_bloqueado(banca, defesa, db):
    for motivo in ("", "   ", "ok"):
        r = _post(banca, "olga", defesa["id"], "remarcacao", {**NOVO, "motivo": motivo})
        assert r.status_code == 422 and r.json()["campo"] == "motivo"
    db.expire_all()
    assert db.get(Defesa, defesa["id"]).inicio == time(14)


def test_ct_09_07_03_membro_ocupado_no_novo_horario_bloqueia(banca, coord, defesa, db):
    _outra_defesa(db, banca, coord, "16:00", "17:00", pessoas=("paulo",))
    r = _post(banca, "olga", defesa["id"], "remarcacao", NOVO)
    assert r.status_code == 409 and r.json()["conflitos"][0]["nome"] == "Paulo Professor"
    db.expire_all()
    assert db.get(Defesa, defesa["id"]).situacao == "CONFIRMADA"


def test_ct_09_07_04_agenda_publicada_mostra_o_novo_horario_sem_duplicar(banca, defesa, db):
    db.get(Defesa, defesa["id"]).publicada = True
    db.commit()
    assert _post(banca, "olga", defesa["id"], "remarcacao", {**NOVO, "data": NOVO_DIA}).status_code == 200
    itens = _agenda(banca["aluno"])
    assert [(i["data"], i["inicio"][:5], i["remarcada"]) for i in itens] == [(NOVO_DIA, "16:00", True)]


def test_ct_09_07_05_aluno_nao_remarca(banca, defesa):
    assert _post(banca, "aluno", defesa["id"], "remarcacao", NOVO).status_code == 403
    assert _post(banca, "otto", defesa["id"], "remarcacao", NOVO).status_code in (403, 404)


def test_ct_09_07_06_log_com_anterior_novo_e_motivo(banca, defesa, db):
    _post(banca, "olga", defesa["id"], "remarcacao", NOVO)
    logs = db.scalars(select(LogAuditoria).where(LogAuditoria.acao == "remarcar_defesa")).all()
    agenda = next(l for l in logs if l.campo == "agenda")
    assert agenda.valor_anterior == f"{DIA} 14:00-14:20 REMOTO" and agenda.valor_novo == f"{DIA} 16:00-16:20 REMOTO"
    assert next(l for l in logs if l.campo == "motivo").valor_novo == NOVO["motivo"]
    assert all(l.usuario_id == banca["ids"]["olga"] and l.criado_em for l in logs)


def test_remarcacao_valida_formato_e_local_de_novo(banca, defesa, db):
    r = _post(banca, "olga", defesa["id"], "remarcacao", {**NOVO, "formato": "PRESENCIAL", "link": None})
    assert r.status_code == 400 and "local_id" in r.json()["campos"]
    sala = LocalDefesa(nome="Sala 2")
    db.add(sala)
    db.commit()
    r = _post(banca, "olga", defesa["id"], "remarcacao", {**NOVO, "formato": "PRESENCIAL", "local_id": sala.id})
    assert r.status_code == 200 and r.json()["local"]["nome"] == "Sala 2" and r.json()["link"] is None


def test_remarcacao_sem_mudanca_e_recusada(banca, defesa):
    igual = {**NOVO, "inicio": "14:00", "fim": "14:20"}
    assert _post(banca, "olga", defesa["id"], "remarcacao", igual).status_code == 422


def test_remarcacao_reabre_o_lembrete_da_vespera(banca, defesa, db):
    """RBN09.06 CA-03: depois de remarcar, o lembrete sai de novo com os dados novos."""
    db.get(Defesa, defesa["id"]).lembrete_enviado_em = datetime(2026, 1, 1)
    db.commit()
    _post(banca, "olga", defesa["id"], "remarcacao", NOVO)
    db.expire_all()
    assert db.get(Defesa, defesa["id"]).lembrete_enviado_em is None


def test_coordenacao_tambem_remarca(banca, defesa, coord):
    assert _post({"coord": coord}, "coord", defesa["id"], "remarcacao", NOVO).status_code == 200


def test_remarcar_defesa_cancelada_ou_realizada_e_409(banca, defesa, db):
    _ontem(db, defesa["id"])
    assert _post(banca, "olga", defesa["id"], "remarcacao", NOVO).status_code == 409
    db.get(Defesa, defesa["id"]).situacao = "CANCELADA"
    db.commit()
    assert _post(banca, "olga", defesa["id"], "remarcacao", NOVO).status_code == 409


# ================================================================ SCRUM-66 · RBN09.08 · cancelar

MOTIVO_CANCELAMENTO = {"justificativa": "Aluno afastado por motivo de saúde."}


def test_ct_09_08_01_cancelar_com_justificativa_avisa_os_participantes(banca, defesa, cartas):
    r = _post(banca, "olga", defesa["id"], "cancelamento", MOTIVO_CANCELAMENTO)
    assert r.status_code == 200 and r.json()["situacao"] == "CANCELADA"
    assert r.json()["historico"][0]["evento"] == "CANCELAMENTO"
    avisos = [c for c in cartas if c["assunto"].startswith("Defesa de TCC cancelada")]
    assert len(avisos) == 5 and MOTIVO_CANCELAMENTO["justificativa"] in avisos[0]["corpo"]


def test_ct_09_08_02_cancelar_sem_justificativa_e_bloqueado(banca, defesa, db):
    r = _post(banca, "olga", defesa["id"], "cancelamento", {"justificativa": "  "})
    assert r.status_code == 422 and r.json()["campo"] == "justificativa"
    db.expire_all()
    assert db.get(Defesa, defesa["id"]).situacao == "CONFIRMADA"


def test_ct_09_08_03_tcc_continua_com_a_mesma_situacao(banca, defesa, db):
    antes = db.get(Tcc, banca["tcc"]["id"]).situacao
    _post(banca, "olga", defesa["id"], "cancelamento", MOTIVO_CANCELAMENTO)
    db.expire_all()
    assert db.get(Tcc, banca["tcc"]["id"]).situacao == antes
    tela = banca["olga"].get(f"/api/v1/tccs/{banca['tcc']['id']}/banca").json()
    assert tela["defesa"] is None and tela["cancelada"]["id"] == defesa["id"]  # "Você pode agendar uma nova."
    assert _agendar(banca, data=NOVO_DIA).status_code == 201


def test_ct_09_08_04_defesa_cancelada_nao_recebe_avaliacao(banca, defesa):
    _post(banca, "olga", defesa["id"], "cancelamento", MOTIVO_CANCELAMENTO)
    r = banca["olga"].put(f"/api/v1/defesas/{defesa['id']}/avaliacao", json={"criterios": [], "parecer": None})
    assert r.status_code == 409


def test_ct_09_08_05_defesa_publicada_sai_da_agenda(banca, defesa, db):
    db.get(Defesa, defesa["id"]).publicada = True
    db.commit()
    assert len(_agenda(banca["aluno"])) == 1
    _post(banca, "olga", defesa["id"], "cancelamento", MOTIVO_CANCELAMENTO)
    assert _agenda(banca["aluno"]) == []


def test_ct_09_08_06_aluno_nao_cancela(banca, defesa):
    assert _post(banca, "aluno", defesa["id"], "cancelamento", MOTIVO_CANCELAMENTO).status_code == 403


def test_ct_09_08_07_cancelamento_no_log(banca, defesa, db):
    _post(banca, "olga", defesa["id"], "cancelamento", MOTIVO_CANCELAMENTO)
    log = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "cancelar_defesa"))
    assert (log.usuario_id, log.valor_anterior) == (banca["ids"]["olga"], "CONFIRMADA")
    assert log.valor_novo == f"CANCELADA: {MOTIVO_CANCELAMENTO['justificativa']}"


def test_cancelar_de_novo_ou_depois_de_realizada_e_409(banca, defesa, db):
    assert _post(banca, "olga", defesa["id"], "cancelamento", MOTIVO_CANCELAMENTO).status_code == 200
    assert _post(banca, "olga", defesa["id"], "cancelamento", MOTIVO_CANCELAMENTO).status_code == 409
    outra = _agendar(banca, data=NOVO_DIA).json()
    _ontem(db, outra["id"])
    assert _post(banca, "olga", outra["id"], "cancelamento", MOTIVO_CANCELAMENTO).status_code == 409


# ================================================================ SCRUM-67 · RBN09.09 · suplente


def _convocar(b, defesa, quem="olga", titular="otto", **extra):
    corpo = {"membro_titular_id": _membro(defesa, b, titular)["id"], "motivo": "Avaliador doente no dia.",
             "data": DIA, **extra}
    return _post(b, quem, defesa["id"], "suplente", corpo)


def test_ct_09_09_01_suplente_passa_a_avaliar_e_o_titular_fica_substituido(banca, defesa, cartas, db):
    r = _convocar(banca, defesa)
    assert r.status_code == 200, r.json()
    otto, ricardo = _membro(r.json(), banca, "otto"), _membro(r.json(), banca, "ricardo")
    assert ricardo["convocado_em"] and ricardo["substitui_membro_id"] == otto["id"]
    assert otto["substituido_por_id"] == ricardo["id"]
    d = db.get(Defesa, defesa["id"])
    assert {m.usuario_id for m in servico_avaliacao.membros_que_avaliam(d)} == {
        banca["ids"]["olga"], banca["ids"]["paulo"], banca["ids"]["ricardo"]}
    evento = db.scalar(select(HistoricoDefesa).where(HistoricoDefesa.evento == "SUPLENTE_CONVOCADO"))
    assert evento.valores_anteriores["titular"] == "Otto Orientador" and evento.valores_anteriores["data"] == DIA
    # suplente, titular e aluno
    assert len([c for c in cartas if c["assunto"].startswith("Suplente convocado")]) == 3


def test_ct_09_09_02_convocar_sem_motivo_ou_sem_data_e_bloqueado(banca, defesa):
    assert _convocar(banca, defesa, motivo="").json()["campo"] == "motivo"
    r = _convocar(banca, defesa, data=None)
    assert r.status_code == 422 and r.json()["campo"] == "data"


def test_ct_09_09_03_suplente_nao_convocado_nao_avalia(banca, defesa):
    assert banca["ricardo"].get(f"/api/v1/defesas/{defesa['id']}/avaliacao").status_code == 403


def test_ct_09_09_04_banca_sem_suplente_informa(banca, cartas):
    sem = _agendar(banca).json()
    r = _convocar(banca, sem)
    assert r.status_code == 409 and r.json()["detail"] == "Esta banca não tem suplente indicado."


def test_ct_09_09_05_aluno_e_avaliador_nao_convocam(banca, defesa):
    assert _convocar(banca, defesa, quem="aluno").status_code == 403
    assert _convocar(banca, defesa, quem="paulo").status_code in (403, 404)


def test_ct_09_09_06_suplente_convocado_lanca_a_avaliacao(banca, defesa, monkeypatch):
    _convocar(banca, defesa)
    url = f"/api/v1/defesas/{defesa['id']}/avaliacao"
    assert banca["ricardo"].get(url).status_code == 200
    assert banca["otto"].get(url).status_code == 403  # o titular substituído não avalia mais


def test_ct_09_09_07_convocacao_no_log(banca, defesa, db):
    _convocar(banca, defesa)
    log = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "convocar_suplente"))
    assert log.usuario_id == banca["ids"]["olga"] and log.valor_anterior == "Otto Orientador"
    assert log.valor_novo == f"Ricardo Alves em {DIA}: Avaliador doente no dia."


def test_so_avaliador_titular_pode_ser_substituido(banca, defesa):
    r = _convocar(banca, defesa, titular="olga")
    assert r.status_code == 422 and r.json()["campo"] == "membro_titular_id"


def test_suplente_ja_convocado_e_409(banca, defesa):
    assert _convocar(banca, defesa).status_code == 200
    assert _convocar(banca, defesa, titular="paulo").status_code == 409


def test_coordenacao_convoca(banca, defesa, coord):
    assert _convocar({**banca, "coord": coord}, defesa, quem="coord").status_code == 200


def test_titular_que_ja_enviou_nao_e_substituido_e_rascunho_e_descartado(banca, defesa, db, monkeypatch):
    """RBN10.02: avaliação enviada não muda; rascunho do titular é descartado (como na troca, D15)."""
    db.add(Avaliacao(defesa_id=defesa["id"], membro_id=_membro(defesa, banca, "paulo")["id"],
                     instrumento_id=1, status="ENVIADA"))
    db.add(Avaliacao(defesa_id=defesa["id"], membro_id=_membro(defesa, banca, "otto")["id"],
                     instrumento_id=1, status="RASCUNHO"))
    db.commit()
    assert _convocar(banca, defesa, titular="paulo").status_code == 409
    assert _convocar(banca, defesa, titular="otto").status_code == 200
    db.expire_all()
    assert db.scalar(select(Avaliacao).where(Avaliacao.membro_id == _membro(defesa, banca, "otto")["id"])) is None


def test_convocar_em_defesa_cancelada_ou_realizada_e_409(banca, defesa, db):
    _ontem(db, defesa["id"])
    assert _convocar(banca, defesa).status_code == 409
