"""SCRUM-70 (RBN09.12): confirmar nota, parecer e resultado da defesa (RN13, RN15 · DS-FL06 e DS-FL06-D).

Cada teste cita o caso de teste da ficha (CT-09.12-xx), o critério de aceite ou o fluxo de exceção. A banca
é a padrão: Olga (orientadora), Otto e Paulo (avaliadores) e o Ricardo de suplente não convocado, que não
avalia. As avaliações são enviadas pela API (RBN10.02 a RBN10.05), como no SCRUM-69.
"""

from decimal import Decimal

from sqlalchemy import select

from app.models import LogAuditoria, ResultadoDefesa
from app.services import resultado as servico
from tests.test_avaliacao import defesa, depois_da_defesa  # noqa: F401  (fixtures)
from tests.test_defesas_banca import banca  # noqa: F401  (fixture usada por defesa)
from tests.test_nota_final import _enviar_nota, _notas
from tests.test_tcc import cenario  # noqa: F401  (fixture usada por banca)

PARECER_BANCA = "Trabalho aprovado; a banca destacou a clareza da apresentação e a qualidade dos experimentos."


def _url(d, retificacao=False) -> str:
    return f"/api/v1/defesas/{d['defesa']['id']}/resultado" + ("/retificacao" if retificacao else "")


def _confirmar(d, resultado="APROVADO", parecer=PARECER_BANCA, quem="olga"):
    return d[quem].post(_url(d), json={"resultado": resultado, "parecer": parecer})


def _retificar(d, resultado="APROVADO_COM_CORRECOES", motivo="Erro na digitação do resultado.", quem="olga"):
    return d[quem].post(_url(d, retificacao=True), json={"resultado": resultado, "motivo": motivo})


def _pronta(d):
    """As três avaliações enviadas: 7,0; 8,0; 6,0 → média e nota final 7,00."""
    _notas(d, "7.0", "8.0", "6.0")


# ---------------------------------------------------------------- CA-01 a CA-06 (CT-09.12-01 a 07)


def test_ct_09_12_01_consolidacao_mostra_notas_media_e_nota_final(defesa, depois_da_defesa):
    """CA-01: com as três avaliações enviadas, o orientador vê as notas, a média e a nota final antes de
    confirmar; ainda não há resultado."""
    _pronta(defesa)
    corpo = defesa["olga"].get(_url(defesa)).json()
    assert corpo["resultado"] is None and corpo["pendentes"] == []
    c = corpo["consolidacao"]
    assert sorted(n["nota"] for n in c["notas"]) == [6.0, 7.0, 8.0]
    assert (c["media"], c["nota_final"]) == (7.0, 7.0)


def test_ct_09_12_02_confirmar_aprovado_grava_com_data_responsavel_e_bloqueia(defesa, depois_da_defesa, db):
    """CA-02: o resultado é gravado com data/hora, responsável e parecer, e a consulta passa a mostrá-lo."""
    _pronta(defesa)
    r = _confirmar(defesa)
    assert r.status_code == 200, r.json()
    res = r.json()["resultado"]
    assert (res["resultado"], res["versao"], res["parecer"]) == ("APROVADO", 1, PARECER_BANCA)
    assert (res["media"], res["nota_final"], res["regra_qualis"]) == (7.0, 7.0, False)
    assert res["confirmado_por"]["id"] == defesa["ids"]["olga"] and res["confirmado_em"]
    assert res["retificacoes"] == [] and r.json()["consolidacao"] is None

    registro = db.scalar(select(ResultadoDefesa))
    assert registro.vigente and registro.nota_final == Decimal("7.00") and registro.confirmado_por == defesa["ids"]["olga"]
    # A2: abrir a tela de novo mostra o resultado confirmado, e não a consolidação
    assert defesa["olga"].get(_url(defesa)).json()["resultado"]["resultado"] == "APROVADO"


def test_ct_09_12_03_duas_de_tres_enviadas_impede_e_lista_pendencia(defesa, depois_da_defesa, db):
    """CA-03 / RBN10.05: com 2 de 3 avaliações enviadas, a confirmação é impedida e quem falta é listado."""
    _enviar_nota(defesa, "olga", "7.0")
    _enviar_nota(defesa, "otto", "8.0")
    r = _confirmar(defesa)
    assert r.status_code == 409
    assert r.json()["detail"] == "Aguardando avaliações. Faltam: Paulo Professor."
    assert [p["pessoa"]["id"] for p in r.json()["pendentes"]] == [defesa["ids"]["paulo"]]
    assert db.scalar(select(ResultadoDefesa)) is None


def test_ct_09_12_04_com_correcoes_deixa_o_resultado_vigente_para_ata_e_correcoes(defesa, depois_da_defesa, db):
    """CA-04 (parte desta história): "aprovado com correções" fica vigente, que é de onde a ata (RBN09.14)
    e a lista de correções (RBN11.01) partem."""
    _pronta(defesa)
    assert _confirmar(defesa, resultado="APROVADO_COM_CORRECOES").status_code == 200
    atual = servico.vigente(db, db.get(ResultadoDefesa, 1).defesa)
    assert atual.resultado == "APROVADO_COM_CORRECOES" and atual.versao == 1


def test_ct_09_12_05_membro_da_banca_nao_confirma(defesa, depois_da_defesa, db):
    """CA-05 / E1: o avaliador recebe 403; o aluno, que vê o TCC, também."""
    _pronta(defesa)
    assert _confirmar(defesa, quem="otto").status_code == 403
    assert _confirmar(defesa, quem="aluno").status_code == 403
    assert db.scalar(select(ResultadoDefesa)) is None


def test_ct_09_12_06_resultado_confirmado_nao_muda_direto(defesa, depois_da_defesa, db):
    """CA-06 / E2: uma segunda confirmação recebe 409; o resultado só muda por retificação."""
    _pronta(defesa)
    assert _confirmar(defesa).status_code == 200
    r = _confirmar(defesa, resultado="REPROVADO")
    assert r.status_code == 409 and "retificação" in r.json()["detail"]
    assert [x.resultado for x in db.scalars(select(ResultadoDefesa))] == ["APROVADO"]


def test_ct_09_12_07_confirmacao_fica_no_log(defesa, depois_da_defesa, db):
    """RNF03: quem confirmou, quando, o resultado e a nota final."""
    _pronta(defesa)
    _confirmar(defesa)
    log = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "confirmar_resultado"))
    assert log.usuario_id == defesa["ids"]["olga"] and log.entidade == "resultado_defesa"
    assert log.valor_novo == "APROVADO; nota final 7.00" and log.criado_em is not None


# ---------------------------------------------------------------- fluxo principal e exceções


def test_parecer_em_branco_e_recusado(defesa, depois_da_defesa, db):
    """CA-02: o parecer faz parte da confirmação; só espaços não vale."""
    _pronta(defesa)
    r = _confirmar(defesa, parecer="   ")
    assert r.status_code == 422 and r.json()["campo"] == "parecer"
    assert db.scalar(select(ResultadoDefesa)) is None


def test_confirmacao_avisa_aluno_e_banca_por_email(defesa, depois_da_defesa, caixa):
    """DS-FL06 mensagens 8 a 15: um e-mail para cada pessoa da banca (com o suplente) e para o aluno."""
    _pronta(defesa)
    caixa.clear()
    _confirmar(defesa)
    assert sorted(e["para"] for e in caixa) == sorted(
        ["ana@uea.edu.br", "olga@exemplo.com", "otto@exemplo.com", "paulo@exemplo.com", "ricardo@uea.edu.br"]
    )
    assert {e["assunto"] for e in caixa} == {"Resultado da defesa de TCC: Aprovado"}


def test_falha_no_email_nao_desfaz_a_confirmacao(defesa, depois_da_defesa, monkeypatch, db):
    """E3: o e-mail não sai, mas o resultado confirmado continua valendo."""
    from app.services import email

    _pronta(defesa)

    def falhar(*_):
        raise RuntimeError("servidor de e-mail fora do ar")

    monkeypatch.setattr(email, "entregar", falhar)
    assert _confirmar(defesa).status_code == 200
    assert db.scalar(select(ResultadoDefesa)).vigente


def test_duas_confirmacoes_ao_mesmo_tempo_gravam_um_resultado(defesa, depois_da_defesa, monkeypatch, db):
    """E2: a segunda confirmação não viu a primeira; o índice de resultado vigente barra a gravação."""
    _pronta(defesa)
    assert _confirmar(defesa).status_code == 200
    monkeypatch.setattr(servico, "vigente", lambda db, defesa: None)
    assert _confirmar(defesa, resultado="REPROVADO").status_code == 409
    assert len(db.scalars(select(ResultadoDefesa)).all()) == 1


# ---------------------------------------------------------------- DS-FL06-D · retificação


def test_retificacao_grava_nova_versao_e_preserva_a_anterior(defesa, depois_da_defesa, db, caixa):
    """RN13: nova versão vigente; a anterior fica registrada com de, para, quem, quando e motivo."""
    _pronta(defesa)
    _confirmar(defesa)
    caixa.clear()
    r = _retificar(defesa)
    assert r.status_code == 200, r.json()
    res = r.json()["resultado"]
    assert (res["resultado"], res["versao"], res["nota_final"]) == ("APROVADO_COM_CORRECOES", 2, 7.0)
    assert [(x["de"], x["para"], x["motivo"], x["por"]["id"]) for x in res["retificacoes"]] == [
        ("APROVADO", "APROVADO_COM_CORRECOES", "Erro na digitação do resultado.", defesa["ids"]["olga"])
    ]
    versoes = db.scalars(select(ResultadoDefesa).order_by(ResultadoDefesa.versao)).all()
    assert [(v.versao, v.vigente, v.resultado) for v in versoes] == [
        (1, False, "APROVADO"), (2, True, "APROVADO_COM_CORRECOES")
    ]
    log = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "retificar_resultado"))
    assert (log.valor_anterior, log.valor_novo) == ("APROVADO", "APROVADO_COM_CORRECOES; motivo: Erro na digitação do resultado.")
    assert len(caixa) == 5 and {e["assunto"] for e in caixa} == {
        "Resultado da defesa de TCC retificado: Aprovado com correções"}


def test_retificacao_sem_motivo_e_422(defesa, depois_da_defesa):
    """E5 (RN13): motivo em branco marca o campo."""
    _pronta(defesa)
    _confirmar(defesa)
    r = _retificar(defesa, motivo="  ")
    assert r.status_code == 422 and r.json()["campo"] == "motivo"


def test_retificacao_para_o_mesmo_resultado_nao_grava(defesa, depois_da_defesa, db):
    """A tela avisa que nada mudou; a API também não grava versão igual."""
    _pronta(defesa)
    _confirmar(defesa)
    r = _retificar(defesa, resultado="APROVADO")
    assert r.status_code == 422 and r.json()["campo"] == "resultado"
    assert len(db.scalars(select(ResultadoDefesa)).all()) == 1


def test_retificacao_so_pelo_orientador_e_so_depois_de_confirmar(defesa, depois_da_defesa):
    """E4: o avaliador recebe 403; sem resultado confirmado não há o que retificar (409)."""
    _pronta(defesa)
    assert _retificar(defesa).status_code == 409
    _confirmar(defesa)
    assert _retificar(defesa, quem="paulo").status_code == 403


def test_duas_retificacoes_seguidas_ficam_em_ordem(defesa, depois_da_defesa):
    _pronta(defesa)
    _confirmar(defesa)
    _retificar(defesa, resultado="APROVADO_COM_CORRECOES", motivo="Primeira correção.")
    r = _retificar(defesa, resultado="REPROVADO", motivo="Segunda correção.")
    res = r.json()["resultado"]
    assert res["versao"] == 3 and res["resultado"] == "REPROVADO"
    assert [(x["de"], x["para"]) for x in res["retificacoes"]] == [
        ("APROVADO", "APROVADO_COM_CORRECOES"), ("APROVADO_COM_CORRECOES", "REPROVADO")
    ]
