"""Agenda de apresentações (TEL17 · RAN14). Qualquer usuário autenticado consulta (DS-FL05-A) e filtra por curso e
período: próximas, próximos 7 dias, todas ou datas escolhidas (RBN14.02). GET /agenda/pdf exporta a agenda filtrada
(RBN14.03), só para a coordenação, os professores da disciplina e os orientadores.

Divulgação na agenda (TEL18, DS-FL05): GET /defesas/{id}/divulgacao, POST .../publicacao e POST .../retirada.
"""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual
from app.models import Usuario
from app.schemas.agenda import ApresentacaoOut, DivulgacaoOut
from app.services import agenda

router = APIRouter(tags=["agenda"])


@router.get("/agenda", response_model=list[ApresentacaoOut])
def consultar_agenda(
    periodo: Literal["proximos", "semana", "todas"] = "proximos",
    curso: int | None = Query(default=None),
    de: date | None = Query(default=None),
    ate: date | None = Query(default=None),
    db: Session = Depends(get_db, scope="function"),
    _: Usuario = Depends(usuario_atual),
) -> list[ApresentacaoOut]:
    """DS-FL05-A passos 1 a 4 (GET /agenda?periodo=proximos): defesas vigentes, sem as canceladas. RBN14.02: curso e
    período de datas (de, ate); 400 {campos: {ate}} se a data final vier antes da inicial."""
    return agenda.listar(db, periodo, curso=curso, de=de, ate=ate)


@router.get("/agenda/pdf", response_class=Response,
            responses={200: {"content": {"application/pdf": {}}, "description": "Agenda filtrada em PDF"}})
def exportar_agenda(
    periodo: Literal["proximos", "semana", "todas"] = "proximos",
    curso: int | None = Query(default=None),
    de: date | None = Query(default=None),
    ate: date | None = Query(default=None),
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
) -> Response:
    """RBN14.03: os mesmos filtros da tela. 403 para quem não é coordenação, professor da disciplina ou orientador."""
    conteudo, nome = agenda.exportar_pdf(db, eu, periodo, curso=curso, de=de, ate=ate)
    return Response(content=conteudo, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})


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
