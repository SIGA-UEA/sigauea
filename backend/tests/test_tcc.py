"""Sprint S03 · cadastro de TCC de ponta a ponta.

Cada teste cita o requisito (RBN/RN) ou o passo do diagrama de sequência (DS-FL01, DS-FL03)
que confere. O cenário é montado pela própria API, como a coordenação faria.
"""

import pytest
from sqlalchemy import select

from app.models import HistoricoSituacao, LogAuditoria, MatriculaTurma, NotificacaoEmail, Tcc
from tests.conftest import ALUNO, ativar

ORIENTADOR = {"nome": "Olga Orientadora", "email": "olga@exemplo.com", "cargo": "orientador",
              "curso_id": 1, "perfis": ["orientador"]}
PROFESSOR = {"nome": "Paulo Professor", "email": "paulo@exemplo.com", "cargo": "professor",
             "curso_id": 1, "perfis": ["professor_disciplina"]}
OUTRO_ORIENTADOR = {**ORIENTADOR, "nome": "Otto Orientador", "email": "otto@exemplo.com"}


@pytest.fixture
def cenario(coord, caixa):
    """Período 2026/2 em curso, turma TCC1 com professor, orientadora e aluna matriculada."""
    periodo = coord.post("/api/v1/periodos", json={"codigo": "2026/2", "inicio": "2026-08-01",
                                                   "fim": "2026-12-20"}).json()
    professor = coord.post("/api/v1/docentes", json=PROFESSOR).json()
    orientador = coord.post("/api/v1/docentes", json=ORIENTADOR).json()
    outro = coord.post("/api/v1/docentes", json=OUTRO_ORIENTADOR).json()
    aluno = coord.post("/api/v1/alunos", json=ALUNO).json()
    turma = coord.post("/api/v1/turmas", json={"disciplina": "TCC1", "curso_id": 1,
                                               "periodo_id": periodo["id"], "professor_id": professor["id"]}).json()
    r = coord.post(f"/api/v1/turmas/{turma['id']}/alunos", json={"aluno_id": aluno["id"]})
    assert r.status_code == 201
    area = coord.get("/api/v1/areas").json()[0]
    return {
        "periodo": periodo, "turma": turma, "area": area, "orientador": orientador, "outro": outro,
        "aluno": ativar(caixa, ALUNO["email"]), "olga": ativar(caixa, ORIENTADOR["email"]),
        "otto": ativar(caixa, OUTRO_ORIENTADOR["email"]),
    }


def _rascunho(c, **extra):
    corpo = {"titulo": "Detecção de fraudes com aprendizado de máquina", "resumo": "Um resumo curto.",
             "palavras_chave": ["IA", "fraude"], "area_id": c["area"]["id"], "modalidade": "MONOGRAFIA",
             "orientador_id": c["orientador"]["id"], **extra}
    return c["aluno"].post("/api/v1/tccs", json=corpo)


def _aceitar(c, quem="olga"):
    pendente = c[quem].get("/api/v1/orientacoes?status=PENDENTE").json()[0]
    r = c[quem].post(f"/api/v1/orientacoes/{pendente['id']}/resposta", json={"decisao": "ACEITAR"})
    assert r.status_code == 200
    return pendente


# ---------------------------------------------------------------- turmas (RBN08)


def test_rbn0801_turma_criada_com_codigo_do_curso_e_periodo(cenario):
    assert cenario["turma"]["codigo"] == "TCC1-EC-2026/2-1"
    assert [a["matricula"] for a in cenario["turma"]["alunos"]] == []  # a resposta da criação veio antes


def test_ct_01_03_04_aluno_de_outro_curso_entra_e_mantem_o_curso(coord, cenario, caixa):
    """CT-01.03-04."""
    outro = coord.post("/api/v1/alunos", json={"nome": "Saulo SI", "email": "saulo@exemplo.com",
                                               "matricula": "24150099", "curso_id": 3}).json()
    turma = coord.post(f"/api/v1/turmas/{cenario['turma']['id']}/alunos", json={"aluno_id": outro["id"]}).json()
    saulo = next(a for a in turma["alunos"] if a["aluno"]["id"] == outro["id"])
    assert saulo["curso"]["sigla"] == "SI" and turma["curso"]["sigla"] == "EC"
    repetido = coord.post(f"/api/v1/turmas/{cenario['turma']['id']}/alunos", json={"aluno_id": outro["id"]})
    assert repetido.status_code == 409


def test_rbn0801_so_a_coordenacao_cria_turma(cenario):
    r = cenario["olga"].post("/api/v1/turmas", json={"disciplina": "TCC1", "curso_id": 1, "periodo_id": 1,
                                                     "professor_id": 1})
    assert r.status_code == 403


# ---------------------------------------------------------------- Minhas turmas (professor e aluno)


def test_minhas_turmas_do_professor_com_contagem_de_alunos_e_tccs(cenario, caixa):
    paulo = ativar(caixa, PROFESSOR["email"])
    [cartao] = paulo.get("/api/v1/turmas/minhas").json()
    assert cartao["codigo"] == "TCC1-EC-2026/2-1" and cartao["periodo"] == "2026/2"
    assert (cartao["alunos"], cartao["com_tcc"], cartao["pendentes"]) == (1, 0, 0)
    assert cartao["minha_matricula"] is None and cartao["meu_tcc"] is None

    tcc = _rascunho(cenario).json()
    assert paulo.get("/api/v1/turmas/minhas").json()[0]["com_tcc"] == 1
    turma = paulo.get(f"/api/v1/turmas/{cartao['id']}").json()
    [aluna] = turma["alunos"]
    assert aluna["tcc"]["id"] == tcc["id"] and aluna["tcc"]["situacao"] == "RASCUNHO"
    assert aluna["tcc"]["orientador"]["nome"] == "Olga Orientadora"
    assert aluna["tcc"]["orientacao"] == "PENDENTE"


def test_minhas_turmas_so_mostra_ao_docente_as_turmas_que_ele_conduz(cenario):
    _rascunho(cenario)
    # a Olga não conduz a turma, então não a vê em Minhas turmas
    assert cenario["olga"].get("/api/v1/turmas/minhas").json() == []


def test_minhas_turmas_do_aluno_mostra_matricula_e_o_proprio_tcc(cenario):
    [cartao] = cenario["aluno"].get("/api/v1/turmas/minhas").json()
    assert cartao["minha_matricula"] == "MATRICULADO" and cartao["meu_tcc"] is None
    assert cartao["professor"]["nome"] == "Paulo Professor"
    tcc = _rascunho(cenario).json()
    cartao = cenario["aluno"].get("/api/v1/turmas/minhas").json()[0]
    assert cartao["meu_tcc"]["id"] == tcc["id"]


def test_rn07_aluno_e_outro_docente_nao_abrem_a_turma(cenario):
    turma_id = cenario["turma"]["id"]
    assert cenario["aluno"].get(f"/api/v1/turmas/{turma_id}").status_code == 404  # não vê colegas
    assert cenario["olga"].get(f"/api/v1/turmas/{turma_id}").status_code == 404


# ---------------------------------------------------------------- DS-FL01-A · abrir o formulário


def test_ct_03_01_01_formulario_traz_turma_orientadores_e_areas(cenario):
    """CT-03.01-01."""
    f = cenario["aluno"].get("/api/v1/tccs/formulario").json()
    assert f["turma"]["disciplina"] == "TCC1" and f["situacao_matricula"] == "MATRICULADO"
    assert f["tcc"] is None
    assert {o["nome"] for o in f["orientadores"]} == {"Olga Orientadora", "Otto Orientador"}
    assert f["areas"]


def test_rn05_aluno_sem_matricula_nao_abre_nem_salva(coord, caixa, cenario):
    coord.post("/api/v1/alunos", json={"nome": "Sem Turma", "email": "semturma@exemplo.com",
                                       "matricula": "24150077", "curso_id": 1})
    sem = ativar(caixa, "semturma@exemplo.com")
    assert sem.get("/api/v1/tccs/formulario").status_code == 403
    corpo = {"titulo": "Título", "area_id": cenario["area"]["id"], "modalidade": "MONOGRAFIA"}
    r = sem.post("/api/v1/tccs", json=corpo)
    assert r.status_code == 403 and r.json()["motivo"] == "sem_matricula"


# ---------------------------------------------------------------- DS-FL01-B · rascunho


def test_ct_03_01_04_e_03_04_02_e_06_01_01_rascunho_sem_protocolo_e_vinculo_pendente(cenario, caixa, db):
    """CT-03.01-04, CT-03.01-05, CT-03.04-02, CT-06.01-01."""
    r = _rascunho(cenario)
    assert r.status_code == 201
    tcc = r.json()
    assert tcc["situacao"] == "RASCUNHO" and tcc["protocolo"] is None
    assert tcc["etapa"] == "TCC1"  # vem da turma
    assert tcc["orientador"]["status"] == "PENDENTE"
    assert "Aguarde o orientador aceitar a orientação." in tcc["pendencias"]
    # RBN03.06: o orientador recebe e-mail com o pedido
    assert any(m["para"] == ORIENTADOR["email"] and "orientação" in m["assunto"] for m in caixa)
    aviso = db.scalar(select(NotificacaoEmail).where(NotificacaoEmail.tipo == "VINCULO_ORIENTACAO"))
    assert (aviso.entidade, aviso.entidade_id) == ("tcc", tcc["id"])


def test_ct_03_04_04_um_cadastro_por_periodo(cenario):
    """CT-03.04-04."""
    assert _rascunho(cenario).status_code == 201
    r = _rascunho(cenario, titulo="Outro trabalho")
    assert r.status_code == 409 and r.json()["motivo"] == "duplicado"


def test_ct_03_01_02_e_03_01_03_resumo_ate_500_palavras_e_ate_10_palavras_chave(cenario):
    """CT-03.01-02, CT-03.01-03."""
    r = _rascunho(cenario, resumo="palavra " * 501)
    assert r.status_code == 400 and "500 palavras" in r.json()["campos"]["resumo"]
    r = _rascunho(cenario, palavras_chave=[f"p{i}" for i in range(11)])
    assert r.status_code == 400 and "10 palavras-chave" in r.json()["campos"]["palavras_chave"]


def test_ds_fl01b_e2_orientador_nao_elegivel(cenario, coord):
    professor_id = cenario["turma"]["professor"]["id"]  # tem perfil de professor, não de orientador
    r = _rascunho(cenario, orientador_id=professor_id)
    assert r.status_code == 422 and "orientador_id" in r.json()["campos"]
    r = _rascunho(cenario, coorientador_id=cenario["orientador"]["id"])
    assert r.status_code == 422 and "coorientador_id" in r.json()["campos"]


def test_ct_03_02_03_e_03_02_04_artigo_publicado_exige_doi(cenario):
    """CT-03.02-03, CT-03.02-04."""
    artigo = {"tipo_veiculo": "PERIODICO", "veiculo": "Revista Brasileira de Computação", "situacao": "PUBLICADO"}
    r = _rascunho(cenario, modalidade="ARTIGO", artigo=artigo)
    assert r.status_code == 400 and "doi" in r.json()["campos"]
    r = _rascunho(cenario, modalidade="ARTIGO", artigo={**artigo, "doi": "10.1000/xyz123"})
    assert r.status_code == 201
    assert r.json()["artigo"]["doi"] == "10.1000/xyz123"


def test_ct_03_01_08_editar_rascunho_audita_cada_campo(cenario, db):
    """CT-03.01-08."""
    tcc = _rascunho(cenario).json()
    corpo = {"titulo": "Novo título do trabalho", "resumo": "Resumo novo.", "palavras_chave": ["IA"],
             "area_id": cenario["area"]["id"], "modalidade": "MONOGRAFIA",
             "orientador_id": cenario["orientador"]["id"]}
    r = cenario["aluno"].put(f"/api/v1/tccs/{tcc['id']}", json=corpo)
    assert r.status_code == 200 and r.json()["titulo"] == "Novo título do trabalho"
    campos = set(db.scalars(select(LogAuditoria.campo).where(LogAuditoria.acao == "editar_tcc")))
    assert {"titulo", "resumo", "palavras_chave"} <= campos


def test_rn07_outro_aluno_nao_ve_nem_edita(cenario, coord, caixa):
    tcc = _rascunho(cenario).json()
    coord.post("/api/v1/alunos", json={"nome": "Bia Outra", "email": "bia@exemplo.com",
                                       "matricula": "24150055", "curso_id": 1})
    bia = ativar(caixa, "bia@exemplo.com")
    assert bia.get(f"/api/v1/tccs/{tcc['id']}").status_code == 404
    assert cenario["olga"].get(f"/api/v1/tccs/{tcc['id']}").status_code == 200  # a orientadora vê
    assert coord.get(f"/api/v1/tccs/{tcc['id']}").status_code == 200  # a coordenação vê


# ---------------------------------------------------------------- DS-FL03 · orientação


def test_ds_fl03_orientador_aceita_e_aluno_e_avisado(cenario, caixa):
    _rascunho(cenario)
    _aceitar(cenario)
    tcc = cenario["aluno"].get("/api/v1/tccs").json()[0]
    assert tcc["orientador"]["status"] == "ACEITA" and tcc["pendencias"] == []
    assert any(m["para"] == ALUNO["email"] and "aceita" in m["assunto"] for m in caixa)


def test_ds_fl03_recusa_exige_motivo_e_nao_pode_responder_duas_vezes(cenario, caixa):
    _rascunho(cenario)
    pedido = cenario["olga"].get("/api/v1/orientacoes?status=PENDENTE").json()[0]
    url = f"/api/v1/orientacoes/{pedido['id']}/resposta"
    assert cenario["olga"].post(url, json={"decisao": "RECUSAR"}).status_code == 400
    r = cenario["olga"].post(url, json={"decisao": "RECUSAR", "motivo": "Sem vaga neste período."})
    assert r.json()["status"] == "RECUSADA"
    assert cenario["olga"].post(url, json={"decisao": "ACEITAR"}).status_code == 409
    tcc = cenario["aluno"].get("/api/v1/tccs").json()[0]
    assert tcc["orientador"]["motivo_recusa"] == "Sem vaga neste período."
    assert "Indique o orientador." in tcc["pendencias"]


def test_ds_fl03b_apos_recusa_aluno_indica_outro_orientador(cenario, caixa):
    tcc = _rascunho(cenario).json()
    pedido = cenario["olga"].get("/api/v1/orientacoes?status=PENDENTE").json()[0]
    cenario["olga"].post(f"/api/v1/orientacoes/{pedido['id']}/resposta",
                         json={"decisao": "RECUSAR", "motivo": "Sem vaga."})
    r = cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/orientacoes",
                              json={"professor_id": cenario["outro"]["id"]})
    assert r.status_code == 201 and r.json()["status"] == "PENDENTE"
    # passo 5: com orientador pendente, não aceita outra indicação
    r = cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/orientacoes",
                              json={"professor_id": cenario["orientador"]["id"]})
    assert r.status_code == 409


def test_rn07_orientador_so_responde_os_proprios_pedidos(cenario):
    _rascunho(cenario)
    pedido = cenario["olga"].get("/api/v1/orientacoes?status=PENDENTE").json()[0]
    r = cenario["otto"].post(f"/api/v1/orientacoes/{pedido['id']}/resposta", json={"decisao": "ACEITAR"})
    assert r.status_code == 404


# ---------------------------------------------------------------- DS-FL01 · submissão


def test_rbn0303_nao_submete_sem_aceite_do_orientador(cenario):
    tcc = _rascunho(cenario).json()
    r = cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao")
    assert r.status_code == 422
    assert "Aguarde o orientador aceitar a orientação." in r.json()["campos_pendentes"]


def test_ct_03_03_02_campos_obrigatorios(cenario):
    """CT-03.03-02."""
    tcc = _rascunho(cenario, resumo="", palavras_chave=[]).json()
    _aceitar(cenario)
    r = cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao")
    assert r.status_code == 422
    assert set(r.json()["campos_pendentes"]) == {"Escreva o resumo.", "Informe ao menos uma palavra-chave."}


def test_ct_03_03_01_e_03_03_06_e_03_04_01_submissao_gera_protocolo_unico_e_repetir_nao_duplica(cenario, caixa, db):
    """CT-03.03-01, CT-03.03-05, CT-03.03-06, CT-03.03-08, CT-03.04-01, CT-03.04-03, CT-03.04-06."""
    tcc = _rascunho(cenario).json()
    _aceitar(cenario)
    r = cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao")
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["situacao"] == "EM_ANALISE" and corpo["protocolo"] == f"TCC-2026-{tcc['id']:05d}"
    # repetição da mesma submissão (clique duplo): o mesmo protocolo, nada novo
    de_novo = cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao").json()
    assert de_novo["protocolo"] == corpo["protocolo"]
    assert db.scalar(select(Tcc).where(Tcc.protocolo == corpo["protocolo"])) is not None
    historico = list(db.scalars(select(HistoricoSituacao).where(HistoricoSituacao.tcc_id == tcc["id"])))
    assert [h.situacao_nova for h in historico] == ["RASCUNHO", "EM_ANALISE"]
    # auditoria (RNF03) e aviso ao orientador (DS-FL01 passos 11 a 14)
    acoes = set(db.scalars(select(LogAuditoria.acao).where(LogAuditoria.entidade_id == tcc["id"])))
    assert {"criar_tcc", "submeter_tcc", "gerar_protocolo"} <= acoes
    assert any(m["para"] == ORIENTADOR["email"] and corpo["protocolo"] in m["assunto"] for m in caixa)


def test_ds_fl01b_em_analise_nao_edita(cenario):
    tcc = _rascunho(cenario).json()
    _aceitar(cenario)
    cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao")
    corpo = {"titulo": "Mudança depois de enviar", "area_id": cenario["area"]["id"], "modalidade": "MONOGRAFIA"}
    r = cenario["aluno"].put(f"/api/v1/tccs/{tcc['id']}", json=corpo)
    assert r.status_code == 409


def test_rbn0305_devolvido_e_corrigido_mantem_o_protocolo(cenario, db):
    tcc = _rascunho(cenario).json()
    _aceitar(cenario)
    protocolo = cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao").json()["protocolo"]
    registro = db.get(Tcc, tcc["id"])  # a análise da coordenação (Marco 3) devolve
    registro.situacao = "DEVOLVIDO"
    db.commit()
    corpo = {"titulo": "Título corrigido", "resumo": "Resumo corrigido.", "palavras_chave": ["IA"],
             "area_id": cenario["area"]["id"], "modalidade": "MONOGRAFIA",
             "orientador_id": cenario["orientador"]["id"]}
    assert cenario["aluno"].put(f"/api/v1/tccs/{tcc['id']}", json=corpo).status_code == 200
    r = cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao").json()
    assert r["protocolo"] == protocolo and r["situacao"] == "EM_ANALISE"


def test_ct_03_03_03_desistente_nao_submete(cenario, coord, db):
    """CT-03.03-03."""
    tcc = _rascunho(cenario).json()
    _aceitar(cenario)
    m = db.scalar(select(MatriculaTurma))
    r = coord.patch(f"/api/v1/turmas/{cenario['turma']['id']}/alunos/{m.id}", json={"situacao": "DESISTENTE"})
    assert r.status_code == 200
    r = cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao")
    assert r.status_code == 403


def test_rbn0501_listas_por_perfil(cenario, coord):
    _rascunho(cenario)
    assert len(cenario["aluno"].get("/api/v1/tccs").json()) == 1
    assert len(cenario["olga"].get("/api/v1/tccs").json()) == 1
    assert len(cenario["otto"].get("/api/v1/tccs").json()) == 0
    assert len(coord.get("/api/v1/tccs").json()) == 1
