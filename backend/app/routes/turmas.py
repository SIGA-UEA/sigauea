"""Períodos letivos e turmas (RBN08.01 a RBN08.03). Só a coordenação altera;
professor e aluno veem as próprias turmas em Minhas turmas."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import coordenador, usuario_atual
from app.models import Usuario
from app.schemas.tcc import (
    MatriculaAtualizar,
    MatriculaCriar,
    PeriodoCriar,
    PeriodoOut,
    TurmaCartao,
    TurmaCriar,
    TurmaOut,
)
from app.services import turmas

router = APIRouter(tags=["turmas"])


@router.get("/periodos", response_model=list[PeriodoOut], dependencies=[Depends(usuario_atual)])
def listar_periodos(db: Session = Depends(get_db, scope="function")):
    return turmas.listar_periodos(db)


@router.post("/periodos", response_model=PeriodoOut, status_code=201)
def criar_periodo(dados: PeriodoCriar, db: Session = Depends(get_db, scope="function"), ator: Usuario = Depends(coordenador)):
    return turmas.criar_periodo(db, dados, ator)


@router.get("/turmas", response_model=list[TurmaOut])
def listar_turmas(
    periodo: int | None = None, db: Session = Depends(get_db, scope="function"), _: Usuario = Depends(coordenador)
) -> list[TurmaOut]:
    return [turmas.para_saida(t) for t in turmas.listar_turmas(db, periodo)]


@router.get("/turmas/minhas", response_model=list[TurmaCartao])
def minhas_turmas(
    db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)
) -> list[TurmaCartao]:
    """Professor: as turmas que conduz. Aluno: as turmas em que está matriculado."""
    return [turmas.cartao(t, eu) for t in turmas.minhas(db, eu)]


@router.post("/turmas", response_model=TurmaOut, status_code=201)
def criar_turma(
    dados: TurmaCriar, db: Session = Depends(get_db, scope="function"), ator: Usuario = Depends(coordenador)
) -> TurmaOut:
    return turmas.para_saida(turmas.criar_turma(db, dados, ator))


@router.get("/turmas/{turma_id}", response_model=TurmaOut)
def obter_turma(
    turma_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)
) -> TurmaOut:
    """Coordenação ou o professor responsável pela turma (404 para os demais)."""
    return turmas.para_saida(turmas.obter_para(db, eu, turma_id))


@router.post("/turmas/{turma_id}/alunos", response_model=TurmaOut, status_code=201)
def incluir_aluno(
    turma_id: int, dados: MatriculaCriar, db: Session = Depends(get_db, scope="function"), ator: Usuario = Depends(coordenador)
) -> TurmaOut:
    return turmas.para_saida(turmas.incluir_aluno(db, turma_id, dados.aluno_id, ator))


@router.patch("/turmas/{turma_id}/alunos/{matricula_id}", response_model=TurmaOut)
def alterar_situacao(
    turma_id: int,
    matricula_id: int,
    dados: MatriculaAtualizar,
    db: Session = Depends(get_db, scope="function"),
    ator: Usuario = Depends(coordenador),
) -> TurmaOut:
    return turmas.para_saida(turmas.alterar_situacao(db, turma_id, matricula_id, dados.situacao, ator))
