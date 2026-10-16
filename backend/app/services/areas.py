"""Áreas de interesse mantidas pela coordenação (RBN01.02).

Excluir uma área tira o vínculo dela com os docentes (RN25); o log guarda quem
estava vinculado, para a exclusão poder ser conferida depois (RNF03).
"""

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.erros import ErroAPI
from app.models import AreaInteresse, DocenteArea, Usuario
from app.schemas.usuario import AreaUsoOut
from app.services import auditoria


def listar_com_uso(db: Session) -> list[AreaUsoOut]:
    uso = (
        select(DocenteArea.area_id, func.count().label("docentes"))
        .group_by(DocenteArea.area_id)
        .subquery()
    )
    linhas = db.execute(
        select(AreaInteresse, func.coalesce(uso.c.docentes, 0))
        .outerjoin(uso, uso.c.area_id == AreaInteresse.id)
        .order_by(AreaInteresse.nome)
    )
    return [AreaUsoOut(id=a.id, nome=a.nome, docentes=n) for a, n in linhas]


def _obter(db: Session, area_id: int) -> AreaInteresse:
    area = db.get(AreaInteresse, area_id)
    if area is None:
        raise ErroAPI(404, "Área de interesse não encontrada.")
    return area


def _exigir_nome_livre(db: Session, nome: str, exceto_id: int | None = None) -> None:
    existente = db.scalar(
        select(AreaInteresse).where(func.lower(AreaInteresse.nome) == nome.lower())
    )
    if existente and existente.id != exceto_id:
        raise ErroAPI(409, "Já existe uma área com este nome.", campo="nome")


def _uso(db: Session, area_id: int) -> int:
    return db.scalar(select(func.count()).where(DocenteArea.area_id == area_id))


def criar(db: Session, nome: str, ator: Usuario) -> AreaUsoOut:
    _exigir_nome_livre(db, nome)
    area = AreaInteresse(nome=nome)
    db.add(area)
    db.flush()
    auditoria.registrar(
        db,
        ator_id=ator.id,
        acao="criar_area",
        entidade="area_interesse",
        entidade_id=area.id,
        campo="nome",
        novo=nome,
    )
    db.commit()
    return AreaUsoOut(id=area.id, nome=area.nome, docentes=0)


def renomear(db: Session, area_id: int, nome: str, ator: Usuario) -> AreaUsoOut:
    area = _obter(db, area_id)
    if area.nome != nome:
        _exigir_nome_livre(db, nome, exceto_id=area.id)
        auditoria.registrar(
            db,
            ator_id=ator.id,
            acao="editar_area",
            entidade="area_interesse",
            entidade_id=area.id,
            campo="nome",
            anterior=area.nome,
            novo=nome,
        )
        area.nome = nome
        db.commit()
    return AreaUsoOut(id=area.id, nome=area.nome, docentes=_uso(db, area.id))


def excluir(db: Session, area_id: int, ator: Usuario) -> None:
    area = _obter(db, area_id)
    docentes = list(
        db.scalars(select(DocenteArea.docente_id).where(DocenteArea.area_id == area.id))
    )
    auditoria.registrar(
        db,
        ator_id=ator.id,
        acao="excluir_area",
        entidade="area_interesse",
        entidade_id=area.id,
        campo="nome",
        anterior=area.nome,
    )
    if docentes:
        auditoria.registrar(
            db,
            ator_id=ator.id,
            acao="excluir_area",
            entidade="area_interesse",
            entidade_id=area.id,
            campo="docentes_desvinculados",
            anterior=", ".join(map(str, sorted(docentes))),
        )
    db.execute(delete(DocenteArea).where(DocenteArea.area_id == area.id))
    db.delete(area)
    db.commit()
