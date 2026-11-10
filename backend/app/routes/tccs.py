"""Rotas do cadastro de TCC (TEL04, TEL05) e da orientação (TEL08).

Os caminhos são os dos diagramas de sequência: DS-FL01-A (GET /tccs/formulario),
DS-FL01-B (POST/PUT /tccs), DS-FL01 (POST /tccs/{id}/submissao), DS-FL02-B (GET /tccs/{id}),
DS-FL03-B (POST /tccs/{id}/orientacoes), DS-FL03-A (GET /orientacoes) e DS-FL03 (resposta).
DS-FL03-D (RBN01.13): a coordenação e o orientador também usam POST /tccs/{id}/orientacoes para informar o
coorientador (interno ou externo) e DELETE /tccs/{id}/orientacoes/{orientacao_id} para encerrar o vínculo.
"""

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import exigir_perfil, usuario_atual
from app.models import PERFIL_ALUNO, PERFIL_ORIENTADOR, PERFIL_PROFESSOR, Usuario
from app.schemas.tcc import (
    EncerrarOrientacao,
    FormularioOut,
    IndicarOrientador,
    RespostaOrientacao,
    SituacaoOut,
    SolicitacaoOut,
    SubmissaoOut,
    TccOut,
    TccSalvar,
    VinculoOut,
)
from app.services import tccs

router = APIRouter(tags=["cadastro de TCC"])
aluno = exigir_perfil(PERFIL_ALUNO)
docente_orientador = exigir_perfil(PERFIL_ORIENTADOR, PERFIL_PROFESSOR)


@router.get("/tccs/formulario", response_model=FormularioOut)
def abrir_formulario(db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(aluno)) -> FormularioOut:
    """403 quando o aluno não está matriculado numa turma (RN05)."""
    return tccs.formulario(db, eu)


@router.get("/tccs", response_model=list[TccOut])
def listar(db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)) -> list[TccOut]:
    return [tccs.para_saida(t) for t in tccs.listar_para(db, eu)]


@router.post("/tccs", response_model=TccOut, status_code=201)
def criar_rascunho(
    dados: TccSalvar, tarefas: BackgroundTasks, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(aluno)
) -> TccOut:
    """201 RASCUNHO sem protocolo; 403 sem matrícula; 409 já há cadastro no período (RN04); 422 orientador."""
    return tccs.para_saida(tccs.criar(db, tarefas, eu, dados))


@router.get("/tccs/{tcc_id}", response_model=TccOut)
def obter(tcc_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)) -> TccOut:
    return tccs.para_saida(tccs.obter_para(db, eu, tcc_id))


@router.put("/tccs/{tcc_id}", response_model=TccOut)
def atualizar_rascunho(
    tcc_id: int,
    dados: TccSalvar,
    tarefas: BackgroundTasks,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(aluno),
) -> TccOut:
    """409 quando a situação não é RASCUNHO nem DEVOLVIDO; mantém protocolo e parecer."""
    return tccs.para_saida(tccs.atualizar(db, tarefas, eu, tcc_id, dados))


@router.post("/tccs/{tcc_id}/submissao", response_model=SubmissaoOut)
def submeter(
    tcc_id: int, tarefas: BackgroundTasks, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(aluno)
) -> SubmissaoOut:
    """200 com protocolo; repetir devolve o mesmo protocolo; 422 com campos_pendentes."""
    return tccs.submeter(db, tarefas, eu, tcc_id)


@router.post("/tccs/{tcc_id}/orientacoes", response_model=VinculoOut, status_code=201)
def indicar_orientador(
    tcc_id: int,
    dados: IndicarOrientador,
    tarefas: BackgroundTasks,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
) -> VinculoOut:
    """O aluno indica um docente (DS-FL03-B); a coordenação e o orientador informam o coorientador, interno ou
    externo (DS-FL03-D, RBN01.13). Outro perfil recebe 403."""
    return tccs._vinculo_out(tccs.indicar_por_perfil(db, tarefas, eu, tcc_id, dados))


@router.delete("/tccs/{tcc_id}/orientacoes/{orientacao_id}", response_model=VinculoOut)
def encerrar_coorientacao(
    tcc_id: int,
    orientacao_id: int,
    dados: EncerrarOrientacao,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
) -> VinculoOut:
    """DS-FL03-D mensagens 14 a 17: encerra o vínculo do coorientador e revoga o acesso do externo (RBN01.13 CA-04)."""
    return tccs._vinculo_out(tccs.encerrar_coorientacao(db, eu, tcc_id, orientacao_id, dados))


@router.get("/orientacoes", response_model=list[SolicitacaoOut])
def listar_solicitacoes(
    status: str | None = None, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(docente_orientador)
) -> list[SolicitacaoOut]:
    return [tccs.solicitacao_out(o) for o in tccs.listar_solicitacoes(db, eu, status)]


@router.get("/orientacoes/{orientacao_id}", response_model=SolicitacaoOut)
def obter_solicitacao(
    orientacao_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(docente_orientador)
) -> SolicitacaoOut:
    return tccs.solicitacao_out(tccs.obter_solicitacao(db, eu, orientacao_id))


@router.post("/orientacoes/{orientacao_id}/resposta", response_model=SituacaoOut)
def responder(
    orientacao_id: int,
    dados: RespostaOrientacao,
    tarefas: BackgroundTasks,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(docente_orientador),
) -> SituacaoOut:
    """409 quando já foi respondida; recusa exige motivo."""
    return SituacaoOut(status=tccs.responder(db, tarefas, eu, orientacao_id, dados).status)
