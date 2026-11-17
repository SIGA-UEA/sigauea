"""Rotas dos indicadores gerenciais (TEL16 Indicadores · RBN13.01 e RBN13.02 · DS-FL08-D).

GET /indicadores/escopo: escopo e filtros do perfil. GET /indicadores/situacao: situação dos TCCs e orientações,
por etapa. Quem pode e o escopo são conferidos no serviço.
"""

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual
from app.models import Usuario
from app.schemas.indicador import EscopoOut, IndicadorSituacaoOut
from app.services import indicadores

router = APIRouter(tags=["indicadores"])


@router.get("/indicadores/escopo", response_model=EscopoOut)
def escopo(db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)):
    """Escopo, períodos (com o vigente), cursos, turmas e orientadores que o perfil pode filtrar. 403 sem perfil
    de coordenação, professor da disciplina ou orientador."""
    return indicadores.consultar_escopo(db, eu)


@router.get("/indicadores/situacao", response_model=IndicadorSituacaoOut)
def situacao(
    periodo: int | None = Query(default=None),
    curso: int | None = Query(default=None),
    etapa: Literal["TCC1", "TCC2"] | None = Query(default=None),
    turma: int | None = Query(default=None),
    orientador: int | None = Query(default=None),
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
):
    """Totais por situação acadêmica e orientandos por orientador, separados por TCC1 e TCC2. Sem período, usa o
    vigente. 403 para filtro fora do perfil ou curso, turma ou orientador fora do escopo."""
    return indicadores.consultar_situacao(db, eu, periodo=periodo, curso=curso, etapa=etapa, turma=turma,
                                          orientador=orientador)
