"""Rotas do instrumento de avaliação (TEL20 Instrumento de avaliação · RBN10.01).

Caminhos do diagrama DS-FL06-G: GET /instrumento-avaliacao (passo 2) e PUT /instrumento-avaliacao
(passo 6). Só o perfil Coordenação usa estas rotas; os demais recebem 403 (CA-06, fluxo E2).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import exigir_perfil
from app.models import PERFIL_COORDENADOR, Usuario
from app.schemas.instrumento import InstrumentoConsulta, InstrumentoEntrada, InstrumentoOut
from app.services import instrumento

router = APIRouter(tags=["instrumento de avaliação"])
coordenador = exigir_perfil(PERFIL_COORDENADOR)


@router.get("/instrumento-avaliacao", response_model=InstrumentoConsulta)
def consultar(db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(coordenador)) -> InstrumentoConsulta:
    """Passos 2 a 4: versão vigente, histórico de versões com data e autor e a estrutura do instrumento."""
    return instrumento.consultar_instrumento(db)


@router.put("/instrumento-avaliacao", response_model=InstrumentoOut)
def salvar(
    dados: InstrumentoEntrada, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(coordenador)
) -> InstrumentoOut:
    """Passos 6 a 12. 422 quando os pesos não fecham 7,0 e 3,0; 409 quando outra pessoa salvou antes."""
    return instrumento.salvar_instrumento(db, eu, dados)
