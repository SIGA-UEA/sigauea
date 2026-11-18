"""Rotas dos indicadores gerenciais (TEL16 Indicadores · RBN13.01 a RBN13.06 · DS-FL08-C e DS-FL08-D).

GET /indicadores/escopo: escopo e filtros do perfil. GET /indicadores/situacao: situação dos TCCs e orientações,
por etapa. GET /indicadores: painel do DS-FL08-C (situação, produção científica e bancas). GET
/indicadores/desistencias: desistências e evolução. GET /indicadores/bancas: participações em banca. GET
/indicadores/relatorio: os quatro indicadores em PDF (RBN13.06). Quem pode e o escopo são conferidos no serviço.
"""

from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual
from app.models import Usuario
from app.schemas.indicador import BancasOut, DesistenciasOut, EscopoOut, IndicadoresOut, IndicadorSituacaoOut
from app.services import indicadores

router = APIRouter(tags=["indicadores"])
Papel = Literal["ORIENTADOR", "AVALIADOR", "COORIENTADOR", "SUPLENTE"]


@router.get("/indicadores", response_model=IndicadoresOut)
def painel(
    periodo: int | None = Query(default=None),
    curso: int | None = Query(default=None),
    turma: int | None = Query(default=None),
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
):
    """DS-FL08-C: situação acadêmica, produção científica (RBN13.03) e bancas. Sem período, usa o vigente. 403 para
    filtro fora do perfil ou curso e turma fora do escopo."""
    return indicadores.consultar_indicadores(db, eu, periodo=periodo, curso=curso, turma=turma)


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


@router.get("/indicadores/desistencias", response_model=DesistenciasOut)
def desistencias(
    periodo: int | None = Query(default=None),
    curso: int | None = Query(default=None),
    turma: int | None = Query(default=None),
    etapa: Literal["TCC1", "TCC2"] | None = Query(default=None),
    periodo_inicio: int | None = Query(default=None),
    periodo_fim: int | None = Query(default=None),
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
):
    """RBN13.04: total por período e curso; a evolução no intervalo de períodos só para a coordenação. 403 para
    filtro fora do perfil (inclusive a evolução pela URL); 400 {campos} para intervalo inválido."""
    return indicadores.consultar_desistencias(db, eu, periodo=periodo, curso=curso, turma=turma, etapa=etapa,
                                              periodo_inicio=periodo_inicio, periodo_fim=periodo_fim)


@router.get("/indicadores/bancas", response_model=BancasOut)
def bancas(
    periodo: int | None = Query(default=None),
    curso: int | None = Query(default=None),
    professor: int | None = Query(default=None),
    papel: Papel | None = Query(default=None),
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
):
    """RBN13.05: participações por professor e por papel, com o suplente só se convocado (RN20). 403 para filtro
    fora do perfil ou professor fora do núcleo."""
    return indicadores.consultar_bancas(db, eu, periodo=periodo, curso=curso, professor=professor, papel=papel)


@router.get("/indicadores/relatorio", response_class=Response,
            responses={200: {"content": {"application/pdf": {}}, "description": "Relatório dos indicadores em PDF"}})
def relatorio(
    periodo: int | None = Query(default=None),
    curso: int | None = Query(default=None),
    etapa: Literal["TCC1", "TCC2"] | None = Query(default=None),
    turma: int | None = Query(default=None),
    orientador: int | None = Query(default=None),
    professor: int | None = Query(default=None),
    papel: Papel | None = Query(default=None),
    periodo_inicio: int | None = Query(default=None),
    periodo_fim: int | None = Query(default=None),
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
) -> Response:
    """RBN13.06: situação, produção científica, desistências e bancas com os filtros da tela, cada indicador com os
    filtros que o perfil tem nele. 403 para filtro que o perfil não tem em nenhum indicador ou fora do escopo."""
    conteudo, nome = indicadores.relatorio_pdf(
        db, eu, periodo=periodo, curso=curso, etapa=etapa, turma=turma, orientador=orientador, professor=professor,
        papel=papel, periodo_inicio=periodo_inicio, periodo_fim=periodo_fim)
    return Response(content=conteudo, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})
