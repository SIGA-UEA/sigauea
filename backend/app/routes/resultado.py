"""Rotas do resultado da defesa (TEL12 Avaliações e resultado · RBN09.11 e RBN09.12).

GET /defesas/{id}/resultado é o caminho do DS-FL06 (mensagem 3): consolidação da nota final (DS-FL06-B) ou o
resultado já confirmado. POST /defesas/{id}/resultado confirma o resultado (DS-FL06, mensagem 7) e
POST /defesas/{id}/resultado/retificacao o retifica (DS-FL06-D). Quem pode é conferido no serviço.
"""

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual
from app.models import Usuario
from app.schemas.resultado import ConfirmacaoEntrada, ResultadoConsulta, RetificacaoEntrada
from app.services import resultado

router = APIRouter(tags=["resultado da defesa"])


@router.get("/defesas/{defesa_id}/resultado", response_model=ResultadoConsulta)
def consultar(
    defesa_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)
) -> ResultadoConsulta:
    """{pendentes[]} enquanto falta avaliação; {notas, média, regra de exceção, nota final} com todas enviadas;
    {resultado} depois da confirmação. 403 para quem não é o orientador do TCC; 404 sem acesso ao TCC; 409 defesa
    cancelada."""
    return resultado.consultar_resultado(db, eu, defesa_id)


@router.post("/defesas/{defesa_id}/resultado", response_model=ResultadoConsulta)
def confirmar(
    defesa_id: int,
    dados: ConfirmacaoEntrada,
    tarefas: BackgroundTasks,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
) -> ResultadoConsulta:
    """Confirma o resultado e o parecer. 403 não é o orientador; 409 já confirmado ou avaliação pendente
    ({pendentes[]}); 422 parecer em branco."""
    return resultado.confirmar_resultado(db, eu, defesa_id, dados, tarefas)


@router.post("/defesas/{defesa_id}/resultado/retificacao", response_model=ResultadoConsulta)
def retificar(
    defesa_id: int,
    dados: RetificacaoEntrada,
    tarefas: BackgroundTasks,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
) -> ResultadoConsulta:
    """Retifica o resultado confirmado com o motivo. 403 não é o orientador; 409 sem resultado confirmado;
    422 motivo em branco ou resultado igual ao vigente."""
    return resultado.retificar_resultado(db, eu, defesa_id, dados, tarefas)
