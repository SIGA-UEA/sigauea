"""Rotas do acompanhamento do TCC (TEL06): situação, histórico cronológico e tarefas (RAN05)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import exigir_perfil, usuario_atual
from app.models import PERFIL_ORIENTADOR, PERFIL_PROFESSOR, Usuario
from app.schemas.tcc import EventoOut, SituacaoAlterar, TarefaCriar, TarefaOut, TccOut
from app.services import acompanhamento, tccs

router = APIRouter(tags=["acompanhamento do TCC"])
docente = exigir_perfil(PERFIL_ORIENTADOR, PERFIL_PROFESSOR)


@router.put("/tccs/{tcc_id}/situacao", response_model=TccOut)
def atualizar_situacao(
    tcc_id: int, dados: SituacaoAlterar, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(docente)
) -> TccOut:
    """403 fora do orientador do TCC; 400 sem motivo; 409 em transição não permitida."""
    return tccs.para_saida(acompanhamento.alterar_situacao(db, eu, tcc_id, dados))


@router.get("/tccs/{tcc_id}/historico", response_model=list[EventoOut])
def historico(
    tcc_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)
) -> list[EventoOut]:
    """404 para quem não vê o TCC; o histórico não tem rota de alteração nem de exclusão."""
    return acompanhamento.historico(db, eu, tcc_id)


@router.get("/tccs/{tcc_id}/tarefas", response_model=list[TarefaOut])
def listar_tarefas(
    tcc_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)
) -> list[TarefaOut]:
    return [acompanhamento.tarefa_out(t) for t in acompanhamento.listar_tarefas(db, eu, tcc_id)]


@router.post("/tccs/{tcc_id}/tarefas", response_model=TarefaOut, status_code=201)
def criar_tarefa(
    tcc_id: int, dados: TarefaCriar, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(docente)
) -> TarefaOut:
    """403 fora do orientador e do professor da turma; 400 sem descrição ou com prazo passado; 409 TCC não aprovado."""
    return acompanhamento.tarefa_out(acompanhamento.criar_tarefa(db, eu, tcc_id, dados))
