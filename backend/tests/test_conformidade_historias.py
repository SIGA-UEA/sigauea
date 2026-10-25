"""Casos de teste das histórias S02 e S03 que ainda não tinham teste automatizado.

Cada teste cita o CT (ou o CA) da ficha da história que confere. Os de tela (largura de 360 px,
botão desabilitado, janela de confirmação) são conferidos no navegador e não estão aqui.
"""

from datetime import date

from sqlalchemy import select

from app.models import LogAuditoria, MatriculaTurma, NotificacaoEmail, Orientacao, Tcc, Turma, Usuario
from app.services import email
from app.database import agora
from tests.conftest import ALUNO, DOCENTE, SENHA, ativar
from tests.test_tcc import ORIENTADOR, PROFESSOR, _aceitar, _rascunho, cenario  # noqa: F401

TELEFONES_INVALIDOS = ["abc", "(92) 9abcd-0000", "92", "+55 92 99999-0000 ramal 2"]


# ---------------------------------------------------------------- telefone (RBN01.01, RBN01.08 a RBN01.10)


def test_telefone_com_letras_e_recusado_no_cadastro_de_docente(coord):
    for valor in TELEFONES_INVALIDOS:
        r = coord.post("/api/v1/docentes", json={**DOCENTE, "telefone": valor})
        assert r.status_code == 400 and "telefone" in r.json()["campos"], valor


def test_telefone_valido_e_aceito_com_ou_sem_mascara(coord):
    r = coord.post("/api/v1/docentes", json={**DOCENTE, "telefone": "(92) 99123-4567"})
    assert r.status_code == 201 and r.json()["telefone"] == "(92) 99123-4567"
    r = coord.put(f"/api/v1/usuarios/{r.json()['id']}", json={"telefone": "+55 92 3333-4444"})
    assert r.status_code == 200 and r.json()["telefone"] == "+55 92 3333-4444"


def test_telefone_com_letras_e_recusado_na_edicao_e_no_proprio_perfil(coord, caixa):
    criado = coord.post("/api/v1/alunos", json=ALUNO).json()
    r = coord.put(f"/api/v1/usuarios/{criado['id']}", json={"telefone": "abc"})
    assert r.status_code == 400 and "telefone" in r.json()["campos"]
    aluno = ativar(caixa, ALUNO["email"])
    r = aluno.put("/api/v1/usuarios/me", json={"telefone": "telefone"})
    assert r.status_code == 400 and "telefone" in r.json()["campos"]
    assert aluno.get("/api/v1/usuarios/me").json()["telefone"] is None


# ---------------------------------------------------------------- S02 · usuários e acesso


def test_ct_01_04_03_senha_com_7_caracteres_e_recusada(coord, caixa, anonimo):
    """CT-01.04-03 e CT-01.04-04: o limite é de 8 caracteres."""
    coord.post("/api/v1/docentes", json=DOCENTE)
    token = next(m["token"] for m in caixa if m["para"] == DOCENTE["email"])
    r = anonimo.post("/api/v1/auth/ativar", json={"token": token, "senha": "Aa1!aaa"})
    assert r.status_code == 422
    assert anonimo.post("/api/v1/auth/ativar", json={"token": token, "senha": "Aa1!aaaa"}).status_code == 200


def test_ct_01_06_08_conta_inativada_nao_entra(coord, caixa, anonimo):
    """CT-01.06-08."""
    criado = coord.post("/api/v1/docentes", json=DOCENTE).json()
    ativar(caixa, DOCENTE["email"])
    assert coord.patch(f"/api/v1/usuarios/{criado['id']}/inativar").status_code == 200
    r = anonimo.post("/api/v1/auth/login", json={"email": DOCENTE["email"], "senha": SENHA})
    assert r.status_code == 401 and r.json()["detail"] == "E-mail ou senha inválidos."


# ---------------------------------------------------------------- SCRUM-36 · formulário de cadastro


def test_ct_03_01_05_sem_subtitulo_e_sem_coorientador_salva_e_envia(cenario):
    """CT-03.01-05 e CA-04."""
    tcc = _rascunho(cenario).json()
    assert tcc["subtitulo"] is None and tcc["coorientador"] is None
    _aceitar(cenario)
    r = cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao")
    assert r.status_code == 200 and r.json()["situacao"] == "EM_ANALISE"


def test_ct_03_01_09_sem_titulo_area_ou_modalidade_destaca_cada_campo(cenario):
    """CT-03.01-09 e CA-03."""
    r = cenario["aluno"].post("/api/v1/tccs", json={"resumo": "x"})
    assert r.status_code == 400
    assert {"titulo", "area_id", "modalidade"} <= set(r.json()["campos"])


def test_ct_03_01_10_e_03_01_11_percurso_completo_so_envia_depois_do_aceite(cenario):
    """CT-03.01-11: sem o aceite, o passo 3 mostra a pendência; CT-03.01-10: com o aceite, envia."""
    tcc = _rascunho(cenario).json()
    assert "Aguarde o orientador aceitar a orientação." in tcc["pendencias"]
    r = cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao")
    assert r.status_code == 422
    _aceitar(cenario)
    tcc = cenario["aluno"].get(f"/api/v1/tccs/{tcc['id']}").json()
    assert tcc["pendencias"] == []
    r = cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao")
    assert r.status_code == 200 and r.json()["protocolo"].startswith("TCC-2026-")


# ---------------------------------------------------------------- SCRUM-37 · dados do artigo

ARTIGO = {"tipo_veiculo": "PERIODICO", "veiculo": "Revista Brasileira de Computação", "situacao": "SUBMETIDO"}


def test_ct_03_02_03_dados_do_artigo_voltam_ao_reabrir(cenario):
    """CT-03.02-03 e CA-02."""
    tcc = _rascunho(cenario, modalidade="ARTIGO", artigo=ARTIGO).json()
    reaberto = cenario["aluno"].get(f"/api/v1/tccs/{tcc['id']}").json()
    assert reaberto["artigo"]["veiculo"] == ARTIGO["veiculo"]


def test_ct_03_02_07_trocar_para_monografia_mantem_os_dados_do_artigo(cenario):
    """CT-03.02-07 e CA-05."""
    tcc = _rascunho(cenario, modalidade="ARTIGO", artigo=ARTIGO).json()
    corpo = {"titulo": tcc["titulo"], "resumo": tcc["resumo"], "palavras_chave": tcc["palavras_chave"],
             "area_id": tcc["area"]["id"], "modalidade": "MONOGRAFIA",
             "orientador_id": cenario["orientador"]["id"]}
    r = cenario["aluno"].put(f"/api/v1/tccs/{tcc['id']}", json=corpo)
    assert r.status_code == 200
    # salvo como monografia e reaberto, os dados do artigo continuam lá para quando o aluno voltar a "Artigo"
    assert cenario["aluno"].get(f"/api/v1/tccs/{tcc['id']}").json()["artigo"]["veiculo"] == ARTIGO["veiculo"]
    r = cenario["aluno"].put(f"/api/v1/tccs/{tcc['id']}", json={**corpo, "modalidade": "ARTIGO"})
    assert r.json()["artigo"]["veiculo"] == ARTIGO["veiculo"]


def test_ct_03_02_08_artigo_aceito_nao_exige_doi(cenario):
    """CT-03.02-08."""
    r = _rascunho(cenario, modalidade="ARTIGO", artigo={**ARTIGO, "situacao": "ACEITO"})
    assert r.status_code == 201 and r.json()["artigo"]["doi"] is None


def test_ct_03_02_04_publicado_sem_doi_e_recusado(cenario):
    """CT-03.02-04 e CA-03."""
    r = _rascunho(cenario, modalidade="ARTIGO", artigo={**ARTIGO, "situacao": "PUBLICADO"})
    assert r.status_code == 400 and r.json()["campos"]["doi"] == "Informe o DOI do artigo publicado."


# ---------------------------------------------------------------- SCRUM-38 e SCRUM-39 · envio e protocolo


def test_ct_03_03_05_envia_sem_pdf(cenario):
    """CT-03.03-05 e CA-04: o PDF não é pedido no cadastro."""
    tcc = _rascunho(cenario).json()
    _aceitar(cenario)
    assert cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao").status_code == 200


def test_ct_03_03_09_pendencias_de_palavra_chave_e_orientador(cenario):
    """CT-03.03-09."""
    tcc = _rascunho(cenario, palavras_chave=[], orientador_id=None).json()
    assert {"Informe ao menos uma palavra-chave.", "Indique o orientador."} <= set(tcc["pendencias"])


def test_ct_03_03_11_cadastro_enviado_nao_pode_ser_editado(cenario):
    """CT-03.03-11."""
    tcc = _rascunho(cenario).json()
    _aceitar(cenario)
    cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao")
    r = cenario["aluno"].put(f"/api/v1/tccs/{tcc['id']}", json={"titulo": "Outro título", "area_id": tcc["area"]["id"],
                                                                "modalidade": "MONOGRAFIA"})
    assert r.status_code == 409 and r.json()["detail"] == "O cadastro não pode ser editado nesta situação."


def test_ct_03_04_03_reenvio_da_mesma_requisicao_devolve_o_mesmo_protocolo(cenario, db):
    """CT-03.04-03 e CA-03."""
    tcc = _rascunho(cenario).json()
    _aceitar(cenario)
    primeiro = cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao").json()
    segundo = cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao").json()
    assert primeiro["protocolo"] == segundo["protocolo"]
    assert len(db.scalars(select(Tcc)).all()) == 1


def test_ct_03_04_06_protocolo_gerado_fica_no_log(cenario, db):
    """CT-03.04-06 e CA-06."""
    tcc = _rascunho(cenario).json()
    _aceitar(cenario)
    protocolo = cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao").json()["protocolo"]
    linha = db.scalar(select(LogAuditoria).where(LogAuditoria.campo == "protocolo",
                                                 LogAuditoria.entidade_id == tcc["id"]))
    assert linha and linha.valor_novo == protocolo and linha.usuario_id and linha.criado_em


def test_ct_03_04_08_protocolo_aparece_para_orientador_e_coordenacao(cenario, coord):
    """CT-03.04-08."""
    tcc = _rascunho(cenario).json()
    _aceitar(cenario)
    protocolo = cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao").json()["protocolo"]
    assert [t["protocolo"] for t in cenario["olga"].get("/api/v1/tccs").json()] == [protocolo]
    assert protocolo in [t["protocolo"] for t in coord.get("/api/v1/tccs").json()]


# ---------------------------------------------------------------- SCRUM-40 · cadastro devolvido


def _devolver(db, tcc_id):
    """A devolução pela coordenação (RBN04.03) ainda é prevista: o teste põe a situação direto no banco."""
    tcc = db.get(Tcc, tcc_id)
    tcc.situacao = "DEVOLVIDO"
    db.commit()


def test_ct_03_05_02_corrigir_e_reenviar_mantem_o_protocolo(cenario, db):
    """CT-03.05-02 e CT-03.05-06."""
    tcc = _rascunho(cenario).json()
    _aceitar(cenario)
    protocolo = cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao").json()["protocolo"]
    _devolver(db, tcc["id"])
    corpo = {"titulo": "Título corrigido", "resumo": tcc["resumo"], "palavras_chave": tcc["palavras_chave"],
             "area_id": tcc["area"]["id"], "modalidade": "MONOGRAFIA", "orientador_id": cenario["orientador"]["id"]}
    assert cenario["aluno"].put(f"/api/v1/tccs/{tcc['id']}", json=corpo).status_code == 200
    r = cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao")
    assert r.status_code == 200 and r.json()["protocolo"] == protocolo and r.json()["situacao"] == "EM_ANALISE"
    db.expire_all()
    linha = db.scalar(select(LogAuditoria).where(LogAuditoria.campo == "titulo",
                                                 LogAuditoria.entidade_id == tcc["id"],
                                                 LogAuditoria.valor_novo == "Título corrigido"))
    assert linha and linha.valor_anterior == tcc["titulo"]


def test_ct_03_05_04_cadastro_aprovado_nao_pode_ser_editado(cenario, db):
    """CT-03.05-04 e CA-04."""
    tcc = _rascunho(cenario).json()
    obj = db.get(Tcc, tcc["id"])
    obj.situacao = "APROVADO"
    db.commit()
    r = cenario["aluno"].put(f"/api/v1/tccs/{tcc['id']}", json={"titulo": "Novo", "area_id": tcc["area"]["id"],
                                                                "modalidade": "MONOGRAFIA"})
    assert r.status_code == 409


def test_ct_03_05_05_outro_aluno_nao_edita_o_cadastro(cenario, coord, caixa):
    """CT-03.05-05 e CA-05: o código responde 404, sem revelar que o cadastro existe (RN07)."""
    tcc = _rascunho(cenario).json()
    coord.post("/api/v1/alunos", json={"nome": "Bruno Aluno", "email": "bruno@exemplo.com",
                                       "matricula": "24150055", "curso_id": 1})
    bruno = ativar(caixa, "bruno@exemplo.com")
    r = bruno.put(f"/api/v1/tccs/{tcc['id']}", json={"titulo": "Invasão", "area_id": tcc["area"]["id"],
                                                    "modalidade": "MONOGRAFIA"})
    assert r.status_code in (403, 404)


# ---------------------------------------------------------------- SCRUM-41 · e-mail ao orientador


def test_ct_03_06_02_email_ao_orientador_nao_leva_matricula_nem_senha(cenario, monkeypatch):
    """CT-03.06-02 e CA-02: sem senha nem dados desnecessários (matrícula, notas, contatos)."""
    corpos = []
    monkeypatch.setattr(email, "entregar", lambda para, assunto, corpo: corpos.append(corpo))
    tcc = _rascunho(cenario).json()
    _aceitar(cenario)
    cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao")
    assert corpos
    for corpo in corpos:
        assert ALUNO["matricula"] not in corpo and "senha" not in corpo.lower()


def test_ct_03_06_05_salvar_sem_mudar_o_orientador_nao_manda_outro_email(cenario, db):
    """CT-03.06-05 e CA-04."""
    tcc = _rascunho(cenario).json()
    antes = len(db.scalars(select(NotificacaoEmail).where(NotificacaoEmail.tipo == "VINCULO_ORIENTACAO")).all())
    corpo = {"titulo": "Título revisto", "resumo": tcc["resumo"], "palavras_chave": tcc["palavras_chave"],
             "area_id": tcc["area"]["id"], "modalidade": "MONOGRAFIA", "orientador_id": cenario["orientador"]["id"]}
    cenario["aluno"].put(f"/api/v1/tccs/{tcc['id']}", json=corpo)
    db.expire_all()
    depois = len(db.scalars(select(NotificacaoEmail).where(NotificacaoEmail.tipo == "VINCULO_ORIENTACAO")).all())
    assert depois == antes


def test_ct_03_06_03_e_03_06_04_email_que_falhou_e_reenviado_sem_duplicar(cenario, db, monkeypatch):
    """CT-03.06-03 e CT-03.06-04 e CA-03: a falha fica pendente e o reenvio não duplica o TCC."""
    def fora_do_ar(para, assunto, corpo):
        raise ConnectionError("serviço de e-mail fora do ar")

    monkeypatch.setattr(email, "entregar", fora_do_ar)
    tcc = _rascunho(cenario).json()
    falha = db.scalar(select(NotificacaoEmail).where(NotificacaoEmail.tipo == "VINCULO_ORIENTACAO"))
    assert falha.status == "falha"

    entregues = []
    monkeypatch.setattr(email, "entregar", lambda para, assunto, corpo: entregues.append(para))
    corpo = {"titulo": tcc["titulo"], "resumo": tcc["resumo"], "palavras_chave": tcc["palavras_chave"],
             "area_id": tcc["area"]["id"], "modalidade": "MONOGRAFIA", "orientador_id": cenario["orientador"]["id"]}
    assert cenario["aluno"].put(f"/api/v1/tccs/{tcc['id']}", json=corpo).status_code == 200
    db.expire_all()
    assert db.get(NotificacaoEmail, falha.id).status == "enviado"
    assert entregues == [ORIENTADOR["email"]]
    assert len(db.scalars(select(Tcc)).all()) == 1


# ---------------------------------------------------------------- SCRUM-47, SCRUM-48 e SCRUM-49 · orientação


def test_ct_06_01_07_aceite_bloqueia_o_campo_do_aluno(cenario):
    """CT-06.01-07: depois do aceite o vínculo fica ACEITA no cadastro do aluno."""
    tcc = _rascunho(cenario).json()
    _aceitar(cenario)
    assert cenario["aluno"].get(f"/api/v1/tccs/{tcc['id']}").json()["orientador"]["status"] == "ACEITA"
    assert cenario["olga"].get("/api/v1/orientacoes?status=PENDENTE").json() == []


def test_ct_06_01_08_recusa_sem_motivo_e_recusada(cenario):
    """CT-06.01-08."""
    _rascunho(cenario)
    pedido = cenario["olga"].get("/api/v1/orientacoes?status=PENDENTE").json()[0]
    r = cenario["olga"].post(f"/api/v1/orientacoes/{pedido['id']}/resposta", json={"decisao": "RECUSAR"})
    assert r.status_code == 400 and "motivo" in r.json()["campos"]


def test_ct_06_01_09_e_06_03_05_recusa_com_motivo_e_nova_indicacao(cenario, db):
    """CT-06.01-09, CT-06.03-02 e CT-06.03-05: o aluno vê a recusa, fica impedido e indica outro."""
    tcc = _rascunho(cenario).json()
    pedido = cenario["olga"].get("/api/v1/orientacoes?status=PENDENTE").json()[0]
    r = cenario["olga"].post(f"/api/v1/orientacoes/{pedido['id']}/resposta",
                             json={"decisao": "RECUSAR", "motivo": "Sem vaga neste semestre."})
    assert r.status_code == 200
    visto = cenario["aluno"].get(f"/api/v1/tccs/{tcc['id']}").json()
    assert visto["orientador"]["status"] == "RECUSADA"
    assert visto["orientador"]["motivo_recusa"] == "Sem vaga neste semestre."
    assert "Indique o orientador." in visto["pendencias"]
    corpo = {"titulo": tcc["titulo"], "resumo": tcc["resumo"], "palavras_chave": tcc["palavras_chave"],
             "area_id": tcc["area"]["id"], "modalidade": "MONOGRAFIA", "orientador_id": cenario["outro"]["id"]}
    assert cenario["aluno"].put(f"/api/v1/tccs/{tcc['id']}", json=corpo).status_code == 200
    assert cenario["otto"].get("/api/v1/orientacoes?status=PENDENTE").json()
    status = {o.status for o in db.scalars(select(Orientacao).where(Orientacao.tcc_id == tcc["id"]))}
    assert {"RECUSADA", "PENDENTE"} <= status  # a recusa continua no histórico


def test_ct_06_01_10_troca_com_pedido_pendente_move_o_pedido(cenario):
    """CT-06.01-10."""
    tcc = _rascunho(cenario).json()
    assert cenario["olga"].get("/api/v1/orientacoes?status=PENDENTE").json()
    corpo = {"titulo": tcc["titulo"], "resumo": tcc["resumo"], "palavras_chave": tcc["palavras_chave"],
             "area_id": tcc["area"]["id"], "modalidade": "MONOGRAFIA", "orientador_id": cenario["outro"]["id"]}
    assert cenario["aluno"].put(f"/api/v1/tccs/{tcc['id']}", json=corpo).status_code == 200
    assert cenario["olga"].get("/api/v1/orientacoes?status=PENDENTE").json() == []
    assert len(cenario["otto"].get("/api/v1/orientacoes?status=PENDENTE").json()) == 1


def test_ct_06_02_04_coorientador_igual_ao_orientador_e_recusado(cenario):
    """CT-06.02-04 e CA-04."""
    r = _rascunho(cenario, coorientador_id=cenario["orientador"]["id"])
    assert r.status_code == 422


def test_ct_06_02_05_trocar_o_coorientador_preserva_o_anterior(cenario, db):
    """CT-06.02-02 e CT-06.02-05."""
    tcc = _rascunho(cenario, coorientador_id=cenario["outro"]["id"]).json()
    assert tcc["coorientador"]["status"] == "PENDENTE"
    corpo = {"titulo": tcc["titulo"], "resumo": tcc["resumo"], "palavras_chave": tcc["palavras_chave"],
             "area_id": tcc["area"]["id"], "modalidade": "MONOGRAFIA", "orientador_id": cenario["orientador"]["id"],
             "coorientador_id": None}
    cenario["aluno"].put(f"/api/v1/tccs/{tcc['id']}", json=corpo)
    vinculos = db.scalars(select(Orientacao).where(Orientacao.tcc_id == tcc["id"],
                                                   Orientacao.papel == "COORIENTADOR")).all()
    assert vinculos and all(v.encerrado_em or v.status == "SUBSTITUIDA" for v in vinculos)


def test_ct_06_03_03_outro_orientador_nao_decide_o_pedido(cenario):
    """CT-06.03-03: o código responde 404, sem revelar o pedido (RN07)."""
    _rascunho(cenario)
    pedido = cenario["olga"].get("/api/v1/orientacoes?status=PENDENTE").json()[0]
    r = cenario["otto"].post(f"/api/v1/orientacoes/{pedido['id']}/resposta", json={"decisao": "ACEITAR"})
    assert r.status_code in (403, 404)


def test_ct_06_03_04_pedido_ja_aceito_nao_e_decidido_de_novo(cenario):
    """CT-06.03-04 e CA-04."""
    _rascunho(cenario)
    pedido = _aceitar(cenario)
    r = cenario["olga"].post(f"/api/v1/orientacoes/{pedido['id']}/resposta",
                             json={"decisao": "RECUSAR", "motivo": "Mudei de ideia."})
    assert r.status_code == 409 and r.json()["detail"] == "Esta solicitação já foi respondida."


def test_ct_06_03_06_decisao_fica_no_log(cenario, db):
    """CT-06.03-06."""
    _rascunho(cenario)
    pedido = _aceitar(cenario)
    linha = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "responder_orientacao",
                                                 LogAuditoria.entidade_id == pedido["tcc"]["id"]))
    assert linha and linha.valor_anterior == "PENDENTE" and linha.valor_novo == "ACEITA" and linha.usuario_id


# ---------------------------------------------------------------- SCRUM-42, SCRUM-43 e SCRUM-44 · turmas


def test_ct_08_01_02_periodo_fora_do_formato_ou_fim_antes_do_inicio(coord):
    """CT-08.01-02 e CA-02."""
    r = coord.post("/api/v1/periodos", json={"codigo": "2026-2", "inicio": "2026-08-01", "fim": "2026-12-20"})
    assert r.status_code == 400
    r = coord.post("/api/v1/periodos", json={"codigo": "2026/2", "inicio": "2026-12-20", "fim": "2026-08-01"})
    assert r.status_code == 400
    coord.post("/api/v1/periodos", json={"codigo": "2026/2", "inicio": "2026-08-01", "fim": "2026-12-20"})
    r = coord.post("/api/v1/periodos", json={"codigo": "2026/2", "inicio": "2026-08-01", "fim": "2026-12-20"})
    assert r.status_code == 409


def test_ct_08_01_03_turma_igual_e_recusada(coord, cenario):
    """CT-08.01-03 e CA-03."""
    t = cenario["turma"]
    r = coord.post("/api/v1/turmas", json={"disciplina": "TCC1", "curso_id": 1, "periodo_id": t["periodo_id"]
                                           if "periodo_id" in t else cenario["periodo"]["id"],
                                           "professor_id": t["professor"]["id"]})
    assert r.status_code == 409


def test_ct_08_01_04_turma_de_tcc2_tem_o_orientador_como_responsavel(coord, cenario):
    """CT-08.01-04 e CA-04: no TCC2 o docente é orientador; professor sem esse perfil é recusado."""
    r = coord.post("/api/v1/turmas", json={"disciplina": "TCC2", "curso_id": 1, "periodo_id": cenario["periodo"]["id"],
                                           "professor_id": cenario["orientador"]["id"]})
    assert r.status_code == 201 and r.json()["professor"]["id"] == cenario["orientador"]["id"]
    professor = cenario["turma"]["professor"]["id"]
    r = coord.post("/api/v1/turmas", json={"disciplina": "TCC2", "curso_id": 1, "periodo_id": cenario["periodo"]["id"],
                                           "professor_id": professor})
    assert r.status_code == 400 and "professor_id" in r.json()["campos"]


def test_ct_08_01_06_criacao_da_turma_fica_no_log(cenario, db):
    """CT-08.01-06 e CA-05."""
    linha = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "criar_turma"))
    assert linha and linha.usuario_id and linha.criado_em


def test_ct_08_02_03_e_08_03_07_so_a_coordenacao_inclui_e_muda_situacao(cenario, caixa):
    """CT-08.02-03 e CT-08.03-07."""
    turma = cenario["turma"]["id"]
    paulo = ativar(caixa, PROFESSOR["email"])
    assert paulo.post(f"/api/v1/turmas/{turma}/alunos", json={"aluno_id": 1}).status_code == 403
    assert cenario["aluno"].post(f"/api/v1/turmas/{turma}/alunos", json={"aluno_id": 1}).status_code == 403
    assert paulo.patch(f"/api/v1/turmas/{turma}/alunos/1", json={"situacao": "DESISTENTE"}).status_code == 403


def test_ct_08_02_04_etapa_e_periodo_vem_da_turma(cenario):
    """CT-08.02-04 e CA-04."""
    tcc = _rascunho(cenario).json()
    assert tcc["etapa"] == "TCC1" and tcc["turma"]["periodo"] == "2026/2"


def test_ct_08_02_05_e_08_03_06_turma_encerrada_bloqueia_inclusao_e_situacao(coord, cenario, db):
    """CT-08.02-05 e CT-08.03-06 (o encerramento, RBN08.05, ainda é previsto: o teste encerra pelo banco)."""
    turma = db.get(Turma, cenario["turma"]["id"])
    matricula = turma.matriculas[0].id
    turma.encerrada_em = agora()
    db.commit()
    novo = coord.post("/api/v1/alunos", json={"nome": "Caio Aluno", "email": "caio@exemplo.com",
                                              "matricula": "24150066", "curso_id": 1}).json()
    r = coord.post(f"/api/v1/turmas/{turma.id}/alunos", json={"aluno_id": novo["id"]})
    assert r.status_code == 409 and r.json()["detail"] == "Turma encerrada não aceita novos alunos."
    r = coord.patch(f"/api/v1/turmas/{turma.id}/alunos/{matricula}", json={"situacao": "DESISTENTE"})
    assert r.status_code == 409


def test_ct_08_02_06_inclusao_fica_no_log(cenario, db):
    """CT-08.02-06."""
    assert db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "incluir_aluno_turma"))


def test_ct_08_03_01_a_08_03_04_situacao_gravada_e_elegibilidade(coord, cenario, db):
    """CT-08.03-01 a CT-08.03-04: Desistente com data; sem rota de exclusão; volta a Matriculado e envia."""
    turma = cenario["turma"]["id"]
    matricula = db.scalar(select(MatriculaTurma).where(MatriculaTurma.turma_id == turma))
    r = coord.patch(f"/api/v1/turmas/{turma}/alunos/{matricula.id}", json={"situacao": "DESISTENTE"})
    assert r.status_code == 200
    db.expire_all()
    assert db.get(MatriculaTurma, matricula.id).situacao_alterada_em is not None
    assert coord.delete(f"/api/v1/turmas/{turma}/alunos/{matricula.id}").status_code in (404, 405)
    tcc = _rascunho(cenario)
    assert tcc.status_code == 403
    coord.patch(f"/api/v1/turmas/{turma}/alunos/{matricula.id}", json={"situacao": "MATRICULADO"})
    tcc = _rascunho(cenario).json()
    _aceitar(cenario)
    assert cenario["aluno"].post(f"/api/v1/tccs/{tcc['id']}/submissao").status_code == 200


def test_ct_08_03_05_edicao_dos_dados_do_aluno_e_auditada(coord, cenario, db):
    """CT-08.03-05."""
    aluno = db.scalar(select(Usuario).where(Usuario.email == ALUNO["email"]))
    r = coord.put(f"/api/v1/usuarios/{aluno.id}", json={"nome": "Ana Ribeiro Lima"})
    assert r.status_code == 200
    assert db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "editar_usuario",
                                                LogAuditoria.campo == "nome",
                                                LogAuditoria.valor_novo == "Ana Ribeiro Lima"))


def test_ct_08_06_02_e_08_06_03_sem_turma_e_sem_sessao(coord, caixa, anonimo):
    """CT-08.06-02 e CT-08.06-03."""
    coord.post("/api/v1/docentes", json=DOCENTE)
    sem_turma = ativar(caixa, DOCENTE["email"])
    assert sem_turma.get("/api/v1/turmas/minhas").json() == []
    assert anonimo.get("/api/v1/turmas/minhas").status_code == 401


# ---------------------------------------------------------------- SCRUM-50 · lista de TCCs


def test_ct_05_01_02_e_05_01_03_cada_um_ve_so_o_seu_escopo(cenario, coord, caixa):
    """CT-05.01-02, CT-05.01-03 e CT-05.01-05."""
    tcc = _rascunho(cenario).json()
    assert [t["id"] for t in cenario["aluno"].get("/api/v1/tccs").json()] == [tcc["id"]]
    assert [t["id"] for t in cenario["olga"].get("/api/v1/tccs").json()] == [tcc["id"]]
    assert cenario["otto"].get("/api/v1/tccs").json() == []


def test_ct_05_01_04_situacao_editorial_separada_da_academica(cenario):
    """CT-05.01-04 e CA-03."""
    _rascunho(cenario, modalidade="ARTIGO", artigo={**ARTIGO, "situacao": "ACEITO"})
    [t] = cenario["aluno"].get("/api/v1/tccs").json()
    assert t["situacao"] == "RASCUNHO" and t["artigo"]["situacao"] == "ACEITO"


def test_ct_05_01_06_membro_sem_vinculo_nao_ve_tcc(cenario, coord, caixa):
    """CT-05.01-06 e CA-05."""
    _rascunho(cenario)
    coord.post("/api/v1/docentes", json={**DOCENTE, "email": "banca@exemplo.com", "perfis": ["membro_banca"],
                                         "cargo": "professor"})
    banca = ativar(caixa, "banca@exemplo.com")
    assert banca.get("/api/v1/tccs").json() == []


# ---------------------------------------------------------------- SCRUM-45 · TCC2 a partir do TCC1


def test_ct_08_04_01_a_08_04_05_tcc2_vem_preenchido_com_o_tcc1(coord, cenario, db):
    """CT-08.04-01, 02, 04 e 05: o TCC2 traz título, área, modalidade e orientador do TCC1; o TCC1 não muda."""
    tcc1 = _rascunho(cenario).json()
    _aceitar(cenario)
    protocolo1 = cenario["aluno"].post(f"/api/v1/tccs/{tcc1['id']}/submissao").json()["protocolo"]
    # o TCC1 fica num período já encerrado (2026/1) e o aluno entra numa turma de TCC2 no período em curso
    periodo1 = db.get(Turma, cenario["turma"]["id"]).periodo
    periodo1.codigo, periodo1.inicio, periodo1.fim = "2026/1", date(2026, 2, 1), date(2026, 6, 30)
    db.commit()
    periodo2 = coord.post("/api/v1/periodos", json={"codigo": "2026/2", "inicio": "2026-08-01",
                                                    "fim": "2026-12-20"}).json()
    turma2 = coord.post("/api/v1/turmas", json={"disciplina": "TCC2", "curso_id": 1, "periodo_id": periodo2["id"],
                                                "professor_id": cenario["orientador"]["id"]}).json()
    aluno_id = db.scalar(select(MatriculaTurma).where(MatriculaTurma.turma_id == cenario["turma"]["id"])).aluno_id
    assert coord.post(f"/api/v1/turmas/{turma2['id']}/alunos", json={"aluno_id": aluno_id}).status_code == 201

    f = cenario["aluno"].get("/api/v1/tccs/formulario").json()
    assert f["turma"]["disciplina"] == "TCC2" and f["tcc"] is None
    assert f["origem"]["titulo"] == tcc1["titulo"] and f["origem"]["orientador_id"] == cenario["orientador"]["id"]
    tcc2 = _rascunho(cenario, titulo="Título do TCC2").json()
    assert tcc2["etapa"] == "TCC2" and tcc2["id"] != tcc1["id"]
    db.expire_all()
    assert db.get(Tcc, tcc1["id"]).titulo == tcc1["titulo"] and db.get(Tcc, tcc1["id"]).protocolo == protocolo1


def test_ct_08_04_04_aluno_de_tcc2_sem_tcc1_abre_em_branco(coord, cenario, db):
    """CT-08.04-04."""
    turma = db.get(Turma, cenario["turma"]["id"])
    turma.disciplina = "TCC2"
    db.commit()
    f = cenario["aluno"].get("/api/v1/tccs/formulario").json()
    assert f["origem"] is None and f["tcc"] is None
