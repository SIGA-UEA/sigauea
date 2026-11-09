"""Sprint S04 · avaliação da defesa pelos membros da banca (RBN10.02 a RBN10.05, SCRUM-77 a SCRUM-80).

Cada teste cita o caso de teste da ficha (CT-10.0x-xx) ou o passo do diagrama DS-FL06-A que confere. O cenário
é montado pela API: TCC de EC aprovado, defesa agendada com a Olga (orientadora), o Otto e o Paulo
(avaliadores); o Ricardo entra como suplente quando o teste precisa. A versão 1 do instrumento vem da carga
base (6 critérios na parte escrita e 3 na oral).

"Depois da defesa" é simulado trocando o relógio do serviço (fixture depois_da_defesa), sem mexer no banco.

O suplente é convocado pela rota da SCRUM-67 (POST /defesas/{id}/suplente) em CT-10.02-06 e CT-10.05-05.

Ficam em skip, até a história de que dependem entrar:
- SCRUM-70 (confirmar o resultado): CT-10.05-03 e CT-10.05-04. A lista de pendentes que a confirmação vai
  usar já é conferida aqui.
"""

from datetime import date, datetime, time
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models import Avaliacao, AvaliacaoCriterio, BancaMembro, Defesa, LogAuditoria
from app.services import avaliacao as servico
from tests.test_defesas_banca import DIA, _agendar, _membros, banca  # noqa: F401  (banca é fixture)
from tests.test_tcc import cenario  # noqa: F401  (fixture usada por banca)

PARECER = "Trabalho bem estruturado e apresentado com clareza."
CAMPOS = ("nome", "peso", "texto_exemplar", "texto_competente", "texto_necessita")


@pytest.fixture
def defesa(banca):
    """Defesa agendada (DIA, 14:00 às 14:20) com a banca padrão e o Ricardo de suplente."""
    r = _agendar(banca, membros=_membros(banca, suplente="ricardo"))
    assert r.status_code == 201, r.json()
    return {**banca, "defesa": r.json()}


@pytest.fixture
def depois_da_defesa(monkeypatch):
    """Relógio do serviço depois do término da defesa (passo 4: realizada)."""
    monkeypatch.setattr(servico, "_agora_manaus", lambda: datetime.combine(date.fromisoformat(DIA), time(15, 0)))


def _url(d, envio=False) -> str:
    return f"/api/v1/defesas/{d['defesa']['id']}/avaliacao" + ("/envio" if envio else "")


def _criterios(consulta: dict) -> list[dict]:
    return [k for c in consulta["instrumento"]["componentes"] for k in c["criterios"]]


def _todos(d, quem="olga", conceito="COMPETENTE", nota="7.0") -> list[dict]:
    """Os 9 critérios preenchidos com o mesmo conceito e nota."""
    consulta = d[quem].get(_url(d)).json()
    return [{"criterio_id": k["id"], "conceito": conceito, "nota": nota} for k in _criterios(consulta)]


def _enviar(d, quem="olga", **kw):
    return d[quem].post(_url(d, envio=True), json={"criterios": _todos(d, quem, **kw), "parecer": PARECER})


def _convocar_ricardo(d, titular="otto"):
    """SCRUM-67: a orientadora convoca o suplente (Ricardo) no lugar do titular."""
    membro = next(m for m in d["defesa"]["membros"] if m["pessoa"]["id"] == d["ids"][titular])
    r = d["olga"].post(f"/api/v1/defesas/{d['defesa']['id']}/suplente",
                       json={"membro_titular_id": membro["id"], "motivo": "Avaliador doente no dia.", "data": DIA})
    assert r.status_code == 200, r.json()


# ---------------------------------------------------------------- SCRUM-77 · RBN10.02


def test_ct_10_02_01_avaliador_lanca_conceitos_e_notas_em_seu_nome(defesa, db):
    """CT-10.02-01 (CA-01): o instrumento vem completo e o lançamento fica no nome de quem lançou (passos 3 a 14)."""
    consulta = defesa["otto"].get(_url(defesa))
    assert consulta.status_code == 200
    corpo = consulta.json()
    assert len(_criterios(corpo)) == 9 and corpo["minha_avaliacao"] is None
    assert corpo["envios"] == {"enviadas": 0, "esperadas": 3}

    r = defesa["otto"].put(_url(defesa), json={"criterios": _todos(defesa, "otto")[:3]})
    assert r.status_code == 200 and r.json()["status"] == "RASCUNHO"
    avaliacao = db.get(Avaliacao, r.json()["id"])
    assert avaliacao.membro.usuario_id == defesa["ids"]["otto"] and avaliacao.membro.papel == "AVALIADOR"


def test_ct_10_02_02_um_avaliador_nao_ve_o_lancamento_do_outro(defesa):
    """CT-10.02-02 (CA-02): o Paulo lança; o Otto só vê a própria avaliação (em branco), sem as notas do Paulo."""
    assert defesa["paulo"].put(_url(defesa), json={"criterios": _todos(
        defesa, "paulo"), "parecer": PARECER}).status_code == 200
    corpo = defesa["otto"].get(_url(defesa)).json()
    assert corpo["minha_avaliacao"] is None
    assert "criterios" not in corpo["envios"] and corpo["envios"]["enviadas"] == 0  # só a contagem de envios


def test_ct_10_02_03_rascunho_parcial_e_retomado(defesa):
    """CT-10.02-03 (CA-03): salvar parte dos critérios e o parecer, sair e voltar com os dados preservados."""
    parciais = _todos(defesa)[:6]  # a parte escrita, antes da defesa (decisão da Professora, D21)
    assert defesa["olga"].put(_url(defesa), json={"criterios": parciais,
                              "parecer": "Primeira leitura"}).status_code == 200

    minha = defesa["olga"].get(_url(defesa)).json()["minha_avaliacao"]
    assert [c["criterio_id"] for c in minha["criterios"]] == [c["criterio_id"] for c in parciais]
    assert minha["parecer"] == "Primeira leitura" and len(minha["pendentes"]) == 3


def test_ct_10_02_04_avaliacao_enviada_nao_e_mais_editada(defesa, depois_da_defesa):
    """CT-10.02-04 (CA-03, fluxo E5): depois do envio, PUT e novo POST recebem 409 e nada muda."""
    assert _enviar(defesa).status_code == 200
    assert defesa["olga"].put(_url(defesa), json={"criterios": []}).status_code == 409
    assert _enviar(defesa, conceito="EXEMPLAR", nota="9.0").status_code == 409
    minha = defesa["olga"].get(_url(defesa)).json()["minha_avaliacao"]
    assert minha["status"] == "ENVIADA" and minha["nota_total"] == 7.0  # fluxo E3: a enviada, sem edição


def test_ct_10_02_05_professor_fora_da_banca_recebe_403(defesa, coord):
    """CT-10.02-05 (CA-04, fluxo E6): quem não está na banca recebe 403 nas três rotas, sem dados."""
    corpo = {"criterios": [], "parecer": PARECER}
    for chamada in (coord.get(_url(defesa)), coord.put(_url(defesa), json=corpo),
                    coord.post(_url(defesa, envio=True), json=corpo)):
        assert chamada.status_code == 403
        assert chamada.json() == {"detail": "Você não avalia esta defesa."}


def test_ct_10_02_06_suplente_convocado_lanca_a_avaliacao(defesa, depois_da_defesa):
    """CT-10.02-06 (CA-05): suplente convocado pela rota da SCRUM-67 lança a avaliação no lugar do titular."""
    assert defesa["ricardo"].get(_url(defesa)).status_code == 403  # antes da convocação (RN20)
    _convocar_ricardo(defesa)
    r = _enviar(defesa, "ricardo")
    assert r.status_code == 200 and r.json()["status"] == "ENVIADA"
    assert defesa["otto"].get(_url(defesa)).status_code == 403  # o titular substituído não avalia


def test_ct_10_02_07_lancamento_e_envio_ficam_no_log(defesa, db, depois_da_defesa):
    """CT-10.02-07 (CA-06, RNF03): avaliador, data/hora, campo, valor anterior e novo."""
    criterios = _todos(defesa)
    assert defesa["olga"].put(_url(defesa), json={"criterios": criterios[:1]}).status_code == 200
    criterios[0]["nota"] = "7.5"
    assert defesa["olga"].post(_url(defesa, envio=True), json={
                               "criterios": criterios, "parecer": PARECER}).status_code == 200

    logs = db.scalars(select(LogAuditoria).where(LogAuditoria.entidade == "avaliacao").order_by(LogAuditoria.id)).all()
    assert {log.usuario_id for log in logs} == {defesa["ids"]["olga"]} and all(log.criado_em for log in logs)
    primeiro = f"criterio_{criterios[0]['criterio_id']}"
    alteracoes = [(log.valor_anterior, log.valor_novo) for log in logs if log.campo == primeiro]
    assert alteracoes[0] == (None, "Relevância do tema: Competente 7,0")
    assert alteracoes[1] == ("Relevância do tema: Competente 7,0", "Relevância do tema: Competente 7,5")
    envio = logs[-1]
    assert (envio.acao, envio.campo, envio.valor_anterior, envio.valor_novo) == (
        "enviar_avaliacao", "status", "RASCUNHO", "ENVIADA · nota 7,0")  # 7,025 arredonda para 7,0


# ---------------------------------------------------------------- SCRUM-78 · RBN10.03


def test_ct_10_03_01_cada_criterio_traz_os_textos_dos_tres_conceitos(defesa):
    """CT-10.03-01 (CA-01): os três textos e as faixas vêm no GET; o lançamento aceita um conceito só."""
    instrumento = defesa["olga"].get(_url(defesa)).json()["instrumento"]
    for k in [k for c in instrumento["componentes"] for k in c["criterios"]]:
        assert k["texto_exemplar"] and k["texto_competente"] and k["texto_necessita"]
    assert [f["rotulo"] for f in instrumento["conceitos"]] == ["Exemplar", "Competente", "Necessita de Trabalho"]
    item = {**_todos(defesa)[0], "conceito": ["EXEMPLAR", "COMPETENTE"]}
    assert defesa["olga"].put(_url(defesa), json={"criterios": [item]}).status_code == 400


def test_ct_10_03_02_nota_sem_conceito_e_recusada(defesa):
    """CT-10.03-02 (CA-02) no servidor: a nota só existe junto do conceito; critério sem conceito dá 400."""
    item = {k: v for k, v in _todos(defesa)[0].items() if k != "conceito"}
    r = defesa["olga"].put(_url(defesa), json={"criterios": [item]})
    assert r.status_code == 400 and "conceito" in r.json()["campos"]


def test_ct_10_03_03_nota_fora_da_faixa_do_exemplar(defesa):
    """CT-10.03-03 (CA-03, fluxo E4): 7,9 em "Exemplar" é rejeitada com a faixa na mensagem."""
    item = {**_todos(defesa)[0], "conceito": "EXEMPLAR", "nota": "7.9"}
    r = defesa["olga"].put(_url(defesa), json={"criterios": [item]})
    assert r.status_code == 422
    assert r.json()["criterios"] == [
        {"id": item["criterio_id"], "nome": "Relevância do tema", "motivo": "A nota de Exemplar vai de 8,0 a 10,0."}
    ]


@pytest.mark.parametrize(("conceito", "aceitas", "recusada"), [
    ("EXEMPLAR", ["8.0", "10.0"], "7.9"),
    ("COMPETENTE", ["6.0", "7.9"], "8.0"),
    ("NECESSITA", ["0.0", "5.9"], "6.0"),
])
def test_ct_10_03_04_e_05_valores_limite_das_faixas(defesa, conceito, aceitas, recusada):
    """CT-10.03-04 e CT-10.03-05 (CA-06): limites aceitos; 8,0 em "Competente" e 6,0 em "Necessita" recusadas."""
    base = _todos(defesa)[0]
    for nota in aceitas:
        assert defesa["olga"].put(_url(defesa), json={"criterios": [
                                  {**base, "conceito": conceito, "nota": nota}]}).status_code == 200
    assert defesa["olga"].put(_url(defesa), json={"criterios": [
                              {**base, "conceito": conceito, "nota": recusada}]}).status_code == 422


def test_ct_10_03_06_trocar_o_conceito_revalida_a_nota(defesa):
    """CT-10.03-06 (CA-04) no servidor: 9,0 em "Exemplar" e troca para "Competente" sem ajustar a nota: recusada;
    a nota anterior continua gravada até vir uma nota da nova faixa."""
    base = _todos(defesa)[0]
    assert defesa["olga"].put(_url(defesa), json={"criterios": [
                              {**base, "conceito": "EXEMPLAR", "nota": "9.0"}]}).status_code == 200
    assert defesa["olga"].put(_url(defesa), json={"criterios": [
                              {**base, "conceito": "COMPETENTE", "nota": "9.0"}]}).status_code == 422
    assert defesa["olga"].get(_url(defesa)).json()["minha_avaliacao"]["criterios"][0]["conceito"] == "EXEMPLAR"
    assert defesa["olga"].put(_url(defesa), json={"criterios": [
                              {**base, "conceito": "COMPETENTE", "nota": "7.0"}]}).status_code == 200


def test_ct_10_03_07_post_com_9_5_em_competente_e_rejeitado(defesa, depois_da_defesa):
    """CT-10.03-07 (CA-05): a API rejeita a nota fora da faixa mesmo sem passar pela tela."""
    criterios = _todos(defesa)
    criterios[0] = {**criterios[0], "nota": "9.5"}
    r = defesa["olga"].post(_url(defesa, envio=True), json={"criterios": criterios, "parecer": PARECER})
    assert r.status_code == 422 and r.json()["criterios"][0]["motivo"] == "A nota de Competente vai de 6,0 a 7,9."


def test_nota_com_duas_casas_e_recusada(defesa):
    """NUMERIC(3,1): a nota tem uma casa decimal (400 por campo)."""
    r = defesa["olga"].put(_url(defesa), json={"criterios": [{**_todos(defesa)[0], "nota": "7.25"}]})
    assert r.status_code == 400 and "nota" in r.json()["campos"]


# ---------------------------------------------------------------- SCRUM-79 · RBN10.04


def test_ct_10_04_01_ponderada_de_peso_3_e_nota_8(defesa):
    """CT-10.04-01 (CA-01): (8 × 3) ÷ 10 = 2,40."""
    assert servico.ponderada_exata(Decimal("8"), Decimal("3")) == Decimal("2.4")


def _instrumento_ti10(coord):
    """Instrumento do exemplo TI-10: pesos 5 e 2 na parte escrita e 3 na oral (soma 10)."""
    atual = coord.get("/api/v1/instrumento-avaliacao").json()["instrumento"]
    escrita, oral = atual["componentes"]
    modelo = {k: escrita["criterios"][0][k] for k in CAMPOS}
    corpo = {"componentes": [
        {"id": escrita["id"], "criterios": [{**modelo, "nome": "B",
                                             "peso": "5"}, {**modelo, "nome": "C", "peso": "2"}]},
        {"id": oral["id"], "criterios": [{**modelo, "nome": "A", "peso": "3"}]},
    ]}
    assert coord.put("/api/v1/instrumento-avaliacao", json=corpo).status_code == 200


def test_ct_10_04_02_exemplo_de_referencia_ti_10(defesa, coord, depois_da_defesa):
    """CT-10.04-02 (CA-03, TI-10): pesos 3, 5 e 2 e notas 8, 6 e 9 → 2,40; 3,00; 1,80; total 7,2."""
    _instrumento_ti10(coord)
    k = {c["nome"]: c["id"] for c in _criterios(defesa["olga"].get(_url(defesa)).json())}
    criterios = [
        {"criterio_id": k["A"], "conceito": "EXEMPLAR", "nota": "8"},
        {"criterio_id": k["B"], "conceito": "COMPETENTE", "nota": "6"},
        {"criterio_id": k["C"], "conceito": "EXEMPLAR", "nota": "9"},
    ]
    r = defesa["olga"].post(_url(defesa, envio=True), json={"criterios": criterios, "parecer": PARECER})
    assert r.status_code == 200
    ponderadas = {c["criterio_id"]: c["nota_ponderada"] for c in r.json()["criterios"]}
    assert [ponderadas[k[n]] for n in "ABC"] == [2.4, 3.0, 1.8]
    assert r.json()["nota_total"] == 7.2


def test_ct_10_04_03_todas_as_notas_10_dao_10(defesa, depois_da_defesa):
    """CT-10.04-03 (CA-02)."""
    assert _enviar(defesa, conceito="EXEMPLAR", nota="10.0").json()["nota_total"] == 10.0


def test_ct_10_04_04_todas_as_notas_0_dao_0(defesa, depois_da_defesa):
    """CT-10.04-04 (CA-02)."""
    assert _enviar(defesa, conceito="NECESSITA", nota="0.0").json()["nota_total"] == 0.0


def test_ct_10_04_05_alterar_a_nota_recalcula(defesa):
    """CT-10.04-05 (CA-04) no servidor: nota de 6 para 7 recalcula a ponderada (Metodologia, peso 2,0)."""
    metodologia = {**_todos(defesa)[1], "nota": "6.0"}
    assert defesa["olga"].put(_url(defesa), json={"criterios": [metodologia]}).json()[
        "criterios"][0]["nota_ponderada"] == 1.2
    metodologia["nota"] = "7.0"
    assert defesa["olga"].put(_url(defesa), json={"criterios": [metodologia]}).json()[
        "criterios"][0]["nota_ponderada"] == 1.4


def test_ct_10_04_06_total_adulterado_e_ignorado(defesa, db, depois_da_defesa):
    """CT-10.04-06 (CA-05): ponderadas e total mandados pelo cliente são ignorados; o servidor recalcula."""
    criterios = [{**c, "nota_ponderada": 9.99} for c in _todos(defesa)]
    corpo = {"criterios": criterios, "parecer": PARECER, "nota_total": 10}
    r = defesa["olga"].post(_url(defesa, envio=True), json=corpo)
    assert r.status_code == 200 and r.json()["nota_total"] == 7.0
    assert db.get(Avaliacao, r.json()["id"]).nota_total == Decimal("7.0")
    assert {float(c.nota_ponderada) for c in db.scalars(select(AvaliacaoCriterio))} == {0.35, 1.4, 0.7, 1.05}


def test_ct_10_04_07_sem_todos_os_criterios_o_total_nao_aparece(defesa):
    """CT-10.04-07 (CA-06): com critério sem nota, a total não é mostrada como final e as pendências vêm listadas."""
    criterios = _todos(defesa)
    minha = defesa["olga"].put(_url(defesa), json={"criterios": criterios[:8]}).json()
    assert minha["nota_total"] is None and minha["pendentes"] == [criterios[8]["criterio_id"]]
    completa = defesa["olga"].put(_url(defesa), json={"criterios": criterios}).json()
    assert completa["nota_total"] == 7.0 and completa["pendentes"] == []


@pytest.mark.parametrize(("itens", "total"), [
    ([("7.3", "1.5"), ("9.9", "5.0")], "6.0"),  # 1,095 + 4,95 = 6,045: arredonda só no final (D9)
    ([("7.5", "1.0"), ("8.0", "1.0"), ("9.0", "1.0")], "2.5"),  # 0,75 + 0,80 + 0,90 = 2,45 → 2,5
])
def test_unitario_total_arredonda_so_no_final(itens, total):
    """RBN10.04 e planilha de avaliação: soma das ponderadas exatas, arredondada para 1 casa (meio para cima)."""
    assert servico.nota_total([(Decimal(n), Decimal(p)) for n, p in itens]) == Decimal(total)


# ---------------------------------------------------------------- SCRUM-80 · RBN10.05


def test_ct_10_05_01_envio_com_criterio_sem_nota_destaca_o_criterio(defesa, depois_da_defesa):
    """CT-10.05-01 (CA-01, fluxo E4): critério 3 sem conceito e nota → 422 com o critério 3 destacado."""
    criterios = _todos(defesa)
    terceiro = criterios.pop(2)
    r = defesa["olga"].post(_url(defesa, envio=True), json={"criterios": criterios, "parecer": PARECER})
    assert r.status_code == 422
    assert r.json()["criterios"] == [
        {"id": terceiro["criterio_id"], "nome": "Revisão da literatura (referencial teórico, trabalhos correlatos, referências bibliográficas)",
         "motivo": "Escolha o conceito e informe a nota."}
    ]


def test_ct_10_05_02_envio_completo_fica_enviada(defesa, depois_da_defesa):
    """CT-10.05-02 (CA-02, passos 17 a 19)."""
    r = _enviar(defesa)
    assert r.status_code == 200
    assert r.json()["status"] == "ENVIADA" and r.json()["enviada_em"].endswith("Z")
    assert defesa["olga"].get(_url(defesa)).json()["envios"] == {"enviadas": 1, "esperadas": 3}


@pytest.mark.skip(reason="A confirmação do resultado é a SCRUM-70 (RBN09.12); a lista de pendentes já é conferida aqui.")
def test_ct_10_05_03_orientador_nao_confirma_com_avaliacao_pendente():
    """CT-10.05-03 (CA-03): 2 de 3 enviadas; a confirmação é impedida e lista o avaliador pendente."""


@pytest.mark.skip(reason="A confirmação do resultado é a SCRUM-70 (RBN09.12).")
def test_ct_10_05_04_com_todas_enviadas_a_confirmacao_fica_disponivel():
    """CT-10.05-04 (CA-04): 3 de 3 enviadas; a confirmação fica disponível."""


def test_ct_10_05_05_completude_considera_o_suplente_convocado(defesa, db, depois_da_defesa):
    """CT-10.05-05 (CA-05, TI-11): titular substituído; o suplente enviou e é ele quem conta."""
    _convocar_ricardo(defesa)
    for quem in ("olga", "paulo", "ricardo"):
        assert _enviar(defesa, quem).status_code == 200
    assert defesa["olga"].get(_url(defesa)).json()["envios"] == {"enviadas": 3, "esperadas": 3}
    assert servico.pendentes(db, db.get(Defesa, defesa["defesa"]["id"])) == []


def test_ct_10_05_06_post_de_envio_incompleto_e_rejeitado(defesa, db, depois_da_defesa):
    """CT-10.05-06 (CA-06): chamada direta à API sem critérios e com parecer curto; nada é gravado."""
    r = defesa["olga"].post(_url(defesa, envio=True), json={"criterios": [], "parecer": PARECER})
    assert r.status_code == 422 and len(r.json()["criterios"]) == 9
    r = defesa["olga"].post(_url(defesa, envio=True), json={"criterios": _todos(defesa), "parecer": "  curto  "})
    assert r.status_code == 422 and r.json()["campo"] == "parecer"
    assert db.scalar(select(func.count()).select_from(Avaliacao)) == 0


def test_pendentes_lista_quem_ainda_nao_enviou(defesa, db, depois_da_defesa):
    """CA-03 da SCRUM-80: a lista que a confirmação do resultado (SCRUM-70) vai usar; o suplente não convocado
    não é esperado."""
    assert _enviar(defesa, "olga").status_code == 200
    assert _enviar(defesa, "paulo").status_code == 200
    pendentes = servico.pendentes(db, db.get(Defesa, defesa["defesa"]["id"]))
    assert [m.usuario_id for m in pendentes] == [defesa["ids"]["otto"]]


def _membro(id_, papel, convocado=False, substitui=None) -> BancaMembro:
    return BancaMembro(id=id_, papel=papel, usuario_id=id_, interno=True,
                       convocado_em=datetime(2026, 12, 1) if convocado else None, substitui_membro_id=substitui)


def test_unitario_membros_que_avaliam():
    """RBN10.05 CA-05 e RN20: orientador e dois avaliadores; o suplente convocado no lugar do titular que ele
    substitui; coorientador e suplente não convocado ficam de fora."""
    banca = [_membro(1, "ORIENTADOR"), _membro(2, "AVALIADOR"), _membro(3, "AVALIADOR"), _membro(4, "COORIENTADOR"),
             _membro(5, "SUPLENTE")]
    assert [m.id for m in servico.membros_que_avaliam(Defesa(membros=banca))] == [1, 2, 3]
    banca[4] = _membro(5, "SUPLENTE", convocado=True, substitui=3)
    assert [m.id for m in servico.membros_que_avaliam(Defesa(membros=banca))] == [1, 2, 5]


# ---------------------------------------------------------------- DS-FL06-A · demais passos e decisões da equipe


def test_sem_sessao_recebe_401(anonimo, defesa):
    assert anonimo.get(_url(defesa)).status_code == 401


def test_defesa_inexistente_da_404(defesa):
    assert defesa["olga"].get("/api/v1/defesas/999/avaliacao").status_code == 404


def test_suplente_nao_convocado_e_coorientador_nao_avaliam(defesa):
    """Passo 5 (RN20): o Ricardo está na banca como suplente, mas não foi convocado."""
    assert defesa["ricardo"].get(_url(defesa)).status_code == 403


def test_rascunho_abre_antes_da_defesa_e_o_envio_espera_a_defesa(defesa):
    """Passo 4 com a decisão da Professora (D21): antes da defesa, rascunho sim e envio não (409)."""
    assert defesa["olga"].get(_url(defesa)).json()["envio_liberado"] is False
    assert defesa["olga"].put(_url(defesa), json={"criterios": _todos(defesa)[:6]}).status_code == 200
    r = _enviar(defesa)
    assert r.status_code == 409 and "ainda não foi realizada" in r.json()["detail"]


def test_defesa_cancelada_da_409(defesa, db):
    db.get(Defesa, defesa["defesa"]["id"]).situacao = "CANCELADA"  # o cancelamento é a SCRUM-66
    db.commit()
    assert defesa["olga"].get(_url(defesa)).status_code == 409


def test_criterio_de_outra_versao_do_instrumento_da_409(defesa, coord):
    """Passo 6 (RN19): a tela foi aberta antes de a coordenação trocar a versão vigente (nenhuma avaliação ainda)."""
    antigos = _todos(defesa)
    _instrumento_ti10(coord)  # a v1 não foi usada: os critérios são trocados no lugar
    r = defesa["olga"].put(_url(defesa), json={"criterios": antigos[:1]})
    assert r.status_code == 409 and "Recarregue a página" in r.json()["detail"]


def test_rascunho_apaga_o_criterio_que_saiu_da_tela(defesa, db):
    """O PUT manda o estado inteiro: o critério que estava salvo e não veio é apagado, com registro no log."""
    criterios = _todos(defesa)
    defesa["olga"].put(_url(defesa), json={"criterios": criterios[:2]})
    minha = defesa["olga"].put(_url(defesa), json={"criterios": criterios[:1]}).json()
    assert [c["criterio_id"] for c in minha["criterios"]] == [criterios[0]["criterio_id"]]
    log = db.scalars(select(LogAuditoria).where(LogAuditoria.acao == "salvar_avaliacao")).all()[-1]
    assert (log.valor_anterior, log.valor_novo) == ("Metodologia: Competente 7,0", None)


# ---------------------------------------------------------------- troca de membro (D15) e visibilidade (D4)


def _trocar(d, quem: str, por: str):
    membro = next(m for m in d["defesa"]["membros"] if m["pessoa"]["id"] == d["ids"][quem])
    return d["olga"].put(f"/api/v1/defesas/{d['defesa']['id']}/banca/{membro['id']}", json={"usuario_id": d["ids"][por]})


def test_troca_de_avaliador_descarta_o_rascunho_e_o_substituto_comeca_em_branco(banca, db):
    """D15: o Otto salvou um rascunho e foi trocado pelo Ricardo; o rascunho sai e fica no log."""
    d = {**banca, "defesa": _agendar(banca).json()}
    assert d["otto"].put(_url(d), json={"criterios": _todos(d, "otto")[:4]}).status_code == 200
    assert _trocar(d, "otto", "ricardo").status_code == 200
    assert db.scalar(select(func.count()).select_from(Avaliacao)) == 0
    log = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "descartar_avaliacao"))
    assert log.valor_anterior == "RASCUNHO de Otto Orientador com 4 critério(s)"
    assert d["ricardo"].get(_url(d)).json()["minha_avaliacao"] is None


def test_troca_de_avaliador_que_ja_enviou_e_recusada(defesa, depois_da_defesa):
    """D15: avaliação enviada não muda mais, então o avaliador não pode mais ser trocado (409)."""
    assert _enviar(defesa, "paulo").status_code == 200
    r = _trocar(defesa, "paulo", "otto")
    assert r.status_code == 409 and "já enviou a avaliação" in r.json()["detail"]


def test_membro_da_banca_ve_o_tcc_enquanto_a_defesa_nao_e_cancelada(banca, db):
    """D4, opção (a): o Otto (avaliador) passa a ver o TCC na lista e na página; com a defesa cancelada, não."""
    tcc = banca["tcc"]["id"]
    assert banca["otto"].get(f"/api/v1/tccs/{tcc}").status_code == 404
    defesa = _agendar(banca).json()
    assert banca["otto"].get(f"/api/v1/tccs/{tcc}").status_code == 200
    assert [t["id"] for t in banca["otto"].get("/api/v1/tccs").json()] == [tcc]
    db.get(Defesa, defesa["id"]).situacao = "CANCELADA"
    db.commit()
    assert banca["otto"].get(f"/api/v1/tccs/{tcc}").status_code == 404
    assert banca["otto"].get("/api/v1/tccs").json() == []
