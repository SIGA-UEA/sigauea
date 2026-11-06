"""Sprint S04 · SCRUM-94 (RBN14.01): publicar a defesa na agenda e retirá-la (DS-FL05, TEL18, RN08 e RN09).

Cada teste cita a mensagem do diagrama DS-FL05 ou a exceção da ficha (E1 a E3). O orientador (Olga)
agenda em EC; Paulo, professor da turma, enxerga o TCC mas não publica (E2).
"""

from sqlalchemy import select

from app.models import Defesa, HistoricoDefesa, LogAuditoria, Tcc
from tests.test_defesas_banca import _agendar, banca  # noqa: F401  (fixture)
from tests.test_tcc import cenario  # noqa: F401  (fixture usada por banca)


def _nova_defesa(banca) -> int:
    r = _agendar(banca)
    assert r.status_code == 201, r.json()
    return r.json()["id"]


def _url(defesa_id, acao="divulgacao"):
    return f"/api/v1/defesas/{defesa_id}/{acao}"


def _na_agenda(cliente):
    return cliente.get("/api/v1/agenda?periodo=todas").json()


def _eventos(db, defesa_id):
    return db.scalars(select(HistoricoDefesa.evento).where(HistoricoDefesa.defesa_id == defesa_id)).all()


# ---------------------------------------------------------------- mensagens 3 a 5 · consultar a divulgação


def test_divulgacao_mostra_condicoes_e_previa_sem_dados_pessoais(banca):
    """Mensagem 3: condições atendidas, prévia como aparece na agenda e a defesa ainda não publicada."""
    d = _nova_defesa(banca)
    r = banca["olga"].get(_url(d))
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["publicada"] is False and corpo["pode_publicar"] is True
    assert [c["atendida"] for c in corpo["condicoes"]] == [True, True, True]
    assert corpo["previa"]["titulo"] == banca["tcc"]["titulo"]
    texto = r.text.lower()
    for proibido in ("matricula", "@uea.edu.br", "telefone", "membros", "nota"):
        assert proibido not in texto


def test_e2_quem_nao_e_responsavel_ve_somente_leitura(banca):
    """E2: o professor da turma enxerga a divulgação, mas não publica nem retira."""
    d = _nova_defesa(banca)
    assert banca["paulo"].get(_url(d)).json()["pode_publicar"] is False
    assert banca["paulo"].post(_url(d, "publicacao")).status_code == 403
    assert banca["paulo"].post(_url(d, "retirada")).status_code == 403


def test_sem_vinculo_com_o_tcc_a_defesa_nao_aparece(banca):
    """RN07: quem não enxerga o TCC recebe 404 na divulgação."""
    d = _nova_defesa(banca)
    assert banca["otto"].get(_url(d)).status_code == 404
    assert banca["otto"].post(_url(d, "publicacao")).status_code == 404
    assert banca["otto"].post(_url(d, "retirada")).status_code == 404


def test_defesa_inexistente_da_404(banca):
    assert banca["olga"].get(_url(999)).status_code == 404
    assert banca["olga"].post(_url(999, "retirada")).status_code == 404


def test_e1_defesa_cancelada(banca, db):
    """E1: cancelada não tem prévia nem botão, e publicar devolve 409."""
    d = _nova_defesa(banca)
    db.get(Defesa, d).situacao = "CANCELADA"
    db.commit()
    corpo = banca["olga"].get(_url(d)).json()
    assert corpo["situacao"] == "CANCELADA" and corpo["pode_publicar"] is False and corpo["previa"] is None
    assert banca["olga"].post(_url(d, "publicacao")).status_code == 409


def test_e1_retirar_defesa_cancelada_da_409(banca, db):
    d = _nova_defesa(banca)
    db.get(Defesa, d).situacao = "CANCELADA"
    db.commit()
    assert banca["olga"].post(_url(d, "retirada")).status_code == 409


# ---------------------------------------------------------------- mensagens 8 a 11 · publicar


def test_publicar_grava_historico_auditoria_e_aparece_na_agenda(banca, db):
    """Mensagens 8 a 11: defesa publicada, evento PUBLICACAO e linha publicar_agenda no log."""
    d = _nova_defesa(banca)
    assert _na_agenda(banca["aluno"]) == []  # RN08: nasce não publicada
    r = banca["olga"].post(_url(d, "publicacao"))
    assert r.status_code == 200, r.json()
    assert r.json()["publicada"] is True
    defesa = db.get(Defesa, d)
    assert defesa.publicada and defesa.publicada_em is not None
    assert _eventos(db, d) == ["AGENDAMENTO", "PUBLICACAO"]
    log = db.scalars(select(LogAuditoria).where(LogAuditoria.acao == "publicar_agenda")).one()
    assert (log.entidade, log.entidade_id, log.valor_anterior, log.valor_novo) == ("defesa", d, "False", "True")
    assert len(_na_agenda(banca["aluno"])) == 1


def test_coordenacao_tambem_publica(banca, coord):
    """RN14: a coordenação pode publicar mesmo sem ser quem agendou."""
    d = _nova_defesa(banca)
    assert coord.post(_url(d, "publicacao")).status_code == 200


def test_publicar_duas_vezes_nao_duplica_o_historico(banca, db):
    d = _nova_defesa(banca)
    assert banca["olga"].post(_url(d, "publicacao")).status_code == 200
    assert banca["olga"].post(_url(d, "publicacao")).status_code == 200
    assert _eventos(db, d).count("PUBLICACAO") == 1


def test_e3_condicao_pendente_devolve_422_com_o_que_falta(banca, db):
    """E3 / RN09: sem TCC identificado a defesa não publica e a resposta diz o que falta."""
    d = _nova_defesa(banca)
    db.get(Tcc, banca["tcc"]["id"]).titulo = " "
    db.commit()
    r = banca["olga"].post(_url(d, "publicacao"))
    assert r.status_code == 422
    assert r.json()["pendencias"] == ["TCC identificado"]
    assert db.get(Defesa, d).publicada is False
    assert _eventos(db, d) == ["AGENDAMENTO"]
    assert _na_agenda(banca["aluno"]) == []


def test_defesa_realizada_nao_publica(banca, db):
    """RN09: data e horário só estão confirmados enquanto a defesa está confirmada ou remarcada."""
    d = _nova_defesa(banca)
    db.get(Defesa, d).situacao = "REALIZADA"
    db.commit()
    r = banca["olga"].post(_url(d, "publicacao"))
    assert r.status_code == 422 and r.json()["pendencias"] == ["Data e horário confirmados"]


# ---------------------------------------------------------------- mensagens 14 a 16 · retirar


def test_retirar_tira_da_agenda_e_a_defesa_continua_marcada(banca, db):
    """Mensagens 14 a 16: retirada registrada no histórico; a defesa não é cancelada."""
    d = _nova_defesa(banca)
    banca["olga"].post(_url(d, "publicacao"))
    r = banca["olga"].post(_url(d, "retirada"))
    assert r.status_code == 200 and r.json()["publicada"] is False
    assert _na_agenda(banca["aluno"]) == []
    defesa = db.get(Defesa, d)
    assert defesa.situacao == "CONFIRMADA" and defesa.publicada_em is None
    assert _eventos(db, d) == ["AGENDAMENTO", "PUBLICACAO", "RETIRADA"]


def test_retirar_o_que_nao_esta_publicado_da_409(banca):
    d = _nova_defesa(banca)
    assert banca["olga"].post(_url(d, "retirada")).status_code == 409


def test_publicar_de_novo_depois_de_retirar(banca, db):
    d = _nova_defesa(banca)
    banca["olga"].post(_url(d, "publicacao"))
    banca["olga"].post(_url(d, "retirada"))
    assert banca["olga"].post(_url(d, "publicacao")).status_code == 200
    assert len(_na_agenda(banca["aluno"])) == 1
    assert _eventos(db, d) == ["AGENDAMENTO", "PUBLICACAO", "RETIRADA", "PUBLICACAO"]


def test_divulgacao_exige_login(anonimo):
    assert anonimo.get(_url(1)).status_code == 401
    assert anonimo.post(_url(1, "publicacao")).status_code == 401
