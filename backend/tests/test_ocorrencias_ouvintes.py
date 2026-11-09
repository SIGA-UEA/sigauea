"""SCRUM-68 (RBN09.10): ocorrências da defesa, lista de ouvintes e declaração de horas.

Cada teste cita o caso de teste da ficha (CT-09.10-xx), o critério de aceite ou o fluxo de exceção
dos diagramas DS-FL09, DS-FL09-A e DS-FL09-B. A defesa do cenário é no dia DIA da agenda padrão, das 14:00 às 14:20;
o relógio de Manaus é fixado para cada situação (antes, durante e depois da defesa).
"""

import hashlib
from datetime import date, datetime, time
from pathlib import Path

import pytest
from sqlalchemy import select

from app import config
from app.models import Defesa, DocumentoOficial, LogAuditoria, OcorrenciaDefesa, OuvinteDefesa
from app.services import ocorrencias
from tests.test_defesas_banca import DIA, _agendar, banca  # noqa: F401  (banca é fixture)
from tests.test_tcc import cenario  # noqa: F401  (fixture usada por banca)

_DIA = date.fromisoformat(DIA)
ANTES = datetime.combine(_DIA, time(13, 0))
DURANTE = datetime.combine(_DIA, time(14, 10))
DEPOIS = datetime.combine(_DIA, time(15, 0))


@pytest.fixture
def relogio(monkeypatch):
    """Muda a hora de Manaus vista pelo serviço; começa com a defesa em andamento."""

    def ajustar(momento: datetime) -> None:
        monkeypatch.setattr(ocorrencias, "_agora_manaus", lambda: momento)

    ajustar(DURANTE)
    return ajustar


@pytest.fixture
def defesa(banca, relogio):
    r = _agendar(banca)
    assert r.status_code == 201, r.json()
    return {**banca, "defesa": r.json(), "url": f"/api/v1/defesas/{r.json()['id']}"}


def _ocorrencia(d, texto="Falha de áudio por 3 min", quem="olga"):
    return d[quem].post(f"{d['url']}/ocorrencias", json={"texto": texto})


def _ouvinte(d, nome="Maria Souza", matricula="2026000011", quem="olga"):
    return d[quem].post(f"{d['url']}/ouvintes", json={"nome": nome, "matricula": matricula})


# ---------------------------------------------------------------- CA-01 e CA-02 · ocorrências


def test_ct_09_10_01_ocorrencia_salva_com_autor_e_data(defesa, db):
    """CT-09.10-01: defesa em andamento → ocorrência salva com autor e data/hora (msgs 9 a 11)."""
    r = _ocorrencia(defesa)
    assert r.status_code == 201, r.json()
    corpo = r.json()
    assert corpo["texto"] == "Falha de áudio por 3 min" and corpo["alterada_em"] is None
    assert corpo["autor"]["id"] == defesa["ids"]["olga"] and corpo["criado_em"].endswith("Z")
    log = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "registrar_ocorrencia"))
    assert log.entidade == "ocorrencia_defesa" and log.entidade_id == corpo["id"]

    vista = defesa["olga"].get(f"{defesa['url']}/ocorrencias").json()
    assert vista["liberada"] and [o["texto"] for o in vista["ocorrencias"]] == ["Falha de áudio por 3 min"]


def test_coordenacao_tambem_registra(defesa, coord):
    """RBN09.10: coordenador ou orientador."""
    r = coord.post(f"{defesa['url']}/ocorrencias", json={"texto": "Banca começou com 10 min de atraso"})
    assert r.status_code == 201


def test_ct_09_10_02_ocorrencia_vazia_ou_curta_e_bloqueada(defesa, db):
    """CT-09.10-02 / CA-02: "texto com 5 caracteres ou mais?" também na API."""
    for texto in ("", "   ", "abc"):
        assert _ocorrencia(defesa, texto=texto).status_code == 400
    assert db.scalars(select(OcorrenciaDefesa)).all() == []


def test_ds_fl09_a_corrigir_ocorrencia_guarda_o_anterior_no_log(defesa, db):
    """DS-FL09-A: texto novo com "corrigido em"; o anterior fica no log (RNF03)."""
    oc = _ocorrencia(defesa).json()
    r = defesa["olga"].put(f"{defesa['url']}/ocorrencias/{oc['id']}", json={"texto": "Falha de áudio por 5 min"})
    assert r.status_code == 200
    assert r.json()["texto"] == "Falha de áudio por 5 min" and r.json()["alterada_em"] is not None
    log = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "corrigir_ocorrencia"))
    assert (log.valor_anterior, log.valor_novo) == ("Falha de áudio por 3 min", "Falha de áudio por 5 min")


def test_corrigir_ocorrencia_de_outra_defesa_da_404(defesa):
    r = defesa["olga"].put(f"{defesa['url']}/ocorrencias/999", json={"texto": "Texto qualquer"})
    assert r.status_code == 404


# ---------------------------------------------------------------- CA-03 e CA-04 · ouvintes


def test_ct_09_10_03_cinco_ouvintes_vinculados_a_defesa(defesa, db):
    """CT-09.10-03: 5 ouvintes → 5 registros vinculados, "5 prontos para declaração"."""
    for i in range(5):
        r = _ouvinte(defesa, nome=f"Ouvinte Número {i}", matricula=f"202600010{i}")
        assert r.status_code == 201 and r.json()["pronto"] and r.json()["declaracao"] is None
    assert len(db.scalars(select(OuvinteDefesa).where(OuvinteDefesa.defesa_id == defesa["defesa"]["id"])).all()) == 5
    vista = defesa["olga"].get(f"{defesa['url']}/ocorrencias").json()
    assert len(vista["ouvintes"]) == 5 and vista["prontos"] == 5


def test_ct_09_10_04_matricula_repetida_nao_duplica(defesa, db):
    """CT-09.10-04 / CA-04 / E3: matrícula já listada → 422 no campo, sem duplicata."""
    assert _ouvinte(defesa).status_code == 201
    r = _ouvinte(defesa, nome="Outra Pessoa")
    assert r.status_code == 422 and r.json()["campo"] == "matricula"
    assert len(db.scalars(select(OuvinteDefesa)).all()) == 1


@pytest.mark.parametrize("nome, matricula, campo", [
    ("Al", "2026000011", "nome"),  # menos de 3 letras
    ("Maria", "2026000011", "nome"),  # sem sobrenome: a declaração sai com o nome completo
    ("Maria Souza", "20260", "matricula"),  # curta demais
    ("Maria Souza", "2026-0011", "matricula"),  # não só números
])
def test_e1_dado_invalido_marca_o_campo(defesa, nome, matricula, campo):
    r = _ouvinte(defesa, nome=nome, matricula=matricula)
    assert r.status_code == 422 and r.json()["campo"] == campo


def test_colar_lista_grava_validas_e_devolve_as_linhas_com_problema(defesa):
    """DS-FL09 msgs 16 a 18: {adicionados, linhas com problema[]}."""
    _ouvinte(defesa, matricula="2026000011")
    linhas = ["João Lima; 2026000012", "Ana Paz, 2026000013", "", "Visitante Externo",
              "Repetido; 2026000011", "Duplicado na lista; 2026000012", "Rui Costa\t2026000014", "a; b; c",
              "Sozinho"]
    r = defesa["olga"].post(f"{defesa['url']}/ouvintes/lote", json={"linhas": linhas})
    assert r.status_code == 200
    adicionados = r.json()["adicionados"]
    assert [o["nome"] for o in adicionados] == ["João Lima", "Ana Paz", "Visitante Externo", "Rui Costa"]
    assert adicionados[2]["matricula"] is None and adicionados[2]["pronto"] is False  # sem matrícula entra
    assert [p["linha"] for p in r.json()["linhas_com_problema"]] == [5, 6, 8, 9]


def test_lote_com_conflito_simultaneo_perde_so_a_linha_repetida(defesa, monkeypatch):
    """Outra pessoa grava a mesma matrícula entre a conferência e a gravação: só aquela linha volta como
    problema, e as outras entram (antes o lote inteiro era desfeito)."""
    _ouvinte(defesa, matricula="2026000011")
    original = ocorrencias._conferir_ouvinte

    def sem_conferir_repeticao(db, defesa_id, nome, matricula, **kw):
        if matricula == "2026000011":  # a conferência não viu a gravação da outra pessoa
            return nome, matricula
        return original(db, defesa_id, nome, matricula, **kw)

    monkeypatch.setattr(ocorrencias, "_conferir_ouvinte", sem_conferir_repeticao)
    linhas = ["João Lima; 2026000012", "Corrida Simultânea; 2026000011", "Ana Paz; 2026000013"]
    r = defesa["olga"].post(f"{defesa['url']}/ouvintes/lote", json={"linhas": linhas})
    assert r.status_code == 200
    assert [o["nome"] for o in r.json()["adicionados"]] == ["João Lima", "Ana Paz"]
    assert r.json()["linhas_com_problema"] == [
        {"linha": 2, "texto": "Corrida Simultânea; 2026000011", "motivo": "Esta matrícula já está na lista."}]


def test_visitante_sem_matricula_entra_e_so_fica_sem_declaracao(defesa, relogio):
    """Dicionário de dados: matrícula só "se for aluno da UEA". FL09: a falta dela impede só a declaração (E5)."""
    r = defesa["olga"].post(f"{defesa['url']}/ouvintes", json={"nome": "Visitante Externo"})
    assert r.status_code == 201 and r.json()["matricula"] is None and r.json()["pronto"] is False
    assert _ouvinte(defesa, nome="Outro Visitante", matricula="").json()["matricula"] is None
    relogio(DEPOIS)
    e = defesa["olga"].post(f"{defesa['url']}/declaracoes", json={"ouvinte_id": r.json()["id"]})
    assert e.status_code == 422 and e.json()["campo"] == "matricula"
    # informar a matrícula depois libera a declaração (DS-FL09-A)
    c = defesa["olga"].put(f"{defesa['url']}/ouvintes/{r.json()['id']}", json={"matricula": "2026000077"})
    assert c.status_code == 200 and c.json()["pronto"]
    assert defesa["olga"].post(f"{defesa['url']}/declaracoes", json={"ouvinte_id": r.json()["id"]}).status_code == 200


def test_rnf03_adicionar_lote_remover_e_emitir_ficam_no_log(defesa, relogio, db):
    um = _ouvinte(defesa).json()
    defesa["olga"].post(f"{defesa['url']}/ouvintes/lote", json={"linhas": ["João Lima; 2026000012"]})
    dois = _ouvinte(defesa, nome="Ana Paz", matricula="2026000013").json()
    defesa["olga"].delete(f"{defesa['url']}/ouvintes/{dois['id']}")
    relogio(DEPOIS)
    declaracao = defesa["olga"].post(f"{defesa['url']}/declaracoes", json={"ouvinte_id": um["id"]}).json()
    acoes = {(l.acao, l.entidade_id): l for l in db.scalars(select(LogAuditoria))}
    assert ("registrar_ouvinte", um["id"]) in acoes and acoes[("registrar_ouvinte", um["id"])].valor_novo == \
        "Maria Souza (2026000011)"
    assert sum(1 for a, _ in acoes if a == "registrar_ouvinte") == 3  # avulso, lote e o removido
    removido = acoes[("remover_ouvinte", dois["id"])]
    assert removido.valor_anterior == "Ana Paz (2026000013)" and removido.usuario_id == defesa["ids"]["olga"]
    emissao = acoes[("emitir_declaracao", declaracao["id"])]
    assert emissao.entidade == "documento_oficial" and "Maria Souza (2026000011)" in emissao.valor_novo


def test_ds_fl09_a_corrigir_matricula_registra_no_log(defesa, db):
    ouvinte = _ouvinte(defesa).json()
    r = defesa["olga"].put(f"{defesa['url']}/ouvintes/{ouvinte['id']}", json={"matricula": "2026000099"})
    assert r.status_code == 200 and r.json()["matricula"] == "2026000099" and r.json()["pronto"]
    log = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "corrigir_ouvinte"))
    assert (log.valor_anterior, log.valor_novo) == ("2026000011", "2026000099")


def test_corrigir_matricula_para_uma_ja_listada_da_422(defesa):
    _ouvinte(defesa, matricula="2026000011")
    outro = _ouvinte(defesa, nome="João Lima", matricula="2026000012").json()
    r = defesa["olga"].put(f"{defesa['url']}/ouvintes/{outro['id']}", json={"matricula": "2026000011"})
    assert r.status_code == 422 and r.json()["campo"] == "matricula"


def test_ds_fl09_a_remover_ouvinte_e_desfazer(defesa):
    """A2: remove e devolve o removido; "Desfazer" é adicionar de novo com os mesmos dados."""
    ouvinte = _ouvinte(defesa).json()
    r = defesa["olga"].delete(f"{defesa['url']}/ouvintes/{ouvinte['id']}")
    assert r.status_code == 200 and r.json()["matricula"] == "2026000011"
    assert defesa["olga"].get(f"{defesa['url']}/ocorrencias").json()["ouvintes"] == []
    assert _ouvinte(defesa).status_code == 201


# ---------------------------------------------------------------- CA-05 e CA-06 · autorização e privacidade


def test_ct_09_10_05_aluno_recebe_403(defesa):
    """CT-09.10-05: aluno (vê o TCC, não tem vínculo de orientação) → 403 na tela e na API."""
    assert _ouvinte(defesa, quem="aluno").status_code == 403
    assert _ocorrencia(defesa, quem="aluno").status_code == 403
    assert defesa["aluno"].get(f"{defesa['url']}/ocorrencias").status_code == 403  # CA-06


def test_professor_da_turma_e_avaliador_recebem_403(defesa):
    """CA-05: professor da turma e avaliador da banca veem o TCC (o membro da banca passou a ver o TCC da
    defesa não cancelada com o RBN10.02), mas não são coordenação nem orientador → 403."""
    assert _ouvinte(defesa, quem="paulo").status_code == 403
    assert defesa["paulo"].get(f"{defesa['url']}/ocorrencias").status_code == 403
    assert defesa["otto"].get(f"{defesa['url']}/ocorrencias").status_code == 403
    assert _ouvinte(defesa, quem="otto").status_code == 403


def test_ct_09_10_06_lista_de_ouvintes_fora_das_consultas_abertas(defesa, anonimo):
    """CT-09.10-06 / CA-06 / RN08: sem sessão não há acesso, e a consulta da banca não traz ouvintes."""
    _ouvinte(defesa)
    assert anonimo.get(f"{defesa['url']}/ocorrencias").status_code == 401
    banca = defesa["otto"].get(f"/api/v1/tccs/{defesa['tcc']['id']}/banca").json()
    assert "ouvintes" not in str(banca) and "2026000011" not in str(banca)


def test_quem_nao_ve_o_tcc_recebe_404(defesa, coord, caixa):
    from tests.conftest import ativar
    coord.post("/api/v1/alunos", json={"nome": "Saulo Silva", "email": "saulo@uea.edu.br",
                                       "matricula": "24150077", "curso_id": 1})
    saulo = ativar(caixa, "saulo@uea.edu.br")
    assert saulo.get(f"{defesa['url']}/ocorrencias").status_code == 404


# ---------------------------------------------------------------- E1 e E2 · etapa e defesa cancelada


def test_e1_antes_da_defesa_a_etapa_nao_esta_liberada(defesa, relogio):
    relogio(ANTES)
    vista = defesa["olga"].get(f"{defesa['url']}/ocorrencias").json()
    assert vista["liberada"] is False and vista["pode_emitir"] is False
    assert _ocorrencia(defesa).status_code == 409
    assert _ouvinte(defesa).status_code == 409


def test_e2_defesa_cancelada_da_409(defesa, db):
    registro = db.get(Defesa, defesa["defesa"]["id"])
    registro.situacao = "CANCELADA"
    db.commit()
    assert _ocorrencia(defesa).status_code == 409


def test_defesa_realizada_libera_mesmo_antes_do_horario(defesa, relogio, db):
    relogio(ANTES)
    registro = db.get(Defesa, defesa["defesa"]["id"])
    registro.situacao = "REALIZADA"
    db.commit()
    assert _ocorrencia(defesa).status_code == 201


# ---------------------------------------------------------------- DS-FL09-B · declaração de horas


def test_ds_fl09_b_declaracao_gera_pdf_e_documento_oficial(defesa, relogio, db):
    ouvinte = _ouvinte(defesa).json()
    relogio(DEPOIS)
    r = defesa["olga"].post(f"{defesa['url']}/declaracoes", json={"ouvinte_id": ouvinte["id"]})
    assert r.status_code == 200, r.json()
    declaracao = r.json()
    doc = db.get(DocumentoOficial, declaracao["id"])
    assert (doc.tipo, doc.versao, doc.vigente, doc.ouvinte_id) == ("DECLARACAO_HORAS", 1, True, ouvinte["id"])
    arquivo = Path(config.ARQUIVOS_DIR) / doc.caminho
    assert arquivo.read_bytes().startswith(b"%PDF") and hashlib.sha256(arquivo.read_bytes()).hexdigest() == doc.sha256

    vista = defesa["olga"].get(f"{defesa['url']}/ocorrencias").json()
    assert vista["ouvintes"][0]["declaracao"]["id"] == declaracao["id"]  # "Emitida" na linha
    pdf = defesa["olga"].get(f"{defesa['url']}/declaracoes/{declaracao['id']}/arquivo")
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"


def test_e4_declaracao_antes_do_fim_da_defesa_da_409(defesa):
    """E4 (RN15): durante a defesa ainda não há declaração."""
    ouvinte = _ouvinte(defesa).json()
    r = defesa["olga"].post(f"{defesa['url']}/declaracoes", json={"ouvinte_id": ouvinte["id"]})
    assert r.status_code == 409


def test_e5_matricula_incompleta_pede_correcao(defesa, relogio, db):
    """E5: matrícula incompleta (lista antiga) → 422 com o campo, para corrigir pelo DS-FL09-A."""
    ouvinte = _ouvinte(defesa).json()
    db.get(OuvinteDefesa, ouvinte["id"]).matricula = "2026"
    db.commit()
    relogio(DEPOIS)
    r = defesa["olga"].post(f"{defesa['url']}/declaracoes", json={"ouvinte_id": ouvinte["id"]})
    assert r.status_code == 422 and r.json()["campo"] == "matricula"


def test_dois_cliques_ao_mesmo_tempo_geram_uma_declaracao_so(defesa, relogio, monkeypatch, db):
    """O índice único parcial barra a segunda declaração vigente mesmo quando a conferência não a vê."""
    ouvinte = _ouvinte(defesa).json()
    relogio(DEPOIS)
    url = f"{defesa['url']}/declaracoes"
    assert defesa["olga"].post(url, json={"ouvinte_id": ouvinte["id"]}).status_code == 200
    monkeypatch.setattr(ocorrencias, "_declaracao", lambda db, ouvinte_id: None)  # o segundo clique não viu o primeiro
    r = defesa["olga"].post(url, json={"ouvinte_id": ouvinte["id"]})
    assert r.status_code == 409
    vigentes = db.scalars(select(DocumentoOficial).where(DocumentoOficial.ouvinte_id == ouvinte["id"])).all()
    assert len(vigentes) == 1
    arquivos = list((Path(config.ARQUIVOS_DIR) / "declaracoes").rglob("*.pdf"))
    assert [a.name for a in arquivos if f"defesa-{defesa['defesa']['id']}" in str(a)] == [Path(vigentes[0].caminho).name]


def test_declaracao_emitida_trava_segunda_emissao_correcao_e_remocao(defesa, relogio):
    ouvinte = _ouvinte(defesa).json()
    relogio(DEPOIS)
    url = f"{defesa['url']}/declaracoes"
    assert defesa["olga"].post(url, json={"ouvinte_id": ouvinte["id"]}).status_code == 200
    assert defesa["olga"].post(url, json={"ouvinte_id": ouvinte["id"]}).status_code == 409
    assert defesa["olga"].put(f"{defesa['url']}/ouvintes/{ouvinte['id']}", json={"matricula": "2026000099"}).status_code == 409
    assert defesa["olga"].delete(f"{defesa['url']}/ouvintes/{ouvinte['id']}").status_code == 409


def test_arquivo_alterado_nao_e_entregue(defesa, relogio, db):
    """RNF06: o SHA-256 é conferido ao ler."""
    ouvinte = _ouvinte(defesa).json()
    relogio(DEPOIS)
    declaracao = defesa["olga"].post(f"{defesa['url']}/declaracoes", json={"ouvinte_id": ouvinte["id"]}).json()
    doc = db.get(DocumentoOficial, declaracao["id"])
    (Path(config.ARQUIVOS_DIR) / doc.caminho).write_bytes(b"%PDF adulterado")
    assert defesa["olga"].get(f"{defesa['url']}/declaracoes/{declaracao['id']}/arquivo").status_code == 409


def test_carga_horaria_e_a_duracao_da_sessao():
    from datetime import time

    from app.services.documentos import carga_horaria
    assert carga_horaria(time(14, 0), time(14, 20)) == "20 min"
    assert carga_horaria(time(14, 0), time(16, 0)) == "2 h"
    assert carga_horaria(time(9, 0), time(10, 30)) == "1 h 30 min"
