"""Rotas da publicação do artigo (TEL15, aba Artigo · RBN12.01 a RBN12.03 · DS-FL08 e DS-FL08-B).

Quem pode é conferido no serviço.
"""

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual
from app.models import Usuario
from app.schemas.publicacao import PublicacaoOut, RegistroEntrada
from app.services import publicacao

router = APIRouter(tags=["publicação do artigo"])


@router.get("/tccs/{tcc_id}/publicacao", response_model=PublicacaoOut)
def consultar(tcc_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)):
    """Situação atual e histórico. 403 sem vínculo; 409 se o TCC não é artigo."""
    return publicacao.consultar(db, eu, tcc_id)


@router.get("/tccs/{tcc_id}/publicacoes/historico", response_model=PublicacaoOut)
def historico(tcc_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)):
    """DS-FL08-B: o histórico, do mais recente para o mais antigo."""
    return publicacao.consultar(db, eu, tcc_id)


@router.post("/tccs/{tcc_id}/publicacao", response_model=PublicacaoOut, status_code=201)
def registrar(
    tcc_id: int,
    dados: RegistroEntrada,
    tarefas: BackgroundTasks,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
):
    """Novo registro da situação editorial. 403 sem vínculo ou sem ser autor nem orientador; 409 não é artigo;
    422 {campos} com campo inválido."""
    return publicacao.registrar(db, eu, tcc_id, dados, tarefas)
