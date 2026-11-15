"""Indicadores gerenciais: escopo por perfil e situação dos TCCs e das orientações (RBN13.01 e RBN13.02 ·
RN01, RN02, RN07, RN10, RN18 · DS-FL08-D, TEL16).

Faz o papel do ControladorIndicadores do diagrama de classes (MOD06): resolverEscopo, contarPorSituacao e
contarOrientandos. Desistências (RBN13.04), participações em banca (RBN13.05), produção científica (RBN13.03) e
o relatório em PDF (RBN13.06) são das histórias SCRUM-90 a SCRUM-93 e usam o mesmo escopo.

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

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.erros import ErroAPI
from app.models import (
    ACEITA,
    PAPEL_ORIENTADOR,
    PERFIL_COORDENADOR,
    PERFIL_ORIENTADOR,
    PERFIL_PROFESSOR,
    Aluno,
    Curso,
    Orientacao,
    PeriodoLetivo,
    Tcc,
    Turma,
    Usuario,
)
from app.schemas.indicador import (
    CursoOut,
    EscopoOut,
    FiltrosOut,
    IndicadorSituacaoOut,
    OrientacoesOut,
    PeriodoOut,
    PorEtapa,
    SituacaoOut,
    TurmaOpcaoOut,
)
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
    )


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
