"""Sprint S04 · SCRUM-59 (RBN09.01): compor a banca e agendar a defesa.

A banca é montada na tela e gravada junto com a defesa (opção 2: banca_membro.defesa_id é
obrigatório no modelo de dados). Cada teste cita o caso de teste da ficha (CT-09.01-xx), o
critério de aceite ou o passo dos diagramas DS-FL04 / DS-FL04-A / DS-FL04-B.

O cadastro precisa estar APROVADO (decisão B). A aprovação pela coordenação (SCRUM-4) ainda
não existe, então os testes colocam o TCC nessa situação direto no banco.
"""

import pytest
from sqlalchemy import select

from app.models import (
    Aluno,
    BancaMembro,
    Defesa,
    HistoricoDefesa,
    LogAuditoria,
    Tcc,
    Usuario,
    UsuarioExterno,
)
from tests.conftest import DOCENTE, ativar
from tests.test_tcc import PROFESSOR, _aceitar, _rascunho, cenario  # noqa: F401  (cenario é fixture)

AGENDA = {"formato": "REMOTO", "data": "2026-12-01", "inicio": "14:00", "fim": "14:20",
          "link": "https://meet.exemplo.com/defesa"}


@pytest.fixture
def banca(cenario, caixa, coord, db):
    """TCC de EC aprovado, orientado pela Olga; Otto, Paulo e Ricardo ativos para a banca."""
    tcc = _rascunho(cenario).json()
    _aceitar(cenario)
    registro = db.get(Tcc, tcc["id"])
    registro.situacao = "APROVADO"
    db.commit()
    ricardo = coord.post("/api/v1/docentes", json=DOCENTE).json()
    return {
        **cenario,
        "tcc": tcc,
        "paulo": ativar(caixa, PROFESSOR["email"]),
        "ricardo": ativar(caixa, DOCENTE["email"]),
        "ids": {
            "olga": cenario["orientador"]["id"],
            "otto": cenario["outro"]["id"],
            "paulo": cenario["turma"]["professor"]["id"],
            "ricardo": ricardo["id"],
        },
    }


def _membros(b, avaliadores=("otto", "paulo"), **extra):
    lista = [{"papel": "ORIENTADOR", "usuario_id": b["ids"]["olga"]}]
    lista += [{"papel": "AVALIADOR", "usuario_id": b["ids"][a]} for a in avaliadores]
    for papel, quem in extra.items():
        lista.append({"papel": papel.upper(), "usuario_id": b["ids"][quem]})
    return lista


def _agendar(b, quem="olga", membros=None, **agenda):
    corpo = {**AGENDA, **agenda, "banca": membros if membros is not None else _membros(b)}
    return b[quem].post(f"/api/v1/tccs/{b['tcc']['id']}/defesa", json=corpo)


# ---------------------------------------------------------------- CA-01 · composição completa


def test_ct_09_01_01_orientador_de_ec_define_a_banca_e_agenda(banca, db):
    """CT-09.01-01: 2 avaliadores + orientador → banca registrada, vinculada àquela defesa."""
    r = _agendar(banca)
    assert r.status_code == 201, r.json()
    defesa = r.json()
    assert defesa["situacao"] == "CONFIRMADA" and defesa["publicada"] is False  # DS-FL04 passo 18
    assert sorted(m["papel"] for m in defesa["membros"]) == ["AVALIADOR", "AVALIADOR", "ORIENTADOR"]
    assert all(m["interno"] and m["convite_enviado_em"] is None for m in defesa["membros"])
    assert defesa["responsavel"]["id"] == banca["ids"]["olga"]
    assert db.scalars(select(HistoricoDefesa.evento).where(HistoricoDefesa.defesa_id == defesa["id"])).all() == [
        "AGENDAMENTO"
    ]  # passo 19

    vista = banca["olga"].get(f"/api/v1/tccs/{banca['tcc']['id']}/banca").json()
    assert vista["liberada"] and vista["pode_editar"]
    assert vista["orientador"]["id"] == banca["ids"]["olga"] and vista["coorientador"] is None
    assert vista["defesa"]["id"] == defesa["id"] and len(vista["defesa"]["membros"]) == 3


def test_banca_com_suplente_opcional(banca):
    r = _agendar(banca, membros=_membros(banca, suplente="ricardo"))
    assert r.status_code == 201
    assert sorted(m["papel"] for m in r.json()["membros"]) == ["AVALIADOR", "AVALIADOR", "ORIENTADOR", "SUPLENTE"]


def test_banca_sai_na_ordem_das_vagas_mesmo_enviada_fora_de_ordem(banca):
    """Suplente enviado entre os avaliadores (remover e desfazer na tela) sai depois dos dois avaliadores."""
    ids = banca["ids"]
    membros = [
        {"papel": "SUPLENTE", "usuario_id": ids["ricardo"]},
        {"papel": "AVALIADOR", "usuario_id": ids["otto"]},
        {"papel": "ORIENTADOR", "usuario_id": ids["olga"]},
        {"papel": "AVALIADOR", "usuario_id": ids["paulo"]},
    ]
    r = _agendar(banca, membros=membros)
    assert r.status_code == 201, r.json()
    esperado = ["ORIENTADOR", "AVALIADOR", "AVALIADOR", "SUPLENTE"]
    assert [m["papel"] for m in r.json()["membros"]] == esperado
    vista = banca["olga"].get(f"/api/v1/tccs/{banca['tcc']['id']}/banca").json()
    assert [m["papel"] for m in vista["defesa"]["membros"]] == esperado


# ---------------------------------------------------------------- CA-02 · elementos obrigatórios


def test_ct_09_01_02_um_avaliador_so_bloqueia_e_informa_o_que_falta(banca, db):
    r = _agendar(banca, membros=_membros(banca, avaliadores=("otto",)))
    assert r.status_code == 422
    assert r.json()["pendencias"] == ["Faltam 1 avaliador(es): a banca precisa de 2."]
    assert db.scalars(select(Defesa)).all() == []  # nada gravado


def test_ca_02_sem_orientador_bloqueia(banca):
    sem_orientador = _membros(banca)[1:]
    r = _agendar(banca, membros=sem_orientador)
    assert r.status_code == 422 and "Falta o orientador." in r.json()["pendencias"]


def test_rn12_tres_avaliadores_ou_dois_suplentes_nao_passam(banca):
    r = _agendar(banca, membros=_membros(banca, avaliadores=("otto", "paulo", "ricardo")))
    assert r.status_code == 422 and "A banca tem só 2 avaliadores." in r.json()["pendencias"]


# ---------------------------------------------------------------- CA-03 · membro externo (DS-FL04-B)


def test_ct_09_01_03_externo_sem_instituicao_e_bloqueado(banca):
    membros = _membros(banca, avaliadores=("otto",)) + [
        {"papel": "AVALIADOR", "externo": {"nome": "Eva Externa", "email": "eva@ufam.edu.br"}}
    ]
    r = _agendar(banca, membros=membros)
    assert r.status_code == 400 and "instituicao" in r.json()["campos"]


def test_ca_03_externo_completo_ganha_conta_sem_senha_com_instituicao(banca, db):
    """Decisão C: conta inativa, sem senha, com instituição e perfil membro_banca (link: SCRUM-32)."""
    membros = _membros(banca, avaliadores=("otto",)) + [
        {"papel": "AVALIADOR", "externo": {"nome": "Eva Externa", "email": "Eva@UFAM.edu.br",
                                           "instituicao": "UFAM"}}
    ]
    r = _agendar(banca, membros=membros)
    assert r.status_code == 201, r.json()
    eva = next(m for m in r.json()["membros"] if not m["interno"])
    assert eva["instituicao"] == "UFAM" and eva["email"] == "eva@ufam.edu.br"
    usuario = db.get(Usuario, eva["pessoa"]["id"])
    assert usuario.senha_hash is None and usuario.ativo is False
    assert usuario.perfis == ["membro_banca"]
    assert db.get(UsuarioExterno, usuario.id).instituicao == "UFAM"


def test_externo_com_email_de_docente_da_uea_e_recusado(banca):
    membros = _membros(banca, avaliadores=("otto",)) + [
        {"papel": "AVALIADOR", "externo": {"nome": "Ricardo", "email": DOCENTE["email"], "instituicao": "UFAM"}}
    ]
    r = _agendar(banca, membros=membros)
    assert r.status_code == 422 and r.json()["campo"] == "email"


# ---------------------------------------------------------------- CA-04 · coorientador do TCC


def test_ct_09_01_04_coorientador_diferente_do_vinculado_e_rejeitado(cenario, caixa, coord, db):
    """CT-09.01-04: o TCC tem o Otto como coorientador; a banca com outro coorientador é rejeitada."""
    tcc = _rascunho(cenario, coorientador_id=cenario["outro"]["id"]).json()
    _aceitar(cenario)
    _aceitar(cenario, "otto")
    db.get(Tcc, tcc["id"]).situacao = "APROVADO"
    db.commit()
    ativar(caixa, PROFESSOR["email"])
    ricardo = coord.post("/api/v1/docentes", json=DOCENTE).json()
    ativar(caixa, DOCENTE["email"])
    vera = coord.post("/api/v1/docentes", json={**DOCENTE, "nome": "Vera Docente", "email": "vera@uea.edu.br"}).json()
    ativar(caixa, "vera@uea.edu.br")
    base = [{"papel": "ORIENTADOR", "usuario_id": cenario["orientador"]["id"]},
            {"papel": "AVALIADOR", "usuario_id": cenario["turma"]["professor"]["id"]},
            {"papel": "AVALIADOR", "usuario_id": ricardo["id"]}]
    url = f"/api/v1/tccs/{tcc['id']}/defesa"

    errado = cenario["olga"].post(url, json={**AGENDA, "banca": base + [{"papel": "COORIENTADOR", "usuario_id": vera["id"]}]})
    assert errado.status_code == 422 and "mesmo vinculado ao TCC" in errado.json()["detail"]

    certo = cenario["olga"].post(url, json={**AGENDA, "banca": base + [{"papel": "COORIENTADOR", "usuario_id": cenario["outro"]["id"]}]})
    assert certo.status_code == 201, certo.json()
    vista = cenario["olga"].get(f"/api/v1/tccs/{tcc['id']}/banca").json()
    assert vista["coorientador"]["id"] == cenario["outro"]["id"]


# ---------------------------------------------------------------- CA-05 · responsável pelo agendamento (RN14)


def test_ct_09_01_05_em_si_o_orientador_nao_agenda_e_o_professor_da_disciplina_sim(banca, db):
    db.get(Aluno, banca["tcc"]["aluno"]["id"]).curso_id = 3  # SI
    db.commit()
    assert _agendar(banca, "olga").status_code == 403
    vista = banca["olga"].get(f"/api/v1/tccs/{banca['tcc']['id']}/banca").json()
    assert vista["pode_editar"] is False  # E2: vagas em somente leitura
    membros = _membros(banca, avaliadores=("otto", "ricardo"))
    assert _agendar(banca, "paulo", membros=membros).status_code == 201


def test_ct_09_01_06_em_ec_o_professor_da_disciplina_nao_agenda(banca):
    membros = _membros(banca, avaliadores=("otto", "ricardo"))
    r = _agendar(banca, "paulo", membros=membros)
    assert r.status_code == 403 and "RN14" in r.json()["detail"]


def test_coordenacao_tambem_pode_agendar(banca, coord):
    banca["coord"] = coord
    assert _agendar(banca, "coord").status_code == 201


def test_rn07_quem_nao_tem_vinculo_nao_ve_a_banca(banca):
    assert banca["ricardo"].get(f"/api/v1/tccs/{banca['tcc']['id']}/banca").status_code == 404
    assert _agendar(banca, "ricardo").status_code == 404
    aluno = banca["aluno"].get(f"/api/v1/tccs/{banca['tcc']['id']}/banca")
    assert aluno.status_code == 200 and aluno.json()["pode_editar"] is False
    assert _agendar(banca, "aluno").status_code == 403


def test_e1_cadastro_nao_aprovado_deixa_a_etapa_bloqueada(cenario, caixa):
    tcc = _rascunho(cenario).json()
    _aceitar(cenario)
    vista = cenario["olga"].get(f"/api/v1/tccs/{tcc['id']}/banca").json()
    assert vista["liberada"] is False and vista["pode_editar"] is False
    r = cenario["olga"].post(f"/api/v1/tccs/{tcc['id']}/defesa", json={**AGENDA, "banca": []})
    assert r.status_code == 409 and "não liberada" in r.json()["detail"]


# ---------------------------------------------------------------- vaga conferida na tela (DS-FL04-A passos 8 a 10)


def test_validar_vaga_aponta_pessoa_repetida_sem_gravar(banca, db):
    url = f"/api/v1/tccs/{banca['tcc']['id']}/banca/validar"
    ja = _membros(banca, avaliadores=("otto",))
    r = banca["olga"].post(url, json={"membro": {"papel": "AVALIADOR", "usuario_id": banca["ids"]["otto"]}, "banca": ja})
    assert r.status_code == 422 and r.json()["detail"] == "Esta pessoa já faz parte da banca."
    ok = banca["olga"].post(url, json={"membro": {"papel": "AVALIADOR", "usuario_id": banca["ids"]["paulo"]}, "banca": ja})
    assert ok.status_code == 200 and ok.json()["id"] is None and ok.json()["pessoa"]["nome"] == "Paulo Professor"
    assert db.scalars(select(BancaMembro)).all() == []


def test_validar_convidado_externo_mostra_a_instituicao(banca):
    url = f"/api/v1/tccs/{banca['tcc']['id']}/banca/validar"
    corpo = {"membro": {"papel": "AVALIADOR", "externo": {"nome": "Eva Externa", "email": "eva@ufam.edu.br",
                                                          "instituicao": "UFAM"}}}
    r = banca["olga"].post(url, json=corpo)
    assert r.status_code == 200 and r.json()["interno"] is False and r.json()["instituicao"] == "UFAM"


def test_agendar_com_pessoa_repetida_e_recusado(banca):
    membros = _membros(banca, avaliadores=("otto", "otto"))
    r = _agendar(banca, membros=membros)
    assert r.status_code == 422 and r.json()["detail"] == "Esta pessoa já faz parte da banca."


def test_tcc_com_defesa_agendada_nao_agenda_outra(banca):
    assert _agendar(banca).status_code == 201
    assert _agendar(banca).status_code == 409


def test_dois_pedidos_simultaneos_gravam_uma_defesa_so(banca, db, monkeypatch):
    """Os dois pedidos passam juntos pela checagem do serviço; o índice uq_defesa_tcc_vigente barra
    o segundo no banco. A simultaneidade é simulada fazendo a checagem não ver a primeira defesa."""
    from app.services import defesas

    monkeypatch.setattr(defesas, "defesa_vigente", lambda tcc_id, db: None)
    assert _agendar(banca).status_code == 201
    segundo = _agendar(banca)
    assert segundo.status_code == 409 and segundo.json()["detail"] == "Este TCC já tem uma defesa agendada."
    assert len(db.scalars(select(Defesa).where(Defesa.tcc_id == banca["tcc"]["id"])).all()) == 1


def test_defesa_cancelada_libera_novo_agendamento(banca, db):
    """O índice só vale para as defesas não canceladas (a cancelada fica no histórico)."""
    primeira = _agendar(banca).json()
    db.get(Defesa, primeira["id"]).situacao = "CANCELADA"  # o cancelamento é a SCRUM-66
    db.commit()
    assert _agendar(banca).status_code == 201


def test_formato_presencial_sem_local_e_bloqueado(banca):
    r = _agendar(banca, formato="PRESENCIAL", link=None)
    assert r.status_code == 400 and "local_id" in r.json()["campos"]


# ---------------------------------------------------------------- CA-06 · alteração posterior


def test_ct_09_01_07_troca_de_avaliador_aceita_com_historico(banca, db):
    defesa = _agendar(banca).json()
    otto = next(m for m in defesa["membros"] if m["pessoa"]["id"] == banca["ids"]["otto"])
    url = f"/api/v1/defesas/{defesa['id']}/banca/{otto['id']}"

    r = banca["olga"].put(url, json={"usuario_id": banca["ids"]["ricardo"]})
    assert r.status_code == 200, r.json()
    trocado = next(m for m in r.json()["membros"] if m["id"] == otto["id"])
    assert trocado["pessoa"]["id"] == banca["ids"]["ricardo"] and trocado["papel"] == "AVALIADOR"
    log = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "trocar_membro_banca"))
    assert (log.valor_anterior, log.valor_novo) == ("Otto Orientador", "Ricardo Alves")  # histórico preservado
    historico = db.scalars(
        select(HistoricoDefesa).where(HistoricoDefesa.defesa_id == defesa["id"]).order_by(HistoricoDefesa.id)
    ).all()
    assert [h.evento for h in historico] == ["AGENDAMENTO", "BANCA_ALTERADA"]  # CA-06 no histórico da defesa
    anterior = historico[1].valores_anteriores
    assert anterior["membro_id"] == otto["id"] and anterior["usuario_id"] == banca["ids"]["otto"]
    assert anterior["nome"] == "Otto Orientador" and anterior["papel"] == "AVALIADOR"
    assert historico[1].usuario_id == banca["ids"]["olga"]

    # as regras de composição valem de novo: não pode repetir quem já está na banca
    repetido = banca["olga"].put(url, json={"usuario_id": banca["ids"]["paulo"]})
    assert repetido.status_code == 422


def test_orientador_da_banca_nao_e_trocado_por_essa_rota(banca):
    defesa = _agendar(banca).json()
    orientador = next(m for m in defesa["membros"] if m["papel"] == "ORIENTADOR")
    r = banca["olga"].put(f"/api/v1/defesas/{defesa['id']}/banca/{orientador['id']}",
                          json={"usuario_id": banca["ids"]["ricardo"]})
    assert r.status_code == 422


def test_so_o_responsavel_troca_membro(banca):
    defesa = _agendar(banca).json()
    membro = defesa["membros"][1]
    r = banca["paulo"].put(f"/api/v1/defesas/{defesa['id']}/banca/{membro['id']}",
                           json={"usuario_id": banca["ids"]["ricardo"]})
    assert r.status_code == 403  # Paulo vê o TCC (professor da turma), mas em EC quem agenda é o orientador


# ---------------------------------------------------------------- RNF03 · auditoria


def test_ct_09_01_08_log_completo_do_agendamento(banca, db):
    defesa = _agendar(banca).json()
    logs = db.scalars(select(LogAuditoria).where(LogAuditoria.acao.in_(
        ["agendar_defesa", "incluir_membro_banca"]))).all()
    acoes = sorted(l.acao for l in logs)
    assert acoes == ["agendar_defesa", "incluir_membro_banca", "incluir_membro_banca", "incluir_membro_banca"]
    assert all(l.usuario_id == banca["ids"]["olga"] and l.criado_em is not None for l in logs)
    agendamento = next(l for l in logs if l.acao == "agendar_defesa")
    assert agendamento.entidade_id == defesa["id"] and "2026-12-01 14:00-14:20 REMOTO" == agendamento.valor_novo
