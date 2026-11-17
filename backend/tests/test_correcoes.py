"""SCRUM-81 a SCRUM-84 (RBN11.01 a RBN11.04): correções exigidas, versão final, aprovação das correções e
conclusão automática do TCC (RN11, RN13, RN17, RN24 · DS-FL07, DS-FL07-A a DS-FL07-D).

Cada teste cita o caso de teste da ficha. Cenário: a defesa realizada da banca padrão (Olga orientadora, Otto e
Paulo avaliadores, Ricardo suplente não convocado), com as três avaliações enviadas. O TCC é de TCC1, então o
professor responsável pela turma é o Paulo, professor da disciplina (RN24); a Olga é a orientadora.
"""

import hashlib
from datetime import date

import pytest
from sqlalchemy import select

from app.models import (
    Correcao,
    HistoricoSituacao,
    LogAuditoria,
    NotificacaoEmail,
    PeriodoLetivo,
    PublicacaoArtigo,
    ResultadoDefesa,
    Tcc,
    Turma,
)
from app.services import correcoes as servico
from tests.test_avaliacao import defesa, depois_da_defesa  # noqa: F401  (fixtures)
from tests.test_defesas_banca import banca  # noqa: F401  (fixture usada por defesa)
from tests.test_documentos_defesa import _confirmar, _retificar, _sem_vinculo, realizada  # noqa: F401
from tests.test_tcc import cenario  # noqa: F401  (fixture usada por banca)

PRAZO = date(2026, 12, 22)
PDF = b"%PDF-1.4\n1 0 obj << /Type /Catalog >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n"
EXIGENCIA_OTTO = "Revisar as referências conforme a ABNT."
EXIGENCIA_PAULO = "Detalhar a metodologia do experimento."


def _url(d) -> str:
    return f"/api/v1/tccs/{d['tcc']['id']}/correcoes"


def _consultar(d, quem="aluno"):
    return d[quem].get(_url(d))


def _exigir(d, quem="otto", descricao=EXIGENCIA_OTTO):
    return d[quem].post(_url(d), json={"descricao": descricao})


def _atendida(d, correcao_id, quem="aluno"):
    return d[quem].post(f"/api/v1/correcoes/{correcao_id}/atendida")


def _decidir(d, correcao_id, decisao="APROVAR", justificativa="", quem="paulo"):
    return d[quem].post(f"/api/v1/correcoes/{correcao_id}/decisao",
                        json={"decisao": decisao, "justificativa": justificativa})


def _enviar(d, conteudo=PDF, nome="versao-final.pdf", quem="aluno"):
    return d[quem].post(f"{_url(d)}/versao-final", files={"arquivo": (nome, conteudo, "application/pdf")})


def _prazo_no_calendario(db, prazo=PRAZO):
    periodo = db.scalar(select(PeriodoLetivo).where(PeriodoLetivo.codigo == "2026/2"))
    periodo.prazo_versao_final = prazo
    db.commit()


@pytest.fixture
def com_correcoes(realizada, db):  # noqa: F811
    """Resultado "aprovado com correções" confirmado, com o prazo do calendário em 22/12/2026, e as duas
    exigências da banca (Otto e Paulo)."""
    _prazo_no_calendario(db)
    _confirmar(realizada, "APROVADO_COM_CORRECOES")
    assert _exigir(realizada).status_code == 201
    r = _exigir(realizada, "paulo", EXIGENCIA_PAULO)
    assert r.status_code == 201, r.json()
    return {**realizada, "ids_correcao": [c["id"] for c in r.json()["correcoes"]]}


def _tcc(db, d) -> Tcc:
    db.expire_all()
    return db.get(Tcc, d["tcc"]["id"])


# =================================================================== SCRUM-81 · RBN11.01


def test_ct_11_01_01_e_11_01_03_lista_com_as_exigencias_pendentes_e_o_prazo(com_correcoes):
    """CT-11.01-01 (CA-01) e CT-11.01-03 (CA-03): duas correções pendentes, com descrição, avaliador e situação."""
    corpo = _consultar(com_correcoes).json()
    assert corpo["resultado"] == "APROVADO_COM_CORRECOES" and corpo["prazo"] == "2026-12-22"
    assert [(c["descricao"], c["avaliador"]["nome"], c["situacao"]) for c in corpo["correcoes"]] == [
        (EXIGENCIA_OTTO, "Otto Orientador", "PENDENTE"),
        (EXIGENCIA_PAULO, "Paulo Professor", "PENDENTE"),
    ]
    assert corpo["professor_responsavel"]["nome"] == "Paulo Professor"


def test_ct_11_01_02_aprovado_sem_correcoes_nao_tem_lista(realizada):
    """CT-11.01-02 (CA-02): resultado "aprovado" não aceita correção."""
    _confirmar(realizada, "APROVADO")
    r = _exigir(realizada)
    assert r.status_code == 409
    assert _consultar(realizada).json()["correcoes"] == []


def test_ct_11_01_04_prazo_vem_do_calendario_do_periodo(realizada, db):
    """CT-11.01-04 (CA-04): o prazo é a data limite da versão final do período."""
    _prazo_no_calendario(db)
    _confirmar(realizada, "APROVADO_COM_CORRECOES")
    assert db.scalar(select(ResultadoDefesa.prazo_versao_final)) == PRAZO


def test_ct_11_01_05_e_11_01_06_professor_muda_o_prazo_so_com_motivo(com_correcoes, db):
    """CT-11.01-05 e CT-11.01-06 (CA-05): sem motivo bloqueia; com motivo grava, com anterior e novo no log."""
    url = f"{_url(com_correcoes)}/prazo"
    sem = com_correcoes["paulo"].post(url, json={"prazo": "2027-01-15", "motivo": " "})
    assert sem.status_code == 422 and sem.json()["campo"] == "motivo"
    r = com_correcoes["paulo"].post(url, json={"prazo": "2027-01-15", "motivo": "Recesso de fim de ano."})
    assert r.status_code == 200 and r.json()["prazo"] == "2027-01-15"
    assert r.json()["prazo_motivo"] == "Recesso de fim de ano."
    log = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "alterar_prazo_versao_final"))
    assert log.valor_anterior == "2026-12-22" and log.valor_novo.startswith("2027-01-15; motivo: Recesso")
    # quem não é o professor responsável pela turma não muda o prazo (RN24)
    assert com_correcoes["olga"].post(url, json={"prazo": "2027-02-01", "motivo": "x"}).status_code == 403


def test_ct_11_01_07_sem_vinculo_recebe_403(com_correcoes, caixa, coord):
    """CT-11.01-07 (CA-06): o aluno, a orientadora, a banca e o professor veem; quem não tem vínculo, não."""
    for quem in ("aluno", "olga", "otto", "paulo"):
        assert _consultar(com_correcoes, quem).status_code == 200
    assert _sem_vinculo(caixa, coord).get(_url(com_correcoes)).status_code == 403


def test_rbn1101_so_quem_avaliou_registra_e_a_descricao_tem_10_caracteres(realizada):
    """DS-FL07-A: aluno e suplente não convocado não registram (E1); descrição curta é recusada."""
    _confirmar(realizada, "APROVADO_COM_CORRECOES")
    assert _exigir(realizada, "aluno").status_code == 403
    assert _exigir(realizada, "ricardo").status_code == 403
    curta = _exigir(realizada, descricao="Rever.")
    assert curta.status_code == 422 and curta.json()["campo"] == "descricao"


def test_rbn1101_aluno_recebe_email_da_correcao(realizada, caixa):
    """DS-FL07-A mensagens 10 a 14: o aluno é avisado de cada correção registrada."""
    _confirmar(realizada, "APROVADO_COM_CORRECOES")
    caixa.clear()
    assert _exigir(realizada).status_code == 201
    assert [m["assunto"] for m in caixa] == ["SIGA UEA: nova correção exigida pela banca"]


# =================================================================== SCRUM-82 · RBN11.02


def test_ct_11_02_01_envia_a_versao_final_e_marca_as_correcoes(com_correcoes, db):
    """CT-11.02-01 (CA-01): versão final registrada e correções marcadas aguardando validação."""
    for cid in com_correcoes["ids_correcao"]:
        assert _atendida(com_correcoes, cid).status_code == 200
    r = _enviar(com_correcoes)
    assert r.status_code == 201, r.json()
    corpo = r.json()
    assert corpo["versao_final"]["versao"] == 1 and corpo["versao_final"]["entregue_com_atraso"] is False
    assert [c["situacao"] for c in corpo["correcoes"]] == ["ATENDIDA", "ATENDIDA"]
    assert _tcc(db, com_correcoes).situacao == "APROVADO"  # entrega não é aprovação


def test_ct_11_02_02_nova_versao_final_nao_apaga_a_anterior(com_correcoes, db):
    """CT-11.02-02 (CA-02): cada envio é uma nova versão; a anterior continua guardada."""
    assert _enviar(com_correcoes).status_code == 201
    r = _enviar(com_correcoes, PDF + b"% revisada\n")
    assert r.json()["versao_final"]["versao"] == 2
    from app.models import DocumentoTcc
    assert [d.versao for d in db.scalars(select(DocumentoTcc).order_by(DocumentoTcc.versao))] == [1, 2]


def test_ct_11_02_03_envio_depois_do_prazo_fica_com_atraso(com_correcoes, monkeypatch, caixa):
    """CT-11.02-03 (CA-03): prazo 22/12, envio em 23/12 → "entregue com atraso"; o professor é avisado."""
    monkeypatch.setattr(servico, "_hoje_manaus", lambda: date(2026, 12, 23))
    caixa.clear()
    corpo = _enviar(com_correcoes).json()
    assert corpo["versao_final"]["entregue_com_atraso"] is True and corpo["versao_final"]["atraso_aceito"] is None
    assert "Decisão do professor responsável sobre a entrega com atraso." in corpo["pendencias"]
    assert [m["para"] for m in caixa] == ["paulo@exemplo.com"]


def test_ct_11_02_03_envio_no_dia_do_prazo_nao_atrasa(com_correcoes, monkeypatch):
    monkeypatch.setattr(servico, "_hoje_manaus", lambda: PRAZO)
    assert _enviar(com_correcoes).json()["versao_final"]["entregue_com_atraso"] is False


@pytest.mark.parametrize("conteudo,nome", [
    (b"MZ\x90\x00 executavel", "trabalho.pdf"),  # .exe renomeado
    (b"", "vazio.pdf"),
])
def test_ct_11_02_04_arquivo_invalido_e_recusado(com_correcoes, conteudo, nome):
    """CT-11.02-04 (CA-04): arquivo que não é PDF ou vazio é recusado e nada muda."""
    r = _enviar(com_correcoes, conteudo, nome)
    assert r.status_code == 422 and r.json()["campo"] == "arquivo"
    assert _consultar(com_correcoes).json()["versao_final"] is None


def test_ct_11_02_04_pdf_acima_de_20_mb_e_recusado(com_correcoes):
    r = _enviar(com_correcoes, PDF + b"0" * (20 * 1024 * 1024))
    assert r.status_code == 422 and "20 MB" in r.json()["detail"]


def test_ct_11_02_05_correcao_nao_marcada_continua_pendente(com_correcoes):
    """CT-11.02-05 (CA-05)."""
    primeira, segunda = com_correcoes["ids_correcao"]
    assert _atendida(com_correcoes, primeira).status_code == 200
    assert _enviar(com_correcoes).status_code == 201
    situacoes = {c["id"]: c["situacao"] for c in _consultar(com_correcoes).json()["correcoes"]}
    assert situacoes == {primeira: "ATENDIDA", segunda: "PENDENTE"}


def test_ct_11_02_06_so_o_aluno_autor_envia_e_marca(com_correcoes, caixa, coord):
    """CT-11.02-06 (CA-06): outro aluno (sem vínculo) e a orientadora recebem 403."""
    bruno = _sem_vinculo(caixa, coord)
    assert bruno.post(f"{_url(com_correcoes)}/versao-final",
                      files={"arquivo": ("x.pdf", PDF, "application/pdf")}).status_code == 403
    assert _enviar(com_correcoes, quem="olga").status_code == 403
    assert _atendida(com_correcoes, com_correcoes["ids_correcao"][0], quem="olga").status_code == 403


def test_ct_11_02_07_arquivo_baixado_confere_com_o_sha256(com_correcoes):
    """CT-11.02-07 (RNF06): o SHA-256 gravado é o do arquivo, e o download devolve o mesmo conteúdo."""
    corpo = _enviar(com_correcoes).json()
    assert corpo["versao_final"]["sha256"] == hashlib.sha256(PDF).hexdigest()
    baixado = com_correcoes["olga"].get(f"{_url(com_correcoes)}/versao-final")
    assert baixado.status_code == 200 and baixado.content == PDF


def test_rbn0915_anuencia_do_aluno_uma_vez(com_correcoes, db):
    """DS-FL07 mensagens 6 a 8: o aluno dá anuência às correções (libera a Folha de Aprovação)."""
    url = f"{_url(com_correcoes)}/anuencia"
    assert com_correcoes["olga"].post(url).status_code == 403
    r = com_correcoes["aluno"].post(url)
    assert r.status_code == 200 and r.json()["anuencia_em"]
    assert com_correcoes["aluno"].post(url).status_code == 409
    db.expire_all()
    assert db.scalar(select(ResultadoDefesa.anuencia_em)) is not None


# =================================================================== SCRUM-83 · RBN11.03


def _atendidas(d):
    for cid in d["ids_correcao"]:
        assert _atendida(d, cid).status_code == 200


def test_ct_11_03_01_professor_aprova_com_autor_e_data(com_correcoes):
    """CT-11.03-01 (CA-01)."""
    _atendidas(com_correcoes)
    corpo = _decidir(com_correcoes, com_correcoes["ids_correcao"][0]).json()
    c = corpo["correcoes"][0]
    assert c["situacao"] == "APROVADA" and c["decidida_por"]["nome"] == "Paulo Professor" and c["decidida_em"]


def test_ct_11_03_02_devolve_com_justificativa_e_aluno_pode_reenviar(com_correcoes, caixa):
    """CT-11.03-02 (CA-02): devolvida, o aluno é avisado e pode marcar de novo."""
    _atendidas(com_correcoes)
    cid = com_correcoes["ids_correcao"][0]
    caixa.clear()
    corpo = _decidir(com_correcoes, cid, "DEVOLVER", "Faltam as referências da seção 2.").json()
    c = corpo["correcoes"][0]
    assert (c["situacao"], c["justificativa"]) == ("DEVOLVIDA", "Faltam as referências da seção 2.")
    assert [m["assunto"] for m in caixa] == ["SIGA UEA: correção devolvida"]
    assert _atendida(com_correcoes, cid).json()["correcoes"][0]["situacao"] == "ATENDIDA"


def test_ct_11_03_03_devolucao_sem_justificativa_e_bloqueada(com_correcoes):
    """CT-11.03-03 (CA-03)."""
    _atendidas(com_correcoes)
    r = _decidir(com_correcoes, com_correcoes["ids_correcao"][0], "DEVOLVER", "  ")
    assert r.status_code == 422 and r.json()["campo"] == "justificativa"


def test_ct_11_03_04_so_o_professor_responsavel_decide(com_correcoes):
    """CT-11.03-04 (CA-04): a orientadora não é a responsável pela turma de TCC1 (RN24); o aluno também não."""
    _atendidas(com_correcoes)
    cid = com_correcoes["ids_correcao"][0]
    assert _decidir(com_correcoes, cid, quem="olga").status_code == 403
    assert _decidir(com_correcoes, cid, quem="aluno").status_code == 403


def test_rbn1103_e2_so_decide_correcao_atendida(com_correcoes):
    r = _decidir(com_correcoes, com_correcoes["ids_correcao"][0])
    assert r.status_code == 409


def test_ct_11_03_05_professor_decide_a_entrega_com_atraso(com_correcoes, monkeypatch, db):
    """CT-11.03-05 (CA-05): a decisão fica registrada; não se decide duas vezes."""
    monkeypatch.setattr(servico, "_hoje_manaus", lambda: date(2026, 12, 23))
    _enviar(com_correcoes)
    url = f"{_url(com_correcoes)}/atraso"
    assert com_correcoes["olga"].post(url, json={"aceita": True}).status_code == 403
    r = com_correcoes["paulo"].post(url, json={"aceita": False})
    assert r.status_code == 200 and r.json()["versao_final"]["atraso_aceito"] is False
    assert any("recusada" in p for p in r.json()["pendencias"])
    assert com_correcoes["paulo"].post(url, json={"aceita": True}).status_code == 409
    log = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "decidir_atraso"))
    assert log.valor_novo == "recusada"


def test_ct_11_03_06_aprovar_a_ultima_correcao_conclui_o_tcc(com_correcoes, db):
    """CT-11.03-06 (CA-06) e CT-11.04-01: com a versão final enviada, a última aprovação conclui o TCC."""
    _atendidas(com_correcoes)
    assert _enviar(com_correcoes).status_code == 201
    primeira, segunda = com_correcoes["ids_correcao"]
    assert _decidir(com_correcoes, primeira).json()["situacao_tcc"] == "APROVADO"
    corpo = _decidir(com_correcoes, segunda).json()
    assert corpo["situacao_tcc"] == "CONCLUIDO" and corpo["concluido_em"] and corpo["pendencias"] == []
    tcc = _tcc(db, com_correcoes)
    assert tcc.situacao == "CONCLUIDO" and tcc.concluido_em is not None


def test_ct_11_03_07_decisoes_ficam_no_log(com_correcoes, db):
    """CT-11.03-07 (RNF03)."""
    _atendidas(com_correcoes)
    primeira, segunda = com_correcoes["ids_correcao"]
    _decidir(com_correcoes, primeira)
    _decidir(com_correcoes, segunda, "DEVOLVER", "Metodologia ainda curta.")
    logs = db.scalars(select(LogAuditoria).where(LogAuditoria.acao == "decidir_correcao")
                      .order_by(LogAuditoria.id)).all()
    assert [(log.entidade_id, log.valor_anterior, log.valor_novo) for log in logs] == [
        (primeira, "ATENDIDA", "APROVADA"), (segunda, "ATENDIDA", "DEVOLVIDA; Metodologia ainda curta."),
    ]


# =================================================================== SCRUM-84 · RBN11.04


def test_ct_11_04_02_mostra_o_que_falta(com_correcoes):
    """CT-11.04-02 (CA-02): sem versão final e com correções pendentes, a consulta diz o que falta."""
    pendencias = _consultar(com_correcoes).json()["pendencias"]
    assert pendencias == ["Correções aprovadas pelo professor responsável: 0 de 2.", "Versão final enviada pelo aluno."]


def test_ct_11_04_03_aprovado_conclui_so_com_a_versao_final(realizada, caixa, db):
    """CT-11.04-03 (CA-03): sem correções, a versão final basta; aluno e orientadora são avisados."""
    _confirmar(realizada, "APROVADO")
    assert _consultar(realizada).json()["pendencias"] == ["Versão final enviada pelo aluno."]
    caixa.clear()
    corpo = _enviar(realizada).json()
    assert corpo["situacao_tcc"] == "CONCLUIDO"
    assert sorted(m["para"] for m in caixa if m["assunto"] == "SIGA UEA: TCC concluído") == [
        "ana@uea.edu.br", "olga@exemplo.com"]
    assert db.scalar(select(NotificacaoEmail.id).where(NotificacaoEmail.tipo == "TCC_CONCLUIDO")) is not None


def test_ct_11_04_04_reprovado_nao_conclui(realizada, db):
    """CT-11.04-04 (CA-04)."""
    _confirmar(realizada, "REPROVADO")
    corpo = _consultar(realizada).json()
    assert corpo["pendencias"] == ["O resultado da defesa é reprovado: o TCC não é concluído como aprovado."]
    assert corpo["permissoes"]["enviar_versao_final"] is False
    assert _enviar(realizada).status_code == 409
    assert _tcc(db, realizada).situacao != "CONCLUIDO"


def test_ct_11_04_05_concluir_nao_muda_a_situacao_editorial(realizada, db):
    """CT-11.04-05 (CA-05, RN10): o artigo "submetido" continua "submetido"."""
    db.add(PublicacaoArtigo(tcc_id=realizada["tcc"]["id"], tipo_veiculo="PERIODICO", veiculo="Revista X",
                            situacao_atual="SUBMETIDO"))
    db.commit()
    _confirmar(realizada, "APROVADO")
    assert _enviar(realizada).json()["situacao_tcc"] == "CONCLUIDO"
    db.expire_all()
    assert db.scalar(select(PublicacaoArtigo.situacao_atual)) == "SUBMETIDO"


def test_ct_11_04_06_concluir_o_tcc_nao_encerra_a_turma(realizada, db):
    """CT-11.04-06 (CA-06): encerrar a turma é outro passo (RBN08.05)."""
    _confirmar(realizada, "APROVADO")
    _enviar(realizada)
    db.expire_all()
    assert db.get(Turma, realizada["turma"]["id"]).encerrada_em is None


def test_ct_11_04_07_conclusao_fica_no_log_e_no_historico(realizada, db):
    """CT-11.04-07 (CA-07): situação anterior e nova, com data e hora."""
    _confirmar(realizada, "APROVADO")
    _enviar(realizada)
    log = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "concluir_tcc"))
    assert (log.valor_anterior, log.valor_novo) == ("APROVADO", "CONCLUIDO") and log.criado_em
    hist = db.scalars(select(HistoricoSituacao).where(HistoricoSituacao.tcc_id == realizada["tcc"]["id"])
                      .order_by(HistoricoSituacao.id)).all()[-1]
    assert hist.situacao_nova == "CONCLUIDO" and "automática" in hist.observacao


def test_rbn1104_atraso_aceito_libera_a_conclusao(realizada, monkeypatch, db):
    _prazo_no_calendario(db)
    _confirmar(realizada, "APROVADO")
    monkeypatch.setattr(servico, "_hoje_manaus", lambda: date(2026, 12, 23))
    assert _enviar(realizada).json()["situacao_tcc"] == "APROVADO"
    r = realizada["paulo"].post(f"{_url(realizada)}/atraso", json={"aceita": True})
    assert r.json()["situacao_tcc"] == "CONCLUIDO"


def test_rbn1104_tcc_concluido_nao_aceita_mais_acoes(realizada):
    _confirmar(realizada, "APROVADO")
    _enviar(realizada)
    assert _enviar(realizada).status_code == 409
    assert realizada["paulo"].post(f"{_url(realizada)}/prazo",
                                   json={"prazo": "2027-01-10", "motivo": "Teste."}).status_code == 409


def test_retificacao_mantem_prazo_e_versao_final_e_pode_concluir(com_correcoes, db):
    """DS-FL06-D: a nova versão do resultado leva o prazo e a versão final; retificar para "aprovado" com a
    versão final já enviada conclui o TCC (RBN11.04)."""
    com_correcoes["paulo"].post(f"{_url(com_correcoes)}/prazo", json={"prazo": "2027-01-15", "motivo": "Recesso."})
    assert _enviar(com_correcoes).status_code == 201
    _retificar(com_correcoes, "APROVADO")
    corpo = _consultar(com_correcoes).json()
    assert corpo["prazo"] == "2027-01-15" and corpo["versao_final"]["versao"] == 1
    assert corpo["situacao_tcc"] == "CONCLUIDO"
    # as correções registradas antes continuam visíveis
    assert len(corpo["correcoes"]) == 2 and db.scalar(select(Correcao.resultado_id)) is not None


# =================================================================== ajustes da revisão do PR #22


def test_tcc_concluido_nao_tem_o_resultado_retificado(realizada, db):
    """RBN11.04: depois da conclusão, a retificação é recusada; o TCC não fica Concluído com resultado Reprovado."""
    _confirmar(realizada, "APROVADO")
    assert _enviar(realizada).json()["situacao_tcc"] == "CONCLUIDO"
    r = realizada["olga"].post(f"{realizada['url']}/resultado/retificacao",
                               json={"resultado": "REPROVADO", "motivo": "Erro na digitação do resultado."})
    assert r.status_code == 409 and "concluído" in r.json()["detail"]
    db.expire_all()
    assert db.scalar(select(ResultadoDefesa.resultado).where(ResultadoDefesa.vigente.is_(True))) == "APROVADO"


def test_anuencia_continua_valendo_depois_da_retificacao(com_correcoes, db):
    """A anuência do aluno passa para a nova versão do resultado, e a Folha de Aprovação não volta a travar."""
    assert com_correcoes["aluno"].post(f"{_url(com_correcoes)}/anuencia").status_code == 200
    _retificar(com_correcoes, "APROVADO")
    _retificar(com_correcoes, "APROVADO_COM_CORRECOES")
    corpo = _consultar(com_correcoes).json()
    assert corpo["anuencia_em"] and corpo["permissoes"]["dar_anuencia"] is False


def test_prazo_novo_nao_pode_ser_anterior_a_hoje(com_correcoes, monkeypatch):
    """O atraso é decidido no envio: o professor não marca um prazo já passado."""
    monkeypatch.setattr(servico, "_hoje_manaus", lambda: date(2026, 12, 1))
    url = f"{_url(com_correcoes)}/prazo"
    r = com_correcoes["paulo"].post(url, json={"prazo": "2026-11-30", "motivo": "Teste de prazo passado."})
    assert r.status_code == 422 and r.json()["campo"] == "prazo"
    assert com_correcoes["paulo"].post(url, json={"prazo": "2026-12-01", "motivo": "Hoje vale."}).status_code == 200
