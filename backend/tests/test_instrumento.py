"""Sprint S04 · instrumento de avaliação ponderado e versionado (RBN10.01, SCRUM-76).

Cada teste cita o caso de teste da ficha (CT-10.01-xx) ou o passo do diagrama DS-FL06-G que
confere. O cenário é montado pela API; a versão 1 vem da carga base (conftest → seed).

Até o SCRUM-77 (RBN10.02) não existe a tabela avaliacao, então nenhuma versão pode ter sido usada
(passo 8 responde sempre "não"). Para cobrir o ramo "já usado" (passos 9 e 10), os testes trocam
existe_avaliacao por uma versão que responde "sim"; no SCRUM-77 eles passam a usar uma avaliação real.
"""

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.erros import ErroAPI
from app.models import CriterioAvaliacao, InstrumentoAvaliacao, LogAuditoria
from app.schemas.instrumento import InstrumentoEntrada
from app.seed import carregar_instrumento
from app.services import instrumento as servico
from tests.conftest import DOCENTE, ativar

URL = "/api/v1/instrumento-avaliacao"
CAMPOS = ("nome", "peso", "texto_exemplar", "texto_competente", "texto_necessita")


def _corpo(consulta: dict) -> dict:
    """O corpo do PUT a partir do GET, como a tela monta (DS-FL06-G passo 6)."""
    return {
        "componentes": [
            {"id": c["id"], "criterios": [{k: x[k] for k in CAMPOS} for x in c["criterios"]]}
            for c in consulta["instrumento"]["componentes"]
        ]
    }


@pytest.fixture
def ja_usado(monkeypatch):
    """Passo 8 respondendo "sim": a versão vigente já foi usada em avaliações (ver docstring do módulo)."""
    monkeypatch.setattr(servico, "existe_avaliacao", lambda db, instrumento_id: True)


# ---------------------------------------------------------------- casos de teste da ficha


def test_ct_10_01_01_consulta_mostra_componentes_criterios_pesos_e_conceitos(coord):
    """CT-10.01-01 (CA-01): 2 componentes, critérios, pesos e 3 conceitos com faixas (passos 2 a 4)."""
    r = coord.get(URL)
    assert r.status_code == 200
    instrumento = r.json()["instrumento"]
    assert instrumento["versao"] == 1 and instrumento["vigente"] is True

    escrita, oral = instrumento["componentes"]
    assert (escrita["nome"], escrita["pontos"], len(escrita["criterios"])) == ("Parte escrita", 7.0, 6)
    assert (oral["nome"], oral["pontos"], len(oral["criterios"])) == ("Parte oral", 3.0, 3)
    assert [k["peso"] for k in escrita["criterios"]] == [0.5, 2.0, 1.0, 2.0, 0.5, 1.0]
    assert [k["peso"] for k in oral["criterios"]] == [1.0, 1.5, 0.5]
    assert escrita["criterios"][1]["nome"] == "Metodologia"
    for k in escrita["criterios"] + oral["criterios"]:
        assert k["texto_exemplar"] and k["texto_competente"] and k["texto_necessita"]

    assert instrumento["conceitos"] == [
        {"conceito": "EXEMPLAR", "rotulo": "Exemplar", "minimo": 8.0, "maximo": 10.0},
        {"conceito": "COMPETENTE", "rotulo": "Competente", "minimo": 6.0, "maximo": 7.9},
        {"conceito": "NECESSITA", "rotulo": "Necessita de Trabalho", "minimo": 0.0, "maximo": 5.9},
    ]


def test_ct_10_01_02_pesos_que_nao_fecham_sao_rejeitados(coord, db):
    """CT-10.01-02 (CA-02, fluxo E1): 422 com os componentes de soma incorreta, e nada é salvo (passo 7)."""
    corpo = _corpo(coord.get(URL).json())
    corpo["componentes"][0]["criterios"][1]["peso"] = "2.5"  # escrita soma 7,5
    corpo["componentes"][1]["criterios"][0]["peso"] = "0.5"  # oral soma 2,5

    r = coord.put(URL, json=corpo)
    assert r.status_code == 422
    assert r.json()["detail"] == "Os pesos não fecham 7,0 e 3,0."
    assert [(c["nome"], c["soma"]) for c in r.json()["componentes"]] == [("Parte escrita", 7.5), ("Parte oral", 2.5)]

    pesos = db.scalars(select(CriterioAvaliacao.peso).order_by(CriterioAvaliacao.id)).all()
    assert [float(p) for p in pesos] == [0.5, 2.0, 1.0, 2.0, 0.5, 1.0, 1.0, 1.5, 0.5]
    assert db.scalar(select(func.count()).where(LogAuditoria.acao == "configurar_instrumento")) == 0


def test_ct_10_01_03_instrumento_usado_gera_nova_versao_e_a_original_fica_intacta(coord, db, ja_usado):
    """CT-10.01-03 (CA-03): alterar um peso de um instrumento já usado cria a versão 2; a versão 1,
    em que as defesas já avaliadas continuam, não muda (passos 8 a 10)."""
    original = coord.get(URL).json()["instrumento"]
    corpo = _corpo({"instrumento": original})
    corpo["componentes"][0]["criterios"][0]["peso"] = "1.0"  # Relevância 0,5 -> 1,0
    corpo["componentes"][0]["criterios"][1]["peso"] = "1.5"  # Metodologia 2,0 -> 1,5

    r = coord.put(URL, json=corpo)
    assert r.status_code == 200
    nova = r.json()
    assert nova["versao"] == 2 and nova["vigente"] is True
    assert [k["peso"] for k in nova["componentes"][0]["criterios"]][:2] == [1.0, 1.5]

    v1 = db.scalar(select(InstrumentoAvaliacao).where(InstrumentoAvaliacao.versao == 1))
    assert v1.vigente is False
    assert [float(k.peso) for k in v1.componentes[0].criterios] == [0.5, 2.0, 1.0, 2.0, 0.5, 1.0]
    assert v1.componentes[0].id == original["componentes"][0]["id"]  # mesmos registros, intactos

    consulta = coord.get(URL).json()
    assert consulta["instrumento"]["versao"] == 2
    assert [(v["versao"], v["vigente"]) for v in consulta["versoes"]] == [(2, True), (1, False)]


@pytest.mark.skip(reason="A fixação da versão acontece ao iniciar a primeira avaliação (DS-FL06-A), que chega com o SCRUM-77 (RBN10.02).")
def test_ct_10_01_04_primeira_avaliacao_fixa_a_versao_vigente():
    """CT-10.01-04 (CA-04): nova defesa, iniciar avaliação -> versão vigente fixada na avaliação."""


def test_ct_10_01_05_historico_mostra_as_3_versoes_com_data_e_autor(coord, ja_usado):
    """CT-10.01-05 (CA-05): com 3 versões, o histórico mostra as 3 com data e autor (passo 3)."""
    for _ in range(2):
        assert coord.put(URL, json=_corpo(coord.get(URL).json())).status_code == 200

    versoes = coord.get(URL).json()["versoes"]
    assert [v["versao"] for v in versoes] == [3, 2, 1]
    assert [v["vigente"] for v in versoes] == [True, False, False]
    for v in versoes:
        assert v["criado_em"].endswith("Z")
        assert v["autor"]["nome"] == "Coordenadora Teste"


def test_ct_10_01_06_professor_recebe_403_no_put_e_no_get(coord, caixa):
    """CT-10.01-06 (CA-06, fluxo E2): quem não é da coordenação não consulta nem altera."""
    corpo = _corpo(coord.get(URL).json())
    assert coord.post("/api/v1/docentes", json=DOCENTE).status_code == 201
    professor = ativar(caixa, DOCENTE["email"])

    assert professor.put(URL, json=corpo).status_code == 403
    assert professor.get(URL).status_code == 403


# ---------------------------------------------------------------- demais passos do DS-FL06-G


def test_sem_sessao_recebe_401(anonimo):
    assert anonimo.get(URL).status_code == 401
    assert anonimo.put(URL, json={"componentes": []}).status_code == 401


def test_ds_fl06g_passo_11_instrumento_nao_usado_e_atualizado_no_lugar(coord, db):
    """Passo 11: sem avaliações, salvar troca os critérios da versão vigente, sem criar outra versão.
    A coordenação pode remover, renomear e reordenar critérios (passo 5)."""
    corpo = _corpo(coord.get(URL).json())
    oral = corpo["componentes"][1]["criterios"]
    oral.pop()  # remove "Postura perante a banca" (0,5)
    oral[0]["peso"] = "1.5"  # Organização 1,0 -> 1,5
    oral.reverse()  # Domínio do assunto passa a ser o primeiro
    oral[0]["nome"] = "Domínio do assunto e da apresentação"

    r = coord.put(URL, json=corpo)
    assert r.status_code == 200
    assert r.json()["versao"] == 1
    assert [(k["nome"], k["peso"], k["ordem"]) for k in r.json()["componentes"][1]["criterios"]] == [
        ("Domínio do assunto e da apresentação", 1.5, 1),
        ("Organização (sequência lógica, qualidade do material e da apresentação, aproveitamento do tempo)", 1.5, 2),
    ]
    assert db.scalar(select(func.count()).select_from(InstrumentoAvaliacao)) == 1
    assert db.scalar(select(func.count()).select_from(CriterioAvaliacao)) == 8


def test_ds_fl06g_passo_12_salvar_registra_no_log(coord, db):
    """Passo 12 (RNF03): registrar(configurar_instrumento, idInstrumento, versão)."""
    assert coord.put(URL, json=_corpo(coord.get(URL).json())).status_code == 200
    log = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "configurar_instrumento"))
    assert (log.entidade, log.campo, log.valor_novo) == ("instrumento_avaliacao", "versao", "1")
    assert log.usuario_id is not None


def test_peso_zero_ou_negativo_e_campos_vazios_sao_recusados(coord):
    """Peso maior que zero, até duas casas (NUMERIC(4,2)); nome e textos obrigatórios: 400 por campo."""
    base = coord.get(URL).json()
    for campo, valor in (("peso", "0"), ("peso", "-1"), ("peso", "0.555"), ("nome", "  "), ("texto_competente", "")):
        corpo = _corpo(base)
        corpo["componentes"][0]["criterios"][0][campo] = valor
        r = coord.put(URL, json=corpo)
        assert r.status_code == 400, (campo, valor)
        assert campo in r.json()["campos"]


def test_tela_desatualizada_recebe_409(coord, ja_usado):
    """Outra pessoa salvou uma versão nova depois que a tela foi aberta: os componentes não são mais os vigentes."""
    corpo_antigo = _corpo(coord.get(URL).json())
    assert coord.put(URL, json=corpo_antigo).status_code == 200  # cria a versão 2
    r = coord.put(URL, json=corpo_antigo)
    assert r.status_code == 409


# ---------------------------------------------------------------- unitários (DoD: versionagem e validação de pesos)


def _entrada(db, **troca) -> InstrumentoEntrada:
    vigente = servico.obter_vigente(db)
    componentes = []
    for c in vigente.componentes:
        criterios = [{k: getattr(x, k) for k in CAMPOS} for x in c.criterios]
        for (cid, indice), peso in troca.get("pesos", {}).items():
            if cid == c.ordem:
                criterios[indice]["peso"] = peso
        componentes.append({"id": c.id, "criterios": criterios})
    return InstrumentoEntrada(componentes=componentes)


def test_unitario_validar_pesos_aceita_soma_exata_em_decimal(db):
    """0,1 + 0,2 em float daria 0,30000000000000004; em Decimal a soma fecha exata."""
    vigente = servico.obter_vigente(db)
    entrada = _entrada(db, pesos={(2, 0): Decimal("0.80"), (2, 1): Decimal("1.70")})  # oral: 0,8 + 1,7 + 0,5 = 3,0
    servico.validar_pesos(list(vigente.componentes), entrada)  # não levanta


def test_unitario_validar_pesos_aponta_so_o_componente_errado(db):
    vigente = servico.obter_vigente(db)
    entrada = _entrada(db, pesos={(2, 2): Decimal("0.6")})  # oral soma 3,1
    with pytest.raises(ErroAPI) as erro:
        servico.validar_pesos(list(vigente.componentes), entrada)
    assert erro.value.status == 422
    assert erro.value.corpo["componentes"] == [
        {"id": vigente.componentes[1].id, "nome": "Parte oral", "pontos": 3.0, "soma": 3.1}
    ]


def test_unitario_nova_versao_copia_componentes_e_numera_em_sequencia(db, ja_usado):
    vigente = servico.obter_vigente(db)
    autor = vigente.autor
    nova = servico.salvar_instrumento(db, autor, _entrada(db))
    assert nova.versao == 2
    assert [(c.nome, c.pontos, len(c.criterios)) for c in nova.componentes] == [
        ("Parte escrita", 7.0, 6),
        ("Parte oral", 3.0, 3),
    ]
    assert db.scalar(select(func.count()).where(InstrumentoAvaliacao.vigente.is_(True))) == 1


def test_unitario_carga_da_versao_1_nao_duplica(db):
    """O seed pode rodar mais de uma vez: se já existe versão, carregar_instrumento não cria outra."""
    autor = servico.obter_vigente(db).autor
    carregar_instrumento(db, autor)
    db.commit()
    assert db.scalar(select(func.count()).select_from(InstrumentoAvaliacao)) == 1
    assert db.scalar(select(func.count()).select_from(CriterioAvaliacao)) == 9