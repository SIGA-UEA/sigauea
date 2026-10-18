"""Casos de teste (CT) das fichas RBN que ainda não tinham teste automatizado.

O nome de cada função leva o ID do CT (test_ct_AA_BB_NN_...). Os CTs que dependem de algo que
ainda não existe no sistema aparecem como "skipped", com o motivo, para ficarem visíveis.
"""

import threading

import pytest
from sqlalchemy import select

from app.models import LogAuditoria
from tests.conftest import ALUNO, DOCENTE, ativar
from tests.test_tcc import ORIENTADOR, _aceitar, _rascunho, cenario  # noqa: F401  (fixture)

LOGIN = "/api/v1/auth/login"


# ---------------------------------------------------------------- RBN01.01 a RBN01.03 · cadastros


def test_ct_01_01_04_docente_recebe_tambem_o_perfil_de_coordenador(coord, caixa):
    """CT-01.01-04: dois perfis ativos, atribuídos pela coordenação."""
    criado = coord.post("/api/v1/docentes", json={**DOCENTE, "perfis": ["professor_disciplina"]}).json()
    r = coord.put(f"/api/v1/usuarios/{criado['id']}", json={"perfis": ["professor_disciplina", "coordenador"]})
    assert r.status_code == 200
    assert set(coord.get(f"/api/v1/docentes/{criado['id']}").json()["perfis"]) == {
        "professor_disciplina",
        "coordenador",
    }


def test_ct_01_03_02_aluno_sem_matricula_e_recusado(coord):
    """CT-01.03-02: campo obrigatório ausente, nada é criado."""
    sem = {k: v for k, v in ALUNO.items() if k != "matricula"}
    r = coord.post("/api/v1/alunos", json=sem)
    assert r.status_code == 400 and "matricula" in r.json()["campos"]
    assert coord.get("/api/v1/alunos").json() == []


def test_ct_01_03_05_aluno_nao_cadastra_aluno(coord, caixa):
    """CT-01.03-05: quem não é coordenação recebe 403."""
    coord.post("/api/v1/alunos", json=ALUNO)
    aluno = ativar(caixa, ALUNO["email"])
    outro = {**ALUNO, "email": "outra@uea.edu.br", "matricula": "24150088"}
    assert aluno.post("/api/v1/alunos", json=outro).status_code == 403


# ---------------------------------------------------------------- RBN01.02 · áreas


def test_ct_01_02_03_area_com_nome_vazio_e_recusada(coord):
    """CT-01.02-03: nome vazio é bloqueado."""
    r = coord.post("/api/v1/areas", json={"nome": ""})
    assert r.status_code == 400 and "nome" in r.json()["campos"]


def test_ct_01_02_04_renomear_area_vale_para_os_docentes_vinculados(coord, caixa):
    """CT-01.02-04: os vínculos passam a exibir o novo nome."""
    area_id = coord.get("/api/v1/areas").json()[0]["id"]
    docente = coord.post("/api/v1/docentes", json={**DOCENTE, "areas": [area_id]}).json()
    assert coord.put(f"/api/v1/areas/{area_id}", json={"nome": "Área Renomeada"}).status_code == 200
    nomes = [a["nome"] for a in coord.get(f"/api/v1/docentes/{docente['id']}").json()["areas"]]
    assert nomes == ["Área Renomeada"]


# ---------------------------------------------------------------- RBN01.06 e RBN01.08


def test_ct_01_06_06_login_com_campos_vazios_e_recusado(anonimo):
    """CT-01.06-06: e-mail e senha em branco não chegam a autenticar."""
    r = anonimo.post(LOGIN, json={"email": "", "senha": ""})
    assert r.status_code == 400 and {"email", "senha"} <= set(r.json()["campos"])


def test_ct_01_08_05_aluno_nao_edita_outro_usuario(coord, caixa):
    """CT-01.08-05: quem não é coordenação recebe 403."""
    coord.post("/api/v1/alunos", json=ALUNO)
    aluno = ativar(caixa, ALUNO["email"])
    outro = coord.post("/api/v1/docentes", json=DOCENTE).json()
    assert aluno.put(f"/api/v1/usuarios/{outro['id']}", json={"telefone": "92999990000"}).status_code == 403
    assert aluno.patch(f"/api/v1/usuarios/{outro['id']}/inativar").status_code == 403


# ---------------------------------------------------------------- RBN03.01 a RBN03.04


def test_ct_03_01_06_aluno_de_outro_curso_salva_o_cadastro_e_mantem_o_curso(coord, cenario, caixa):  # noqa: F811
    """CT-03.01-06: aluno de SI em turma de EC; o curso SI continua no cadastro."""
    saulo = coord.post(
        "/api/v1/alunos",
        json={"nome": "Saulo SI", "email": "saulo@exemplo.com", "matricula": "24150099", "curso_id": 3},
    ).json()
    coord.post(f"/api/v1/turmas/{cenario['turma']['id']}/alunos", json={"aluno_id": saulo["id"]})
    cenario["aluno"] = ativar(caixa, "saulo@exemplo.com")
    r = _rascunho(cenario)
    assert r.status_code == 201
    assert cenario["aluno"].get("/api/v1/auth/me").json()["curso"]["sigla"] == "SI"
    assert coord.get(f"/api/v1/alunos/{saulo['id']}").json()["curso"]["sigla"] == "SI"


ARTIGO = {"tipo_veiculo": "PERIODICO", "veiculo": "Revista Brasileira de Computação"}


def test_ct_03_02_05_artigo_submetido_nao_exige_doi(cenario):  # noqa: F811
    """CT-03.02-05: o DOI só é obrigatório quando a situação é publicado."""
    r = _rascunho(cenario, modalidade="ARTIGO", artigo={**ARTIGO, "situacao": "SUBMETIDO"})
    assert r.status_code == 201


def test_ct_03_02_06_situacao_editorial_fora_dos_valores_previstos_e_recusada(cenario):  # noqa: F811
    """CT-03.02-06: a API rejeita valor que não é do RN03."""
    r = _rascunho(cenario, modalidade="ARTIGO", artigo={**ARTIGO, "situacao": "XYZ"})
    assert r.status_code == 400
    assert cenario["aluno"].get("/api/v1/tccs").json() == []


def test_ct_03_03_04_aluno_incluido_na_turma_passa_a_poder_submeter(coord, cenario, caixa):  # noqa: F811
    """CT-03.03-04: sem matrícula é recusado; depois da inclusão pela coordenação, a submissão é aceita."""
    coord.post("/api/v1/alunos", json={"nome": "Bia Outra", "email": "bia@exemplo.com",
                                       "matricula": "24150055", "curso_id": 1})
    bia = ativar(caixa, "bia@exemplo.com")
    assert bia.get("/api/v1/tccs/formulario").status_code == 403

    bia_id = bia.get("/api/v1/auth/me").json()["id"]
    r = coord.post(f"/api/v1/turmas/{cenario['turma']['id']}/alunos", json={"aluno_id": bia_id})
    assert r.status_code == 201

    cenario["aluno"] = bia
    tcc = _rascunho(cenario).json()
    _aceitar(cenario)
    r = bia.post(f"/api/v1/tccs/{tcc['id']}/submissao")
    assert r.status_code == 200 and r.json()["situacao"] == "EM_ANALISE"


def test_ct_03_04_05_submissoes_simultaneas_geram_protocolos_distintos(coord, cenario, caixa):  # noqa: F811
    """CT-03.04-05: vários alunos enviam ao mesmo tempo e nenhum protocolo se repete."""
    alunos = [cenario["aluno"]]
    tccs = [_rascunho(cenario).json()]
    _aceitar(cenario)
    for i in range(7):
        email = f"aluno{i}@exemplo.com"
        criado = coord.post(
            "/api/v1/alunos",
            json={"nome": f"Aluno {i}", "email": email, "matricula": f"2416{i:04d}", "curso_id": 1},
        ).json()
        coord.post(f"/api/v1/turmas/{cenario['turma']['id']}/alunos", json={"aluno_id": criado["id"]})
        cenario["aluno"] = ativar(caixa, email)
        tccs.append(_rascunho(cenario).json())
        alunos.append(cenario["aluno"])
        _aceitar(cenario)

    respostas = [None] * len(alunos)

    def enviar(i):
        respostas[i] = alunos[i].post(f"/api/v1/tccs/{tccs[i]['id']}/submissao")

    fios = [threading.Thread(target=enviar, args=(i,)) for i in range(len(alunos))]
    for f in fios:
        f.start()
    for f in fios:
        f.join()
    assert [r.status_code for r in respostas] == [200] * len(alunos)
    protocolos = [r.json()["protocolo"] for r in respostas]
    assert len(set(protocolos)) == len(alunos)


# ---------------------------------------------------------------- RBN06.01 · orientador


def test_ct_06_01_02_orientador_inativo_nao_aparece_na_lista(coord, cenario):  # noqa: F811
    """CT-06.01-02: só docente ativo com perfil de orientador é elegível."""
    assert coord.patch(f"/api/v1/usuarios/{cenario['outro']['id']}/inativar").status_code == 200
    nomes = {o["nome"] for o in cenario["aluno"].get("/api/v1/tccs/formulario").json()["orientadores"]}
    assert nomes == {"Olga Orientadora"}
    r = _rascunho(cenario, orientador_id=cenario["outro"]["id"])
    assert r.status_code == 422


def test_ct_06_01_03_nao_submete_sem_orientador(cenario):  # noqa: F811
    """CT-06.01-03: o cadastro sem orientador é bloqueado e indica o campo."""
    tcc = _rascunho(cenario, orientador_id=None).json()
    r = cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao")
    assert r.status_code == 422
    assert "Indique o orientador." in r.json()["campos_pendentes"]


def test_ct_06_01_05_aluno_de_outro_cadastro_nao_altera_a_orientacao(coord, cenario, caixa):  # noqa: F811
    """CT-06.01-05: o sistema nega (404, RN07: não revela que o cadastro existe)."""
    tcc = _rascunho(cenario).json()
    coord.post("/api/v1/alunos", json={"nome": "Bia Outra", "email": "bia@exemplo.com",
                                       "matricula": "24150055", "curso_id": 1})
    bia = ativar(caixa, "bia@exemplo.com")
    r = bia.post(f"/api/v1/tccs/{tcc['id']}/orientacoes", json={"professor_id": cenario["outro"]["id"]})
    assert r.status_code in (403, 404)


def test_ct_06_01_06_vinculo_de_orientacao_fica_no_log(cenario, db):  # noqa: F811
    """CT-06.01-06: usuário, data/hora e o docente indicado."""
    tcc = _rascunho(cenario).json()
    log = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "indicar_orientacao",
                                               LogAuditoria.entidade_id == tcc["id"]))
    assert log.usuario_id and log.criado_em
    assert log.campo == "orientador" and log.valor_novo == ORIENTADOR["nome"]


@pytest.mark.skip(reason="Não existe rota nem tela para a coordenação trocar o orientador depois do aceite.")
def test_ct_06_01_04_substituir_orientador_preserva_o_historico():
    """CT-06.01-04: o vínculo anterior é encerrado e fica no histórico (RN16)."""


@pytest.mark.skip(reason="Depende do módulo de ideias e propostas (RBN02.01), ainda não implementado.")
def test_ct_01_10_06_professor_ve_as_propostas_da_sua_area():
    """CT-01.10-06: proposta direcionada à área aparece para o professor vinculado."""
