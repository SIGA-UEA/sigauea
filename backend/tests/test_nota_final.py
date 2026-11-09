"""SCRUM-69 (RBN09.11): calcular a nota final da defesa (RN13, RN21 · DS-FL06-B).

Os casos de teste da ficha (CT-09.11-01 a 08) usam avaliações reais, enviadas pela API da avaliação
(RBN10.02 a RBN10.05): com a mesma nota em todos os critérios (pesos somando 10), a nota total do membro é a
própria nota, o que dá os valores exatos da ficha. A banca é a padrão: Olga (orientadora), Otto e Paulo
(avaliadores) e o Ricardo de suplente não convocado, que não avalia.

Os testes unitários conferem o cálculo isolado: valores-limite, arredondamento e todas as combinações da regra
de exceção do Qualis.
"""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models import Defesa, PublicacaoArtigo, Tcc
from app.services import nota_final
from tests.test_avaliacao import PARECER, _todos, _url, defesa, depois_da_defesa  # noqa: F401  (fixtures)
from tests.test_defesas_banca import banca  # noqa: F401  (fixture usada por defesa)
from tests.test_tcc import cenario  # noqa: F401  (fixture usada por banca)


def _conceito(nota: str) -> str:
    valor = Decimal(nota)
    return "EXEMPLAR" if valor >= 8 else "COMPETENTE" if valor >= 6 else "NECESSITA"


def _enviar_nota(d, quem: str, nota: str) -> None:
    criterios = _todos(d, quem, conceito=_conceito(nota), nota=nota)
    r = d[quem].post(_url(d, envio=True), json={"criterios": criterios, "parecer": PARECER})
    assert r.status_code == 200, r.json()
    assert r.json()["nota_total"] == float(nota)


def _notas(d, orientadora: str, otto: str, paulo: str) -> None:
    for quem, nota in (("olga", orientadora), ("otto", otto), ("paulo", paulo)):
        _enviar_nota(d, quem, nota)


def _artigo(d, db, situacao: str, qualis: str | None) -> None:
    tcc = db.get(Tcc, d["tcc"]["id"])
    tcc.modalidade = "ARTIGO"
    db.add(PublicacaoArtigo(tcc_id=tcc.id, tipo_veiculo="PERIODICO", veiculo="Revista de Computação Aplicada",
                            qualis=qualis, situacao_atual=situacao,
                            doi="10.1000/exemplo" if situacao == "PUBLICADO" else None))
    db.commit()


def _resultado(d, quem="olga"):
    return d[quem].get(f"/api/v1/defesas/{d['defesa']['id']}/resultado")


# ---------------------------------------------------------------- CT-09.11-01 a 08 (ficha)


def test_ct_09_11_01_media_simples_7_8_6(defesa, depois_da_defesa):
    """CA-01: a nota final é a média das três notas."""
    _notas(defesa, "7.0", "8.0", "6.0")
    r = _resultado(defesa)
    assert r.status_code == 200 and r.json()["pendentes"] == []
    c = r.json()["consolidacao"]
    assert (c["media"], c["nota_final"]) == (7.0, 7.0)
    assert sorted(n["nota"] for n in c["notas"]) == [6.0, 7.0, 8.0]
    assert {n["papel"] for n in c["notas"]} == {"ORIENTADOR", "AVALIADOR"}  # o suplente não convocado não entra


def test_ct_09_11_02_qualis_a_eleva_para_6(defesa, depois_da_defesa, db):
    """CA-02 / RN21: 5,0; 5,4; 5,2 com artigo Qualis A → média 5,20 e nota final 6,00."""
    _artigo(defesa, db, "ACEITO", "A1")
    _notas(defesa, "5.0", "5.4", "5.2")
    c = _resultado(defesa).json()["consolidacao"]
    assert (c["media"], c["nota_final"]) == (5.2, 6.0)
    assert c["regra"]["aplicada"] is True
    assert c["regra"]["porque"] == ("Artigo aceito em veículo Qualis A1: a nota final é o maior valor entre 6,00 "
                                    "e a média.")
    assert (c["regra"]["situacao_editorial"], c["regra"]["qualis"]) == ("ACEITO", "A1")


def test_ct_09_11_03_limite_6_com_qualis_b(defesa, depois_da_defesa, db):
    """CA-03: média exatamente 6,0 com Qualis B → 6,00 (a exceção não muda nada no limite)."""
    _artigo(defesa, db, "PUBLICADO", "B2")
    _notas(defesa, "6.0", "6.0", "6.0")
    c = _resultado(defesa).json()["consolidacao"]
    assert (c["media"], c["nota_final"]) == (6.0, 6.0) and c["regra"]["aplicada"] is True


def test_ct_09_11_04_excecao_nao_rebaixa_8_33(defesa, depois_da_defesa, db):
    """CA-03: 8,0; 8,0; 9,0 com Qualis A → 8,33 (a própria média, com duas casas)."""
    _artigo(defesa, db, "ACEITO", "A2")
    _notas(defesa, "8.0", "8.0", "9.0")
    c = _resultado(defesa).json()["consolidacao"]
    assert (c["media"], c["nota_final"]) == (8.33, 8.33)


def test_ct_09_11_05_monografia_sem_piso(defesa, depois_da_defesa):
    """CA-04: 5,0; 5,4; 5,2 em monografia → 5,20."""
    _notas(defesa, "5.0", "5.4", "5.2")
    c = _resultado(defesa).json()["consolidacao"]
    assert (c["media"], c["nota_final"]) == (5.2, 5.2)
    assert c["regra"] == {"aplicada": False, "porque": "Não se aplica: a modalidade é monografia.",
                          "modalidade": "MONOGRAFIA", "situacao_editorial": None, "qualis": None}


def test_ct_09_11_06_artigo_submetido_sem_piso(defesa, depois_da_defesa, db):
    """CA-04: artigo "submetido", mesmo em Qualis A, com média 5,0 → 5,00."""
    _artigo(defesa, db, "SUBMETIDO", "A1")
    _notas(defesa, "5.0", "5.0", "5.0")
    c = _resultado(defesa).json()["consolidacao"]
    assert (c["media"], c["nota_final"]) == (5.0, 5.0)
    assert c["regra"]["porque"] == "Não aplicada: o artigo não está aceito ou publicado em veículo Qualis A ou B."


def test_ct_09_11_07_duas_de_tres_enviadas_bloqueia_e_indica_quem_falta(defesa, depois_da_defesa):
    """CA-05: com 2 de 3 avaliações enviadas, o cálculo não é liberado e a pendência é indicada."""
    _enviar_nota(defesa, "olga", "7.0")
    _enviar_nota(defesa, "otto", "8.0")
    corpo = _resultado(defesa).json()
    assert corpo["consolidacao"] is None
    assert [(p["papel"], p["pessoa"]["id"]) for p in corpo["pendentes"]] == [("AVALIADOR", defesa["ids"]["paulo"])]


def test_ct_09_11_08_mesmo_valor_no_recalculo_e_na_tela(defesa, depois_da_defesa, db):
    """CA-06: o valor mostrado na tela é o mesmo do recálculo que a confirmação e a ata vão usar (duas casas)."""
    _artigo(defesa, db, "ACEITO", "B1")
    _notas(defesa, "8.0", "8.5", "8.0")  # média 8,1666... → 8,17
    c = _resultado(defesa).json()["consolidacao"]
    recalculo = nota_final.recalcular_nota_final(db, db.get(Defesa, defesa["defesa"]["id"]))
    assert c["media"] == float(recalculo.media) == 8.17
    assert c["nota_final"] == float(recalculo.nota_final) == 8.17
    assert recalculo.media.as_tuple().exponent == -2  # sempre duas casas


# ---------------------------------------------------------------- acesso e situações da defesa


def test_antes_das_avaliacoes_todos_os_tres_aparecem_como_pendentes(defesa):
    corpo = _resultado(defesa).json()
    assert corpo["consolidacao"] is None
    assert sorted(p["papel"] for p in corpo["pendentes"]) == ["AVALIADOR", "AVALIADOR", "ORIENTADOR"]


def test_so_o_orientador_consulta_a_consolidacao(defesa, coord, depois_da_defesa):
    """DS-FL06: o ator é o orientador. Avaliador, aluno e professor da turma veem o TCC, mas recebem 403
    (o avaliador vê só a própria avaliação, RBN10.02 CA-02)."""
    _notas(defesa, "7.0", "7.0", "7.0")
    for quem in ("otto", "paulo", "aluno"):
        assert _resultado(defesa, quem).status_code == 403
    assert coord.get(f"/api/v1/defesas/{defesa['defesa']['id']}/resultado").status_code == 403


def test_defesa_inexistente_da_404(defesa):
    assert defesa["olga"].get("/api/v1/defesas/999/resultado").status_code == 404


def test_defesa_cancelada_da_409(defesa, db):
    db.get(Defesa, defesa["defesa"]["id"]).situacao = "CANCELADA"
    db.commit()
    assert _resultado(defesa).status_code == 409


# ---------------------------------------------------------------- unitários do cálculo (valores-limite)


@pytest.mark.parametrize("notas, media", [
    (["7.0", "8.0", "6.0"], "7.00"),
    (["5.0", "5.4", "5.2"], "5.20"),
    (["8.0", "8.0", "9.0"], "8.33"),  # 8,333... arredonda para baixo
    (["8.0", "8.5", "8.0"], "8.17"),  # 8,1666... arredonda para cima
    (["6.0", "6.0", "6.1"], "6.03"),
    (["0.0", "0.0", "0.0"], "0.00"),  # limite inferior (RN13)
    (["10.0", "10.0", "10.0"], "10.00"),  # limite superior (RN13)
    (["9.9", "10.0", "10.0"], "9.97"),
    (["5.9", "6.0", "6.0"], "5.97"),
])
def test_calcular_media_com_duas_casas(notas, media):
    resultado = nota_final.calcular_media([Decimal(n) for n in notas])
    assert resultado == Decimal(media) and resultado.as_tuple().exponent == -2


def test_meio_centesimo_arredonda_para_cima():
    assert nota_final.calcular_media([Decimal("8.005")]) == Decimal("8.01")


def test_sem_notas_nao_calcula():
    with pytest.raises(ValueError):
        nota_final.calcular_media([])


def _tcc(modalidade="ARTIGO", situacao=None, qualis=None, publicacoes=None):
    if publicacoes is None:
        publicacoes = [SimpleNamespace(situacao_atual=situacao, qualis=qualis)] if situacao else []
    return SimpleNamespace(tcc=SimpleNamespace(modalidade=modalidade, publicacoes=publicacoes))


@pytest.mark.parametrize("situacao, qualis, aplicada", [
    ("ACEITO", "A1", True), ("ACEITO", "A4", True), ("PUBLICADO", "B1", True), ("PUBLICADO", "B4", True),
    ("ACEITO", "a2", True),  # estrato em minúscula conta igual
    ("ACEITO", "C", False), ("PUBLICADO", None, False), ("ACEITO", "", False),
    ("ACEITO", "BX", False), ("ACEITO", "B5", False), ("ACEITO", "A", False),  # fora da lista A1 a B4
    ("ACEITO", " b3 ", True),  # espaços e minúscula não mudam o estrato
    ("SUBMETIDO", "A1", False), ("EM_REVISAO", "A1", False), ("RECUSADO", "A1", False),
])
def test_regra_do_qualis(situacao, qualis, aplicada):
    assert nota_final.regra_excecao(_tcc(situacao=situacao, qualis=qualis)).aplicada is aplicada


def test_monografia_e_artigo_sem_publicacao_nao_aplicam():
    assert nota_final.regra_excecao(_tcc(modalidade="MONOGRAFIA", situacao="ACEITO", qualis="A1")).aplicada is False
    sem = nota_final.regra_excecao(_tcc(publicacoes=[]))
    assert sem.aplicada is False and sem.situacao_editorial is None


def test_vale_a_situacao_mais_recente_do_artigo():
    """A regra olha a situação editorial atual (o registro mais recente), como no DS-FL06-B."""
    antiga = SimpleNamespace(situacao_atual="SUBMETIDO", qualis="A1")
    atual = SimpleNamespace(situacao_atual="ACEITO", qualis="A1")
    assert nota_final.regra_excecao(_tcc(publicacoes=[antiga, atual])).aplicada is True
    assert nota_final.regra_excecao(_tcc(publicacoes=[atual, antiga])).aplicada is False
