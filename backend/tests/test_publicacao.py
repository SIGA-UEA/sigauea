"""SCRUM-85 a SCRUM-87 (RBN12.01 a RBN12.03): situação editorial, histórico e aviso por e-mail da publicação do
artigo (RN03, RN07 · DS-FL08, DS-FL08-A e DS-FL08-B, TEL15).

Cada teste cita o caso de teste da ficha. Cenário: a Ana cadastra o TCC na modalidade artigo, já submetido à
"Revista de Computação Aplicada" (dados do cadastro, RBN03.02), e a Olga aceita a orientação.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models import LogAuditoria, Tcc
from tests.conftest import ativar
from tests.test_tcc import _aceitar, _rascunho, cenario  # noqa: F401  (cenario é fixture)

REVISTA = "Revista de Computação Aplicada"
HOJE = date.today().isoformat()
OUTRO = {"nome": "Bruno Batista", "email": "bruno@uea.edu.br", "matricula": "24159999", "curso_id": 1}


@pytest.fixture
def artigo(cenario, db):
    r = _rascunho(cenario, modalidade="ARTIGO",
                  artigo={"tipo_veiculo": "PERIODICO", "veiculo": REVISTA, "situacao": "SUBMETIDO", "qualis": "B1"})
    assert r.status_code in (200, 201), r.json()
    _aceitar(cenario)
    return {**cenario, "tcc": r.json(), "url": f"/api/v1/tccs/{r.json()['id']}/publicacao"}


def _registrar(d, quem="aluno", **campos):
    corpo = {"veiculo": REVISTA, "situacao": "EM_REVISAO", "data": HOJE, **campos}
    return d[quem].post(d["url"], json=corpo)


# ---------------------------------------------------------------- SCRUM-85 · RBN12.01 registrar


def test_ct_12_01_01_aluno_registra_situacao_veiculo_e_data(artigo):
    r = _registrar(artigo)
    assert r.status_code == 201, r.json()
    atual = r.json()["atual"]
    assert (atual["situacao"], atual["veiculo"]) == ("EM_REVISAO", REVISTA)
    assert r.json()["historico"][0]["situacao"] == "EM_REVISAO" and r.json()["historico"][0]["data"] == HOJE


def test_ct_12_01_02_dados_do_cadastro_vem_preenchidos(artigo):
    """CA-02: a TEL15 abre com o veículo, o Qualis e a situação informados no cadastro."""
    atual = artigo["aluno"].get(artigo["url"]).json()["atual"]
    assert (atual["veiculo"], atual["qualis"], atual["situacao"], atual["tipo_veiculo"]) == (
        REVISTA, "B1", "SUBMETIDO", "PERIODICO")


def test_ct_12_01_03_doi_registrado(artigo):
    r = _registrar(artigo, situacao="PUBLICADO", link="10.1000/xyz123")
    assert r.status_code == 201 and r.json()["atual"]["link"] == "10.1000/xyz123"


def test_ct_12_01_04_sem_doi_o_registro_e_aceito(artigo):
    r = _registrar(artigo, situacao="ACEITO")
    assert r.status_code == 201 and r.json()["atual"]["link"] is None


def test_ct_12_01_05_aceito_nao_muda_o_cadastro_nem_a_defesa(artigo, db):
    """CA-04 / RN03: a situação acadêmica do TCC continua a mesma."""
    antes = db.get(Tcc, artigo["tcc"]["id"]).situacao
    _registrar(artigo, situacao="ACEITO")
    db.expire_all()
    assert db.get(Tcc, artigo["tcc"]["id"]).situacao == antes


def test_ct_12_01_06_veiculo_em_branco_bloqueia(artigo):
    """CA-05 / E2: situação, veículo ou data em branco marcam os campos."""
    r = _registrar(artigo, veiculo="  ", situacao="", data=None)
    assert r.status_code == 422 and set(r.json()["campos"]) >= {"veiculo", "situacao", "data"}
    r = _registrar(artigo, situacao="EM_ANALISE")  # fora do vocabulário (RN03)
    assert r.status_code == 422 and "situacao" in r.json()["campos"]


def test_ct_12_01_07_sem_vinculo_e_negado(artigo, caixa, coord):
    """CA-06 / E1: quem não vê o TCC recebe 403 na consulta e no registro."""
    assert coord.post("/api/v1/alunos", json=OUTRO).status_code == 201
    bruno = ativar(caixa, OUTRO["email"])
    assert bruno.get(artigo["url"]).status_code == 403
    assert bruno.post(artigo["url"], json={"veiculo": REVISTA, "situacao": "ACEITO", "data": HOJE}).status_code == 403


def test_ct_12_01_08_orientador_registra_com_responsavel(artigo, db):
    r = _registrar(artigo, quem="olga", situacao="ACEITO")
    assert r.status_code == 201
    assert r.json()["historico"][0]["responsavel"]["id"] == artigo["orientador"]["id"]
    log = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "registrar_publicacao"))
    assert log.usuario_id == artigo["orientador"]["id"] and log.valor_anterior == "SUBMETIDO"


def test_monografia_nao_tem_publicacao(cenario):
    """E1: TCC que não é artigo recebe 409."""
    r = _rascunho(cenario)
    url = f"/api/v1/tccs/{r.json()['id']}/publicacao"
    assert cenario["aluno"].get(url).status_code == 409
    assert cenario["aluno"].post(url, json={"veiculo": REVISTA, "situacao": "ACEITO", "data": HOJE}).status_code == 409


def test_outro_orientador_nao_registra(artigo):
    """Só o aluno autor e o orientador do TCC registram; o Otto não é orientador deste TCC."""
    assert _registrar(artigo, quem="otto").status_code == 403


def test_data_futura_e_link_sem_https_sao_recusados(artigo):
    amanha = (date.today() + timedelta(days=1)).isoformat()
    r = _registrar(artigo, data=amanha, link="www.revista.com/artigo")
    assert r.status_code == 422 and set(r.json()["campos"]) == {"data", "link"}


def test_publicado_exige_doi_ou_endereco(artigo):
    r = _registrar(artigo, situacao="PUBLICADO")
    assert r.status_code == 422 and "link" in r.json()["campos"]


# ---------------------------------------------------------------- SCRUM-86 · RBN12.02 histórico


def test_ct_12_02_01_historico_em_ordem_com_os_quatro_campos(artigo):
    """CA-01: situação, data, responsável e veículo, do mais recente para o mais antigo (DS-FL08-B)."""
    _registrar(artigo, situacao="EM_REVISAO")
    _registrar(artigo, quem="olga", situacao="ACEITO")
    h = artigo["aluno"].get(f"/api/v1/tccs/{artigo['tcc']['id']}/publicacoes/historico").json()["historico"]
    assert [r["situacao"] for r in h] == ["ACEITO", "EM_REVISAO", "SUBMETIDO"]
    assert all(r["veiculo"] == REVISTA and r["data"] and r["responsavel"] for r in h)


def test_ct_12_02_02_nova_submissao_nao_apaga_a_anterior(artigo):
    """CA-02: recusado na revista A, submetido ao congresso B; os dois ficam no histórico."""
    _registrar(artigo, situacao="RECUSADO")
    r = _registrar(artigo, veiculo="Congresso Brasileiro de Software", tipo_veiculo="CONGRESSO", situacao="SUBMETIDO")
    assert r.status_code == 201, r.json()
    h = r.json()["historico"]
    assert {x["veiculo"] for x in h} == {REVISTA, "Congresso Brasileiro de Software"}
    assert r.json()["atual"]["veiculo"] == "Congresso Brasileiro de Software"


def test_veiculo_novo_exige_o_tipo(artigo):
    r = _registrar(artigo, veiculo="Outro Evento")
    assert r.status_code == 422 and "tipo_veiculo" in r.json()["campos"]


def test_ct_12_02_03_sem_registros_mostra_vazio(cenario, db):
    """CA-03: artigo cadastrado sem submissão ainda não tem histórico."""
    r = _rascunho(cenario, modalidade="ARTIGO")
    corpo = cenario["aluno"].get(f"/api/v1/tccs/{r.json()['id']}/publicacao").json()
    assert corpo["atual"] is None and corpo["historico"] == []


def test_ct_12_02_04_historico_e_somente_leitura(artigo):
    """CA-04: não há rota para editar nem apagar um registro."""
    hid = artigo["aluno"].get(artigo["url"]).json()["historico"][0]["id"]
    assert artigo["aluno"].put(f"{artigo['url']}/{hid}", json={"situacao": "ACEITO"}).status_code in (404, 405)
    assert artigo["aluno"].delete(f"{artigo['url']}/{hid}").status_code in (404, 405)


def test_ct_12_02_05_sem_vinculo_nao_ve_o_historico(artigo):
    """CA-05: o Otto, orientador sem vínculo com este TCC, recebe 403."""
    assert artigo["otto"].get(f"/api/v1/tccs/{artigo['tcc']['id']}/publicacoes/historico").status_code == 403


# ---------------------------------------------------------------- SCRUM-87 · RBN12.03 e-mail


def _avisos(caixa):
    return [e for e in caixa if e["assunto"].startswith("O seu artigo passou para")]


def test_ct_12_03_01_mudanca_de_situacao_avisa_orientador_e_aluno(artigo, caixa):
    caixa.clear()
    _registrar(artigo, situacao="ACEITO")
    assert sorted(e["para"] for e in _avisos(caixa)) == ["ana@uea.edu.br", "olga@exemplo.com"]


def test_ct_12_03_02_03_e_06_conteudo_link_e_sem_dados_sensiveis(artigo, monkeypatch):
    """CA-02: título, veículo, nova situação e data; CA-03: link do histórico; CA-06: sem matrícula nem notas."""
    from app.services import email

    corpos = []
    monkeypatch.setattr(email, "entregar", lambda destinatario, assunto, corpo: corpos.append((assunto, corpo)))
    _registrar(artigo, situacao="ACEITO")
    assunto, corpo = corpos[0]
    assert assunto == "O seu artigo passou para: Aceito"
    assert "Detecção de fraudes com aprendizado de máquina" in corpo and REVISTA in corpo
    assert date.today().strftime("%d/%m/%Y") in corpo
    assert f"/tccs/{artigo['tcc']['id']}#artigo" in corpo
    assert "24150001" not in corpo and "nota" not in corpo.lower()


def test_ct_12_03_04_sem_mudanca_de_situacao_sem_email(artigo, caixa):
    caixa.clear()
    r = _registrar(artigo, situacao="SUBMETIDO", qualis="A2")  # só o Qualis mudou
    assert r.status_code == 201 and _avisos(caixa) == []


def test_ct_12_03_05_falha_no_email_mantem_a_alteracao(artigo, monkeypatch):
    from app.services import email

    def falhar(*_, **__):
        raise RuntimeError("SMTP indisponível")

    monkeypatch.setattr(email, "entregar", falhar)
    assert _registrar(artigo, situacao="ACEITO").status_code == 201
    assert artigo["aluno"].get(artigo["url"]).json()["atual"]["situacao"] == "ACEITO"
