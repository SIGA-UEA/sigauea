"""SCRUM-90 (RBN13.03), SCRUM-91 (RBN13.04) e SCRUM-92 (RBN13.05): produção científica, desistências e
participações em banca (RN03, RN10, RN18, RN20 · DS-FL08-C, DS-FL08-D, TEL16).

Cada teste cita o caso de teste da ficha (CT-13.03-xx, CT-13.04-xx e CT-13.05-xx). Cenário: a fixture `ind` do
test_indicadores (período 2026/2 vigente, turmas do Paulo e do Otto, TCCs em todas as situações). As publicações são
registradas pela rota da publicação (PR #23) e as defesas pela rota de agendamento; ficam direto no banco só o que
ainda não tem rota: a modalidade artigo dos TCCs extras, a situação DESISTENCIA (SCRUM-51, D1) e a defesa realizada.
"""

import json
from datetime import date

from app.models import Defesa, PublicacaoArtigo, Tcc
from tests.test_defesas_banca import DIA, banca  # noqa: F401  (fixture)
from tests.test_indicadores import URL, _aluno, _tcc, ind  # noqa: F401  (ind é fixture)
from tests.test_tcc import cenario  # noqa: F401  (fixture usada por banca)

NOMES_DE_ALUNOS = ("Aluno Indicador", "Ana")


def _sem_nome_de_aluno(resposta) -> None:
    """CA-05 do RBN13.03, CA-06 do RBN13.04 (RNF02): nenhuma resposta traz nome de aluno."""
    texto = json.dumps(resposta.json(), ensure_ascii=False)
    assert not any(nome in texto for nome in NOMES_DE_ALUNOS), texto


# ---------------------------------------------------------------- SCRUM-90 · RBN13.03 produção científica


def _artigo(db, b, aluno_id: int, orientador: str = "olga", **extra) -> int:
    tcc_id = _tcc(db, b, aluno_id, "APROVADO", orientador=orientador, **extra)
    db.get(Tcc, tcc_id).modalidade = "ARTIGO"
    db.commit()
    return tcc_id


def _publicar(b, tcc_id: int, situacao: str, quem: str = "olga", veiculo: str = "Revista Brasileira de Computação"):
    r = b[quem].post(f"/api/v1/tccs/{tcc_id}/publicacao", json={
        "veiculo": veiculo, "tipo_veiculo": "PERIODICO", "situacao": situacao, "data": date.today().isoformat(),
        "link": "10.1234/rbc.2026" if situacao == "PUBLICADO" else None})
    assert r.status_code == 201, r.json()


def _producao(cliente, **params) -> dict:
    r = cliente.get(URL, params=params)
    assert r.status_code == 200, r.json()
    return {s["situacao"]: s["total"] for s in r.json()["producao"]["situacoes"]}


def _zerado(**contagem) -> dict:
    return {"SUBMETIDO": 0, "EM_REVISAO": 0, "ACEITO": 0, "PUBLICADO": 0, "RECUSADO": 0, **contagem}


def test_ct_13_03_01_dois_submetidos_e_um_aceito(ind, db):
    """CT-13.03-01: 2 submetidos e 1 aceito → 2 / 0 / 1 / 0 (e RECUSADO zerado, D3)."""
    a, b_, c = (_artigo(db, ind, _aluno(ind["coord"], n)) for n in (20, 21, 22))
    _publicar(ind, a, "SUBMETIDO")
    _publicar(ind, b_, "SUBMETIDO")
    _publicar(ind, c, "ACEITO")
    assert _producao(ind["coord"]) == _zerado(SUBMETIDO=2, ACEITO=1)
    assert ind["coord"].get(URL).json()["producao"]["total"] == 3


def test_ct_13_03_02_tcc_que_nao_e_artigo_nao_conta(ind, db):
    """CT-13.03-02: uma publicação que ficou de um TCC que virou monografia não entra (CA-02)."""
    tcc_id = _tcc(db, ind, _aluno(ind["coord"], 23), "APROVADO")
    db.add(PublicacaoArtigo(tcc_id=tcc_id, tipo_veiculo="PERIODICO", veiculo="Revista X", situacao_atual="ACEITO"))
    db.commit()
    corpo = ind["coord"].get(URL).json()["producao"]
    assert corpo["total"] == 0 and corpo["sem_dados"] is True


def test_ct_13_03_03_mudar_para_aceito_muda_o_grupo_e_nao_o_total(ind, db):
    """CT-13.03-03: o artigo submetido passa a aceito; o total fica igual e os grupos mudam (CA-03)."""
    a, b_ = (_artigo(db, ind, _aluno(ind["coord"], n)) for n in (24, 25))
    _publicar(ind, a, "SUBMETIDO")
    _publicar(ind, b_, "SUBMETIDO")
    assert _producao(ind["coord"]) == _zerado(SUBMETIDO=2)
    _publicar(ind, a, "ACEITO")
    assert _producao(ind["coord"]) == _zerado(SUBMETIDO=1, ACEITO=1)


def test_tcc_com_duas_submissoes_conta_uma_vez_pela_mais_recente(ind, db):
    """Decisão 4 (RN18): recusado num veículo e submetido em outro conta uma vez, como submetido."""
    a = _artigo(db, ind, _aluno(ind["coord"], 26))
    _publicar(ind, a, "RECUSADO")
    _publicar(ind, a, "SUBMETIDO", veiculo="Simpósio Brasileiro de Sistemas")
    assert _producao(ind["coord"]) == _zerado(SUBMETIDO=1)


def test_ct_13_03_04_orientador_filtra_periodo_e_curso_e_ve_so_os_seus(ind, db):
    """CT-13.03-04: a Olga filtra período e curso e vê só os orientandos dela (CA-04); turma é do professor."""
    _publicar(ind, _artigo(db, ind, _aluno(ind["coord"], 27)), "SUBMETIDO")
    _publicar(ind, _artigo(db, ind, _aluno(ind["coord"], 28), orientador="otto"), "ACEITO", quem="otto")
    params = {"periodo": ind["periodo"]["id"], "curso": 1}
    assert _producao(ind["olga"], **params) == _zerado(SUBMETIDO=1)
    assert _producao(ind["otto"], **params) == _zerado(ACEITO=1)
    assert _producao(ind["coord"], **params) == _zerado(SUBMETIDO=1, ACEITO=1)
    r = ind["olga"].get(URL, params={"turma": ind["turma"]["id"]})
    assert r.status_code == 403 and r.json()["campo"] == "turma"


def test_professor_filtra_producao_por_turma(ind, db):
    """CA-04: o Paulo filtra período e turma; curso não é filtro dele."""
    _publicar(ind, _artigo(db, ind, _aluno(ind["coord"], 29)), "PUBLICADO")
    _publicar(ind, _artigo(db, ind, _aluno(ind["coord"], 30), turma_id=ind["turma_tcc2"]), "SUBMETIDO")
    assert _producao(ind["paulo"], turma=ind["turma"]["id"]) == _zerado(PUBLICADO=1)
    assert _producao(ind["paulo"]) == _zerado(PUBLICADO=1, SUBMETIDO=1)
    r = ind["paulo"].get(URL, params={"curso": 1})
    assert r.status_code == 403 and r.json()["campo"] == "curso"


def test_ct_13_03_05_painel_sem_nome_de_aluno(ind, db):
    """CT-13.03-05 (RNF02): o painel do DS-FL08-C, nos três perfis, não traz nome de aluno."""
    _publicar(ind, _artigo(db, ind, _aluno(ind["coord"], 31)), "SUBMETIDO")
    for quem in ("coord", "paulo", "olga"):
        r = ind[quem].get(URL)
        assert r.status_code == 200 and set(r.json()) == {"periodo_id", "situacao", "producao", "bancas"}
        _sem_nome_de_aluno(r)


def test_painel_usa_o_periodo_vigente_e_zera_filtro_sem_dados(ind, db):
    """DS-FL08-C alt "sem dados": curso sem TCCs zera a produção e avisa."""
    corpo = ind["coord"].get(URL, params={"curso": 3}).json()
    assert corpo["periodo_id"] == ind["periodo"]["id"]
    assert corpo["producao"]["sem_dados"] is True and corpo["situacao"]["sem_dados"] is True


# ---------------------------------------------------------------- SCRUM-91 · RBN13.04 desistências


def _desistencias(cliente, **params) -> dict:
    r = cliente.get(f"{URL}/desistencias", params=params)
    assert r.status_code == 200, r.json()
    return r.json()


def _por_curso(corpo) -> dict:
    return {c["curso"]["sigla"]: c["total"] for c in corpo["por_curso"]}


def test_ct_13_04_01_desistencias_em_dois_cursos(ind, db):
    """CT-13.04-01: total por curso e período. O `ind` já tem 1 desistência de EC; somam-se 1 de EC e 1 de LC."""
    _tcc(db, ind, _aluno(ind["coord"], 40), "DESISTENCIA")
    _tcc(db, ind, _aluno(ind["coord"], 41, curso=2), "DESISTENCIA", orientador="otto", turma_id=ind["turma_lc"])
    corpo = _desistencias(ind["coord"])
    assert corpo["periodo_id"] == ind["periodo"]["id"] and corpo["total"] == 3
    assert _por_curso(corpo)["EC"] == 2 and _por_curso(corpo)["LC"] == 1
    assert _por_curso(_desistencias(ind["coord"], curso=2)) == {"LC": 1}


def test_ct_13_04_02_coordenacao_ve_a_evolucao_no_intervalo(ind, coord, db):
    """CT-13.04-02: desistências em três períodos; a coordenação escolhe o intervalo e vê a evolução (CA-02)."""
    p1 = coord.post("/api/v1/periodos", json={"codigo": "2025/2", "inicio": "2025-08-01", "fim": "2025-12-20"}).json()
    p2 = coord.post("/api/v1/periodos", json={"codigo": "2026/1", "inicio": "2026-02-01", "fim": "2026-07-10"}).json()
    for n, periodo in ((42, p1["id"]), (43, p1["id"]), (44, p2["id"])):
        _tcc(db, ind, _aluno(coord, n), "DESISTENCIA", periodo_id=periodo)
    evolucao = _desistencias(coord)["evolucao"]
    assert [(e["periodo"]["codigo"], e["total"]) for e in evolucao] == [("2025/2", 2), ("2026/1", 1), ("2026/2", 1)]
    assert evolucao[-1]["periodo"]["vigente"] is True
    recorte = _desistencias(coord, periodo_inicio=p2["id"], periodo_fim=ind["periodo"]["id"])["evolucao"]
    assert [e["periodo"]["codigo"] for e in recorte] == ["2026/1", "2026/2"]
    r = coord.get(f"{URL}/desistencias", params={"periodo_inicio": ind["periodo"]["id"], "periodo_fim": p1["id"]})
    assert r.status_code == 400 and "periodo_fim" in r.json()["campos"]


def test_ct_13_04_03_professor_e_orientador_sem_evolucao(ind):
    """CT-13.04-03: o professor e o orientador veem só o total do período (CA-03)."""
    for quem in ("paulo", "olga"):
        corpo = _desistencias(ind[quem])
        assert corpo["evolucao"] is None and corpo["total"] == 1


def test_ct_13_04_04_reprovado_nao_conta(ind, db):
    """CT-13.04-04: 2 reprovados e 1 desistente → 1 desistência (o `ind` já tem 1 de cada)."""
    _tcc(db, ind, _aluno(ind["coord"], 45), "REPROVADO")
    assert _desistencias(ind["coord"])["total"] == 1


def test_ct_13_04_05_filtros_das_desistencias_fora_do_perfil(ind):
    """CT-13.04-05 (CA-05): o orientador só filtra período; o professor, período e turma; etapa é da coordenação."""
    for quem, params in (("olga", {"curso": 1}), ("olga", {"turma": ind["turma"]["id"]}),
                         ("paulo", {"etapa": "TCC1"}), ("paulo", {"curso": 1})):
        r = ind[quem].get(f"{URL}/desistencias", params=params)
        assert r.status_code == 403 and r.json()["campo"] == next(iter(params)), (quem, params)
    assert _desistencias(ind["paulo"], turma=ind["turma_tcc2"])["total"] == 0
    assert _desistencias(ind["coord"], etapa="TCC2")["sem_dados"] is True


def test_ct_13_04_06_desistencias_sem_nome_de_aluno(ind):
    """CT-13.04-06 (RNF02)."""
    for quem in ("coord", "paulo", "olga"):
        _sem_nome_de_aluno(ind[quem].get(f"{URL}/desistencias"))


def test_ct_13_04_07_orientador_pede_a_evolucao_pela_url(ind):
    """CT-13.04-07 (e CT-13.01-06): a evolução pela URL é negada ao orientador e ao professor."""
    periodo = ind["periodo"]["id"]
    for quem, campo in (("olga", "periodo_inicio"), ("paulo", "periodo_fim")):
        r = ind[quem].get(f"{URL}/desistencias", params={campo: periodo})
        assert r.status_code == 403 and r.json()["campo"] == campo


# ---------------------------------------------------------------- SCRUM-92 · RBN13.05 participações em banca

BANCA_DA_ANA = [("ORIENTADOR", "olga"), ("AVALIADOR", "otto"), ("AVALIADOR", "paulo")]
HORARIOS = (("08:00", "08:40"), ("09:00", "09:40"), ("10:00", "10:40"), ("11:00", "11:40"), ("15:00", "15:40"))


def _defesa(b, db, tcc_id: int, quem: str, membros: list[tuple[str, str]], horario: int, realizada=True) -> dict:
    """Agenda pela rota (DS-FL04) e, se pedido, marca a defesa como realizada direto no banco (sem rota ainda)."""
    inicio, fim = HORARIOS[horario]
    corpo = {"formato": "REMOTO", "data": DIA, "inicio": inicio, "fim": fim, "link": "https://meet.exemplo.com/d",
             "banca": [{"papel": papel, "usuario_id": b["ids"][nome]} for papel, nome in membros]}
    r = b[quem].post(f"/api/v1/tccs/{tcc_id}/defesa", json=corpo)
    assert r.status_code == 201, r.json()
    if realizada:
        db.get(Defesa, r.json()["id"]).situacao = "REALIZADA"
        db.commit()
    return r.json()


def _bancas(cliente, **params) -> dict:
    r = cliente.get(f"{URL}/bancas", params=params)
    assert r.status_code == 200, r.json()
    return {p["professor"]["nome"]: p["total"] for p in r.json()["professores"]}


def _papeis(**n) -> dict:
    return {"ORIENTADOR": 0, "AVALIADOR": 0, "COORIENTADOR": 0, "SUPLENTE": 0, **n}


def _tccs_do_otto(db, b, coord, quantos: int) -> list[int]:
    return [_tcc(db, b, _aluno(coord, 50 + n), "APROVADO", orientador="otto") for n in range(quantos)]


def test_ct_13_05_01_tres_vezes_avaliadora_e_uma_orientadora(ind, db):
    """CT-13.05-01: a Olga orienta 1 banca e avalia 3 (do Otto) → 1 e 3 por papel (CA-01)."""
    _defesa(ind, db, ind["tcc"]["id"], "olga", BANCA_DA_ANA, 0)
    for i, tcc_id in enumerate(_tccs_do_otto(db, ind, ind["coord"], 3), start=1):
        _defesa(ind, db, tcc_id, "otto", [("ORIENTADOR", "otto"), ("AVALIADOR", "olga"), ("AVALIADOR", "ricardo")], i)
    bancas = _bancas(ind["coord"])
    assert bancas["Olga Orientadora"] == _papeis(ORIENTADOR=1, AVALIADOR=3)
    assert bancas["Otto Orientador"] == _papeis(ORIENTADOR=3, AVALIADOR=1)


def test_ct_13_05_02_e_03_suplente_so_conta_se_convocado(ind, db):
    """CT-13.05-02 e 03 (RN20): o Ricardo suplente sem convocação não conta; convocado no lugar do Paulo, conta
    como suplente, e o Paulo, substituído, deixa de contar."""
    tcc_otto = _tccs_do_otto(db, ind, ind["coord"], 1)[0]
    _defesa(ind, db, ind["tcc"]["id"], "olga", BANCA_DA_ANA + [("SUPLENTE", "ricardo")], 0)
    assert "Ricardo Alves" not in _bancas(ind["coord"])  # CT-13.05-02

    d = _defesa(ind, db, tcc_otto, "otto", [("ORIENTADOR", "otto"), ("AVALIADOR", "olga"), ("AVALIADOR", "paulo"),
                                            ("SUPLENTE", "ricardo")], 1, realizada=False)
    titular = next(m["id"] for m in d["membros"] if m["pessoa"]["id"] == ind["ids"]["paulo"])
    r = ind["otto"].post(f"/api/v1/defesas/{d['id']}/suplente",
                         json={"membro_titular_id": titular, "motivo": "Viagem a congresso",
                               "data": date.today().isoformat()})
    assert r.status_code == 200, r.json()
    db.get(Defesa, d["id"]).situacao = "REALIZADA"
    db.commit()
    bancas = _bancas(ind["coord"])  # CT-13.05-03
    assert bancas["Ricardo Alves"] == _papeis(SUPLENTE=1)
    assert bancas["Paulo Professor"] == _papeis(AVALIADOR=1)  # só a primeira banca


def test_defesa_ainda_nao_realizada_nao_conta(ind, db):
    """Decisão 9: só a defesa realizada conta; a agendada para daqui a 30 dias ainda não."""
    _defesa(ind, db, ind["tcc"]["id"], "olga", BANCA_DA_ANA, 0, realizada=False)
    corpo = ind["coord"].get(f"{URL}/bancas").json()
    assert corpo["professores"] == [] and corpo["sem_dados"] is True


def test_ct_13_05_04_coordenacao_aplica_os_quatro_filtros(ind, db, coord):
    """CT-13.05-04 (CA-03): curso, período, professor e papel."""
    _defesa(ind, db, ind["tcc"]["id"], "olga", BANCA_DA_ANA, 0)
    tcc_lc = _tcc(db, ind, _aluno(coord, 60, curso=2), "APROVADO", orientador="otto", turma_id=ind["turma_lc"])
    _defesa(ind, db, tcc_lc, "otto", [("ORIENTADOR", "otto"), ("AVALIADOR", "olga"), ("AVALIADOR", "ricardo")], 1)
    olga = ind["ids"]["olga"]
    assert _bancas(coord, curso=2) == {"Olga Orientadora": _papeis(AVALIADOR=1), "Otto Orientador":
                                       _papeis(ORIENTADOR=1), "Ricardo Alves": _papeis(AVALIADOR=1)}
    assert _bancas(coord, professor=olga) == {"Olga Orientadora": _papeis(ORIENTADOR=1, AVALIADOR=1)}
    assert _bancas(coord, papel="ORIENTADOR", professor=olga) == {"Olga Orientadora": _papeis(ORIENTADOR=1)}
    outro = coord.post("/api/v1/periodos", json={"codigo": "2027/1", "inicio": "2027-02-01",
                                                 "fim": "2027-07-10"}).json()
    assert _bancas(coord, periodo=outro["id"]) == {}


def test_ct_13_05_05_professor_comum_ve_so_as_proprias(ind, db):
    """CT-13.05-05 (CA-04): o Paulo vê só a própria linha; professor e curso não são filtros dele."""
    _defesa(ind, db, ind["tcc"]["id"], "olga", BANCA_DA_ANA, 0)
    assert _bancas(ind["paulo"]) == {"Paulo Professor": _papeis(AVALIADOR=1)}
    assert _bancas(ind["paulo"], papel="ORIENTADOR") == {"Paulo Professor": _papeis()}  # próprio total, zerado
    for params in ({"professor": ind["ids"]["olga"]}, {"curso": 1}):
        r = ind["paulo"].get(f"{URL}/bancas", params=params)
        assert r.status_code == 403 and r.json()["campo"] == next(iter(params))


def test_ct_13_05_06_banca_de_tres_conta_cada_professor_uma_vez(ind, db):
    """CT-13.05-06 (CA-05): banca de 3 → uma participação para cada um, no seu papel."""
    _defesa(ind, db, ind["tcc"]["id"], "olga", BANCA_DA_ANA, 0)
    r = ind["coord"].get(f"{URL}/bancas")
    assert _bancas(ind["coord"]) == {"Olga Orientadora": _papeis(ORIENTADOR=1), "Otto Orientador":
                                     _papeis(AVALIADOR=1), "Paulo Professor": _papeis(AVALIADOR=1)}
    assert r.json()["total"] == _papeis(ORIENTADOR=1, AVALIADOR=2)
    _sem_nome_de_aluno(r)
    painel = ind["coord"].get(URL).json()["bancas"]  # o mesmo número no painel do DS-FL08-C
    assert painel["total"] == r.json()["total"]


def test_periodo_letivo_inexistente_no_intervalo(ind):
    """Intervalo com período que não existe: 400 com o campo."""
    r = ind["coord"].get(f"{URL}/desistencias", params={"periodo_inicio": 9999})
    assert r.status_code == 400 and "periodo_inicio" in r.json()["campos"]
