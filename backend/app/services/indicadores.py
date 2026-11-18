"""Indicadores gerenciais: escopo por perfil, situação dos TCCs e das orientações, produção científica, desistências
e participações em banca, com o relatório em PDF (RBN13.01 a RBN13.06 · RN01, RN02, RN03, RN07, RN10, RN18, RN20 · DS-FL08-C, DS-FL08-D,
TEL16).

Faz o papel do ControladorIndicadores do diagrama de classes (MOD06): resolverEscopo, contarPorSituacao e
contarOrientandos (SCRUM-88 e 89); contarPorSituacao em PublicacaoArtigo (SCRUM-90); contarDesistencias e
evolucaoPorPeriodo (SCRUM-91); contarParticipacoes e suplentesConvocados (SCRUM-92); e consultarIndicadores, o painel
do DS-FL08-C. O relatório em PDF (RBN13.06, SCRUM-93, relatorio_pdf) usa estas mesmas funções. Os filtros de cada indicador por
perfil ficam em `filtros_indicadores`.

Escopo (RN18, RBN13.01):
- coordenação: todos os TCCs dos cursos do seu núcleo;
- professor da disciplina: os TCCs das turmas sob sua responsabilidade;
- orientador: os TCCs de que é orientador (orientação aceita e não encerrada);
- quem tem mais de um perfil vê a soma dos escopos, e cada TCC conta uma vez (CA-04).
Filtros por perfil (CA-04 do RBN13.02): coordenação usa curso, período, etapa e orientador; professor, período
e turma; orientador, período, etapa e curso. Um filtro fora do perfil, ou um curso, turma ou orientador fora do
escopo, recebe 403 (CA-06 do RBN13.01). Nenhuma resposta traz nome de aluno (CA-05).
"""

from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import agora
from app.erros import ErroAPI
from app.models import (
    ACEITA,
    PAPEL_ORIENTADOR,
    PERFIL_COORDENADOR,
    PERFIL_ORIENTADOR,
    PERFIL_PROFESSOR,
    Aluno,
    BancaMembro,
    Curso,
    Defesa,
    Docente,
    Orientacao,
    PeriodoLetivo,
    Tcc,
    Turma,
    Usuario,
)
from app.schemas.indicador import (
    BancasOut,
    CursoOut,
    DesistenciasCursoOut,
    DesistenciasOut,
    EscopoOut,
    EvolucaoOut,
    FiltrosDoIndicador,
    FiltrosIndicadoresOut,
    FiltrosOut,
    IndicadoresOut,
    IndicadorSituacaoOut,
    OrientacoesOut,
    ParticipacoesOut,
    PeriodoOut,
    PorEtapa,
    PorPapel,
    ProducaoOut,
    SituacaoEditorialOut,
    SituacaoOut,
    TurmaOpcaoOut,
)
from app.services import auditoria, documentos
from app.services.defesas import realizada
from app.services.turmas import pessoa

ETAPAS = ("TCC1", "TCC2")
# RN10: as seis situações acadêmicas do card, mais "Concluído", que vem do encerramento (RBN11.04)
SITUACOES = ("RASCUNHO", "EM_ANALISE", "APROVADO", "DEVOLVIDO", "REPROVADO", "DESISTENCIA", "CONCLUIDO")
FORA_DO_PERFIL = "Este filtro não está disponível para o seu perfil."
FORA_DO_ESCOPO = "Fora do escopo dos seus indicadores."


def _perfis(db: Session, usuario: Usuario) -> set[str]:
    """Perfis que dão escopo. O professor da disciplina sem nenhuma turma não acrescenta nada (escopo vazio): fica de
    fora, para a tela não mostrar um filtro de turma vazio (H8). O orientador fica mesmo sem orientandos, para ver o
    próprio total zerado."""
    perfis = {p for p in (PERFIL_COORDENADOR, PERFIL_PROFESSOR, PERFIL_ORIENTADOR) if p in usuario.perfis}
    if PERFIL_PROFESSOR in perfis and db.scalar(select(Turma.id).where(Turma.professor_id == usuario.id).limit(1)) is None:
        if perfis != {PERFIL_PROFESSOR}:
            perfis.discard(PERFIL_PROFESSOR)
    return perfis


def _exigir_perfil(db: Session, usuario: Usuario) -> set[str]:
    perfis = _perfis(db, usuario)
    if not perfis:
        raise ErroAPI(403, "Os indicadores são para a coordenação, os professores da disciplina e os orientadores.")
    return perfis


def _filtros(perfis: set[str]) -> FiltrosOut:
    coord, prof, orient = (PERFIL_COORDENADOR in perfis, PERFIL_PROFESSOR in perfis, PERFIL_ORIENTADOR in perfis)
    return FiltrosOut(periodo=True, curso=coord or orient, etapa=coord or orient, turma=prof, orientador=coord)


def filtros_indicadores(perfis: set[str]) -> FiltrosIndicadoresOut:
    """Filtros de cada indicador por perfil, como nas fichas; quem tem mais de um perfil tem a soma deles.

    - situação (RBN13.02): os mesmos de `_filtros`;
    - produção científica (RBN13.03): coordenação curso e período; professor período e turma; orientador período
      e curso;
    - desistências (RBN13.04): coordenação curso, intervalo de períodos e etapa; professor período e turma;
      orientador só período;
    - participações em banca (RBN13.05): coordenação curso, período, professor e papel; professor e orientador
      período e papel.
    """
    coord, prof, orient = (PERFIL_COORDENADOR in perfis, PERFIL_PROFESSOR in perfis, PERFIL_ORIENTADOR in perfis)
    return FiltrosIndicadoresOut(
        situacao=FiltrosDoIndicador(**_filtros(perfis).model_dump()),
        producao=FiltrosDoIndicador(periodo=True, curso=coord or orient, turma=prof),
        desistencias=FiltrosDoIndicador(periodo=True, curso=coord, etapa=coord, intervalo=coord, turma=prof),
        bancas=FiltrosDoIndicador(periodo=True, curso=coord, professor=coord, papel=True),
    )


def periodo_vigente(db: Session) -> PeriodoLetivo | None:
    """O período que contém a data de hoje; sem isso, o mais recente (CA-05 do RBN13.02)."""
    hoje = date.today()
    atual = db.scalar(select(PeriodoLetivo).where(PeriodoLetivo.inicio <= hoje, PeriodoLetivo.fim >= hoje))
    return atual or db.scalar(select(PeriodoLetivo).order_by(PeriodoLetivo.inicio.desc()).limit(1))


def _ids_orientados(db: Session, usuario: Usuario) -> set[int]:
    return set(db.scalars(select(Orientacao.tcc_id).where(
        Orientacao.professor_id == usuario.id, Orientacao.papel == PAPEL_ORIENTADOR,
        Orientacao.status == ACEITA, Orientacao.encerrado_em.is_(None))))


def escopo_tccs(db: Session, usuario: Usuario, perfis: set[str]) -> dict[int, Tcc]:
    """resolverEscopo (DS-FL08-D mensagem 3): os TCCs que o usuário pode contar, sem repetição (soma dos escopos)."""
    tccs: dict[int, Tcc] = {}
    if PERFIL_COORDENADOR in perfis and usuario.docente is not None:
        consulta = (select(Tcc).join(Aluno, Aluno.usuario_id == Tcc.aluno_id).join(Curso, Curso.id == Aluno.curso_id)
                    .where(Curso.nucleo_id == usuario.docente.nucleo_id))
        tccs.update({t.id: t for t in db.scalars(consulta)})
    if PERFIL_PROFESSOR in perfis:
        consulta = select(Tcc).join(Turma, Turma.id == Tcc.turma_id).where(Turma.professor_id == usuario.id)
        tccs.update({t.id: t for t in db.scalars(consulta)})
    if PERFIL_ORIENTADOR in perfis:
        ids = _ids_orientados(db, usuario)
        if ids:
            tccs.update({t.id: t for t in db.scalars(select(Tcc).where(Tcc.id.in_(ids)))})
    return tccs


def _orientador(t: Tcc) -> Usuario | None:
    return next((o.professor for o in t.orientacoes
                 if o.papel == PAPEL_ORIENTADOR and o.status == ACEITA and o.encerrado_em is None), None)


def _orientadores_visiveis(usuario: Usuario, perfis: set[str], tccs: dict[int, Tcc]) -> dict[int, Usuario] | None:
    """Quem aparece no indicador de orientações. None = todos (coordenação). O professor vê os orientadores dos
    alunos das suas turmas; o orientador, só a si mesmo (CA-06 do RBN13.02)."""
    if PERFIL_COORDENADOR in perfis:
        return None
    visiveis: dict[int, Usuario] = {}
    if PERFIL_PROFESSOR in perfis:
        for t in tccs.values():
            o = _orientador(t)
            if o is not None and t.turma.professor_id == usuario.id:
                visiveis[o.id] = o
    if PERFIL_ORIENTADOR in perfis:
        visiveis[usuario.id] = usuario
    return visiveis


def _descricao(usuario: Usuario, perfis: set[str], db: Session) -> list[tuple[str, str]]:
    chips = []
    if PERFIL_COORDENADOR in perfis:
        chips.append(("Coordenação", "todos os cursos do núcleo"))
    if PERFIL_PROFESSOR in perfis:
        n = len(db.scalars(select(Turma.id).where(Turma.professor_id == usuario.id)).all())
        chips.append(("Professor da disciplina", f"{n} {'turma' if n == 1 else 'turmas'} sob sua responsabilidade"))
    if PERFIL_ORIENTADOR in perfis:
        n = len(_ids_orientados(db, usuario))
        chips.append(("Orientador", f"{n} {'orientando' if n == 1 else 'orientandos'}"))
    return chips


def consultar_escopo(db: Session, usuario: Usuario) -> EscopoOut:
    """GET /indicadores/escopo (DS-FL08-D mensagens 2 e 3)."""
    perfis = _exigir_perfil(db, usuario)
    tccs = escopo_tccs(db, usuario, perfis)
    filtros = _filtros(perfis)
    vigente = periodo_vigente(db)
    periodos = db.scalars(select(PeriodoLetivo).order_by(PeriodoLetivo.inicio.desc())).all()
    if PERFIL_COORDENADOR in perfis:
        cursos = db.scalars(select(Curso).where(Curso.nucleo_id == usuario.docente.nucleo_id).order_by(Curso.nome)).all() \
            if usuario.docente else []
    else:
        cursos = sorted({t.aluno.curso.id: t.aluno.curso for t in tccs.values()}.values(), key=lambda c: c.nome)
    turmas = sorted({t.turma.id: t.turma for t in tccs.values() if t.turma.professor_id == usuario.id}.values(),
                    key=lambda t: t.codigo) if filtros.turma else []
    orientadores = []
    if filtros.orientador:
        orientadores = sorted({o.id: o for t in tccs.values() if (o := _orientador(t))}.values(), key=lambda u: u.nome)
    return EscopoOut(
        perfis=sorted(perfis),
        descricao=_descricao(usuario, perfis, db),
        periodo_vigente_id=vigente.id if vigente else None,
        filtros=filtros,
        periodos=[PeriodoOut(id=p.id, codigo=p.codigo, vigente=vigente is not None and p.id == vigente.id)
                  for p in periodos],
        cursos=[CursoOut(id=c.id, sigla=c.sigla, nome=c.nome) for c in cursos],
        turmas=[TurmaOpcaoOut(id=t.id, codigo=t.codigo) for t in turmas],
        orientadores=[pessoa(u) for u in orientadores],
        filtros_indicadores=filtros_indicadores(perfis),
        professores=[pessoa(u) for u in _professores(db, usuario, perfis)],
    )


def _professores(db: Session, usuario: Usuario, perfis: set[str]) -> list[Usuario]:
    """Opções do filtro "professor" das bancas, que é só da coordenação (RBN13.05): os docentes do núcleo dela."""
    if PERFIL_COORDENADOR not in perfis or usuario.docente is None:
        return []
    consulta = (select(Usuario).join(Docente, Docente.usuario_id == Usuario.id)
                .where(Docente.nucleo_id == usuario.docente.nucleo_id).order_by(Usuario.nome))
    return list(db.scalars(consulta))


def consultar_situacao(
    db: Session, usuario: Usuario, *, periodo: int | None = None, curso: int | None = None, etapa: str | None = None,
    turma: int | None = None, orientador: int | None = None,
) -> IndicadorSituacaoOut:
    """GET /indicadores/situacao?periodo&curso&etapa&orientador (DS-FL08-D mensagens 5 a 7), com turma para o
    professor da disciplina (filtros do card)."""
    perfis = _exigir_perfil(db, usuario)
    filtros = _filtros(perfis)
    for nome, valor, permitido in (("curso", curso, filtros.curso), ("etapa", etapa, filtros.etapa),
                                   ("turma", turma, filtros.turma), ("orientador", orientador, filtros.orientador)):
        if valor is not None and not permitido:  # CA-04 do RBN13.02 e CA-06 do RBN13.01
            raise ErroAPI(403, FORA_DO_PERFIL, campo=nome)
    if etapa is not None and etapa not in ETAPAS:
        raise ErroAPI(400, "Confira os campos destacados.", campos={"etapa": "Use TCC1 ou TCC2."})

    tccs = escopo_tccs(db, usuario, perfis)
    if curso is not None and PERFIL_COORDENADOR not in perfis and curso not in {t.aluno.curso_id for t in tccs.values()}:
        raise ErroAPI(403, FORA_DO_ESCOPO, campo="curso")
    if turma is not None and turma not in {t.turma_id for t in tccs.values() if t.turma.professor_id == usuario.id}:
        raise ErroAPI(403, FORA_DO_ESCOPO, campo="turma")

    if periodo is None:
        vigente = periodo_vigente(db)
        periodo = vigente.id if vigente else None
    selecionados = [
        t for t in tccs.values()
        if (periodo is None or t.periodo_id == periodo)
        and (curso is None or t.aluno.curso_id == curso)
        and (etapa is None or t.etapa == etapa)
        and (turma is None or t.turma_id == turma)
        and (orientador is None or ((o := _orientador(t)) is not None and o.id == orientador))
    ]

    def por_etapa(lista) -> PorEtapa:
        return PorEtapa(TCC1=sum(1 for t in lista if t.etapa == "TCC1"),
                        TCC2=sum(1 for t in lista if t.etapa == "TCC2"))

    situacoes = [SituacaoOut(situacao=s, total=por_etapa([t for t in selecionados if t.situacao == s]))
                 for s in SITUACOES]  # contarPorSituacao: cada TCC conta uma vez (RN18)

    visiveis = _orientadores_visiveis(usuario, perfis, tccs)  # contarOrientandos
    grupos: dict[int, tuple[Usuario, list[Tcc]]] = {}
    for t in selecionados:
        o = _orientador(t)
        if o is None or (visiveis is not None and o.id not in visiveis):
            continue
        grupos.setdefault(o.id, (o, []))[1].append(t)
    if visiveis is not None and PERFIL_ORIENTADOR in perfis and usuario.id not in grupos and orientador in (None, usuario.id):
        grupos[usuario.id] = (usuario, [])  # o orientador vê o próprio total, mesmo zerado
    orientacoes = [OrientacoesOut(orientador=pessoa(o), total=por_etapa(lista))
                   for o, lista in sorted(grupos.values(), key=lambda g: g[0].nome)]

    return IndicadorSituacaoOut(periodo_id=periodo, total=por_etapa(selecionados), situacoes=situacoes,
                                orientacoes=orientacoes, sem_dados=not selecionados)


# =================================================================== comum às SCRUM-90 a 92


def _conferir_filtros(filtros: FiltrosDoIndicador, **valores) -> None:
    """Filtro fora do perfil recebe 403 com o campo (CA-06 do RBN13.01), mesmo vindo pela URL. As chaves são os
    nomes dos parâmetros; `periodo_inicio` e `periodo_fim` são o filtro `intervalo`."""
    for nome, valor in valores.items():
        filtro = "intervalo" if nome in ("periodo_inicio", "periodo_fim") else nome
        if valor is not None and not getattr(filtros, filtro):
            raise ErroAPI(403, FORA_DO_PERFIL, campo=nome)


def _conferir_escopo(usuario: Usuario, perfis: set[str], tccs: dict[int, Tcc], *, curso: int | None = None,
                     turma: int | None = None) -> None:
    """Curso ou turma fora do escopo: 403, como na situação (CA-06 do RBN13.01)."""
    cursos = {t.aluno.curso_id for t in tccs.values()}
    if curso is not None and PERFIL_COORDENADOR not in perfis and curso not in cursos:
        raise ErroAPI(403, FORA_DO_ESCOPO, campo="curso")
    if turma is not None and turma not in {t.turma_id for t in tccs.values() if t.turma.professor_id == usuario.id}:
        raise ErroAPI(403, FORA_DO_ESCOPO, campo="turma")


def _periodo_ou_vigente(db: Session, periodo: int | None) -> int | None:
    if periodo is not None:
        return periodo
    vigente = periodo_vigente(db)
    return vigente.id if vigente else None


# =================================================================== SCRUM-90 · RBN13.03 produção científica

# RN03 e ficha: submetido, em revisão, aceito e publicado; RECUSADO existe no DDL e no PR #23 e fica como 5º grupo,
# pendente de decisão do PO (D3).
SITUACOES_EDITORIAIS = ("SUBMETIDO", "EM_REVISAO", "ACEITO", "PUBLICADO", "RECUSADO")


def contar_producao(tccs: list[Tcc]) -> list[SituacaoEditorialOut]:
    """contarPorSituacao em PublicacaoArtigo (DS-FL08-C mensagem 5). Só modalidade artigo (CA-02). Cada TCC conta uma
    vez, pela situação atual da submissão mais recente, a mesma regra da publicação (PR #23) e da nota final; mudar a
    situação move o TCC de grupo sem mudar o total (CA-03)."""
    contagem = dict.fromkeys(SITUACOES_EDITORIAIS, 0)
    for t in tccs:
        if t.modalidade == "ARTIGO" and t.publicacoes:
            contagem[t.publicacoes[-1].situacao_atual] += 1
    return [SituacaoEditorialOut(situacao=s, total=n) for s, n in contagem.items()]


def consultar_producao(db: Session, usuario: Usuario, *, periodo: int | None = None, curso: int | None = None,
                       turma: int | None = None) -> ProducaoOut:
    """Produção científica (DS-FL08-C mensagem 5). Filtros: coordenação curso e período; professor período e turma;
    orientador período e curso (CA-04). Sem nome de aluno (CA-05)."""
    perfis = _exigir_perfil(db, usuario)
    _conferir_filtros(filtros_indicadores(perfis).producao, curso=curso, turma=turma)
    tccs = escopo_tccs(db, usuario, perfis)  # passo 3: resolverEscopo
    _conferir_escopo(usuario, perfis, tccs, curso=curso, turma=turma)
    periodo = _periodo_ou_vigente(db, periodo)
    selecionados = [
        t for t in tccs.values()
        if (periodo is None or t.periodo_id == periodo)
        and (curso is None or t.aluno.curso_id == curso)
        and (turma is None or t.turma_id == turma)
    ]
    situacoes = contar_producao(selecionados)  # passo 5
    total = sum(s.total for s in situacoes)
    return ProducaoOut(periodo_id=periodo, total=total, situacoes=situacoes, sem_dados=total == 0)


# =================================================================== SCRUM-91 · RBN13.04 desistências


def _intervalo(db: Session, periodo_inicio: int | None, periodo_fim: int | None) -> list[PeriodoLetivo]:
    """Os períodos da evolução, em ordem de início. Sem intervalo, todos; início depois do fim, 400."""
    periodos = list(db.scalars(select(PeriodoLetivo).order_by(PeriodoLetivo.inicio)))
    ids = [p.id for p in periodos]
    campos = {nome: "Escolha um período letivo." for nome, valor in (("periodo_inicio", periodo_inicio),
                                                                     ("periodo_fim", periodo_fim))
              if valor is not None and valor not in ids}
    if campos:
        raise ErroAPI(400, "Confira os campos destacados.", campos=campos)
    de = ids.index(periodo_inicio) if periodo_inicio is not None else 0
    ate = ids.index(periodo_fim) if periodo_fim is not None else len(ids) - 1
    if de > ate:
        raise ErroAPI(400, "Confira os campos destacados.",
                      campos={"periodo_fim": "O fim do intervalo não pode vir antes do início."})
    return periodos[de:ate + 1]


def consultar_desistencias(
    db: Session, usuario: Usuario, *, periodo: int | None = None, curso: int | None = None, turma: int | None = None,
    etapa: str | None = None, periodo_inicio: int | None = None, periodo_fim: int | None = None,
) -> DesistenciasOut:
    """GET /indicadores/desistencias (DS-FL08-D mensagens 9 a 11). Filtros: coordenação curso, intervalo de períodos
    e etapa; professor período e turma; orientador só período (CA-05). Só TCC na situação DESISTENCIA conta;
    reprovado não (CA-04). A evolução por período é só da coordenação (alt do diagrama, CA-02 e CA-03)."""
    perfis = _exigir_perfil(db, usuario)
    _conferir_filtros(filtros_indicadores(perfis).desistencias, curso=curso, turma=turma, etapa=etapa,
                      periodo_inicio=periodo_inicio, periodo_fim=periodo_fim)  # CT-13.04-07: evolução pela URL
    if etapa is not None and etapa not in ETAPAS:
        raise ErroAPI(400, "Confira os campos destacados.", campos={"etapa": "Use TCC1 ou TCC2."})
    tccs = escopo_tccs(db, usuario, perfis)
    _conferir_escopo(usuario, perfis, tccs, curso=curso, turma=turma)
    periodo = _periodo_ou_vigente(db, periodo)

    desistentes = [  # mensagem 10: contarDesistencias(escopo, filtros)
        t for t in tccs.values()
        if t.situacao == "DESISTENCIA"
        and (curso is None or t.aluno.curso_id == curso)
        and (turma is None or t.turma_id == turma)
        and (etapa is None or t.etapa == etapa)
    ]
    no_periodo = [t for t in desistentes if periodo is None or t.periodo_id == periodo]
    if PERFIL_COORDENADOR in perfis:
        cursos = list(db.scalars(select(Curso).where(Curso.nucleo_id == usuario.docente.nucleo_id)
                                 .order_by(Curso.nome))) if usuario.docente else []
    else:
        cursos = sorted({t.aluno.curso.id: t.aluno.curso for t in tccs.values()}.values(), key=lambda c: c.nome)
    por_curso = [DesistenciasCursoOut(curso=CursoOut(id=c.id, sigla=c.sigla, nome=c.nome),
                                      total=sum(1 for t in no_periodo if t.aluno.curso_id == c.id))
                 for c in cursos if curso is None or c.id == curso]

    evolucao = None
    if PERFIL_COORDENADOR in perfis:  # mensagem 11: evolucaoPorPeriodo(intervalo), só na coordenação
        vigente = periodo_vigente(db)
        evolucao = [EvolucaoOut(periodo=PeriodoOut(id=p.id, codigo=p.codigo,
                                                   vigente=vigente is not None and p.id == vigente.id),
                                total=sum(1 for t in desistentes if t.periodo_id == p.id))
                    for p in _intervalo(db, periodo_inicio, periodo_fim)]
    return DesistenciasOut(periodo_id=periodo, total=len(no_periodo), por_curso=por_curso, evolucao=evolucao,
                           sem_dados=not no_periodo)


# =================================================================== SCRUM-92 · RBN13.05 participações em banca

PAPEIS = ("ORIENTADOR", "AVALIADOR", "COORIENTADOR", "SUPLENTE")


def _membros_da_banca(db: Session, usuario: Usuario, perfis: set[str]) -> list[BancaMembro]:
    """O escopo das bancas (CA-03 e CA-04): a coordenação vê os membros das bancas dos TCCs do núcleo; o professor e
    o orientador, só as próprias participações. Só docentes da UEA (interno) e defesas não canceladas."""
    donos = []
    if PERFIL_COORDENADOR in perfis and usuario.docente is not None:
        donos.append(Curso.nucleo_id == usuario.docente.nucleo_id)
    if PERFIL_PROFESSOR in perfis or PERFIL_ORIENTADOR in perfis:
        donos.append(BancaMembro.usuario_id == usuario.id)
    if not donos:
        return []
    consulta = (select(BancaMembro).join(Defesa, Defesa.id == BancaMembro.defesa_id)
                .join(Tcc, Tcc.id == Defesa.tcc_id).join(Aluno, Aluno.usuario_id == Tcc.aluno_id)
                .join(Curso, Curso.id == Aluno.curso_id)
                .where(BancaMembro.interno.is_(True), Defesa.situacao != "CANCELADA", or_(*donos)))
    return list(db.scalars(consulta))


def contar_participacoes(membros: list[BancaMembro]) -> dict[int, tuple[Usuario, dict[str, int]]]:
    """contarParticipacoes e suplentesConvocados (DS-FL08-D mensagens 14 e 15). Só defesa realizada (a regra da
    avaliação e da declaração). Um por professor e por papel em cada banca (CA-05; a banca não repete o membro). O
    suplente só conta se foi convocado, e o titular que ele substituiu deixa de contar (CA-02, RN20)."""
    grupos: dict[int, tuple[Usuario, dict[str, int]]] = {}
    for m in membros:
        if not realizada(m.defesa):
            continue
        if m.papel == "SUPLENTE" and m.convocado_em is None:
            continue
        if any(s.substitui_membro_id == m.id and s.convocado_em is not None for s in m.defesa.membros):
            continue
        grupos.setdefault(m.usuario_id, (m.usuario, dict.fromkeys(PAPEIS, 0)))[1][m.papel] += 1
    return grupos


def consultar_bancas(
    db: Session, usuario: Usuario, *, periodo: int | None = None, curso: int | None = None,
    professor: int | None = None, papel: str | None = None,
) -> BancasOut:
    """GET /indicadores/bancas (DS-FL08-D mensagens 13 a 15). Filtros: coordenação curso, período, professor e papel;
    professor e orientador período e papel (CA-03 e CA-04). Período e curso são os do TCC defendido."""
    perfis = _exigir_perfil(db, usuario)
    _conferir_filtros(filtros_indicadores(perfis).bancas, curso=curso, professor=professor)
    if papel is not None and papel not in PAPEIS:
        raise ErroAPI(400, "Confira os campos destacados.", campos={"papel": "Escolha um dos papéis da banca."})
    if professor is not None and professor not in {u.id for u in _professores(db, usuario, perfis)}:
        raise ErroAPI(403, FORA_DO_ESCOPO, campo="professor")
    periodo = _periodo_ou_vigente(db, periodo)
    membros = [
        m for m in _membros_da_banca(db, usuario, perfis)
        if (periodo is None or m.defesa.tcc.periodo_id == periodo)
        and (curso is None or m.defesa.tcc.aluno.curso_id == curso)
        and (professor is None or m.usuario_id == professor)
        and (papel is None or m.papel == papel)
    ]
    grupos = contar_participacoes(membros)
    if PERFIL_COORDENADOR not in perfis and usuario.id not in grupos:
        grupos[usuario.id] = (usuario, dict.fromkeys(PAPEIS, 0))  # o professor vê o próprio total, mesmo zerado
    professores = [ParticipacoesOut(professor=pessoa(u), total=PorPapel(**n))
                   for u, n in sorted(grupos.values(), key=lambda g: g[0].nome)]
    total = PorPapel(**{p: sum(n[p] for _, n in grupos.values()) for p in PAPEIS})
    return BancasOut(periodo_id=periodo, total=total, professores=professores,
                     sem_dados=not any(total.model_dump().values()))


# =================================================================== DS-FL08-C · painel


def consultar_indicadores(db: Session, usuario: Usuario, *, periodo: int | None = None, curso: int | None = None,
                          turma: int | None = None) -> IndicadoresOut:
    """GET /indicadores?periodo&curso (DS-FL08-C mensagens 2 a 6, consultarIndicadores), com turma para o professor
    da disciplina. Os filtros são os da produção científica; as bancas recebem o período e, se o perfil filtra
    bancas por curso, o curso (E2)."""
    perfis = _exigir_perfil(db, usuario)
    filtros = filtros_indicadores(perfis)
    _conferir_filtros(filtros.producao, curso=curso, turma=turma)
    producao = consultar_producao(db, usuario, periodo=periodo, curso=curso, turma=turma)  # mensagem 5
    situacao = consultar_situacao(db, usuario, periodo=periodo, curso=curso, turma=turma)  # mensagem 4
    bancas = consultar_bancas(db, usuario, periodo=periodo,
                              curso=curso if filtros.bancas.curso else None)  # mensagem 6
    return IndicadoresOut(periodo_id=producao.periodo_id, situacao=situacao, producao=producao, bancas=bancas)


# =================================================================== SCRUM-93 · RBN13.06 relatório em PDF

NOME_SITUACAO = {"RASCUNHO": "Rascunho", "EM_ANALISE": "Em análise", "APROVADO": "Aprovado",
                 "DEVOLVIDO": "Devolvido para correção", "REPROVADO": "Reprovado", "DESISTENCIA": "Desistência",
                 "CONCLUIDO": "Concluído"}
NOME_EDITORIAL = {"SUBMETIDO": "Submetido", "EM_REVISAO": "Em revisão", "ACEITO": "Aceito",
                  "PUBLICADO": "Publicado", "RECUSADO": "Recusado"}
NOME_PAPEL = {"ORIENTADOR": "Orientador(a)", "AVALIADOR": "Avaliador(a)", "COORIENTADOR": "Coorientador(a)",
              "SUPLENTE": "Suplente convocado"}


def _so_permitidos(filtros: FiltrosDoIndicador, valores: dict) -> dict:
    """Os filtros da tela que valem para um indicador: o mesmo recorte que a tela faz em cada aba."""
    def permitido(nome):
        return getattr(filtros, "intervalo" if nome in ("periodo_inicio", "periodo_fim") else nome)
    return {k: v for k, v in valores.items() if v is not None and permitido(k)}


def _rotulos_dos_filtros(db: Session, valores: dict, periodo_id: int | None) -> list[tuple[str, str]]:
    """O que o relatório imprime no início: período letivo, curso e os demais filtros usados (CA do RBN13.06)."""
    periodo = db.get(PeriodoLetivo, periodo_id) if periodo_id else None
    curso = db.get(Curso, valores["curso"]) if valores.get("curso") else None
    linhas = [("Período letivo", periodo.codigo if periodo else "nenhum cadastrado"),
              ("Curso", curso.nome if curso else "todos do escopo")]
    extras = []
    if valores.get("etapa"):
        extras.append(f"etapa {valores['etapa']}")
    if valores.get("turma"):
        turma = db.get(Turma, valores["turma"])
        extras.append(f"turma {turma.codigo if turma else valores['turma']}")
    for chave, rotulo in (("orientador", "orientador"), ("professor", "professor")):
        if valores.get(chave):
            pessoa_ = db.get(Usuario, valores[chave])
            extras.append(f"{rotulo} {pessoa_.nome if pessoa_ else valores[chave]}")
    if valores.get("papel"):
        extras.append(f"papel na banca {NOME_PAPEL[valores['papel']].lower()}")
    if valores.get("periodo_inicio") or valores.get("periodo_fim"):
        ini = db.get(PeriodoLetivo, valores["periodo_inicio"]) if valores.get("periodo_inicio") else None
        fim = db.get(PeriodoLetivo, valores["periodo_fim"]) if valores.get("periodo_fim") else None
        extras.append(f"evolução de {ini.codigo if ini else 'início'} a {fim.codigo if fim else 'hoje'}")
    linhas.append(("Outros filtros", "; ".join(extras) if extras else "nenhum"))
    return linhas


def relatorio_pdf(db: Session, usuario: Usuario, **valores) -> tuple[bytes, str]:
    """GET /indicadores/relatorio (RBN13.06): os indicadores RBN13.02 a 13.05 com os filtros escolhidos na tela, cada um
    com os filtros que o perfil tem nele, no mesmo escopo da tela (RBN13.01, RN18) e sem nome de aluno. Filtro que
    o perfil não tem em nenhum indicador recebe 403; a geração fica no log (RNF03)."""
    perfis = _exigir_perfil(db, usuario)
    por_indicador = filtros_indicadores(perfis)
    for nome, valor in valores.items():
        if valor is not None and nome != "periodo" and not any(
                _so_permitidos(getattr(por_indicador, ind), {nome: valor})
                for ind in ("situacao", "producao", "desistencias", "bancas")):
            raise ErroAPI(403, FORA_DO_PERFIL, campo=nome)

    situacao = consultar_situacao(db, usuario, **_so_permitidos(por_indicador.situacao, valores))
    producao = consultar_producao(db, usuario, **_so_permitidos(por_indicador.producao, valores))
    desistencias = consultar_desistencias(db, usuario, **_so_permitidos(por_indicador.desistencias, valores))
    bancas = consultar_bancas(db, usuario, **_so_permitidos(por_indicador.bancas, valores))

    def etapas(t: PorEtapa) -> list[str]:
        return [str(t.TCC1), str(t.TCC2), str(t.TCC1 + t.TCC2)]

    secoes = [
        ("1. Situação dos TCCs", ["Situação", "TCC1", "TCC2", "Total"],
         [[NOME_SITUACAO[s.situacao], *etapas(s.total)] for s in situacao.situacoes]
         + [["Total", *etapas(situacao.total)]], (88, 27, 27, 24), None),
        ("Orientandos por orientador", ["Orientador(a)", "TCC1", "TCC2", "Total"],
         [[o.orientador.nome, *etapas(o.total)] for o in situacao.orientacoes], (88, 27, 27, 24), None),
        ("2. Produção científica", ["Situação editorial", "TCCs"],
         [[NOME_EDITORIAL[s.situacao], str(s.total)] for s in producao.situacoes] + [["Total", str(producao.total)]],
         (120, 46), "Só TCCs na modalidade artigo, pela situação da submissão mais recente."),
        ("3. Desistências", ["Curso", "Desistências"],
         [[c.curso.nome, str(c.total)] for c in desistencias.por_curso] + [["Total", str(desistencias.total)]],
         (120, 46), None),
    ]
    if desistencias.evolucao is not None:
        secoes.append(("Evolução das desistências por período", ["Período letivo", "Desistências"],
                       [[e.periodo.codigo, str(e.total)] for e in desistencias.evolucao], (120, 46), None))
    papeis = list(NOME_PAPEL)
    secoes.append((
        "4. Participações em banca", ["Professor(a)", *[NOME_PAPEL[p] for p in papeis], "Total"],
        [[p.professor.nome, *[str(getattr(p.total, k)) for k in papeis], str(sum(p.total.model_dump().values()))]
         for p in bancas.professores],
        (50, 22, 22, 24, 26, 22), "Só defesas realizadas; o suplente conta apenas quando convocado."))

    usados = {k: v for k, v in valores.items() if v is not None}
    conteudo = documentos.indicadores_pdf(secoes, filtros=_rotulos_dos_filtros(db, usados, situacao.periodo_id),
                                          gerado_por=usuario.nome, gerado_em=agora())
    auditoria.registrar(db, ator_id=usuario.id, acao="relatorio_indicadores_gerado", entidade="indicadores",
                        novo="; ".join(f"{k}={v}" for k, v in usados.items()) or "sem filtros")
    db.commit()
    return conteudo, f"relatorio-indicadores-{date.today().isoformat()}.pdf"
