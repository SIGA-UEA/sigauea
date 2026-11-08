"""Rotas da banca e do agendamento da defesa (TEL10 Banca, TEL11 Agendamento · RAN09).

Caminhos dos diagramas DS-FL04-A (GET /tccs/{id}/banca) e DS-FL04 (POST /tccs/{id}/defesa).
Com a banca montada na tela (opção 2), POST /tccs/{id}/banca/validar confere uma vaga sem gravar
e PUT /defesas/{id}/banca/{membro} troca um membro depois da confirmação (CA-06 do RBN09.01).
GET /defesas/conflitos confere a agenda antes de confirmar (RBN09.04, DS-FL04 mensagem 11).
Quem pode compor e agendar é conferido no serviço (RN14).
"""

from datetime import date, time
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual
from app.models import Usuario
from app.schemas.defesa import (
    BancaOut,
    ConflitosOut,
    DefesaCriar,
    DefesaOut,
    MembroOut,
    PessoaBanca,
    ValidarMembro,
)
from app.services import defesas

router = APIRouter(tags=["defesa e banca"])


@router.get("/tccs/{tcc_id}/banca", response_model=BancaOut)
def consultar_banca(
    tcc_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)
) -> BancaOut:
    """DS-FL04-A passos 3 a 5: vagas, membros e se quem pede pode editar (404 sem vínculo, RN07)."""
    return defesas.consultar(db, eu, tcc_id)


@router.post("/tccs/{tcc_id}/banca/validar", response_model=MembroOut)
def validar_membro(
    tcc_id: int,
    dados: ValidarMembro,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
) -> MembroOut:
    """Confere uma vaga sem gravar: 403 (RN14), 409 etapa não liberada, 422 pessoa repetida ou inválida."""
    return defesas.validar_membro(db, eu, tcc_id, dados)


@router.get("/defesas/conflitos", response_model=ConflitosOut)
def verificar_conflitos(
    tcc_id: int,
    data: date,
    inicio: time,
    fim: time,
    local_id: int | None = None,
    pessoa: Annotated[list[int], Query()] = [],
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
) -> ConflitosOut:
    """RBN09.04 · DS-FL04 mensagem 11: outras defesas no mesmo horário com o mesmo local ou alguém
    desta banca (pessoa=id, repetido). Sem pessoa, vale a banca da defesa vigente (remarcação)."""
    return defesas.verificar_conflitos(db, eu, tcc_id, data, inicio, fim, local_id, pessoa)


@router.post("/tccs/{tcc_id}/defesa", response_model=DefesaOut, status_code=201)
def agendar_defesa(
    tcc_id: int,
    dados: DefesaCriar,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
) -> DefesaOut:
    """DS-FL04 passo 16: grava a defesa CONFIRMADA com a banca. 422 com pendencias (RN12)."""
    return defesas.defesa_out(db, defesas.agendar(db, eu, tcc_id, dados))


@router.put("/defesas/{defesa_id}/banca/{membro_id}", response_model=DefesaOut)
def trocar_membro(
    defesa_id: int,
    membro_id: int,
    dados: PessoaBanca,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
) -> DefesaOut:
    """CA-06: troca a pessoa de uma vaga antes da defesa e revalida a composição (RN12)."""
    return defesas.defesa_out(db, defesas.trocar_membro(db, eu, defesa_id, membro_id, dados))
