"""SCRUM-93 (RBN13.06): relatório em PDF dos indicadores RBN13.02 a RBN13.05 com os filtros da tela (TEL16 · RN07,
RN18, RN20, RNF02, RNF03).

Cenário: a fixture `ind` de test_indicadores.py (coordenação vê 7 TCC1 e 3 TCC2; Paulo, professor das turmas de EC,
vê 6 e 3; Olga, orientadora, vê 6 e 2). Para conferir os números sem ler o PDF, os testes espiam as seções que o
serviço manda para o gerador do arquivo.
"""

import pytest

from app.models import LogAuditoria
from app.services import documentos
from tests.test_agenda_filtros_pdf import _texto_pdf
from tests.test_defesas_banca import banca  # noqa: F401  (fixture)
from tests.test_indicadores import ind  # noqa: F401  (fixture)
from tests.test_tcc import cenario  # noqa: F401  (fixture usada por banca)

URL = "/api/v1/indicadores/relatorio"


@pytest.fixture
def espiao(monkeypatch):
    recebido = {}
    original = documentos.indicadores_pdf

    def espiar(secoes, **kw):
        recebido.update(secoes={s[0]: s[2] for s in secoes}, **kw)
        return original(secoes, **kw)

    monkeypatch.setattr(documentos, "indicadores_pdf", espiar)
    return recebido


def _total_situacao(recebido):
    """A linha "Total" da tabela de situação: [TCC1, TCC2, soma]."""
    return next(linha for linha in recebido["secoes"]["1. Situação dos TCCs"] if linha[0] == "Total")[1:]


def test_ct_13_06_01_coordenacao_gera_as_quatro_tabelas(ind, espiao):
    """CA: o PDF começa com período, curso, filtros, quem gerou, data e hora, e traz as quatro tabelas."""
    r = ind["coord"].get(URL)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf" and r.content.startswith(b"%PDF")
    assert "attachment" in r.headers["content-disposition"]
    titulos = list(espiao["secoes"])
    for prefixo in ("1. Situação", "2. Produção", "3. Desistências", "4. Participações"):
        assert any(t.startswith(prefixo) for t in titulos), titulos
    assert _total_situacao(espiao) == ["7", "3", "10"]
    filtros = dict(espiao["filtros"])
    assert filtros["Período letivo"] == "2026/2" and filtros["Curso"] == "todos do escopo"
    assert espiao["gerado_por"] and espiao["gerado_em"]
    texto = _texto_pdf(r.content)
    assert "RELAT" in texto and "2026/2" in texto


def test_ct_13_06_02_usa_os_filtros_escolhidos(ind, espiao):
    """Exemplo da ficha: a coordenação escolhe o curso e o relatório sai só com ele."""
    assert ind["coord"].get(f"{URL}?curso=2").status_code == 200
    assert _total_situacao(espiao) == ["1", "0", "1"]
    assert dict(espiao["filtros"])["Curso"] != "todos do escopo"


def test_ct_13_06_03_orientador_recebe_so_os_seus_orientandos(ind, espiao):
    """Exemplo da ficha: o orientador gera o PDF e recebe os totais dos seus orientandos."""
    assert ind["olga"].get(URL).status_code == 200
    assert _total_situacao(espiao) == ["6", "2", "8"]
    orientadores = [linha[0] for linha in espiao["secoes"]["Orientandos por orientador"]]
    assert orientadores == [ind["orientador"]["nome"]]
    assert "Evolução das desistências por período" not in espiao["secoes"]  # evolução é da coordenação


def test_ct_13_06_04_professor_filtra_pela_turma(ind, espiao):
    assert ind["paulo"].get(f"{URL}?turma={ind['turma_tcc2']}").status_code == 200
    assert _total_situacao(espiao) == ["0", "3", "3"]


def test_ct_13_06_05_nenhum_nome_de_aluno(ind):
    """RN18: o arquivo não traz nome de aluno."""
    for cliente in (ind["coord"], ind["paulo"], ind["olga"]):
        texto = _texto_pdf(cliente.get(URL).content)
        assert "Aluno Indicador" not in texto and "Ana Ribeiro" not in texto


def test_ct_13_06_06_filtro_fora_do_perfil_e_escopo(ind):
    """O mesmo recorte da tela: filtro que o perfil não tem em nenhum indicador ou fora do escopo, 403."""
    r = ind["olga"].get(f"{URL}?orientador={ind['ids']['otto']}")
    assert r.status_code == 403 and r.json()["campo"] == "orientador"
    assert ind["paulo"].get(f"{URL}?curso=1").status_code == 403
    assert ind["paulo"].get(f"{URL}?turma={ind['turma_lc']}").status_code == 403


def test_ct_13_06_07_filtro_de_um_indicador_so_vale_nele(ind, espiao):
    """O papel é filtro das bancas: a orientadora pode usá-lo, e a situação não muda por isso."""
    assert ind["olga"].get(f"{URL}?papel=AVALIADOR").status_code == 200
    assert _total_situacao(espiao) == ["6", "2", "8"]
    assert "papel na banca" in dict(espiao["filtros"])["Outros filtros"]


def test_ct_13_06_08_aluno_nao_gera(ind):
    assert ind["aluno"].get(URL).status_code == 403


def test_ct_13_06_09_geracao_fica_no_log(ind, db):
    """RNF03: quem gerou e com quais filtros."""
    assert ind["coord"].get(f"{URL}?curso=2").status_code == 200
    log = db.query(LogAuditoria).filter_by(acao="relatorio_indicadores_gerado").one()
    assert "curso=2" in log.valor_novo
