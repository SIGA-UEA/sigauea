"""Agenda de apresentações (TEL17 · RAN14). Qualquer usuário autenticado consulta (DS-FL05-A)."""

from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual
from app.models import Usuario
from app.schemas.agenda import ApresentacaoOut
from app.services import agenda

router = APIRouter(tags=["agenda"])


@router.get("/agenda", response_model=list[ApresentacaoOut])
def consultar_agenda(
    periodo: Literal["proximos", "todas"] = "proximos",
    db: Session = Depends(get_db, scope="function"),
    _: Usuario = Depends(usuario_atual),
) -> list[ApresentacaoOut]:
    """DS-FL05-A passos 1 a 4 (GET /agenda?periodo=proximos): defesas vigentes, sem as canceladas."""
    return agenda.listar(db, periodo)
