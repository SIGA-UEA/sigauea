"""SCRUM-32 (RBN01.12, conta limitada do membro externo da banca) e SCRUM-33 (RBN01.13, conta limitada do
coorientador externo).

Cada teste cita o caso de teste da ficha (CT-01.12-xx e CT-01.13-xx) ou a decisão registrada no documento de
divergências (32-a, 32-c...). O cenário é montado pela API: a fixture `banca` da SCRUM-59 (TCC de EC aprovado,
Olga orienta; Otto, Paulo e Ricardo são docentes ativos). A Ana, da UFAM, é a convidada externa. Os e-mails
ficam na fixture `caixa`, que guarda o token do link.
"""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import config
from app.database import agora
from app.main import app
from app.models import AcessoLimitado, LogAuditoria, ResultadoDefesa, TokenUsuario, Usuario
from tests.conftest import SENHA, ativar
from tests.test_avaliacao import RESULTADO, _enviar, depois_da_defesa  # noqa: F401  (depois_da_defesa é fixture)
from tests.test_defesas_banca import _agendar, _membros, banca  # noqa: F401  (banca é fixture)
from tests.test_tcc import cenario  # noqa: F401  (fixture usada por banca)

ANA = {"nome": "Ana Externa", "email": "ana@ufam.edu.br", "instituicao": "UFAM"}
MOTIVO = {"justificativa": "A aluna pediu o cancelamento."}


def _com_ana(b) -> list[dict]:
    """Banca com a Olga (orientadora), o Otto e a Ana (avaliadores)."""
    return _membros(b, avaliadores=("otto",)) + [{"papel": "AVALIADOR", "externo": ANA}]


@pytest.fixture
def defesa(banca):
    r = _agendar(banca, membros=_com_ana(banca))
    assert r.status_code == 201, r.json()
    return {**banca, "defesa": r.json()}


def _ana(db) -> Usuario:
    return db.scalar(select(Usuario).where(Usuario.email == ANA["email"]))


def _acessos(db, usuario_id: int) -> list[AcessoLimitado]:
    db.expire_all()
    return list(db.scalars(select(AcessoLimitado).where(AcessoLimitado.usuario_id == usuario_id).order_by(AcessoLimitado.id)))


def _convites(caixa, email: str) -> list[dict]:
    return [m for m in caixa if m["para"] == email and m["assunto"].startswith("Convite para banca")]


def _vaga(d, quem_id: int) -> dict:
    return next(m for m in d["defesa"]["membros"] if m["pessoa"]["id"] == quem_id)


# ---------------------------------------------------------------- SCRUM-32 · RBN01.12 · geração (CA-01)


def test_ct_01_12_01_conta_limitada_criada_e_link_enviado_no_convite(defesa, caixa, db):
    """CT-01.12-01 (CA-01, decisões 32-a, 32-c e 32-h): a confirmação da defesa cria a conta sem senha e o acesso
    limitado àquela defesa, e o convite leva o link de ativação; com ele, a Ana define a senha e entra."""
    ana = _ana(db)
    assert ana.senha_hash is None and not ana.ativo
    [acesso] = _acessos(db, ana.id)
    assert (acesso.escopo, acesso.defesa_id, acesso.tcc_id) == ("BANCA", defesa["defesa"]["id"], None)
    assert acesso.expira_em is None and acesso.revogado_em is None  # o prazo nasce com o resultado (32-d)

    [convite] = _convites(caixa, ANA["email"])
    assert convite["token"]  # o link de ativação vai no próprio convite
    cliente = ativar(caixa, ANA["email"])
    assert cliente.get("/api/v1/auth/me").json()["email"] == ANA["email"]


def test_membro_interno_nao_recebe_acesso_limitado(defesa, db):
    """Só a pessoa externa tem acesso limitado; os docentes da UEA continuam como estão."""
    assert db.scalars(select(AcessoLimitado.usuario_id)).all() == [_ana(db).id]


def test_ct_01_12_05_aluno_nao_gera_a_conta(banca, db):
    """CT-01.12-05 (CA-04, decisão 59-f): a conta nasce na confirmação da defesa, que o aluno não faz (403)."""
    r = _agendar(banca, quem="aluno", membros=_com_ana(banca))
    assert r.status_code == 403
    assert _ana(db) is None and db.scalars(select(AcessoLimitado)).all() == []


def test_ct_01_12_06_geracao_fica_no_log(defesa, db):
    """CT-01.12-06 (CA-05, RNF03): responsável, data e hora, defesa e evento."""
    log = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "criar_acesso_banca"))
    assert log.usuario_id == defesa["ids"]["olga"] and log.criado_em is not None
    assert log.entidade == "acesso_limitado" and log.entidade_id == _acessos(db, _ana(db).id)[0].id
    assert log.valor_novo.startswith(f"Ana Externa · Defesa {defesa['defesa']['id']} (")


# ---------------------------------------------------------------- link vencido, troca e cancelamento


def test_link_vencido_e_renovado_pelo_reenvio_do_convite(defesa, caixa, db):
    """Decisão 32-b: o link vale 48 horas; o reenvio do convite manda um link novo, e o antigo deixa de valer."""
    antigo = _convites(caixa, ANA["email"])[-1]["token"]
    for token in db.scalars(select(TokenUsuario).where(TokenUsuario.usuario_id == _ana(db).id)):
        token.expira_em = agora() - timedelta(minutes=1)
    db.commit()
    anonimo = TestClient(app)
    assert anonimo.post("/api/v1/auth/validar-token", json={"token": antigo, "tipo": "ativacao"}).json() == {
        "valido": False, "motivo": "expirado"}

    vaga = _vaga(defesa, _ana(db).id)
    r = defesa["olga"].post(f"/api/v1/defesas/{defesa['defesa']['id']}/banca/{vaga['id']}/convite")
    assert r.status_code == 200
    novo = _convites(caixa, ANA["email"])[-1]["token"]
    assert novo != antigo
    assert ativar(caixa, ANA["email"]).get("/api/v1/auth/me").status_code == 200


def test_quem_ja_ativou_recebe_o_endereco_de_entrada(defesa, caixa, db):
    """Decisão 32-h: quem já tem senha não recebe outro link de ativação, só o endereço de entrada."""
    ativar(caixa, ANA["email"])
    vaga = _vaga(defesa, _ana(db).id)
    defesa["olga"].post(f"/api/v1/defesas/{defesa['defesa']['id']}/banca/{vaga['id']}/convite")
    assert _convites(caixa, ANA["email"])[-1]["token"] is None


def test_trocar_a_ana_revoga_o_acesso_e_a_volta_cria_outro(defesa, caixa, db):
    """Decisões 32-c e 32-k: quem sai da banca perde o acesso; quem entra (mesmo com conta) ganha um novo."""
    ana = _ana(db)
    url = f"/api/v1/defesas/{defesa['defesa']['id']}/banca/{_vaga(defesa, ana.id)['id']}"
    assert defesa["olga"].put(url, json={"usuario_id": defesa["ids"]["paulo"]}).status_code == 200
    [antigo] = _acessos(db, ana.id)
    assert antigo.revogado_em is not None
    assert db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "revogar_acesso")).entidade_id == antigo.id

    assert defesa["olga"].put(url, json={"externo": ANA}).status_code == 200
    antigo, novo = _acessos(db, ana.id)
    assert novo.revogado_em is None and novo.defesa_id == defesa["defesa"]["id"]
    assert len(_convites(caixa, ANA["email"])) == 2


def test_cancelar_a_defesa_revoga_o_acesso(defesa, db):
    """Decisão 32-k: a defesa cancelada encerra o acesso de todos os membros externos."""
    r = defesa["olga"].post(f"/api/v1/defesas/{defesa['defesa']['id']}/cancelamento", json=MOTIVO)
    assert r.status_code == 200
    assert [a.revogado_em is not None for a in _acessos(db, _ana(db).id)] == [True]


def test_conta_desligada_volta_com_um_acesso_novo(defesa, caixa, db):
    """Decisão 32-f: a conta desligada por falta de acesso (ativo falso, sem inativação da coordenação) volta a
    entrar quando a pessoa ganha um acesso novo."""
    ativar(caixa, ANA["email"])
    ana = _ana(db)
    url = f"/api/v1/defesas/{defesa['defesa']['id']}/banca/{_vaga(defesa, ana.id)['id']}"
    assert defesa["olga"].put(url, json={"usuario_id": defesa["ids"]["paulo"]}).status_code == 200
    ana.ativo = False  # o desligamento é da rotina de expiração (etapa 3); aqui só o efeito
    db.commit()
    entrar = {"email": ANA["email"], "senha": SENHA}
    assert TestClient(app).post("/api/v1/auth/login", json=entrar).status_code == 401
    assert defesa["olga"].put(url, json={"externo": ANA}).status_code == 200
    assert TestClient(app).post("/api/v1/auth/login", json=entrar).status_code == 200


# ---------------------------------------------------------------- SCRUM-32 · RBN01.12 · escopo (CA-02)


@pytest.fixture
def ana(defesa, caixa):
    """A Ana com a conta ativada e logada."""
    return ativar(caixa, ANA["email"])


def test_ana_ve_so_o_tcc_e_a_avaliacao_da_sua_defesa(defesa, ana):
    """CA-02 e decisão 32-33-a: a lista e a página do TCC da defesa, e a avaliação dela (lançar nota e parecer)."""
    tcc, defesa_id = defesa["tcc"]["id"], defesa["defesa"]["id"]
    assert [t["id"] for t in ana.get("/api/v1/tccs").json()] == [tcc]
    assert ana.get(f"/api/v1/tccs/{tcc}").status_code == 200
    assert ana.get(f"/api/v1/defesas/{defesa_id}/avaliacao").status_code == 200
    assert ana.put(f"/api/v1/defesas/{defesa_id}/avaliacao", json={"criterios": []}).status_code == 200


def test_me_diz_que_e_externa_e_traz_os_acessos(defesa, ana):
    """Decisões 32-33-d e opção A: tipo "externo" e a defesa que ela pode abrir, para a tela achar a avaliação."""
    eu = ana.get("/api/v1/auth/me").json()
    assert eu["tipo"] == "externo"
    assert eu["acessos"] == [{"escopo": "BANCA", "tcc_id": defesa["tcc"]["id"], "defesa_id": defesa["defesa"]["id"]}]
    assert ana.get("/api/v1/usuarios/me").json()["acessos"] == eu["acessos"]


def test_docente_continua_sem_acessos_e_com_tipo_docente(defesa):
    eu = defesa["otto"].get("/api/v1/auth/me").json()
    assert eu["tipo"] == "docente" and eu["acessos"] == []


@pytest.mark.parametrize("rota", [
    "/api/v1/agenda", "/api/v1/turmas/minhas", "/api/v1/periodos", "/api/v1/perfis", "/api/v1/docentes",
    "/api/v1/orientacoes", "/api/v1/instrumento-avaliacao", "/api/v1/cadastros",
])
def test_ct_01_12_03_telas_de_gestao_e_agenda_negadas(defesa, ana, rota):
    """CT-01.12-03 (CA-02, decisão 32-33-a): fora da lista, 403, inclusive a Agenda."""
    r = ana.get(rota)
    assert r.status_code == 403 and r.json()["detail"] == "Esta conta só acessa a defesa ou o TCC para os quais foi convidada."


def test_rotas_da_propria_defesa_fora_da_lista_tambem_sao_negadas(defesa, ana):
    """A banca (com e-mails e docentes), a presença e o resultado da própria defesa ficam de fora (32-33-a)."""
    tcc, defesa_id = defesa["tcc"]["id"], defesa["defesa"]["id"]
    for rota in (f"/api/v1/tccs/{tcc}/banca", f"/api/v1/defesas/{defesa_id}/ocorrencias",
                 f"/api/v1/defesas/{defesa_id}/resultado", f"/api/v1/defesas/{defesa_id}/divulgacao"):
        assert ana.get(rota).status_code == 403, rota


def test_ct_01_12_02_outra_defesa_recebe_403(defesa, ana):
    """CT-01.12-02 (CA-02, E2, decisão 32-33-b): defesa e TCC fora do escopo da Ana respondem 403, e não 404,
    exista o registro ou não (a resposta não revela se ele existe)."""
    fora = defesa["defesa"]["id"] + 1, defesa["tcc"]["id"] + 1
    assert ana.get(f"/api/v1/defesas/{fora[0]}/avaliacao").status_code == 403
    assert ana.put(f"/api/v1/defesas/{fora[0]}/avaliacao", json={"criterios": []}).status_code == 403
    assert ana.get(f"/api/v1/tccs/{fora[1]}").status_code == 403


def test_foto_so_a_propria(defesa, ana, db):
    """O menu mostra o avatar de quem entrou; a foto dos outros fica de fora."""
    assert ana.get(f"/api/v1/usuarios/{_ana(db).id}/foto").status_code != 403
    assert ana.get(f"/api/v1/usuarios/{defesa['ids']['olga']}/foto").status_code == 403


def test_membro_interno_da_banca_nao_muda(defesa):
    """O perfil membro_banca também é de docentes; a restrição vale só para quem tem usuario_externo."""
    assert defesa["otto"].get("/api/v1/agenda").status_code == 200
    assert defesa["otto"].get(f"/api/v1/tccs/{defesa['tcc']['id']}/banca").status_code == 200


# ---------------------------------------------------------------- SCRUM-32 · RBN01.12 · expiração (CA-03)

CHAVE = {"X-Chave-Tarefas": "segredo-certo"}


@pytest.fixture
def confirmada(defesa, ana, depois_da_defesa, monkeypatch, db):
    """Defesa realizada, as três avaliações enviadas (Olga, Otto e Ana) e o resultado confirmado (SCRUM-70)."""
    monkeypatch.setattr(config, "TAREFAS_CHAVE", "segredo-certo")
    d = {**defesa, "ana": ana}
    for quem in ("olga", "otto", "ana"):
        assert _enviar(d, quem).status_code == 200, quem
    r = defesa["olga"].post(f"/api/v1/defesas/{defesa['defesa']['id']}/resultado", json=RESULTADO)
    assert r.status_code == 200, r.json()
    return d


def _vencer(db, ana_id: int):
    """Os 7 dias passaram: o prazo gravado na confirmação fica no passado."""
    for acesso in _acessos(db, ana_id):
        acesso.expira_em = agora() - timedelta(minutes=1)
    db.commit()


def _rotina():
    return TestClient(app).post("/api/v1/tarefas/expirar-acessos", headers=CHAVE)


def test_confirmar_o_resultado_marca_o_prazo_de_7_dias(confirmada, db):
    """Decisão 32-d (opção A): expira_em = confirmação do resultado + 7 dias."""
    resultado = db.scalar(select(ResultadoDefesa).where(ResultadoDefesa.defesa_id == confirmada["defesa"]["id"]))
    [acesso] = _acessos(db, _ana(db).id)
    assert acesso.expira_em == resultado.confirmado_em + timedelta(days=7)


def test_retificar_o_resultado_nao_reinicia_o_prazo(confirmada, db):
    """Decisão 32-d: o prazo conta da primeira confirmação."""
    antes = _acessos(db, _ana(db).id)[0].expira_em
    r = confirmada["olga"].post(f"/api/v1/defesas/{confirmada['defesa']['id']}/resultado/retificacao",
                                json={"resultado": "APROVADO_COM_CORRECOES", "motivo": "Faltou registrar as correções."})
    assert r.status_code == 200, r.json()
    assert _acessos(db, _ana(db).id)[0].expira_em == antes


def test_antes_dos_7_dias_a_rotina_nao_mexe_em_nada(confirmada, db):
    assert _rotina().json() == {"expirados": 0, "contas_desligadas": 0}
    assert confirmada["ana"].get("/api/v1/auth/me").status_code == 200


def test_ct_01_12_04_depois_de_7_dias_a_conta_e_desativada(confirmada, db):
    """CT-01.12-04 (CA-03): resultado confirmado há 7 dias; a rotina desativa a conta, encerra a sessão aberta e
    o login passa a ser negado. Rodar de novo não repete nada."""
    _vencer(db, _ana(db).id)
    assert _rotina().json() == {"expirados": 1, "contas_desligadas": 1}
    db.expire_all()
    assert _ana(db).ativo is False and _ana(db).inativado_em is None
    assert confirmada["ana"].get("/api/v1/auth/me").status_code == 401  # a sessão aberta caiu
    entrar = {"email": ANA["email"], "senha": SENHA}
    assert TestClient(app).post("/api/v1/auth/login", json=entrar).status_code == 401
    assert _rotina().json() == {"expirados": 0, "contas_desligadas": 0}


def test_ct_01_12_06_expiracao_fica_no_log(confirmada, db):
    """CT-01.12-06 (CA-05, RNF03): a expiração registra data e hora, defesa e evento; o responsável é a rotina."""
    _vencer(db, _ana(db).id)
    _rotina()
    expirou = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "expirar_acesso"))
    assert expirou.usuario_id is None and expirou.criado_em is not None
    assert expirou.valor_anterior.startswith(f"Ana Externa · Defesa {confirmada['defesa']['id']} (")
    desligou = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "desligar_conta_externa"))
    assert desligou.entidade_id == _ana(db).id


def test_conta_com_outro_acesso_valido_continua_ativa(confirmada, db):
    """Decisão 32-f: vence só o acesso; a conta segue ativa enquanto houver outro (aqui, uma coorientação)."""
    db.add(AcessoLimitado(usuario_id=_ana(db).id, escopo="COORIENTACAO", tcc_id=confirmada["tcc"]["id"]))
    db.commit()
    _vencer_banca = [a for a in _acessos(db, _ana(db).id) if a.escopo == "BANCA"]
    _vencer_banca[0].expira_em = agora() - timedelta(minutes=1)
    db.commit()
    assert _rotina().json() == {"expirados": 1, "contas_desligadas": 0}
    db.expire_all()
    assert _ana(db).ativo is True


def test_revogar_o_ultimo_acesso_desliga_a_conta(defesa, ana, db):
    """Decisões 32-f e 32-k: com a defesa cancelada, a Ana fica sem acesso e a conta é desligada na hora."""
    defesa["olga"].post(f"/api/v1/defesas/{defesa['defesa']['id']}/cancelamento", json=MOTIVO)
    db.expire_all()
    assert _ana(db).ativo is False
    assert ana.get("/api/v1/auth/me").status_code == 401


def test_rotina_exige_a_chave(monkeypatch):
    monkeypatch.setattr(config, "TAREFAS_CHAVE", "segredo-certo")
    assert TestClient(app).post("/api/v1/tarefas/expirar-acessos").status_code == 401
    monkeypatch.setattr(config, "TAREFAS_CHAVE", "")
    assert TestClient(app).post("/api/v1/tarefas/expirar-acessos", headers=CHAVE).status_code == 503