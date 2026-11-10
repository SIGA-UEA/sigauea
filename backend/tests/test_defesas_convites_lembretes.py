"""Sprint S04 · SCRUM-63 (RBN09.05, convite por e-mail) e SCRUM-64 (RBN09.06, lembrete da véspera).

Os e-mails não saem de verdade: a fixture `cartas` troca o envio por uma lista com destinatário,
assunto e corpo. A fixture `banca` é a da SCRUM-59 (Olga orienta; Otto e Paulo avaliam).
"""

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app import config
from app.models import BancaMembro, Defesa, LogAuditoria, NotificacaoEmail
from app.services import email, lembretes
from tests.test_defesas_banca import DIA, _agendar, _membros, banca  # noqa: F401  (banca é fixture)
from tests.conftest import ALUNO
from tests.test_tcc import cenario  # noqa: F401  (fixture usada por banca)

ALUNO_EMAIL = ALUNO["email"]

VESPERA = date.fromisoformat(DIA) - timedelta(days=1)


class Cartas(list):
    """Lista de e-mails enviados; `falhar` guarda os endereços cujo envio dá erro."""

    falhar: set[str]


@pytest.fixture
def cartas(banca, monkeypatch):
    """E-mails "enviados" a partir daqui. `falhar` guarda os endereços cujo envio dá erro."""
    enviados = Cartas()
    enviados.falhar = falhar = set()

    def entregar(destinatario, assunto, corpo):
        if destinatario in falhar:
            raise RuntimeError("servidor de e-mail fora do ar")
        enviados.append({"para": destinatario, "assunto": assunto, "corpo": corpo})

    monkeypatch.setattr(email, "entregar", entregar)
    return enviados


def _convites(cartas):
    return [c for c in cartas if c["assunto"].startswith("Convite para banca")]


def _lembretes(cartas):
    return [c for c in cartas if c["assunto"].startswith("Lembrete")]


def _email(banca, quem):
    return banca[quem].get("/api/v1/auth/me").json()["email"]


def _banca(b):
    return b["olga"].get(f"/api/v1/tccs/{b['tcc']['id']}/banca").json()["defesa"]


# ================================================================ SCRUM-63 · RBN09.05 · convite


def test_ca_01_cada_membro_recebe_o_convite_e_a_vaga_mostra_enviado(banca, cartas):
    r = _agendar(banca)
    assert r.status_code == 201
    assert len(_convites(cartas)) == 3  # orientadora e dois avaliadores
    for m in _banca(banca)["membros"]:
        assert m["convite"] == "ENVIADO" and m["convite_enviado_em"] is not None


def test_ca_02_convite_tem_so_os_dados_necessarios(banca, cartas):
    _agendar(banca)
    otto = next(c for c in _convites(cartas) if c["para"] == _email(banca, "otto"))
    corpo = otto["corpo"]
    assert "Detecção de fraudes com aprendizado de máquina" in corpo
    assert date.fromisoformat(DIA).strftime("%d/%m/%Y") in corpo
    assert "14:00 às 14:20" in corpo and "https://meet.exemplo.com/defesa" in corpo
    assert "como avaliador(a)" in corpo
    # nada de nota, matrícula nem contato pessoal do aluno
    assert ALUNO_EMAIL not in corpo and "matrícula" not in corpo.lower() and "nota" not in corpo.lower()


def test_ca_03_falha_no_envio_nao_desfaz_a_defesa_e_o_convite_pode_ser_reenviado(banca, cartas, db):
    otto_email = _email(banca, "otto")
    cartas.falhar.add(otto_email)
    defesa = _agendar(banca).json()
    assert defesa["id"]  # E5: o que foi salvo continua valendo
    otto = next(m for m in _banca(banca)["membros"] if m["email"] == otto_email)
    assert otto["convite"] == "FALHA" and otto["convite_enviado_em"] is None

    cartas.falhar.clear()
    r = banca["olga"].post(f"/api/v1/defesas/{defesa['id']}/banca/{otto['id']}/convite")
    assert r.status_code == 200 and r.json()["convite"] == "PENDENTE"  # o envio é depois da resposta
    assert next(m for m in _banca(banca)["membros"] if m["id"] == otto["id"])["convite"] == "ENVIADO"
    assert [c["para"] for c in _convites(cartas)].count(otto_email) == 1
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Defesa)) == 1  # nada duplicado
    assert db.scalar(select(func.count()).select_from(BancaMembro)) == 3
    assert db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "reenviar_convite_banca")) is not None


def test_suplente_e_avisado_de_que_so_avalia_se_convocado(banca, cartas):
    _agendar(banca, membros=_membros(banca, suplente="ricardo"))
    ricardo = next(c for c in _convites(cartas) if c["para"] == _email(banca, "ricardo"))
    assert "como suplente" in ricardo["corpo"] and "convocado(a)" in ricardo["corpo"]


def test_convidado_externo_recebe_convite_com_link_de_ativacao(banca, cartas):
    """O convite do externo leva o link de ativação da conta limitada (SCRUM-32, decisão 32-h), e não o link
    interno do TCC."""
    externo = {"nome": "Ana Externa", "email": "ana@ufam.edu.br", "instituicao": "UFAM"}
    membros = [m for m in _membros(banca) if m["papel"] == "ORIENTADOR"] + [
        {"papel": "AVALIADOR", "usuario_id": banca["ids"]["otto"]}, {"papel": "AVALIADOR", "externo": externo}]
    assert _agendar(banca, membros=membros).status_code == 201
    carta = next(c for c in _convites(cartas) if c["para"] == "ana@ufam.edu.br")
    assert "/ativar?token=" in carta["corpo"] and "/tccs/" not in carta["corpo"]


def test_troca_de_membro_convida_a_pessoa_nova(banca, cartas):
    defesa = _agendar(banca).json()
    otto = next(m for m in defesa["membros"] if m["pessoa"]["id"] == banca["ids"]["otto"])
    nova = banca["olga"].put(f"/api/v1/defesas/{defesa['id']}/banca/{otto['id']}",
                             json={"usuario_id": banca["ids"]["ricardo"]}).json()
    vaga = next(m for m in nova["membros"] if m["id"] == otto["id"])
    assert vaga["pessoa"]["id"] == banca["ids"]["ricardo"] and vaga["convite"] == "PENDENTE"
    assert next(m for m in _banca(banca)["membros"] if m["id"] == otto["id"])["convite"] == "ENVIADO"
    assert _email(banca, "ricardo") in [c["para"] for c in _convites(cartas)]


def test_convite_antigo_nao_marca_a_pessoa_nova_da_vaga(banca, cartas, db):
    """Se o convite da pessoa anterior só sai depois da troca, a vaga continua sem convite marcado."""
    defesa = _agendar(banca).json()
    membro = db.get(BancaMembro, defesa["membros"][1]["id"])
    antigo = email.registrar(db, membro.usuario, email.TIPO_CONVITE_BANCA, "banca_membro", membro.id)
    membro.usuario_id = banca["ids"]["ricardo"]
    membro.convite_enviado_em = None
    db.commit()
    email.processar(antigo.id, "Convite para banca", "x")
    db.expire_all()
    assert db.get(BancaMembro, membro.id).convite_enviado_em is None


def test_reenvio_so_para_quem_agenda_e_so_com_a_defesa_agendada(banca, cartas, db):
    defesa = _agendar(banca).json()
    membro = defesa["membros"][0]["id"]
    url = f"/api/v1/defesas/{defesa['id']}/banca/{membro}/convite"
    assert banca["aluno"].post(url).status_code == 403
    assert banca["olga"].post(f"/api/v1/defesas/{defesa['id']}/banca/99999/convite").status_code == 404
    db.get(Defesa, defesa["id"]).situacao = "CANCELADA"
    db.commit()
    assert banca["olga"].post(url).status_code == 409


# ================================================================ SCRUM-64 · RBN09.06 · lembrete


@pytest.fixture
def vespera(monkeypatch):
    """Faz "hoje" ser a véspera da defesa (DIA), no fuso de Manaus."""
    monkeypatch.setattr(lembretes, "agora_manaus", lambda: datetime.combine(VESPERA, datetime.min.time()))


def _rodar(db):
    return lembretes.lembrar_defesas_de_amanha(db)


def test_ca_01_defesa_de_amanha_lembra_banca_e_aluno(banca, cartas, db, vespera):
    defesa = _agendar(banca).json()
    resumo = _rodar(db)
    assert resumo == {"data": DIA, "defesas": 1, "enviados": 4, "falhas": 0, "repetidos": 0}
    destinos = sorted(c["para"] for c in _lembretes(cartas))
    assert destinos == sorted([ALUNO_EMAIL, _email(banca, "olga"), _email(banca, "otto"), _email(banca, "paulo")])
    corpo = _lembretes(cartas)[0]["corpo"]
    assert "acontece amanhã" in corpo and "14:00 às 14:20" in corpo and "https://meet.exemplo.com/defesa" in corpo
    db.expire_all()
    assert db.get(Defesa, defesa["id"]).lembrete_enviado_em is not None


def test_ca_02_defesa_cancelada_nao_recebe_lembrete(banca, cartas, db, vespera):
    defesa = _agendar(banca).json()
    db.get(Defesa, defesa["id"]).situacao = "CANCELADA"
    db.commit()
    assert _rodar(db)["defesas"] == 0 and _lembretes(cartas) == []


def test_ca_03_defesa_remarcada_tambem_e_lembrada(banca, cartas, db, vespera):
    defesa = _agendar(banca).json()
    db.get(Defesa, defesa["id"]).situacao = "REMARCADA"
    db.commit()
    assert _rodar(db)["enviados"] == 4


def test_ca_04_rodar_de_novo_no_mesmo_dia_nao_duplica(banca, cartas, db, vespera):
    _agendar(banca)
    _rodar(db)
    segundo = _rodar(db)
    assert segundo["enviados"] == 0 and segundo["repetidos"] == 0
    assert len(_lembretes(cartas)) == 4


def test_ca_05_falha_de_um_nao_impede_os_outros_e_so_ele_e_repetido(banca, cartas, db, vespera):
    _agendar(banca)
    otto = _email(banca, "otto")
    cartas.falhar.add(otto)
    primeiro = _rodar(db)
    assert primeiro["enviados"] == 3 and primeiro["falhas"] == 1
    assert otto not in [c["para"] for c in _lembretes(cartas)]

    cartas.falhar.clear()
    segundo = _rodar(db)
    assert segundo == {"data": DIA, "defesas": 1, "enviados": 1, "falhas": 0, "repetidos": 1}
    assert [c["para"] for c in _lembretes(cartas)].count(otto) == 1
    assert len(_lembretes(cartas)) == 4


def test_falha_e_repetida_no_maximo_tres_vezes(banca, cartas, db, vespera):
    _agendar(banca)
    cartas.falhar.add(_email(banca, "otto"))
    for _ in range(5):
        _rodar(db)
    db.expire_all()
    falha = db.scalar(select(NotificacaoEmail).where(NotificacaoEmail.tipo == "LEMBRETE_DEFESA",
                                                     NotificacaoEmail.status == "falha"))
    assert falha.tentativas == lembretes.MAX_TENTATIVAS


def test_defesa_que_nao_e_amanha_nao_e_lembrada(banca, cartas, db, monkeypatch):
    _agendar(banca)
    dois_dias_antes = VESPERA - timedelta(days=1)
    monkeypatch.setattr(lembretes, "agora_manaus", lambda: datetime.combine(dois_dias_antes, datetime.min.time()))
    assert _rodar(db)["defesas"] == 0 and _lembretes(cartas) == []


# ---------------------------------------------------------------- rota chamada pelo GitHub Actions


def test_rota_desligada_sem_chave_no_servidor(anonimo, monkeypatch):
    monkeypatch.setattr(config, "TAREFAS_CHAVE", "")
    assert anonimo.post("/api/v1/tarefas/lembretes-defesa").status_code == 503


def test_rota_recusa_chave_errada_ou_ausente(anonimo, monkeypatch):
    monkeypatch.setattr(config, "TAREFAS_CHAVE", "segredo-certo")
    assert anonimo.post("/api/v1/tarefas/lembretes-defesa").status_code == 401
    r = anonimo.post("/api/v1/tarefas/lembretes-defesa", headers={"X-Chave-Tarefas": "errado"})
    assert r.status_code == 401


def test_rota_com_a_chave_envia_os_lembretes(banca, cartas, db, vespera, anonimo, monkeypatch):
    _agendar(banca)
    monkeypatch.setattr(config, "TAREFAS_CHAVE", "segredo-certo")
    r = anonimo.post("/api/v1/tarefas/lembretes-defesa", headers={"X-Chave-Tarefas": "segredo-certo"})
    assert r.status_code == 200 and r.json()["enviados"] == 4
