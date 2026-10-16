"""Gestão das áreas de interesse (RBN01.02). Só a coordenação.

A lista simples, usada nos formulários, continua em GET /areas (catalogo.py).
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import coordenador
from app.models import Usuario
from app.schemas.usuario import AreaEntrada, AreaUsoOut
from app.services import areas

router = APIRouter(prefix="/areas", tags=["áreas de interesse"])


@router.get("/gestao", response_model=list[AreaUsoOut])
def listar_para_gestao(
    db: Session = Depends(get_db), _: Usuario = Depends(coordenador)
) -> list[AreaUsoOut]:
    return areas.listar_com_uso(db)


@router.post("", response_model=AreaUsoOut, status_code=201)
def criar_area(
    dados: AreaEntrada, db: Session = Depends(get_db), ator: Usuario = Depends(coordenador)
) -> AreaUsoOut:
    return areas.criar(db, dados.nome, ator)


@router.put("/{area_id}", response_model=AreaUsoOut)
def renomear_area(
    area_id: int,
    dados: AreaEntrada,
    db: Session = Depends(get_db),
    ator: Usuario = Depends(coordenador),
) -> AreaUsoOut:
    return areas.renomear(db, area_id, dados.nome, ator)


@router.delete("/{area_id}", status_code=204)
def excluir_area(
    area_id: int, db: Session = Depends(get_db), ator: Usuario = Depends(coordenador)
) -> Response:
    areas.excluir(db, area_id, ator)
    return Response(status_code=204)
