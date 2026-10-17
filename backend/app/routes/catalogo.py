"""Listas de apoio dos formulários: perfis, cursos e áreas de interesse."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual
from app.models import AreaInteresse, Curso, Perfil
from app.schemas.usuario import AreaOut, CursoOut, PerfilOut

router = APIRouter(tags=["catálogo"], dependencies=[Depends(usuario_atual)])


@router.get("/perfis", response_model=list[PerfilOut])
def listar_perfis(db: Session = Depends(get_db, scope="function")):
    return db.scalars(select(Perfil).order_by(Perfil.id)).all()


@router.get("/cursos", response_model=list[CursoOut])
def listar_cursos(db: Session = Depends(get_db, scope="function")):
    return db.scalars(select(Curso).order_by(Curso.nome)).all()


@router.get("/areas", response_model=list[AreaOut])
def listar_areas(db: Session = Depends(get_db, scope="function")):
    return db.scalars(select(AreaInteresse).order_by(AreaInteresse.nome)).all()
