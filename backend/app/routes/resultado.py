"""Rota do resultado da defesa (TEL12 Avaliações e resultado, seção "Consolidar resultado" · RBN09.11).

GET /defesas/{id}/resultado é o caminho do DS-FL06 (mensagem 3), que chama a consolidação da nota final
(DS-FL06-B). O POST da confirmação (RBN09.12) entra no SCRUM-70. Quem pode é conferido no serviço.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual
from app.models import Usuario
from app.schemas.resultado import ResultadoConsulta
from app.services import resultado

router = APIRouter(tags=["resultado da defesa"])


@router.get("/defesas/{defesa_id}/resultado", response_model=ResultadoConsulta)
def consultar(
    defesa_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)
) -> ResultadoConsulta:
    """{pendentes[]} enquanto falta avaliação; {notas, média, regra de exceção, nota final} com todas enviadas.
    403 para quem não é o orientador do TCC; 404 sem acesso ao TCC; 409 defesa cancelada."""
    return resultado.consultar_resultado(db, eu, defesa_id)
