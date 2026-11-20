"""SCRUM-95 (RBN14.02) e SCRUM-96 (RBN14.03): filtros da agenda por curso e período de datas e exportação em PDF
(TEL17 · RN01, RN08, RN09, RNF02, RNF03).

Cenário: a fixture `banca` (TCC de EC da Ana, orientado pela Olga) e defesas gravadas direto no banco, já publicadas,
como em test_agenda.py; um TCC de LC (curso 2) para o filtro de curso.
"""

import re
import zlib

from app.models import LogAuditoria
from app.services import documentos
from tests.test_agenda import _defesa, _outro_tcc, dia
from tests.test_defesas_banca import banca  # noqa: F401  (fixture)
from tests.test_tcc import cenario  # noqa: F401  (fixture usada por banca)

URL = "/api/v1/agenda"


def _tcc_lc(banca, db, coord):
    """Um TCC aprovado de aluno de Licenciatura em Computação (curso 2)."""
    from app.models import Tcc

    aluno = coord.post("/api/v1/alunos", json={"nome": "Lia Campos", "email": "lia@uea.edu.br",
                                               "matricula": "24150777", "curso_id": 2}).json()
    base = db.get(Tcc, banca["tcc"]["id"])
    tcc = Tcc(aluno_id=aluno["id"], turma_id=base.turma_id, periodo_id=base.periodo_id, etapa=base.etapa,
              modalidade=base.modalidade, titulo="Jogos no ensino de lógica", resumo="Resumo.", area_id=base.area_id,
              situacao="APROVADO")
    db.add(tcc)
    db.commit()
    return tcc.id


def _cenario(banca, db, coord):
    """EC em 2 e 10 dias; LC em 5 dias."""
    _defesa(db, banca, banca["tcc"]["id"], dia(2), "09:00")
    _defesa(db, banca, _outro_tcc(banca, db, coord, 1, "Segundo de EC"), dia(10), "10:00")
    _defesa(db, banca, _tcc_lc(banca, db, coord), dia(5), "14:00")


def _titulos(cliente, consulta=""):
    r = cliente.get(f"{URL}?{consulta}")
    assert r.status_code == 200, r.json()
    return [i["titulo"] for i in r.json()]


def _texto_pdf(conteudo: bytes) -> str:
    """O texto dos fluxos do PDF (o fpdf2 comprime cada página com zlib)."""
    partes = []
    for fluxo in re.findall(rb"stream\r?\n(.*?)\r?\nendstream", conteudo, re.S):
        try:
            partes.append(zlib.decompress(fluxo).decode("latin-1"))
        except zlib.error:
            continue
    return "\n".join(partes)


# ---------------------------------------------------------------- RBN14.02 filtros


def test_ct_14_02_01_filtra_por_curso(banca, coord, db):
    """CA: o curso escolhido mostra só as apresentações dele (RN01); o curso vem com id para o filtro da tela."""
    _cenario(banca, db, coord)
    assert _titulos(banca["aluno"], "curso=2") == ["Jogos no ensino de lógica"]
    assert _titulos(banca["aluno"], "curso=1") == [banca["tcc"]["titulo"], "Segundo de EC"]
    assert banca["aluno"].get(URL).json()[0]["curso"] == {"id": 1, "sigla": "EC",
                                                          "nome": banca["aluno"].get(URL).json()[0]["curso"]["nome"]}


def test_ct_14_02_02_filtra_por_periodo_de_datas(banca, coord, db):
    """CA: só as apresentações entre a data inicial e a final, inclusive as dos dois extremos."""
    _cenario(banca, db, coord)
    assert _titulos(banca["aluno"], f"de={dia(2)}&ate={dia(5)}") == [banca["tcc"]["titulo"], "Jogos no ensino de lógica"]
    assert _titulos(banca["aluno"], f"de={dia(6)}") == ["Segundo de EC"]
    assert _titulos(banca["aluno"], f"ate={dia(4)}") == [banca["tcc"]["titulo"]]


def test_ct_14_02_03_curso_e_periodo_juntos(banca, coord, db):
    _cenario(banca, db, coord)
    assert _titulos(banca["aluno"], f"curso=1&de={dia(3)}&ate={dia(30)}") == ["Segundo de EC"]


def test_ct_14_02_04_data_final_antes_da_inicial(banca):
    """CA: data final igual ou posterior à inicial; antes dela, 400 com o campo destacado."""
    r = banca["aluno"].get(f"{URL}?de={dia(5)}&ate={dia(2)}")
    assert r.status_code == 400
    assert "ate" in r.json()["campos"]
    assert banca["aluno"].get(f"{URL}?de={dia(5)}&ate={dia(5)}").status_code == 200  # a mesma data vale


def test_ct_14_02_05_periodo_sem_apresentacoes_volta_vazio(banca, coord, db):
    """CA: período sem apresentações devolve a lista vazia (a tela mostra a mensagem)."""
    _cenario(banca, db, coord)
    assert _titulos(banca["aluno"], f"de={dia(40)}&ate={dia(50)}") == []


def test_ct_14_02_06_data_inicial_no_passado_mostra_as_realizadas(banca, coord, db):
    """Com data inicial, o período escolhido manda: uma defesa de ontem aparece se o período a inclui."""
    _defesa(db, banca, banca["tcc"]["id"], dia(-1), "09:00")
    assert _titulos(banca["aluno"]) == []  # "próximos" começa hoje
    assert _titulos(banca["aluno"], f"de={dia(-3)}") == [banca["tcc"]["titulo"]]


def test_filtros_nao_mostram_defesa_nao_publicada(banca, coord, db):
    """RN08: o filtro só recorta o que já está na agenda."""
    _cenario(banca, db, coord)
    from app.models import Defesa

    for d in db.query(Defesa):
        d.publicada = False
    db.commit()
    assert _titulos(banca["aluno"], f"curso=1&de={dia(0)}") == []


# ---------------------------------------------------------------- RBN14.03 exportar em PDF


def test_ct_14_03_01_orientador_exporta_a_agenda_filtrada(banca, coord, db, monkeypatch):
    """CA: o PDF reaproveita os filtros da tela (curso e período) e traz só as apresentações deles."""
    _cenario(banca, db, coord)
    recebido = {}
    original = documentos.agenda_pdf

    def espiar(itens, **kw):
        recebido.update(itens=[i.titulo for i in itens], **kw)
        return original(itens, **kw)

    monkeypatch.setattr(documentos, "agenda_pdf", espiar)
    r = banca["olga"].get(f"{URL}/pdf?curso=1&de={dia(1)}&ate={dia(3)}")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"] and ".pdf" in r.headers["content-disposition"]
    assert r.content.startswith(b"%PDF")
    assert recebido["itens"] == [banca["tcc"]["titulo"]]
    assert recebido["curso"] and recebido["de"].isoformat() == dia(1) and recebido["ate"].isoformat() == dia(3)
    texto = _texto_pdf(r.content)
    assert "AGENDA DE APRESENTA" in texto and "Ana Ribeiro" in texto


def test_ct_14_03_02_pdf_sem_dados_sensiveis(banca, coord, db):
    """CA: o arquivo não traz contatos, matrícula nem notas (RN08); o link só se a defesa autoriza divulgar."""
    _cenario(banca, db, coord)
    texto = _texto_pdf(coord.get(f"{URL}/pdf").content).lower()
    assert "ana ribeiro" in texto
    for proibido in ("24150777", "24150001", "@uea.edu.br", "telefone", "nota final", "media", "meet.exemplo.com"):
        assert proibido not in texto  # o rodapé avisa "sem contatos, matrículas ou notas"


def test_ct_14_03_03_so_coordenacao_professor_e_orientador_exportam(banca, coord, db):
    """O aluno e o membro externo consultam a agenda, mas não exportam (403)."""
    _cenario(banca, db, coord)
    assert banca["aluno"].get(f"{URL}/pdf").status_code == 403
    assert coord.get(f"{URL}/pdf").status_code == 200
    assert banca["paulo"].get(f"{URL}/pdf").status_code == 200  # professor da disciplina


def test_ct_14_03_04_exportacao_sem_apresentacoes_gera_pdf_com_aviso(banca):
    r = banca["olga"].get(f"{URL}/pdf?de={dia(40)}")
    assert r.status_code == 200
    assert "Nenhuma apresenta" in _texto_pdf(r.content)


def test_ct_14_03_05_exportacao_fica_no_log(banca, coord, db):
    """RNF03: quem exportou e com quais filtros."""
    _cenario(banca, db, coord)
    assert banca["olga"].get(f"{URL}/pdf?curso=2").status_code == 200
    log = db.query(LogAuditoria).filter_by(acao="agenda_exportada").one()
    assert log.usuario_id == banca["ids"]["olga"] and "curso=2" in log.valor_novo and "itens=1" in log.valor_novo


def test_exportacao_valida_as_datas_como_a_tela(banca):
    assert banca["olga"].get(f"{URL}/pdf?de={dia(5)}&ate={dia(1)}").status_code == 400


def test_titulo_com_caracteres_fora_do_latin1_nao_quebra_o_pdf(banca, coord, db):
    """Aspas tipográficas, travessão e emoji no título não podem derrubar a exportação."""
    from app.models import Tcc

    tcc = db.get(Tcc, banca["tcc"]["id"])
    tcc.titulo = "“Visão” — redes neurais 🚀 e grafos"
    db.commit()
    _defesa(db, banca, tcc.id, dia(2), "09:00")
    r = coord.get(f"{URL}/pdf")
    assert r.status_code == 200
    assert '"Vis' in _texto_pdf(r.content)


def test_exportar_exige_login(anonimo):
    assert anonimo.get(f"{URL}/pdf").status_code == 401


def test_periodos_do_prototipo(banca, coord, db):
    """DS-FL05-A e protótipo da TEL17: "Próximas apresentações", "Próximos 7 dias" e "Todas (inclui passadas)"."""
    _cenario(banca, db, coord)  # EC em 2 e 10 dias; LC em 5
    _defesa(db, banca, _outro_tcc(banca, db, coord, 3, "Já realizada"), dia(-2), "09:00")
    assert _titulos(banca["aluno"], "periodo=semana") == [banca["tcc"]["titulo"], "Jogos no ensino de lógica"]
    assert len(_titulos(banca["aluno"], "periodo=proximos")) == 3
    assert _titulos(banca["aluno"], "periodo=todas")[0] == "Já realizada"
    assert _titulos(banca["aluno"], "periodo=semana&curso=2") == ["Jogos no ensino de lógica"]
