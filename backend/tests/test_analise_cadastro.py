"""Sprint S04 · análise do cadastro de TCC pela coordenação (RAN04).

Cada teste cita o caso de teste da ficha (CT-04.01-xx a CT-04.05-xx) ou o passo do diagrama
de sequência (DS-FL02-A, DS-FL02, DS-FL02-B) que confere. O cenário é montado pela API.
"""

from datetime import date

import pytest
from sqlalchemy import select

from app.models import (
    AnaliseCadastro,
    Curso,
    HistoricoPublicacao,
    LogAuditoria,
    Nucleo,
    NotificacaoEmail,
    PeriodoLetivo,
    PublicacaoArtigo,
    Tcc,
)
from tests.conftest import ativar
from tests.test_tcc import ORIENTADOR, PROFESSOR, _aceitar, _rascunho, cenario  # noqa: F401

COORD2 = {"nome": "Cecília Coordenadora", "email": "cecilia@exemplo.com", "cargo": "coordenador",
          "curso_id": None, "perfis": ["coordenador"]}
ALUNO_B = {"nome": "Bruno Batista", "email": "bruno@exemplo.com", "matricula": "24150002", "curso_id": 3}


def _enviado(c, cliente=None, **extra) -> dict:
    """Rascunho, aceite da orientadora e submissão: o cadastro fica EM_ANALISE."""
    cliente = cliente or c["aluno"]
    corpo = {"titulo": "Detecção de fraudes com aprendizado de máquina", "resumo": "Um resumo curto.",
             "palavras_chave": ["IA", "fraude"], "area_id": c["area"]["id"], "modalidade": "MONOGRAFIA",
             "orientador_id": c["orientador"]["id"], **extra}
    tcc = cliente.post("/api/v1/tccs", json=corpo).json()
    _aceitar(c)
    r = cliente.post(f"/api/v1/tccs/{tcc['id']}/submissao")
    assert r.status_code == 200
    return r.json()["tcc"]


def _segundo_aluno(c, coord, caixa):
    """Bruno, de Sistemas de Informação, na mesma turma."""
    aluno = coord.post("/api/v1/alunos", json=ALUNO_B).json()
    assert coord.post(f"/api/v1/turmas/{c['turma']['id']}/alunos", json={"aluno_id": aluno["id"]}).status_code == 201
    return ativar(caixa, ALUNO_B["email"])


def _decidir(cliente, tcc_id, resultado, parecer=""):
    return cliente.post(f"/api/v1/cadastros/{tcc_id}/decisao", json={"resultado": resultado, "parecer": parecer})


# ---------------------------------------------------------------- RBN04.01 · fila e filtros (DS-FL02-A)


def test_ct_04_01_01_fila_lista_protocolo_aluno_titulo_e_data(cenario, coord, caixa):
    """CT-04.01-01 (CA-01): a fila mostra protocolo, aluno, título, data e há quantos dias aguarda."""
    assert coord.get("/api/v1/cadastros?situacao=EM_ANALISE").json() == []  # A1: fila vazia
    _rascunho(cenario)  # rascunho nunca enviado não aparece
    primeiro = cenario["aluno"].get("/api/v1/tccs").json()[0]
    _aceitar(cenario)
    cenario["aluno"].post(f"/api/v1/tccs/{primeiro['id']}/submissao")
    bruno = _segundo_aluno(cenario, coord, caixa)
    segundo = _enviado(cenario, bruno, titulo="Segundo trabalho")
    fila = coord.get("/api/v1/cadastros?situacao=EM_ANALISE").json()
    assert [f["id"] for f in fila] == [primeiro["id"], segundo["id"]]  # do mais antigo para o mais recente
    item = fila[0]
    assert item["protocolo"] == f"TCC-2026-{primeiro['id']:05d}"
    assert item["aluno"]["nome"] == "Ana Ribeiro" and item["titulo"].startswith("Detecção")
    assert item["submetido_em"] and item["dias_aguardando"] == 0
    assert item["curso"]["sigla"] == "EC" and item["etapa"] == "TCC1" and item["periodo"] == "2026/2"
    assert item["situacao"] == "EM_ANALISE" and item["decisao"] is None


def test_ct_04_01_02_filtro_por_situacao(cenario, coord, caixa):
    """CT-04.01-02 (CA-02): cadastros em 4 situações; filtrar por uma só traz essa."""
    tccs = [_enviado(cenario)]
    bruno = _segundo_aluno(cenario, coord, caixa)
    tccs.append(_enviado(cenario, bruno))
    _decidir(coord, tccs[0]["id"], "REPROVADO", "Escopo fora das áreas do NUCOMP")
    so_reprovados = coord.get("/api/v1/cadastros?situacao=REPROVADO").json()
    assert [t["id"] for t in so_reprovados] == [tccs[0]["id"]]
    assert so_reprovados[0]["decisao"]["parecer"] == "Escopo fora das áreas do NUCOMP"
    ja_analisados = coord.get("/api/v1/cadastros?situacao=APROVADO,DEVOLVIDO,REPROVADO").json()  # passo 14
    assert [t["id"] for t in ja_analisados] == [tccs[0]["id"]]
    assert len(coord.get("/api/v1/cadastros").json()) == 2  # sem filtro: todas as situações da análise
    assert coord.get("/api/v1/cadastros?situacao=QUALQUER").status_code == 400


def test_ct_04_01_03_e_04_01_04_filtros_por_curso_e_periodo(cenario, coord, caixa, db):
    """CT-04.01-03 (CA-03) e CT-04.01-04 (CA-04): curso e período combinados; combinação sem resultado."""
    ana = _enviado(cenario)
    bruno = _segundo_aluno(cenario, coord, caixa)
    do_bruno = _enviado(cenario, bruno)
    # o cadastro do Bruno passa para outro período letivo
    outro = PeriodoLetivo(codigo="2026/1", inicio=date(2026, 2, 1), fim=date(2026, 6, 30))
    db.add(outro)
    db.flush()
    db.get(Tcc, do_bruno["id"]).periodo_id = outro.id
    db.commit()
    assert [t["id"] for t in coord.get("/api/v1/cadastros?curso=1&periodo=2026/2").json()] == [ana["id"]]
    assert [t["id"] for t in coord.get("/api/v1/cadastros?curso=3").json()] == [do_bruno["id"]]
    assert coord.get("/api/v1/cadastros?curso=3&periodo=2026/2").json() == []  # interseção vazia
    assert coord.get("/api/v1/cadastros?periodo=2025/1").json() == []  # CT-04.01-04
    assert len(coord.get("/api/v1/cadastros").json()) == 2  # limpar os filtros restaura


def test_ct_04_01_05_decisao_aparece_atualizada_ao_recarregar(cenario, coord, caixa):
    """CT-04.01-05 (CA-05): decisão de outra sessão aparece na lista recarregada."""
    tcc = _enviado(cenario)
    coord.post("/api/v1/docentes", json=COORD2)
    cecilia = ativar(caixa, COORD2["email"])
    assert _decidir(cecilia, tcc["id"], "APROVADO").status_code == 200
    assert coord.get("/api/v1/cadastros?situacao=EM_ANALISE").json() == []
    [item] = coord.get("/api/v1/cadastros").json()
    assert item["situacao"] == "APROVADO" and item["decisao"]["coordenador"]["nome"] == COORD2["nome"]


def test_ct_04_01_06_outros_perfis_recebem_403_sem_dados(cenario, caixa):
    """CT-04.01-06 (CA-06, RN06): aluno, orientador, professor e banca não abrem a fila nem o cadastro."""
    tcc = _enviado(cenario)
    paulo = ativar(caixa, PROFESSOR["email"])
    for cliente in (cenario["aluno"], cenario["olga"], paulo):
        for rota in ("/api/v1/cadastros", f"/api/v1/cadastros/{tcc['id']}", f"/api/v1/cadastros/{tcc['id']}/documento"):
            r = cliente.get(rota)
            assert r.status_code == 403 and set(r.json()) == {"detail"}


def test_ct_04_01_07_coordenador_nao_ve_cadastro_de_outro_nucleo(cenario, coord, db):
    """CT-04.01-07 (CA-01, RN07): o curso passa para outro núcleo e o cadastro some para esta coordenação."""
    tcc = _enviado(cenario)
    outro = Nucleo(sigla="NUOUTRO", nome="Outro núcleo")
    db.add(outro)
    db.flush()
    db.get(Curso, 1).nucleo_id = outro.id
    db.commit()
    assert coord.get("/api/v1/cadastros").json() == []
    assert coord.get(f"/api/v1/cadastros/{tcc['id']}").status_code == 404
    assert _decidir(coord, tcc["id"], "APROVADO").status_code == 404


# ---------------------------------------------------------------- DS-FL02-A · examinar um cadastro


def test_ds_fl02a_abrir_cadastro_em_analise_traz_dados_e_pdf_vazio(cenario, coord):
    """Passos 7 a 10: dados, PDF (vazio enquanto o aluno não enviar) e nenhuma decisão ainda."""
    tcc = _enviado(cenario)
    corpo = coord.get(f"/api/v1/cadastros/{tcc['id']}").json()
    assert corpo["tcc"]["situacao"] == "EM_ANALISE" and corpo["tcc"]["orientador"]["professor"]["nome"] == ORIENTADOR["nome"]
    assert corpo["tcc"]["resumo"] and corpo["tcc"]["modalidade"] == "MONOGRAFIA"
    assert corpo["documento"] is None and corpo["decisao"] is None
    r = coord.get(f"/api/v1/cadastros/{tcc['id']}/documento")  # passo 12
    assert r.status_code == 404 and r.json()["detail"] == "Nenhum PDF enviado."


def test_ds_fl02a_cadastro_ja_decidido_traz_a_decisao(cenario, coord):
    tcc = _enviado(cenario)
    _decidir(coord, tcc["id"], "DEVOLVIDO", "Título do PDF difere do cadastro")
    corpo = coord.get(f"/api/v1/cadastros/{tcc['id']}").json()
    assert corpo["tcc"]["situacao"] == "DEVOLVIDO"
    assert corpo["decisao"]["resultado"] == "DEVOLVIDO" and corpo["decisao"]["parecer"].startswith("Título")


def test_ds_fl02a_rascunho_nao_chega_a_coordenacao(cenario, coord):
    tcc = _rascunho(cenario).json()
    assert coord.get(f"/api/v1/cadastros/{tcc['id']}").status_code == 404
    assert _decidir(coord, tcc["id"], "APROVADO").status_code == 404


# ---------------------------------------------------------------- RBN04.02 · aprovar (DS-FL02)


def test_ct_04_02_01_aprovar_com_parecer_mantem_protocolo(cenario, coord, caixa, db):
    """CT-04.02-01 (CA-01) e passos 7 a 12: situação, data, responsável, protocolo e aviso a aluno e orientador."""
    tcc = _enviado(cenario)
    caixa.clear()
    r = _decidir(coord, tcc["id"], "APROVADO", "Cadastro conforme")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["resultado"] == "APROVADO" and corpo["parecer"] == "Cadastro conforme"
    assert corpo["coordenador"]["nome"] == "Coordenadora Teste" and corpo["decidido_em"].endswith("Z")
    registro = db.get(Tcc, tcc["id"])
    assert registro.situacao == "APROVADO" and registro.protocolo == tcc["protocolo"]
    [analise] = db.scalars(select(AnaliseCadastro))
    assert (analise.resultado, analise.parecer, analise.coordenador_id) == ("APROVADO", "Cadastro conforme", 1)
    assert [h.situacao_nova for h in registro.historico][-1] == "APROVADO"
    avisos = db.scalars(select(NotificacaoEmail).where(NotificacaoEmail.tipo == "RESULTADO_ANALISE")).all()
    assert {n.destinatario for n in avisos} == {"ana@uea.edu.br", ORIENTADOR["email"]}
    assert {m["para"] for m in caixa} == {"ana@uea.edu.br", ORIENTADOR["email"]}
    assert all("aprovado" in m["assunto"] and tcc["protocolo"] in m["assunto"] for m in caixa)


def test_aprovar_sem_parecer_e_permitido(cenario, coord):
    """Parecer opcional para aprovar (TEL07: "Opcional para aprovar")."""
    tcc = _enviado(cenario)
    r = _decidir(coord, tcc["id"], "APROVADO")
    assert r.status_code == 200 and r.json()["parecer"] == ""


def test_ct_04_02_02_nao_aprova_cadastro_ja_reprovado(cenario, coord, db):
    """CT-04.02-02 (CA-02): bloqueio com mensagem e situação inalterada."""
    tcc = _enviado(cenario)
    _decidir(coord, tcc["id"], "REPROVADO", "Escopo fora das áreas do NUCOMP")
    r = _decidir(coord, tcc["id"], "APROVADO")
    assert r.status_code == 409
    assert r.json()["situacao"] == "REPROVADO" and r.json()["decisao"]["resultado"] == "REPROVADO"
    assert db.get(Tcc, tcc["id"]).situacao == "REPROVADO"
    assert len(db.scalars(select(AnaliseCadastro)).all()) == 1


def test_ct_04_02_03_aprovar_nao_muda_situacao_editorial(cenario, coord, db):
    """CT-04.02-03 (CA-03, RN10): artigo "submetido" continua "submetido"."""
    artigo = {"tipo_veiculo": "PERIODICO", "veiculo": "Revista de Computação", "situacao": "SUBMETIDO"}
    tcc = _enviado(cenario, modalidade="ARTIGO", artigo=artigo)
    _decidir(coord, tcc["id"], "APROVADO", "Cadastro conforme")
    pub = db.scalar(select(PublicacaoArtigo))
    assert pub.situacao_atual == "SUBMETIDO"
    assert len(db.scalars(select(HistoricoPublicacao)).all()) == 1  # nenhuma mudança editorial registrada


@pytest.mark.parametrize("resultado", ["APROVADO", "DEVOLVIDO", "REPROVADO"])
def test_ct_04_02_04_e_04_03_06_e_04_04_06_so_a_coordenacao_decide(cenario, caixa, db, resultado):
    """CT-04.02-04, CT-04.03-06, CT-04.04-06 (RN06): 403 para aluno, orientador e professor; nada muda."""
    tcc = _enviado(cenario)
    paulo = ativar(caixa, PROFESSOR["email"])
    for cliente in (cenario["aluno"], cenario["olga"], paulo):
        r = _decidir(cliente, tcc["id"], resultado, "Parecer qualquer com texto")
        assert r.status_code == 403
    assert db.get(Tcc, tcc["id"]).situacao == "EM_ANALISE"
    assert db.scalars(select(AnaliseCadastro)).all() == []


def test_ct_04_02_05_segunda_decisao_concorrente_e_rejeitada(cenario, coord, caixa, db):
    """CT-04.02-05 (CA-05): dois coordenadores com a tela aberta; o segundo recebe 409 e um único registro fica."""
    tcc = _enviado(cenario)
    coord.post("/api/v1/docentes", json=COORD2)
    cecilia = ativar(caixa, COORD2["email"])
    assert coord.get(f"/api/v1/cadastros/{tcc['id']}").json()["decisao"] is None  # as duas telas abertas
    assert cecilia.get(f"/api/v1/cadastros/{tcc['id']}").json()["decisao"] is None
    assert _decidir(coord, tcc["id"], "APROVADO", "Cadastro conforme").status_code == 200
    r = _decidir(cecilia, tcc["id"], "DEVOLVIDO", "Corrigir o resumo do trabalho")
    assert r.status_code == 409 and r.json()["situacao"] == "APROVADO"
    assert r.json()["decisao"]["coordenador"]["nome"] == "Coordenadora Teste"
    assert len(db.scalars(select(AnaliseCadastro)).all()) == 1
    assert db.get(Tcc, tcc["id"]).situacao == "APROVADO"


@pytest.mark.parametrize("resultado", ["APROVADO", "DEVOLVIDO", "REPROVADO"])
def test_ct_04_02_06_e_04_03_07_e_04_04_08_auditoria(cenario, coord, db, resultado):
    """CT-04.02-06, CT-04.03-07, CT-04.04-08 (RNF03): usuário, data/hora, campo, anterior e novo."""
    tcc = _enviado(cenario)
    _decidir(coord, tcc["id"], resultado, "Parecer da coordenação")
    log = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "decidir_cadastro"))
    assert (log.usuario_id, log.entidade, log.entidade_id) == (1, "tcc", tcc["id"])
    assert (log.campo, log.valor_anterior, log.valor_novo) == ("situacao", "EM_ANALISE", resultado)
    assert log.criado_em is not None


def test_ct_04_02_07_aprovacao_persiste_e_volta_na_lista(cenario, coord):
    """CT-04.02-07: a decisão gravada volta igual na lista e no detalhe."""
    tcc = _enviado(cenario)
    decisao = _decidir(coord, tcc["id"], "APROVADO", "Cadastro conforme").json()
    [item] = coord.get("/api/v1/cadastros?situacao=APROVADO,DEVOLVIDO,REPROVADO").json()
    assert item["decisao"] == decisao
    assert coord.get(f"/api/v1/cadastros/{tcc['id']}").json()["decisao"] == decisao


# ---------------------------------------------------------------- RBN04.03 · devolver


def test_ct_04_03_01_devolver_com_justificativa(cenario, coord, db):
    """CT-04.03-01 (CA-01)."""
    tcc = _enviado(cenario)
    r = _decidir(coord, tcc["id"], "DEVOLVIDO", "Título do PDF difere do cadastro")
    assert r.status_code == 200
    registro = db.get(Tcc, tcc["id"])
    assert registro.situacao == "DEVOLVIDO" and registro.protocolo == tcc["protocolo"]
    assert registro.analises[-1].parecer == "Título do PDF difere do cadastro"


@pytest.mark.parametrize("resultado", ["DEVOLVIDO", "REPROVADO"])
@pytest.mark.parametrize("parecer", ["", "    ", "Curto", "  123456789  "])
def test_ct_04_03_02_03_e_04_04_02_03_parecer_obrigatorio(cenario, coord, db, resultado, parecer):
    """CT-04.03-02, CT-04.03-03, CT-04.04-02, CT-04.04-03 (E1): 422 com o campo parecer; continua em análise.

    Vazio, só espaços ou com menos de 10 caracteres (sem contar os espaços das pontas), igual à TEL07.
    """
    tcc = _enviado(cenario)
    r = _decidir(coord, tcc["id"], resultado, parecer)
    assert r.status_code == 422 and "parecer" in r.json()["campos"]
    assert db.get(Tcc, tcc["id"]).situacao == "EM_ANALISE"
    assert db.scalars(select(AnaliseCadastro)).all() == []


def test_parecer_acima_de_1000_caracteres_e_recusado(cenario, coord):
    tcc = _enviado(cenario)
    r = _decidir(coord, tcc["id"], "DEVOLVIDO", "x" * 1001)
    assert r.status_code == 400 and "parecer" in r.json()["campos"]


def test_ct_04_03_04_aluno_corrige_e_reenvia_com_o_mesmo_protocolo(cenario, coord):
    """CT-04.03-04 (CA-03, RN10): volta a EM_ANALISE, mesmo protocolo, a devolução continua no histórico."""
    tcc = _enviado(cenario)
    _decidir(coord, tcc["id"], "DEVOLVIDO", "Título do PDF difere do cadastro")
    corpo = {"titulo": "Título corrigido", "resumo": "Resumo corrigido.", "palavras_chave": ["IA"],
             "area_id": cenario["area"]["id"], "modalidade": "MONOGRAFIA",
             "orientador_id": cenario["orientador"]["id"]}
    assert cenario["aluno"].put(f"/api/v1/tccs/{tcc['id']}", json=corpo).status_code == 200
    r = cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao").json()
    assert r["protocolo"] == tcc["protocolo"] and r["situacao"] == "EM_ANALISE"
    detalhe = cenario["aluno"].get(f"/api/v1/tccs/{tcc['id']}").json()
    assert [d["parecer"] for d in detalhe["decisoes"]] == ["Título do PDF difere do cadastro"]
    assert [h["situacao_nova"] for h in detalhe["historico"]] == ["RASCUNHO", "EM_ANALISE", "DEVOLVIDO", "EM_ANALISE"]
    assert [t["id"] for t in coord.get("/api/v1/cadastros?situacao=EM_ANALISE").json()] == [tcc["id"]]


def test_ct_04_03_05_nao_devolve_cadastro_aprovado(cenario, coord):
    """CT-04.03-05 (CA-04)."""
    tcc = _enviado(cenario)
    _decidir(coord, tcc["id"], "APROVADO")
    r = _decidir(coord, tcc["id"], "DEVOLVIDO", "Corrigir o resumo do trabalho")
    assert r.status_code == 409 and r.json()["detail"]


def test_ct_04_03_08_aluno_ve_a_devolucao_e_a_justificativa(cenario, coord):
    """CT-04.03-08 e CT-04.05-02 (CA-02): o aluno abre o TCC e vê a devolução com o parecer."""
    tcc = _enviado(cenario)
    _decidir(coord, tcc["id"], "DEVOLVIDO", "Título do PDF difere do cadastro")
    detalhe = cenario["aluno"].get(f"/api/v1/tccs/{tcc['id']}").json()
    assert detalhe["situacao"] == "DEVOLVIDO"
    [decisao] = detalhe["decisoes"]
    assert decisao["resultado"] == "DEVOLVIDO" and decisao["parecer"] == "Título do PDF difere do cadastro"


# ---------------------------------------------------------------- RBN04.04 · reprovar


def test_ct_04_04_01_reprovar_com_justificativa_sem_excluir_dados(cenario, coord, db):
    """CT-04.04-01 (CA-01)."""
    tcc = _enviado(cenario)
    r = _decidir(coord, tcc["id"], "REPROVADO", "Escopo fora das áreas do NUCOMP")
    assert r.status_code == 200
    registro = db.get(Tcc, tcc["id"])
    assert registro.situacao == "REPROVADO" and registro.protocolo == tcc["protocolo"]
    assert registro.titulo == tcc["titulo"] and [p.palavra for p in registro.palavras] == ["IA", "fraude"]
    assert registro.analises[-1].coordenador_id == 1 and registro.analises[-1].decidido_em is not None


def test_ct_04_04_04_reprovado_continua_consultavel_e_nao_e_editado(cenario, coord):
    """CT-04.04-04 (CA-03): o histórico mantém a reprovação e o protocolo.

    O DS-FL02-B manda o aluno com cadastro reprovado procurar a Coordenação; ele não edita nem reenvia
    o cadastro reprovado pela tela (a edição vale só para rascunho e devolvido, DS-FL01-B).
    """
    tcc = _enviado(cenario)
    _decidir(coord, tcc["id"], "REPROVADO", "Escopo fora das áreas do NUCOMP")
    detalhe = cenario["aluno"].get(f"/api/v1/tccs/{tcc['id']}").json()
    assert detalhe["protocolo"] == tcc["protocolo"] and detalhe["decisoes"][-1]["resultado"] == "REPROVADO"
    assert cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao").status_code == 409


def test_ct_04_04_05_nao_reprova_cadastro_aprovado(cenario, coord):
    """CT-04.04-05 (CA-04)."""
    tcc = _enviado(cenario)
    _decidir(coord, tcc["id"], "APROVADO")
    assert _decidir(coord, tcc["id"], "REPROVADO", "Escopo fora das áreas do NUCOMP").status_code == 409


def test_ct_04_04_07_reprovar_nao_muda_situacao_editorial(cenario, coord, db):
    """CT-04.04-07 (CA-06, RN10): artigo "aceito" continua "aceito"."""
    artigo = {"tipo_veiculo": "CONGRESSO", "veiculo": "Simpósio de Computação", "situacao": "ACEITO"}
    tcc = _enviado(cenario, modalidade="ARTIGO", artigo=artigo)
    _decidir(coord, tcc["id"], "REPROVADO", "Escopo fora das áreas do NUCOMP")
    assert db.scalar(select(PublicacaoArtigo)).situacao_atual == "ACEITO"


def test_ct_04_04_09_reprovacao_persiste_avisa_e_audita(cenario, coord, caixa, db):
    """CT-04.04-09: persistência, notificação e auditoria."""
    tcc = _enviado(cenario)
    caixa.clear()
    _decidir(coord, tcc["id"], "REPROVADO", "Escopo fora das áreas do NUCOMP")
    assert db.get(Tcc, tcc["id"]).situacao == "REPROVADO"
    assert {m["para"] for m in caixa} == {"ana@uea.edu.br", ORIENTADOR["email"]}
    assert db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "decidir_cadastro")) is not None


def test_ds_fl02_falha_de_envio_fica_registrada_e_a_decisao_vale(cenario, coord, db, monkeypatch):
    """Passo 16: o e-mail que falha fica como falha; a decisão continua valendo."""
    from app.services import email

    tcc = _enviado(cenario)

    def falhar(*_):
        raise OSError("servidor de e-mail fora do ar")

    monkeypatch.setattr(email, "entregar", falhar)
    assert _decidir(coord, tcc["id"], "APROVADO").status_code == 200
    db.expire_all()
    avisos = db.scalars(select(NotificacaoEmail).where(NotificacaoEmail.tipo == "RESULTADO_ANALISE")).all()
    assert avisos and all(n.status == "falha" for n in avisos)
    assert db.get(Tcc, tcc["id"]).situacao == "APROVADO"


# ---------------------------------------------------------------- RBN04.05 · resultado ao aluno e ao orientador (DS-FL02-B)


def test_ct_04_05_01_aluno_ve_aprovacao_e_parecer(cenario, coord):
    """CT-04.05-01 (CA-01) e CT-04.05-04 (CA-04): visível logo depois da decisão."""
    tcc = _enviado(cenario)
    _decidir(coord, tcc["id"], "APROVADO", "Cadastro conforme")
    [na_lista] = cenario["aluno"].get("/api/v1/tccs").json()  # passo 2: selo com a situação nova
    assert na_lista["situacao"] == "APROVADO"
    detalhe = cenario["aluno"].get(f"/api/v1/tccs/{tcc['id']}").json()
    assert detalhe["situacao"] == "APROVADO" and detalhe["decisoes"][-1]["parecer"] == "Cadastro conforme"


def test_ct_04_05_03_orientador_ve_reprovacao_e_justificativa(cenario, coord):
    """CT-04.05-03 (CA-03)."""
    tcc = _enviado(cenario)
    _decidir(coord, tcc["id"], "REPROVADO", "Escopo fora das áreas do NUCOMP")
    detalhe = cenario["olga"].get(f"/api/v1/tccs/{tcc['id']}").json()
    assert detalhe["situacao"] == "REPROVADO"
    assert detalhe["decisoes"][-1]["parecer"] == "Escopo fora das áreas do NUCOMP"


def test_ct_04_05_05_aluno_sem_vinculo_nao_ve_o_resultado(cenario, coord, caixa):
    """CT-04.05-05 (CA-05, RN07): o aluno B não abre o TCC do aluno A nem vê o parecer.

    A API responde 404, que não revela se o cadastro existe (mesmo padrão do RBN03.05 e do RBN05.01).
    """
    tcc = _enviado(cenario)
    _decidir(coord, tcc["id"], "DEVOLVIDO", "Título do PDF difere do cadastro")
    bruno = _segundo_aluno(cenario, coord, caixa)
    r = bruno.get(f"/api/v1/tccs/{tcc['id']}")
    assert r.status_code == 404 and "Título do PDF" not in r.text
    assert cenario["otto"].get(f"/api/v1/tccs/{tcc['id']}").status_code == 404  # orientador sem vínculo


def test_ct_04_05_06_situacao_academica_e_editorial_separadas(cenario, coord):
    """CT-04.05-06 (CA-06, RN10)."""
    artigo = {"tipo_veiculo": "PERIODICO", "veiculo": "Revista de Computação", "situacao": "PUBLICADO",
              "doi": "10.1000/xyz"}
    tcc = _enviado(cenario, modalidade="ARTIGO", artigo=artigo)
    _decidir(coord, tcc["id"], "APROVADO")
    detalhe = cenario["aluno"].get(f"/api/v1/tccs/{tcc['id']}").json()
    assert detalhe["situacao"] == "APROVADO" and detalhe["artigo"]["situacao"] == "PUBLICADO"


def test_ct_04_05_07_devolvido_e_depois_aprovado_em_ordem(cenario, coord):
    """CT-04.05-07 (CA-07): duas decisões em ordem cronológica, com autor e data."""
    tcc = _enviado(cenario)
    _decidir(coord, tcc["id"], "DEVOLVIDO", "Título do PDF difere do cadastro")
    corpo = {"titulo": "Título corrigido", "resumo": "Resumo corrigido.", "palavras_chave": ["IA"],
             "area_id": cenario["area"]["id"], "modalidade": "MONOGRAFIA",
             "orientador_id": cenario["orientador"]["id"]}
    cenario["aluno"].put(f"/api/v1/tccs/{tcc['id']}", json=corpo)
    cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao")
    _decidir(coord, tcc["id"], "APROVADO", "Cadastro conforme")
    decisoes = cenario["aluno"].get(f"/api/v1/tccs/{tcc['id']}").json()["decisoes"]
    assert [d["resultado"] for d in decisoes] == ["DEVOLVIDO", "APROVADO"]
    assert decisoes[0]["decidido_em"] <= decisoes[1]["decidido_em"]
    assert all(d["coordenador"]["nome"] == "Coordenadora Teste" for d in decisoes)
