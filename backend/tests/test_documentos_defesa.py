"""SCRUM-71 a SCRUM-75 (RBN09.13 a RBN09.17): consulta do resultado, ata, Folha de Aprovação, versões da ata e
certificados de participação (RN07, RN13, RN15, RN17, RN20 · DS-FL06-C, DS-FL06-E e DS-FL06-F), e a presença da
banca na TEL19, base do certificado (decisão da equipe em 11/11/2026).

Cada teste cita o caso de teste da ficha. Cenário: a banca padrão (Olga orientadora, Otto e Paulo avaliadores,
Ricardo suplente não convocado), avaliações enviadas pela API e o relógio depois do término da defesa.
"""

import hashlib
import time
from datetime import date, datetime, time as hora
from pathlib import Path

import pytest
from sqlalchemy import select

from app import config
from app.models import Defesa, DocumentoOficial, LogAuditoria, ResultadoDefesa, Tcc
from app.services import documentos, ocorrencias
from tests.conftest import ativar
from tests.test_avaliacao import _convocar_ricardo, defesa, depois_da_defesa  # noqa: F401  (fixtures)
from tests.test_defesas_banca import DIA, banca  # noqa: F401  (fixture usada por defesa)
from tests.test_nota_final import _enviar_nota, _notas
from tests.test_tcc import cenario  # noqa: F401  (fixture usada por banca)

PARECER = "Trabalho consistente; a banca pede ajustes na revisão de literatura."
DEPOIS = datetime.combine(date.fromisoformat(DIA), hora(15, 0))
OUTRO = {"nome": "Bruno Batista", "email": "bruno@uea.edu.br", "matricula": "24150002", "curso_id": 1}


@pytest.fixture
def realizada(defesa, depois_da_defesa, monkeypatch):  # noqa: F811
    """A defesa já terminou (presença, ata e certificados liberados) e as três avaliações foram enviadas."""
    monkeypatch.setattr(ocorrencias, "_agora_manaus", lambda: DEPOIS)
    _notas(defesa, "7.0", "8.0", "6.0")
    return {**defesa, "url": f"/api/v1/defesas/{defesa['defesa']['id']}"}


def _membro(d, quem: str) -> int:
    return next(m["id"] for m in d["defesa"]["membros"] if m["pessoa"]["id"] == d["ids"][quem])


def _presenca(d, quem: str, presente: bool = True, por="olga"):
    return d[por].put(f"{d['url']}/banca/{_membro(d, quem)}/presenca", json={"presente": presente})


def _todos_presentes(d):
    for quem in ("olga", "otto", "paulo"):
        assert _presenca(d, quem).status_code == 200


def _confirmar(d, resultado="APROVADO"):
    r = d["olga"].post(f"{d['url']}/resultado", json={"resultado": resultado, "parecer": PARECER})
    assert r.status_code == 200, r.json()


def _retificar(d, resultado, motivo="Erro na digitação do resultado."):
    r = d["olga"].post(f"{d['url']}/resultado/retificacao", json={"resultado": resultado, "motivo": motivo})
    assert r.status_code == 200, r.json()


def _docs(d, quem="olga"):
    return d[quem].get(f"{d['url']}/documentos")


def _gerar(d, tipo="ata", quem="olga"):
    return d[quem].post(f"{d['url']}/documentos/{tipo}")


def _arquivo(d, documento_id, quem="aluno"):
    return d[quem].get(f"/api/v1/documentos/{documento_id}/arquivo")


def _sem_vinculo(caixa, coord):
    assert coord.post("/api/v1/alunos", json=OUTRO).status_code == 201
    return ativar(caixa, OUTRO["email"])


# ---------------------------------------------------------------- presença da banca (TEL19)


def test_presenca_da_banca_lista_participantes_e_registra_no_log(realizada, db):
    """O suplente não convocado não participa (RN20); a marcação fica no log."""
    banca = realizada["olga"].get(f"{realizada['url']}/ocorrencias").json()["banca"]
    assert sorted(m["pessoa"]["nome"] for m in banca) == ["Olga Orientadora", "Otto Orientador", "Paulo Professor"]
    assert all(m["presente"] is None for m in banca)
    r = _presenca(realizada, "otto", False)
    assert r.status_code == 200 and r.json()["presente"] is False
    log = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "registrar_presenca_banca"))
    assert (log.entidade_id, log.valor_novo) == (_membro(realizada, "otto"), "ausente")


def test_presenca_so_coordenacao_ou_orientador_e_so_do_participante(realizada):
    assert _presenca(realizada, "otto", por="aluno").status_code == 403
    assert _presenca(realizada, "otto", por="paulo").status_code == 403
    assert _presenca(realizada, "ricardo").status_code == 404  # suplente não convocado


# ---------------------------------------------------------------- SCRUM-71 · RBN09.13 consultar o resultado


def test_ct_09_13_01_aluno_ve_resultado_parecer_e_nota_final(realizada):
    """CA-01: resultado com correções, parecer e nota final para o aluno, o orientador e a coordenação."""
    _confirmar(realizada, "APROVADO_COM_CORRECOES")
    r = realizada["aluno"].get(f"{realizada['url']}/resultado")
    assert r.status_code == 200
    res = r.json()["resultado"]
    assert (res["resultado"], res["parecer"], res["nota_final"]) == ("APROVADO_COM_CORRECOES", PARECER, 7.0)
    assert r.json()["pode_confirmar"] is False


def test_ct_09_13_02_antes_da_confirmacao_aluno_nao_ve_notas_nem_resultado(realizada):
    """CA-02."""
    corpo = realizada["aluno"].get(f"{realizada['url']}/resultado").json()
    assert (corpo["resultado"], corpo["consolidacao"], corpo["pendentes"]) == (None, None, [])


def test_ct_09_13_03_sem_vinculo_recebe_403(realizada, caixa, coord):
    """CA-03 / E2."""
    bruno = _sem_vinculo(caixa, coord)
    assert bruno.get(f"{realizada['url']}/resultado").status_code == 403


def test_ct_09_13_04_agenda_publica_nao_mostra_notas_pareceres_nem_resultado(realizada):
    """CA-04 / RN08: mesmo com o resultado confirmado, a agenda não traz nota, parecer nem resultado."""
    _confirmar(realizada)
    assert realizada["olga"].post(f"{realizada['url']}/publicacao").status_code in (200, 201)
    agenda = realizada["aluno"].get("/api/v1/agenda?periodo=todas")
    assert agenda.status_code == 200 and agenda.json()
    texto = str(agenda.json()).lower()
    for proibido in ("nota", "parecer", "resultado", "aprovado"):
        assert proibido not in texto


def test_ct_09_13_05_aluno_nao_recebe_notas_individuais(realizada):
    """CA-05 (RN13/TI-10): a consulta do aluno não traz as notas de cada avaliador."""
    _confirmar(realizada)
    corpo = realizada["aluno"].get(f"{realizada['url']}/resultado").json()
    assert corpo["consolidacao"] is None
    assert "notas" not in corpo["resultado"] and "7.0" not in str(corpo["resultado"].get("retificacoes"))


# ---------------------------------------------------------------- SCRUM-72 · RBN09.14 ata da defesa


def test_ct_09_14_01_ata_disponivel_para_download_apos_confirmar(realizada):
    """CA-01."""
    _todos_presentes(realizada)
    _confirmar(realizada)
    r = _gerar(realizada)
    assert r.status_code == 200, r.json()
    [v1] = r.json()["ata"]["versoes"]
    assert (v1["versao"], v1["vigente"]) == (1, True)
    pdf = _arquivo(realizada, v1["id"])
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")


def test_ct_09_14_02_ata_traz_todos_os_campos_do_modelo(realizada, db):
    """CA-02: TCC, autor, banca, data, local, notas, resultado, parecer e correções exigidas."""
    _todos_presentes(realizada)
    _confirmar(realizada, "APROVADO_COM_CORRECOES")
    defesa = db.get(Defesa, realizada["defesa"]["id"])
    resultado = db.scalar(select(ResultadoDefesa))
    from app.services import nota_final
    c = documentos.montar_ata(defesa=defesa, tcc=defesa.tcc, membros=ocorrencias.participantes(defesa),
                              notas=[(n.membro, n.nota) for n in nota_final.calcular_nota_final(db, defesa).notas],
                              resultado=resultado, retificacoes=[])
    assert "Detecção de fraudes com aprendizado de máquina" in c["abertura"] and "Ana Ribeiro" in c["abertura"]
    assert defesa.data.strftime("%Y") in c["abertura"] and "14:00" in c["abertura"] and "14:20" in c["abertura"]
    assert "meet.exemplo.com" in c["abertura"]  # local: a sala virtual da defesa remota
    assert {linha[0] for linha in c["banca"]} == {"Olga Orientadora", "Otto Orientador", "Paulo Professor"}
    assert sorted(linha[2] for linha in c["notas"]) == ["6,00", "7,00", "8,00"]
    assert (c["media"], c["nota_final"], c["resultado"]) == ("7,00", "7,00", "APROVADO COM CORREÇÕES")
    assert c["parecer"] == PARECER and "correções" in c["correcoes"]
    assert documentos.ata_defesa(c, numero=1, versao=1, gerado_em=datetime(2026, 12, 1, 18)).startswith(b"%PDF")


def test_ct_09_14_03_sem_presenca_registrada_nao_emite_e_diz_o_que_falta(realizada, db):
    """CA-03: falta a presença do Paulo; a ata não sai e a falta é indicada."""
    _presenca(realizada, "olga")
    _presenca(realizada, "otto")
    _confirmar(realizada)
    r = _gerar(realizada)
    assert r.status_code == 409 and r.json()["faltas"] == ["Presença de Paulo Professor (Presença e ocorrências)."]
    assert db.scalar(select(DocumentoOficial)) is None
    assert _docs(realizada).json()["ata"]["faltas"] == r.json()["faltas"]


def test_ct_09_14_04_resultado_nao_confirmado_impede(realizada):
    """CA-04 / E1: "Indisponível por enquanto"."""
    _todos_presentes(realizada)
    r = _gerar(realizada)
    assert r.status_code == 409 and r.json()["detail"].startswith("Indisponível por enquanto")
    assert _docs(realizada).json()["ata"]["disponivel"] is False


def test_ct_09_14_05_p95_da_geracao_ate_5_segundos(realizada):
    """CA-05 / RNF05: 20 gerações seguidas; o p95 do tempo até o PDF disponível fica abaixo de 5 s."""
    _todos_presentes(realizada)
    _confirmar(realizada)
    tempos = []
    for _ in range(20):
        inicio = time.perf_counter()
        r = _gerar(realizada)
        tempos.append(time.perf_counter() - inicio)
        assert r.status_code == 200
    p95 = sorted(tempos)[int(len(tempos) * 0.95) - 1]
    assert p95 <= 5.0, f"p95 = {p95:.2f} s"


def test_ct_09_14_06_sha256_da_ata_confere(realizada, db):
    """CA-06 / RNF06."""
    _todos_presentes(realizada)
    _confirmar(realizada)
    _gerar(realizada)
    doc = db.scalar(select(DocumentoOficial))
    arquivo = (Path(config.ARQUIVOS_DIR) / doc.caminho).read_bytes()
    assert hashlib.sha256(arquivo).hexdigest() == doc.sha256
    assert hashlib.sha256(_arquivo(realizada, doc.id).content).hexdigest() == doc.sha256


def test_falha_ao_gerar_nao_muda_nada(realizada, monkeypatch, db):
    """E2: "Não foi possível gerar o documento"; nada é gravado."""
    _todos_presentes(realizada)
    _confirmar(realizada)

    def quebrar(*_, **__):
        raise RuntimeError("falha no gerador")

    monkeypatch.setattr(documentos, "ata_defesa", quebrar)
    r = _gerar(realizada)
    assert r.status_code == 500 and "Nada foi alterado" in r.json()["detail"]
    assert db.scalar(select(DocumentoOficial)) is None


def test_so_coordenacao_ou_orientador_gera(realizada, coord):
    _todos_presentes(realizada)
    _confirmar(realizada)
    assert _gerar(realizada, quem="aluno").status_code == 403
    assert _gerar(realizada, quem="otto").status_code == 403
    assert coord.post(f"{realizada['url']}/documentos/ata").status_code == 200


# ---------------------------------------------------------------- SCRUM-73 · RBN09.15 Folha de Aprovação


def _tcc2(d, db):
    tcc = db.get(Tcc, d["tcc"]["id"])
    tcc.etapa = "TCC2"
    db.commit()


def test_ct_09_15_01_tcc2_gera_folha_distinta_da_ata(realizada, db):
    """CA-01."""
    _tcc2(realizada, db)
    _todos_presentes(realizada)
    _confirmar(realizada)
    r = _gerar(realizada, "folha")
    assert r.status_code == 200, r.json()
    assert r.json()["folha"]["versoes"][0]["vigente"] and r.json()["ata"]["versoes"] == []
    assert db.scalar(select(DocumentoOficial)).tipo == "FOLHA_APROVACAO"


def test_ct_09_15_02_tcc1_monografia_nao_tem_folha(realizada):
    """CA-02: não é oferecida nem gerada."""
    _todos_presentes(realizada)
    _confirmar(realizada)
    assert _docs(realizada).json()["folha"]["aplica"] is False
    assert _gerar(realizada, "folha").status_code == 409


def test_ct_09_15_03_com_correcoes_sem_anuencia_fica_bloqueada(realizada, db):
    """CA-03 / E3: sem a anuência do aluno, a folha não é gerada nem liberada."""
    _tcc2(realizada, db)
    _todos_presentes(realizada)
    _confirmar(realizada, "APROVADO_COM_CORRECOES")
    r = _gerar(realizada, "folha")
    assert r.status_code == 409 and "anuência" in r.json()["detail"]
    folha = _docs(realizada, "aluno").json()["folha"]
    assert folha["disponivel"] is False and "anuência" in folha["motivo"] and folha["versoes"] == []


def test_ct_09_15_04_depois_da_anuencia_a_folha_e_liberada(realizada, db):
    """CA-03: com a anuência registrada (aba Correções, SCRUM-81/82), a folha sai e o aluno baixa."""
    _tcc2(realizada, db)
    _todos_presentes(realizada)
    _confirmar(realizada, "APROVADO_COM_CORRECOES")
    resultado = db.scalar(select(ResultadoDefesa))
    resultado.anuencia_em = datetime(2026, 12, 2, 12)
    db.commit()
    r = _gerar(realizada, "folha")
    assert r.status_code == 200, r.json()
    folha_id = r.json()["folha"]["versoes"][0]["id"]
    assert _docs(realizada, "aluno").json()["folha"]["versoes"][0]["id"] == folha_id
    assert _arquivo(realizada, folha_id).status_code == 200


def test_ct_09_15_05_dados_incompletos_nao_emite(realizada, db):
    """CA-04."""
    _tcc2(realizada, db)
    _presenca(realizada, "olga")
    _confirmar(realizada)
    r = _gerar(realizada, "folha")
    assert r.status_code == 409 and len(r.json()["faltas"]) == 2


def test_ct_09_15_06_resultado_retificado_regera_e_substitui(realizada, db):
    """CA-05 / RN15: a anterior fica substituída e a nova vigente."""
    _tcc2(realizada, db)
    _todos_presentes(realizada)
    _confirmar(realizada, "APROVADO_COM_CORRECOES")
    db.scalar(select(ResultadoDefesa)).anuencia_em = datetime(2026, 12, 2, 12)
    db.commit()
    _gerar(realizada, "folha")
    _retificar(realizada, "APROVADO")
    assert _docs(realizada).json()["folha"]["desatualizada"] is True
    versoes = _gerar(realizada, "folha").json()["folha"]["versoes"]
    assert [(v["versao"], v["vigente"], v["substituido_em"] is not None) for v in versoes] == [
        (2, True, False), (1, False, True)]


def test_ct_09_15_07_sha256_da_folha_confere(realizada, db):
    """CA-06."""
    _tcc2(realizada, db)
    _todos_presentes(realizada)
    _confirmar(realizada)
    _gerar(realizada, "folha")
    doc = db.scalar(select(DocumentoOficial))
    assert hashlib.sha256((Path(config.ARQUIVOS_DIR) / doc.caminho).read_bytes()).hexdigest() == doc.sha256


# ---------------------------------------------------------------- SCRUM-74 · RBN09.16 versões da ata


def test_ct_09_16_01_aluno_baixa_a_ata_vigente(realizada):
    """CA-01: aluno e avaliador da defesa consultam e baixam."""
    _todos_presentes(realizada)
    _confirmar(realizada)
    v1 = _gerar(realizada).json()["ata"]["versoes"][0]
    for quem in ("aluno", "otto"):
        assert _docs(realizada, quem).json()["ata"]["versoes"][0]["vigente"] is True
        assert _arquivo(realizada, v1["id"], quem).status_code == 200


def test_ct_09_16_02_ata_retificada_v2_vigente_e_v1_substituida(realizada):
    """CA-02: depois da retificação a ata fica desatualizada; a nova versão substitui a anterior."""
    _todos_presentes(realizada)
    _confirmar(realizada)
    _gerar(realizada)
    _retificar(realizada, "APROVADO_COM_CORRECOES")
    assert _docs(realizada).json()["ata"]["desatualizada"] is True
    _gerar(realizada)
    ata = _docs(realizada, "aluno").json()["ata"]
    assert [(v["versao"], v["vigente"]) for v in ata["versoes"]] == [(2, True), (1, False)]
    assert ata["desatualizada"] is False


def test_ct_09_16_03_e_04_sem_vinculo_recebe_403_na_tela_e_na_url(realizada, caixa, coord):
    """CA-03: professor que não está na banca e aluno sem vínculo, pela tela e pela URL direta do PDF."""
    _todos_presentes(realizada)
    _confirmar(realizada)
    ata_id = _gerar(realizada).json()["ata"]["versoes"][0]["id"]
    bruno = _sem_vinculo(caixa, coord)
    assert bruno.get(f"{realizada['url']}/documentos").status_code == 403
    assert bruno.get(f"/api/v1/documentos/{ata_id}/arquivo").status_code == 403


def test_ct_09_16_05_arquivo_alterado_nao_e_entregue(realizada, db):
    """CA-04 / RNF06: o SHA-256 não confere e o arquivo não sai."""
    _todos_presentes(realizada)
    _confirmar(realizada)
    _gerar(realizada)
    doc = db.scalar(select(DocumentoOficial))
    (Path(config.ARQUIVOS_DIR) / doc.caminho).write_bytes(b"%PDF adulterado")
    assert _arquivo(realizada, doc.id).status_code == 409


def test_ct_09_16_06_download_fica_no_log_com_a_versao(realizada, db):
    """CA-05: usuário, data/hora e versão acessada."""
    _todos_presentes(realizada)
    _confirmar(realizada)
    doc_id = _gerar(realizada).json()["ata"]["versoes"][0]["id"]
    _arquivo(realizada, doc_id)
    log = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "baixar_documento"))
    assert log.entidade_id == doc_id and log.valor_novo == "versão 1 (vigente)" and log.criado_em
    assert log.usuario_id == realizada["aluno"].get("/api/v1/auth/me").json()["id"]


# ---------------------------------------------------------------- SCRUM-75 · RBN09.17 certificados


def _emitir(d, *quem, por="olga"):
    return d[por].post(f"{d['url']}/documentos/certificados", json={"ids_membro": [_membro(d, q) for q in quem]})


def test_ct_09_17_01_quatro_presentes_quatro_certificados(defesa, depois_da_defesa, monkeypatch, db):  # noqa: F811
    """CA-01: com o suplente convocado no lugar do Otto, os quatro presentes recebem certificado."""
    monkeypatch.setattr(ocorrencias, "_agora_manaus", lambda: DEPOIS)
    _convocar_ricardo(defesa)
    d = {**defesa, "url": f"/api/v1/defesas/{defesa['defesa']['id']}"}
    for quem in ("olga", "otto", "paulo", "ricardo"):
        assert _presenca(d, quem).status_code == 200
    r = _emitir(d, "olga", "otto", "paulo", "ricardo")
    assert r.status_code == 200, r.json()
    assert len(db.scalars(select(DocumentoOficial).where(DocumentoOficial.tipo == "CERTIFICADO")).all()) == 4


def test_ct_09_17_02_certificado_vai_anexado_por_email_e_o_envio_fica_registrado(realizada, caixa):
    """CA-02."""
    _todos_presentes(realizada)
    caixa.clear()
    linhas = _emitir(realizada, "olga", "otto", "paulo").json()["certificados"]
    assert sorted(e["para"] for e in caixa) == ["olga@exemplo.com", "otto@exemplo.com", "paulo@exemplo.com"]
    assert all(e["anexo_pdf"] and e["anexo"].startswith("certificado") for e in caixa)
    linhas = _docs(realizada).json()["certificados"]
    assert {(l["envio"], l["certificado_id"] is not None) for l in linhas} == {("ENVIADO", True)}


def test_ct_09_17_03_defesa_cancelada_nao_gera(realizada, db):
    """CA-03."""
    _todos_presentes(realizada)
    db.get(Defesa, realizada["defesa"]["id"]).situacao = "CANCELADA"
    db.commit()
    assert _emitir(realizada, "olga").status_code == 409
    assert db.scalar(select(DocumentoOficial)) is None


def test_ct_09_17_04_ausente_nao_recebe(realizada, db):
    """CA-03: o Otto ausente não recebe certificado; os presentes sim."""
    _todos_presentes(realizada)
    _presenca(realizada, "otto", False)
    r = _emitir(realizada, "otto")
    assert r.status_code == 409 and r.json()["membro_id"] == _membro(realizada, "otto")
    assert _emitir(realizada, "olga", "paulo").status_code == 200
    linhas = {l["pessoa"]["nome"]: l for l in _docs(realizada).json()["certificados"]}
    assert linhas["Otto Orientador"]["certificado_id"] is None
    assert linhas["Otto Orientador"]["motivo"] == "Ausente na defesa."


def test_ct_09_17_05_suplente_nao_convocado_fica_de_fora(realizada):
    """CA-04 / RN20."""
    _todos_presentes(realizada)
    nomes = [l["pessoa"]["nome"] for l in _docs(realizada).json()["certificados"]]
    assert "Ricardo Alves" not in nomes
    assert _emitir(realizada, "ricardo").status_code == 404


def test_ct_09_17_06_falha_de_envio_e_reenvio_sem_duplicar(realizada, monkeypatch, db):
    """CA-05 / E2: a falha fica registrada; o reenvio usa o mesmo certificado."""
    from app.services import email

    _todos_presentes(realizada)

    def falhar(*_, **__):
        raise RuntimeError("servidor de e-mail fora do ar")

    monkeypatch.setattr(email, "entregar", falhar)
    _emitir(realizada, "paulo")
    [linha] = [l for l in _docs(realizada).json()["certificados"] if l["pessoa"]["nome"] == "Paulo Professor"]
    assert linha["envio"] == "FALHA"
    monkeypatch.setattr(email, "entregar", lambda *a, **k: None)
    assert _emitir(realizada, "paulo").status_code == 200  # emitir de novo não duplica
    r = realizada["olga"].post(f"/api/v1/documentos/{linha['certificado_id']}/reenvio")
    assert r.status_code == 200  # a resposta sai antes do envio: o e-mail ainda está "pendente" nela
    [linha] = [l for l in _docs(realizada).json()["certificados"] if l["pessoa"]["nome"] == "Paulo Professor"]
    assert linha["envio"] == "ENVIADO"
    assert len(db.scalars(select(DocumentoOficial)).all()) == 1


def test_ct_09_17_07_aluno_nao_emite(realizada):
    """CA-06 / E3."""
    _todos_presentes(realizada)
    assert _emitir(realizada, "olga", por="aluno").status_code == 403


def test_membro_baixa_so_o_proprio_certificado(realizada, db):
    _todos_presentes(realizada)
    _emitir(realizada, "olga", "otto")
    certs = {d.membro_id: d.id for d in db.scalars(select(DocumentoOficial))}
    meu = _docs(realizada, "otto").json()["meus_certificados"]
    assert [c["id"] for c in meu] == [certs[_membro(realizada, "otto")]]
    assert _arquivo(realizada, certs[_membro(realizada, "otto")], "otto").status_code == 200
    assert _arquivo(realizada, certs[_membro(realizada, "olga")], "otto").status_code == 403


def test_antes_do_fim_da_defesa_nao_emite(defesa, depois_da_defesa, monkeypatch):  # noqa: F811
    """E1: defesa não realizada (RN15)."""
    durante = datetime.combine(date.fromisoformat(DIA), hora(14, 10))
    monkeypatch.setattr(ocorrencias, "_agora_manaus", lambda: durante)
    d = {**defesa, "url": f"/api/v1/defesas/{defesa['defesa']['id']}"}
    _presenca(d, "olga")
    assert _emitir(d, "olga").status_code == 409


def test_enviar_nota_reaproveita_o_helper():
    """Garante que o helper do SCRUM-69 continua importável aqui (usado nos cenários)."""
    assert callable(_enviar_nota)
