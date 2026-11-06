"""Agenda de apresentações (TEL17 · RAN14). Qualquer usuário autenticado consulta (DS-FL05-A).

Divulgação na agenda (TEL18, DS-FL05): GET /defesas/{id}/divulgacao, POST .../publicacao e POST .../retirada.
"""

from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual
from app.models import Usuario
from app.schemas.agenda import ApresentacaoOut, DivulgacaoOut
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


@router.get("/defesas/{defesa_id}/divulgacao", response_model=DivulgacaoOut)
def consultar_divulgacao(
    defesa_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)
) -> DivulgacaoOut:
    """DS-FL05 mensagem 3: condições, prévia e situação. 404 sem vínculo com o TCC (RN07)."""
    return agenda.divulgacao(db, eu, defesa_id)


@router.post("/defesas/{defesa_id}/publicacao", response_model=DivulgacaoOut)
def publicar_na_agenda(
    defesa_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)
) -> DivulgacaoOut:
    """DS-FL05 mensagem 8: 422 com pendencias (RN09), 403 sem permissão (RN14), 409 se cancelada."""
    return agenda.publicar(db, eu, defesa_id)


@router.post("/defesas/{defesa_id}/retirada", response_model=DivulgacaoOut)
def retirar_da_agenda(
    defesa_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)
) -> DivulgacaoOut:
    """DS-FL05 mensagem 14: tira da agenda sem cancelar a defesa."""
    return agenda.retirar(db, eu, defesa_id)
