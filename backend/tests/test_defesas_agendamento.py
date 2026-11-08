"""Sprint S04 · SCRUM-60 (RBN09.02), SCRUM-61 (RBN09.03) e SCRUM-62 (RBN09.04).

Composição da banca, dados do agendamento e conflitos de agenda. Cada teste cita o caso de teste da
ficha (CT-09.0x-yy) ou o critério de aceite. A banca e o agendamento reaproveitam a fixture da
SCRUM-59 (TCC de EC aprovado, orientado pela Olga; Otto, Paulo e Ricardo disponíveis para a banca).
"""

from datetime import date, time, timedelta

import pytest
from sqlalchemy import func, select

from app.models import BancaMembro, Defesa, LocalDefesa
from tests.test_agenda import _outro_tcc
from tests.test_defesas_banca import DIA, _agendar, _membros, banca  # noqa: F401  (banca é fixture)
from tests.test_tcc import cenario  # noqa: F401  (fixture usada por banca)


def _url(b):
    return f"/api/v1/tccs/{b['tcc']['id']}/defesa"


def _total_defesas(db):
    db.expire_all()
    return db.scalar(select(func.count()).select_from(Defesa))


def _local(db, nome="Sala S"):
    sala = LocalDefesa(nome=nome)
    db.add(sala)
    db.commit()
    return sala.id


def _outra_defesa(db, banca, coord, inicio, fim, pessoas=(), local_id=None, situacao="CONFIRMADA", n=1):
    """Defesa de outro TCC no mesmo dia (DIA), com as pessoas indicadas na banca."""
    tcc_id = _outro_tcc(banca, db, coord, n, f"Outro trabalho {n}")
    d = Defesa(
        tcc_id=tcc_id, data=date.fromisoformat(DIA), inicio=time.fromisoformat(inicio), fim=time.fromisoformat(fim),
        formato="PRESENCIAL" if local_id else "REMOTO", local_id=local_id,
        link=None if local_id else "https://meet.exemplo.com/outra",
        responsavel_id=banca["ids"]["olga"], situacao=situacao,
    )
    db.add(d)
    db.flush()
    for quem in pessoas:
        db.add(BancaMembro(defesa_id=d.id, usuario_id=banca["ids"][quem], papel="AVALIADOR", interno=True))
    db.commit()
    return d.id


def _conflitos(b, quem="olga", **params):
    query = {"tcc_id": b["tcc"]["id"], "data": DIA, **params}
    return b[quem].get("/api/v1/defesas/conflitos", params=query)


# ================================================================ SCRUM-60 · RBN09.02 · composição


def test_ct_09_02_01_mesmo_professor_como_avaliador_1_e_2(banca, db):
    r = _agendar(banca, membros=_membros(banca, avaliadores=("otto", "otto")))
    assert r.status_code == 422 and r.json()["detail"] == "Esta pessoa já faz parte da banca."
    assert _total_defesas(db) == 0


def test_ct_09_02_02_orientador_tambem_como_avaliador(banca, db):
    r = _agendar(banca, membros=_membros(banca, avaliadores=("olga", "paulo")))
    assert r.status_code == 422 and r.json()["campo"] == "usuario_id"
    assert _total_defesas(db) == 0


def test_ct_09_02_03_repeticao_e_pela_pessoa_e_nao_pelo_texto(banca):
    """CA-02: a vaga traz o id do cadastro; o mesmo cadastro duas vezes é repetição. No convidado
    externo a identidade é o e-mail, sem diferenciar maiúsculas."""
    tela = _membros(banca)
    r = banca["olga"].post(f"/api/v1/tccs/{banca['tcc']['id']}/banca/validar",
                           json={"membro": {"papel": "SUPLENTE", "usuario_id": banca["ids"]["otto"]}, "banca": tela})
    assert r.status_code == 422

    externo = {"nome": "Ana Silva", "email": "ana.silva@ufam.edu.br", "instituicao": "UFAM"}
    grafia = {"nome": "ANA SILVA", "email": "Ana.Silva@UFAM.edu.br", "instituicao": "UFAM"}
    membros = [m for m in tela if m["papel"] == "ORIENTADOR"] + [
        {"papel": "AVALIADOR", "externo": externo}, {"papel": "AVALIADOR", "externo": grafia}]
    assert _agendar(banca, membros=membros).status_code == 422


def test_ct_09_02_04_um_avaliador_so_e_bloqueado_com_o_que_falta(banca):
    r = _agendar(banca, membros=_membros(banca, avaliadores=("otto",)))
    assert r.status_code == 422
    assert r.json()["pendencias"] == ["Faltam 1 avaliador(es): a banca precisa de 2."]


def test_ct_09_02_05_orientador_e_suplente_nao_contam_como_avaliadores(banca):
    """CA-04 (RN12, RN20): sem avaliadores a banca está incompleta, mesmo com 3 pessoas."""
    membros = [{"papel": "ORIENTADOR", "usuario_id": banca["ids"]["olga"]},
               {"papel": "SUPLENTE", "usuario_id": banca["ids"]["otto"]}]
    r = _agendar(banca, membros=membros)
    assert r.status_code == 422
    assert "Faltam 2 avaliador(es): a banca precisa de 2." in r.json()["pendencias"]


def test_ct_09_02_06_post_direto_com_duplicidade_e_recusado_na_api(banca, db):
    """CA-05: a regra vale sem passar pela tela (nada de /banca/validar antes)."""
    membros = _membros(banca) + [{"papel": "SUPLENTE", "usuario_id": banca["ids"]["paulo"]}]
    r = banca["olga"].post(_url(banca), json={"formato": "REMOTO", "data": DIA, "inicio": "14:00", "fim": "14:20",
                                              "link": "https://meet.exemplo.com/x", "banca": membros})
    assert r.status_code == 422
    assert _total_defesas(db) == 0


def test_ct_09_02_07_dois_avaliadores_distintos_e_o_orientador_sao_aceitos(banca):
    r = _agendar(banca)
    assert r.status_code == 201, r.json()
    assert sorted(m["papel"] for m in r.json()["membros"]) == ["AVALIADOR", "AVALIADOR", "ORIENTADOR"]


# ================================================================ SCRUM-61 · RBN09.03 · agendamento


def test_ct_09_03_01_presencial_com_local_herda_titulo_e_autor(banca, db):
    sala = _local(db)
    r = _agendar(banca, formato="PRESENCIAL", local_id=sala, link=None)
    assert r.status_code == 201, r.json()
    d = r.json()
    assert d["titulo"] == "Detecção de fraudes com aprendizado de máquina"
    assert d["autor"]["id"] == banca["tcc"]["aluno"]["id"]
    assert d["local"]["id"] == sala and d["link"] is None


def test_ct_09_03_02_remota_sem_link_e_bloqueada(banca):
    r = _agendar(banca, formato="REMOTO", link=None)
    assert r.status_code == 400 and "link" in r.json()["campos"]


def test_ct_09_03_03_hibrida_so_com_local_e_bloqueada(banca, db):
    r = _agendar(banca, formato="HIBRIDO", local_id=_local(db), link=None)
    assert r.status_code == 400 and list(r.json()["campos"]) == ["link"]


def test_hibrida_so_com_link_e_bloqueada(banca):
    r = _agendar(banca, formato="HIBRIDO")
    assert r.status_code == 400 and list(r.json()["campos"]) == ["local_id"]


def test_ct_09_03_04_termino_igual_ao_inicio_e_rejeitado(banca):
    r = _agendar(banca, inicio="14:00", fim="14:00")
    assert r.status_code == 400 and r.json()["campos"]["fim"] == "O término deve ser depois do início."


def test_ct_09_03_05_banca_informa_a_etapa_para_a_duracao_sugerida(banca):
    """CA-04: a tela sugere 15 min no TCC1 e 20 no TCC2 a partir da etapa (RN22)."""
    assert banca["olga"].get(f"/api/v1/tccs/{banca['tcc']['id']}/banca").json()["etapa"] == "TCC1"


def test_ct_09_03_06_defesa_mais_longa_e_aceita(banca):
    assert _agendar(banca, inicio="14:00", fim="14:30").status_code == 201


def test_ct_09_03_07_aluno_nao_agenda(banca):
    assert _agendar(banca, quem="aluno").status_code == 403


def test_data_passada_e_rejeitada(banca):
    """DS-FL04 mensagem 8: a data não pode estar no passado."""
    ontem = (date.today() - timedelta(days=1)).isoformat()
    r = _agendar(banca, data=ontem)
    assert r.status_code == 400 and "data" in r.json()["campos"]


def test_link_sem_https_e_rejeitado(banca):
    """DS-FL04 mensagem 10: link https:// para remoto e híbrido."""
    r = _agendar(banca, link="http://meet.exemplo.com/defesa")
    assert r.status_code == 400 and r.json()["campos"]["link"] == "O link da sala virtual deve começar com https://."


# ================================================================ SCRUM-62 · RBN09.04 · conflitos


def test_ct_09_04_01_conflito_por_participante_bloqueia_e_indica_quem_e_quando(banca, coord, db):
    _outra_defesa(db, banca, coord, "14:00", "15:00", pessoas=("otto",))

    vista = _conflitos(banca, inicio="14:30", fim="15:30", pessoa=[banca["ids"]["otto"], banca["ids"]["paulo"]])
    assert vista.status_code == 200, vista.json()
    assert [(c["tipo"], c["nome"], c["inicio"][:5], c["fim"][:5]) for c in vista.json()["conflitos"]] == [
        ("PARTICIPANTE", "Otto Orientador", "14:00", "15:00")]

    r = _agendar(banca, inicio="14:30", fim="15:30")
    assert r.status_code == 409
    assert r.json()["detail"] == "Há conflito neste horário: Otto Orientador já está em outra defesa das 14:00 às 15:00."
    assert r.json()["conflitos"][0]["nome"] == "Otto Orientador"
    assert _total_defesas(db) == 1  # só a outra


def test_ct_09_04_02_conflito_por_local(banca, coord, db):
    sala = _local(db)
    _outra_defesa(db, banca, coord, "10:00", "11:00", pessoas=("ricardo",), local_id=sala)

    r = _agendar(banca, formato="PRESENCIAL", local_id=sala, link=None, inicio="10:30", fim="11:30")
    assert r.status_code == 409
    assert r.json()["conflitos"] == [{"tipo": "LOCAL", "nome": "Sala S", "data": DIA,
                                      "inicio": "10:00:00", "fim": "11:00:00"}]


def test_outro_local_no_mesmo_horario_nao_conflita(banca, coord, db):
    _outra_defesa(db, banca, coord, "10:00", "11:00", local_id=_local(db, "Sala A"))
    r = _agendar(banca, formato="PRESENCIAL", local_id=_local(db, "Sala B"), link=None, inicio="10:30", fim="11:30")
    assert r.status_code == 201


def test_ct_09_04_03_intervalos_que_se_encostam_nao_conflitam(banca, coord, db):
    _outra_defesa(db, banca, coord, "14:00", "15:00", pessoas=("otto",))
    assert _agendar(banca, inicio="15:00", fim="15:20").status_code == 201


def test_ct_09_04_04_defesa_cancelada_nao_conflita(banca, coord, db):
    _outra_defesa(db, banca, coord, "14:00", "15:00", pessoas=("otto",), situacao="CANCELADA")
    assert _agendar(banca, inicio="14:00", fim="15:00").status_code == 201


def test_ct_09_04_05_a_propria_defesa_nao_conflita_na_remarcacao(banca, coord, db):
    """CA-05: sem pessoa, vale a banca da defesa vigente, que não conflita com ela mesma."""
    assert _agendar(banca, inicio="14:00", fim="14:20").status_code == 201
    livre = _conflitos(banca, inicio="14:10", fim="14:40")
    assert livre.status_code == 200 and livre.json()["conflitos"] == []

    _outra_defesa(db, banca, coord, "16:00", "17:00", pessoas=("paulo",))
    ocupado = _conflitos(banca, inicio="16:30", fim="16:50")
    assert [c["nome"] for c in ocupado.json()["conflitos"]] == ["Paulo Professor"]


def test_ct_09_04_06_segunda_defesa_sobreposta_e_bloqueada_e_a_primeira_fica(banca, coord, db):
    """TI-08: a outra defesa, já gravada, continua; a nova não é criada."""
    outra = _outra_defesa(db, banca, coord, "14:00", "15:00", pessoas=("paulo",))
    assert _agendar(banca, inicio="14:50", fim="15:10").status_code == 409
    db.expire_all()
    assert [d.id for d in db.scalars(select(Defesa))] == [outra]


def test_ca_06_resposta_avisa_que_compromissos_externos_nao_sao_verificados(banca):
    r = _conflitos(banca, inicio="14:00", fim="14:20", pessoa=[banca["ids"]["otto"]])
    assert r.json()["aviso"] == "Compromissos fora do SIGA UEA não são verificados."


def test_conflitos_so_para_quem_agenda(banca):
    """RN14: aluno e professor da turma (em EC) recebem 403; a outra agenda não vaza (RNF02)."""
    assert _conflitos(banca, quem="aluno", inicio="14:00", fim="14:20").status_code == 403
    assert _conflitos(banca, quem="paulo", inicio="14:00", fim="14:20").status_code == 403


def test_conflitos_sem_vinculo_recebe_404(banca):
    assert _conflitos(banca, quem="otto", inicio="14:00", fim="14:20").status_code == 404


def test_conflitos_com_horario_invertido_e_400(banca):
    r = _conflitos(banca, inicio="15:00", fim="14:00")
    assert r.status_code == 400 and "fim" in r.json()["campos"]


def test_troca_de_membro_para_quem_esta_em_outra_defesa_no_horario_e_bloqueada(banca, coord, db):
    defesa = _agendar(banca, inicio="14:00", fim="14:20").json()
    _outra_defesa(db, banca, coord, "14:10", "15:00", pessoas=("ricardo",))
    otto = next(m for m in defesa["membros"] if m["pessoa"]["id"] == banca["ids"]["otto"])
    r = banca["olga"].put(f"/api/v1/defesas/{defesa['id']}/banca/{otto['id']}",
                          json={"usuario_id": banca["ids"]["ricardo"]})
    assert r.status_code == 409 and r.json()["conflitos"][0]["nome"] == "Ricardo Alves"


@pytest.mark.parametrize("formato", ["REMOTO", "HIBRIDO"])
def test_formato_com_link_aceita_https_maiusculo(banca, db, formato):
    extra = {"local_id": _local(db)} if formato == "HIBRIDO" else {}
    assert _agendar(banca, formato=formato, link="HTTPS://meet.exemplo.com/x", **extra).status_code == 201
