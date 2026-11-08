"""Rotas da avaliação da defesa (TEL12 Avaliação · RBN10.02 a RBN10.05).

Caminhos do diagrama DS-FL06-A: GET /defesas/{id}/avaliacao (passo 3), PUT /defesas/{id}/avaliacao
(passo 12) e POST /defesas/{id}/avaliacao/envio (passo 17). Basta estar logado; quem avalia é
conferido no serviço (403 para quem não avalia esta defesa, RN20).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual
from app.models import Usuario
from app.schemas.avaliacao import AvaliacaoConsulta, AvaliacaoEntrada, MinhaAvaliacaoOut
from app.services import avaliacao

router = APIRouter(tags=["avaliação da defesa"])


@router.get("/defesas/{defesa_id}/avaliacao", response_model=AvaliacaoConsulta)
def consultar(
    defesa_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)
) -> AvaliacaoConsulta:
    """Passos 3 a 7: {instrumento, minha avaliação, envios}. 403 quem não avalia; 409 defesa cancelada."""
    return avaliacao.consultar(db, eu, defesa_id)


@router.put("/defesas/{defesa_id}/avaliacao", response_model=MinhaAvaliacaoOut)
def salvar_rascunho(
    defesa_id: int,
    dados: AvaliacaoEntrada,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
) -> MinhaAvaliacaoOut:
    """Passos 12 a 14: salva o rascunho. 422 nota fora da faixa; 409 já enviada ou instrumento mudou."""
    return avaliacao.salvar_rascunho(db, eu, defesa_id, dados)


@router.post("/defesas/{defesa_id}/avaliacao/envio", response_model=MinhaAvaliacaoOut)
def enviar(
    defesa_id: int,
    dados: AvaliacaoEntrada,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
) -> MinhaAvaliacaoOut:
    """Passos 17 a 19: envia. 422 critério faltando ou fora da faixa e parecer curto; 409 já enviada ou
    defesa ainda não realizada."""
    return avaliacao.enviar(db, eu, defesa_id, dados)
