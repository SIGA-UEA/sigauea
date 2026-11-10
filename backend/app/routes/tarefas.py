"""Rotinas agendadas, chamadas por um agendador externo e não por uma pessoa.

POST /tarefas/lembretes-defesa (SCRUM-64, RBN09.06) e POST /tarefas/expirar-acessos (SCRUM-32, RBN01.12 CA-03):
o GitHub Actions chama cada uma uma vez por dia (.github/workflows/lembretes-defesa.yml e expirar-acessos.yml).
Não usam sessão: a chamada traz o cabeçalho X-Chave-Tarefas com o valor de TAREFAS_CHAVE, definido no servidor
e nos segredos do GitHub. Sem TAREFAS_CHAVE no servidor, as rotas ficam desligadas (503).
"""

import hmac

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.erros import ErroAPI
from app.services import acessos, lembretes

router = APIRouter(prefix="/tarefas", tags=["tarefas agendadas"])


def chave_tarefas(x_chave_tarefas: str | None = Header(default=None)) -> None:
    if not config.TAREFAS_CHAVE:
        raise ErroAPI(503, "Rotinas agendadas desligadas: defina TAREFAS_CHAVE no servidor.")
    if not x_chave_tarefas or not hmac.compare_digest(x_chave_tarefas, config.TAREFAS_CHAVE):
        raise ErroAPI(401, "Chave das rotinas agendadas inválida.")


@router.post("/lembretes-defesa", dependencies=[Depends(chave_tarefas)])
def lembretes_defesa(db: Session = Depends(get_db, scope="function")) -> dict:
    """DS-FL05-D: lembrete das defesas de amanhã. Pode ser chamada de novo sem duplicar (CA-04)."""
    return lembretes.lembrar_defesas_de_amanha(db)


@router.post("/expirar-acessos", dependencies=[Depends(chave_tarefas)])
def expirar_acessos(db: Session = Depends(get_db, scope="function")) -> dict:
    """RBN01.12 CA-03: expira os acessos vencidos e desliga as contas externas sem acesso. Pode ser chamada de novo
    sem repetir nada."""
    return acessos.expirar_vencidos(db)
