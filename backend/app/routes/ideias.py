"""Rotas das ideias de TCC (TEL03 Ideias de TCC · RBN02.01 e RBN02.02 · DS-FL12 e DS-FL12-A).

Quem pode é conferido no serviço: o aluno cadastra e vê as próprias propostas; professores da disciplina e
orientadores veem e comentam as que foram direcionadas a eles (RN07, RN25).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual
from app.models import Usuario
from app.schemas.ideia import ComentarioEntrada, FormularioIdeia, PropostaDetalhe, PropostaEntrada, PropostaResumo
from app.services import ideias

router = APIRouter(tags=["ideias de TCC"])


@router.get("/ideias/formulario", response_model=FormularioIdeia)
def formulario(db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)):
    """Áreas de interesse e professores que podem receber a proposta. 403 para quem não é aluno."""
    return ideias.formulario(db, eu)


@router.post("/ideias", response_model=PropostaDetalhe, status_code=201)
def criar(
    dados: PropostaEntrada, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)
):
    """Cadastra a proposta (sem protocolo). 400 {campos} com campo ausente; 403 para quem não é aluno."""
    return ideias.criar(db, eu, dados)


@router.get("/ideias", response_model=list[PropostaResumo])
def listar(db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)):
    """Propostas do aluno ou as direcionadas ao professor, da mais nova para a mais antiga."""
    return ideias.listar(db, eu)


@router.get("/ideias/{proposta_id}", response_model=PropostaDetalhe)
def consultar(
    proposta_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)
):
    """Proposta com a discussão. 403 para quem não é o autor nem destinatário; 404 inexistente."""
    return ideias.consultar(db, eu, proposta_id)


@router.post("/ideias/{proposta_id}/comentarios", response_model=PropostaDetalhe, status_code=201)
def comentar(
    proposta_id: int,
    dados: ComentarioEntrada,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
):
    """Registra o comentário do professor destinatário. 400 {campos} texto vazio; 403 não destinatário."""
    return ideias.comentar(db, eu, proposta_id, dados)
