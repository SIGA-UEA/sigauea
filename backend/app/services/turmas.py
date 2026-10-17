"""Períodos letivos, turmas e matrícula de alunos na turma (RBN08.01 a RBN08.03).

A matrícula na turma com situação MATRICULADO é o que libera o cadastro de TCC (RN05).
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import agora
from app.erros import ErroAPI
from app.models import (
    MATRICULADO,
    PERFIL_ORIENTADOR,
    PERFIL_PROFESSOR,
    Aluno,
    Docente,
    MatriculaTurma,
    PeriodoLetivo,
    Turma,
    Usuario,
)
from app.schemas.tcc import (
    MatriculaOut,
    PeriodoCriar,
    PeriodoOut,
    PessoaOut,
    TurmaCriar,
    TurmaOut,
    TurmaResumo,
)
from app.schemas.usuario import CursoOut
from app.services import auditoria
from app.services.usuarios import curso_valido


def pessoa(u: Usuario) -> PessoaOut:
    return PessoaOut(id=u.id, nome=u.nome)


def turma_resumo(t: Turma) -> TurmaResumo:
    return TurmaResumo(
        id=t.id,
        codigo=t.codigo,
        disciplina=t.disciplina,
        periodo=t.periodo.codigo,
        professor=pessoa(t.professor.usuario),
    )


def para_saida(t: Turma) -> TurmaOut:
    return TurmaOut(
        id=t.id,
        codigo=t.codigo,
        disciplina=t.disciplina,
        curso=CursoOut.model_validate(t.curso),
        periodo=PeriodoOut.model_validate(t.periodo),
        professor=pessoa(t.professor.usuario),
        encerrada=t.encerrada_em is not None,
        alunos=[
            MatriculaOut(
                id=m.id,
                aluno=pessoa(m.aluno.usuario),
                matricula=m.aluno.matricula,
                curso=CursoOut.model_validate(m.aluno.curso),
                situacao=m.situacao,
                incluido_em=m.incluido_em,
            )
            for m in t.matriculas
        ],
    )


# ---------------------------------------------------------------- períodos


def criar_periodo(db: Session, dados: PeriodoCriar, ator: Usuario) -> PeriodoLetivo:
    if dados.fim <= dados.inicio:
        raise ErroAPI(
            400, "Confira os campos destacados.", campos={"fim": "O fim deve ser depois do início."}
        )
    if db.scalar(select(PeriodoLetivo).where(PeriodoLetivo.codigo == dados.codigo)):
        raise ErroAPI(409, "Este período letivo já existe.", campo="codigo")
    periodo = PeriodoLetivo(**dados.model_dump())
    db.add(periodo)
    db.flush()
    auditoria.registrar(
        db,
        ator_id=ator.id,
        acao="criar_periodo",
        entidade="periodo_letivo",
        entidade_id=periodo.id,
        campo="codigo",
        novo=periodo.codigo,
    )
    db.commit()
    return periodo


def listar_periodos(db: Session) -> list[PeriodoLetivo]:
    return list(db.scalars(select(PeriodoLetivo).order_by(PeriodoLetivo.inicio.desc())))


# ---------------------------------------------------------------- turmas


def _obter(db: Session, turma_id: int) -> Turma:
    turma = db.get(Turma, turma_id)
    if turma is None:
        raise ErroAPI(404, "Turma não encontrada.")
    return turma


def obter(db: Session, turma_id: int) -> Turma:
    return _obter(db, turma_id)


def criar_turma(db: Session, dados: TurmaCriar, ator: Usuario) -> Turma:
    curso = curso_valido(db, dados.curso_id)
    periodo = db.get(PeriodoLetivo, dados.periodo_id)
    if periodo is None:
        raise ErroAPI(400, "Confira os campos destacados.", campos={"periodo_id": "Período inválido."})
    docente = db.get(Docente, dados.professor_id)
    # TCC1: professor da disciplina; TCC2: a turma é do orientador (RN26).
    exigido = PERFIL_PROFESSOR if dados.disciplina == "TCC1" else PERFIL_ORIENTADOR
    # Basta não estar inativado: a turma pode ser montada antes de o docente ativar a conta.
    if docente is None or docente.usuario.inativado_em is not None or exigido not in docente.usuario.perfis:
        quem = "professor da disciplina" if dados.disciplina == "TCC1" else "orientador"
        raise ErroAPI(
            400,
            "Confira os campos destacados.",
            campos={"professor_id": f"Escolha um docente (não inativado) com perfil de {quem}."},
        )
    base = f"{dados.disciplina}-{curso.sigla}-{periodo.codigo}"
    n = 1 + len(list(db.scalars(select(Turma.id).where(Turma.codigo.like(f"{base}%")))))
    turma = Turma(
        codigo=f"{base}-{n}",
        disciplina=dados.disciplina,
        curso_id=curso.id,
        periodo_id=periodo.id,
        professor_id=docente.usuario_id,
    )
    db.add(turma)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ErroAPI(
            409, "Já existe uma turma igual (mesmo curso, disciplina, período e professor)."
        ) from None
    auditoria.registrar(
        db,
        ator_id=ator.id,
        acao="criar_turma",
        entidade="turma",
        entidade_id=turma.id,
        campo="codigo",
        novo=turma.codigo,
    )
    db.commit()
    db.refresh(turma)
    return turma


def listar_turmas(db: Session, periodo_id: int | None = None) -> list[Turma]:
    consulta = select(Turma).order_by(Turma.codigo)
    if periodo_id:
        consulta = consulta.where(Turma.periodo_id == periodo_id)
    return list(db.scalars(consulta))


def incluir_aluno(db: Session, turma_id: int, aluno_id: int, ator: Usuario) -> Turma:
    """RBN08.02: só a coordenação inclui; o curso do aluno é mantido mesmo se for outro."""
    turma = _obter(db, turma_id)
    if turma.encerrada_em is not None:
        raise ErroAPI(409, "Turma encerrada não aceita novos alunos.")
    aluno = db.get(Aluno, aluno_id)
    if aluno is None or aluno.usuario.inativado_em is not None:
        raise ErroAPI(400, "Confira os campos destacados.", campos={"aluno_id": "Aluno inválido ou inativo."})
    if any(m.aluno_id == aluno_id for m in turma.matriculas):
        raise ErroAPI(409, "Este aluno já está nesta turma.", campo="aluno_id")
    # Um aluno fica em uma única turma da mesma disciplina por período.
    outra = db.scalar(
        select(MatriculaTurma)
        .join(Turma)
        .where(
            MatriculaTurma.aluno_id == aluno_id,
            Turma.periodo_id == turma.periodo_id,
            Turma.disciplina == turma.disciplina,
        )
    )
    if outra:
        raise ErroAPI(409, f"O aluno já está na turma {outra.turma.codigo} neste período.", campo="aluno_id")
    m = MatriculaTurma(turma_id=turma.id, aluno_id=aluno_id, situacao=MATRICULADO, incluido_por=ator.id)
    db.add(m)
    db.flush()
    auditoria.registrar(
        db,
        ator_id=ator.id,
        acao="incluir_aluno_turma",
        entidade="matricula_turma",
        entidade_id=m.id,
        campo="turma",
        novo=turma.codigo,
    )
    db.commit()
    db.refresh(turma)
    return turma


def alterar_situacao(db: Session, turma_id: int, matricula_id: int, situacao: str, ator: Usuario) -> Turma:
    """RBN08.03: em vez de excluir, a matrícula muda de situação; o histórico fica."""
    turma = _obter(db, turma_id)
    if turma.encerrada_em is not None:
        raise ErroAPI(409, "Turma encerrada não aceita mudança de situação.")
    m = db.get(MatriculaTurma, matricula_id)
    if m is None or m.turma_id != turma.id:
        raise ErroAPI(404, "Aluno não encontrado nesta turma.")
    if m.situacao != situacao:
        auditoria.registrar(
            db,
            ator_id=ator.id,
            acao="alterar_situacao_matricula",
            entidade="matricula_turma",
            entidade_id=m.id,
            campo="situacao",
            anterior=m.situacao,
            novo=situacao,
        )
        m.situacao = situacao
        m.situacao_alterada_em = agora()
        db.commit()
        db.refresh(turma)
    return turma
