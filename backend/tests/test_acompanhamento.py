"""Sprint S05 · RAN05: busca e filtros (RBN05.03), situação (RBN05.02), histórico (RBN05.04) e tarefas (RBN05.05).

Cada teste cita o caso de teste da ficha (CT-05.xx-yy). O cenário vem da API: o TCC da Ana (aluna) orientado pela Olga,
na turma do Paulo; Otto é outro orientador; a coordenação aprova o cadastro pela rota de análise.
"""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.database import agora
from app.models import LogAuditoria, Tcc
from tests.conftest import ativar
from tests.test_defesas_banca import banca  # noqa: F401  (fixture: TCC aprovado da Olga na turma do Paulo)
from tests.test_tcc import _aceitar, _rascunho, cenario  # noqa: F401  (fixture usada por banca)

URL = "/api/v1/tccs"


def _hoje():
    return (agora() - timedelta(hours=4)).date()


def _situacao(c, quem, tcc_id, situacao, motivo=None):
    return c[quem].put(f"{URL}/{tcc_id}/situacao", json={"situacao": situacao, "motivo": motivo})


def _outro_aluno(cenario, coord, caixa, email, nome, titulo, curso_id=1, orientador="orientador"):
    aluno = coord.post("/api/v1/alunos", json={"nome": nome, "email": email, "matricula": f"2415{abs(hash(email)) % 10000:04d}",
                                               "curso_id": curso_id}).json()
    coord.post(f"/api/v1/turmas/{cenario['turma']['id']}/alunos", json={"aluno_id": aluno["id"]})
    cliente = ativar(caixa, email)
    corpo = {"titulo": titulo, "resumo": "Resumo.", "palavras_chave": ["x"], "area_id": cenario["area"]["id"],
             "modalidade": "MONOGRAFIA", "orientador_id": cenario[orientador]["id"]}
    return cliente, cliente.post(URL, json=corpo).json()


# ---------------------------------------------------------------- RBN05.03 · busca e filtros


@pytest.fixture
def varios(cenario, coord, caixa):
    primeiro = _rascunho(cenario).json()
    _aceitar(cenario)
    assert cenario["aluno"].post(f"{URL}/{primeiro['id']}/submissao").status_code == 200
    saulo, segundo = _outro_aluno(
        cenario, coord, caixa, "saulo@exemplo.com", "Saulo Souza", "Ensino de robótica na educação básica",
        curso_id=3, orientador="outro")
    _, terceiro = _outro_aluno(
        cenario, coord, caixa, "tania@exemplo.com", "Tânia Torres", "Análise de redes sociais")
    return {**cenario, "tccs": [primeiro, segundo, terceiro], "saulo": saulo}


def _ids(r):
    assert r.status_code == 200, r.json()
    return sorted(t["id"] for t in r.json())


def test_ct_05_03_01_busca_por_trecho_do_titulo(varios, coord):
    achados = coord.get(URL, params={"busca": "robótica"})
    assert _ids(achados) == [varios["tccs"][1]["id"]]


def test_busca_pelo_nome_do_aluno(varios, coord):
    assert _ids(coord.get(URL, params={"busca": "tânia"})) == [varios["tccs"][2]["id"]]


def test_ct_05_03_02_busca_por_protocolo_exato(varios, coord):
    protocolo = varios["tccs"][0]["protocolo"] or coord.get(f"{URL}/{varios['tccs'][0]['id']}").json()["protocolo"]
    assert _ids(coord.get(URL, params={"busca": protocolo})) == [varios["tccs"][0]["id"]]


def test_ct_05_03_03_filtros_combinados_so_a_intersecao(varios, coord):
    por_curso = coord.get(URL, params={"curso_id": 3})
    assert _ids(por_curso) == [varios["tccs"][1]["id"]]
    combinado = coord.get(URL, params={"curso_id": 1, "situacao": "EM_ANALISE"})
    assert _ids(combinado) == [varios["tccs"][0]["id"]]
    assert _ids(coord.get(URL, params={"curso_id": 3, "situacao": "EM_ANALISE"})) == []


def test_filtro_por_periodo_e_por_orientador(varios, coord):
    periodo = varios["periodo"]["id"]
    assert len(_ids(coord.get(URL, params={"periodo_id": periodo}))) == 3
    assert _ids(coord.get(URL, params={"periodo_id": periodo + 99})) == []
    assert _ids(coord.get(URL, params={"orientador_id": varios["outro"]["id"]})) == [varios["tccs"][1]["id"]]
    assert len(_ids(coord.get(URL, params={"orientador_id": varios["orientador"]["id"]}))) == 2


def test_ct_05_03_04_sem_correspondencia_devolve_lista_vazia(varios, coord):
    assert coord.get(URL, params={"busca": "inexistente"}).json() == []


def test_situacao_invalida_e_recusada(varios, coord):
    assert coord.get(URL, params={"situacao": "QUALQUER"}).status_code == 400


def test_ct_05_03_05_orientador_nao_acha_tcc_de_outro(varios):
    assert _ids(varios["olga"].get(URL, params={"busca": "robótica"})) == []
    assert _ids(varios["otto"].get(URL, params={"busca": "robótica"})) == [varios["tccs"][1]["id"]]


def test_ct_05_03_06_aluno_nao_ve_dados_de_colega(varios):
    assert varios["aluno"].get(URL, params={"busca": "Saulo"}).json() == []
    assert varios["saulo"].get(URL, params={"busca": "Ana"}).json() == []


def test_busca_com_curinga_nao_vira_padrao(varios, coord):
    assert coord.get(URL, params={"busca": "%"}).json() == []


# ---------------------------------------------------------------- RBN05.02 · situação


def test_ct_05_02_01_orientador_registra_desistencia_no_historico(banca):
    tcc_id = banca["tcc"]["id"]
    r = _situacao(banca, "olga", tcc_id, "DESISTENCIA", "A aluna trancou o curso.")
    assert r.status_code == 200, r.json()
    corpo = r.json()
    assert corpo["situacao"] == "DESISTENCIA" and corpo["desistencia_motivo"] == "A aluna trancou o curso."
    ultimo = corpo["historico"][-1]
    assert (ultimo["situacao_anterior"], ultimo["situacao_nova"]) == ("APROVADO", "DESISTENCIA")
    assert ultimo["usuario"]["id"] == banca["ids"]["olga"] and ultimo["observacao"] == "A aluna trancou o curso."
    assert ultimo["registrado_em"]


def test_ct_05_02_02_desistencia_sem_motivo_e_bloqueada(banca):
    r = _situacao(banca, "olga", banca["tcc"]["id"], "DESISTENCIA", "   ")
    assert r.status_code == 400 and "motivo" in r.json()["campos"]
    assert _situacao(banca, "olga", banca["tcc"]["id"], "DESISTENCIA").status_code == 400
    assert banca["olga"].get(f"{URL}/{banca['tcc']['id']}").json()["situacao"] == "APROVADO"


def test_ct_05_02_03_reativacao_com_motivo_limpa_a_desistencia(banca):
    tcc_id = banca["tcc"]["id"]
    _situacao(banca, "olga", tcc_id, "DESISTENCIA", "Trancou o curso.")
    r = _situacao(banca, "olga", tcc_id, "APROVADO", "A aluna voltou ao curso.")
    assert r.status_code == 200 and r.json()["situacao"] == "APROVADO" and r.json()["desistencia_motivo"] is None
    assert [h["situacao_nova"] for h in r.json()["historico"]][-2:] == ["DESISTENCIA", "APROVADO"]


def test_ct_05_02_04_outro_orientador_e_aluno_recebem_403(banca):
    tcc_id = banca["tcc"]["id"]
    assert _situacao(banca, "otto", tcc_id, "DESISTENCIA", "Motivo qualquer.").status_code == 403
    assert _situacao(banca, "aluno", tcc_id, "DESISTENCIA", "Motivo qualquer.").status_code == 403
    assert banca["olga"].get(f"{URL}/{tcc_id}").json()["situacao"] == "APROVADO"


def test_ct_05_02_05_transicao_invalida_e_rejeitada(banca, db):
    tcc_id = banca["tcc"]["id"]
    db.get(Tcc, tcc_id).situacao = "CONCLUIDO"
    db.commit()
    r = _situacao(banca, "olga", tcc_id, "DESISTENCIA", "Motivo qualquer.")
    assert r.status_code == 409 and r.json()["motivo"] == "transicao_invalida"
    db.get(Tcc, tcc_id).situacao = "APROVADO"
    db.commit()
    assert _situacao(banca, "olga", tcc_id, "APROVADO", "Motivo qualquer.").status_code == 409


def test_ct_05_02_06_log_guarda_anterior_e_novo(banca, db):
    tcc_id = banca["tcc"]["id"]
    _situacao(banca, "olga", tcc_id, "DESISTENCIA", "Trancou o curso.")
    db.expire_all()
    log = db.scalars(select(LogAuditoria).where(LogAuditoria.acao == "atualizar_situacao_tcc")).one()
    assert (log.usuario_id, log.entidade_id, log.valor_anterior, log.valor_novo) == (
        banca["ids"]["olga"], tcc_id, "APROVADO", "DESISTENCIA")


# ---------------------------------------------------------------- RBN05.04 · histórico


@pytest.fixture
def trajetoria(cenario, coord):
    tcc = _rascunho(cenario).json()
    _aceitar(cenario)
    assert cenario["aluno"].post(f"{URL}/{tcc['id']}/submissao").status_code == 200
    r = coord.post(f"/api/v1/cadastros/{tcc['id']}/decisao", json={"resultado": "APROVADO", "parecer": "Cadastro completo."})
    assert r.status_code == 200, r.json()
    assert _situacao(cenario, "olga", tcc["id"], "DESISTENCIA", "Trancou o curso.").status_code == 200
    return {**cenario, "tcc": tcc}


def test_ct_05_04_01_ordem_cronologica_com_autor_e_hora(trajetoria):
    eventos = trajetoria["olga"].get(f"{URL}/{trajetoria['tcc']['id']}/historico").json()
    assert len(eventos) >= 6
    assert [e["em"] for e in eventos] == sorted(e["em"] for e in eventos)
    assert all(e["em"].endswith("Z") for e in eventos)
    assert eventos[-1]["tipo"] == "SITUACAO" and eventos[-1]["autor"]["nome"] == "Olga Orientadora"


def test_ct_05_04_02_cobre_submissao_parecer_vinculo_e_situacao(trajetoria):
    eventos = trajetoria["aluno"].get(f"{URL}/{trajetoria['tcc']['id']}/historico").json()
    assert {e["tipo"] for e in eventos} == {"SUBMISSAO", "PARECER", "VINCULO", "SITUACAO"}
    parecer = next(e for e in eventos if e["tipo"] == "PARECER")
    assert parecer["detalhe"] == "Cadastro completo." and "APROVADO" in parecer["descricao"]
    vinculos = [e["descricao"] for e in eventos if e["tipo"] == "VINCULO"]
    assert any("solicitada" in d for d in vinculos) and any("aceita" in d for d in vinculos)


def test_ct_05_04_04_historico_nao_tem_alteracao_nem_exclusao(trajetoria):
    url = f"{URL}/{trajetoria['tcc']['id']}/historico"
    for metodo in ("delete", "put", "patch", "post"):
        assert getattr(trajetoria["olga"], metodo)(url).status_code == 405


def test_ct_05_04_05_sem_vinculo_nao_ve_o_historico(trajetoria):
    assert trajetoria["otto"].get(f"{URL}/{trajetoria['tcc']['id']}/historico").status_code == 404


def test_historico_exige_sessao(trajetoria, anonimo):
    assert anonimo.get(f"{URL}/{trajetoria['tcc']['id']}/historico").status_code == 401


# ---------------------------------------------------------------- RBN05.05 · tarefas


def _tarefa(c, quem, tcc_id, descricao="Entregar o capítulo 1", dias=7):
    prazo = (_hoje() + timedelta(days=dias)).isoformat()
    return c[quem].post(f"{URL}/{tcc_id}/tarefas", json={"descricao": descricao, "prazo": prazo})


def test_ct_05_05_01_orientador_cria_tarefa_no_tcc(banca):
    r = _tarefa(banca, "olga", banca["tcc"]["id"])
    assert r.status_code == 201, r.json()
    corpo = r.json()
    assert corpo["descricao"] == "Entregar o capítulo 1" and corpo["status"] == "PENDENTE"
    assert corpo["cadastrada_por"]["id"] == banca["ids"]["olga"] and corpo["criado_em"] and corpo["entregue_em"] is None


def test_ct_05_05_02_professor_da_turma_tambem_cria(banca):
    assert _tarefa(banca, "paulo", banca["tcc"]["id"], "Entregar o projeto").status_code == 201


def test_ct_05_05_03_campos_obrigatorios(banca):
    tcc_id = banca["tcc"]["id"]
    r = banca["olga"].post(f"{URL}/{tcc_id}/tarefas", json={"descricao": "  ", "prazo": _hoje().isoformat()})
    assert r.status_code == 400 and "descricao" in r.json()["campos"]
    r = banca["olga"].post(f"{URL}/{tcc_id}/tarefas", json={"descricao": "Entregar"})
    assert r.status_code == 400 and "prazo" in r.json()["campos"]


def test_ct_05_05_04_prazo_anterior_a_hoje_e_rejeitado(banca):
    r = _tarefa(banca, "olga", banca["tcc"]["id"], dias=-1)
    assert r.status_code == 400 and r.json()["campos"]["prazo"] == "O prazo não pode ser anterior a hoje."
    assert _tarefa(banca, "olga", banca["tcc"]["id"], dias=0).status_code == 201


def test_ct_05_05_05_aluno_e_orientador_veem_a_tarefa(banca):
    tcc_id = banca["tcc"]["id"]
    _tarefa(banca, "olga", tcc_id)
    for quem in ("aluno", "olga", "paulo"):
        lista = banca[quem].get(f"{URL}/{tcc_id}/tarefas").json()
        assert [t["descricao"] for t in lista] == ["Entregar o capítulo 1"]
    assert banca["otto"].get(f"{URL}/{tcc_id}/tarefas").status_code == 404


def test_ct_05_05_06_tarefa_fica_so_no_tcc_escolhido(banca, coord, caixa):
    _, outro = _outro_aluno(banca, coord, caixa, "saulo@exemplo.com", "Saulo Souza", "Outro trabalho")
    _tarefa(banca, "olga", banca["tcc"]["id"])
    assert coord.get(f"{URL}/{outro['id']}/tarefas").json() == []
    assert len(coord.get(f"{URL}/{banca['tcc']['id']}/tarefas").json()) == 1


def test_ct_05_05_07_aluno_e_banca_nao_criam(banca):
    tcc_id = banca["tcc"]["id"]
    assert _tarefa(banca, "aluno", tcc_id).status_code == 403
    assert _tarefa(banca, "otto", tcc_id).status_code == 403
    assert banca["olga"].get(f"{URL}/{tcc_id}/tarefas").json() == []


def test_tarefa_so_em_tcc_aprovado(banca, db):
    db.get(Tcc, banca["tcc"]["id"]).situacao = "DESISTENCIA"
    db.commit()
    r = _tarefa(banca, "olga", banca["tcc"]["id"])
    assert r.status_code == 409 and r.json()["motivo"] == "tcc_nao_aprovado"


def test_tarefa_vencida_aparece_atrasada(banca, db):
    from app.models import TarefaTcc

    tarefa = _tarefa(banca, "olga", banca["tcc"]["id"]).json()
    registro = db.get(TarefaTcc, tarefa["id"])
    registro.prazo = _hoje() - timedelta(days=2)
    db.commit()
    assert banca["aluno"].get(f"{URL}/{banca['tcc']['id']}/tarefas").json()[0]["status"] == "ATRASADA"


def test_criar_tarefa_fica_no_log(banca, db):
    tarefa = _tarefa(banca, "olga", banca["tcc"]["id"]).json()
    db.expire_all()
    log = db.scalars(select(LogAuditoria).where(LogAuditoria.acao == "criar_tarefa_tcc")).one()
    assert (log.usuario_id, log.entidade, log.entidade_id) == (banca["ids"]["olga"], "tarefa_tcc", tarefa["id"])
