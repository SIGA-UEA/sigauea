"""Rotas da aba Correções (TEL14 · RBN11.01 a RBN11.04 · DS-FL07, DS-FL07-A a DS-FL07-D).

Quem pode cada ação é conferido no serviço: registrar correção, só membro da banca que avalia; anuência, marcar
atendida e enviar a versão final, só o aluno autor; decidir correção, decidir atraso e mudar o prazo, só o
professor responsável pela turma (RN24). Sem vínculo com o TCC, 403.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, Response, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual
from app.models import Usuario
from app.schemas.correcoes import AtrasoEntrada, CorrecaoEntrada, CorrecoesOut, DecisaoCorrecao, PrazoEntrada
from app.services import correcoes

router = APIRouter(tags=["correções e conclusão do TCC"])


@router.get("/tccs/{tcc_id}/correcoes", response_model=CorrecoesOut)
def consultar(tcc_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)):
    """Prazo, correções, versão final, o que falta para concluir e o que quem consulta pode fazer. 403 sem
    vínculo; 404 TCC inexistente."""
    return correcoes.consultar(db, eu, tcc_id)


@router.post("/tccs/{tcc_id}/correcoes", response_model=CorrecoesOut, status_code=201)
def registrar(
    tcc_id: int,
    dados: CorrecaoEntrada,
    tarefas: BackgroundTasks,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
):
    """Correção exigida por um membro da banca (DS-FL07-A). 403 não avaliou a defesa; 409 resultado sem
    correções ou TCC concluído; 422 descrição com menos de 10 caracteres."""
    return correcoes.registrar_correcao(db, tarefas, eu, tcc_id, dados.descricao)


@router.post("/tccs/{tcc_id}/correcoes/anuencia", response_model=CorrecoesOut)
def anuencia(tcc_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)):
    """O aluno dá anuência às correções exigidas (libera a Folha de Aprovação, RBN09.15). 403 não é o aluno;
    409 resultado sem correções ou anuência já dada."""
    return correcoes.registrar_anuencia(db, eu, tcc_id)


@router.post("/tccs/{tcc_id}/correcoes/prazo", response_model=CorrecoesOut)
def prazo(
    tcc_id: int, dados: PrazoEntrada, db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
):
    """Novo prazo da versão final (DS-FL07-D, A1). 403 não é o professor responsável; 409 sem resultado
    confirmado; 422 motivo em branco."""
    return correcoes.alterar_prazo(db, eu, tcc_id, dados.prazo, dados.motivo)


@router.post("/tccs/{tcc_id}/correcoes/atraso", response_model=CorrecoesOut)
def atraso(
    tcc_id: int,
    dados: AtrasoEntrada,
    tarefas: BackgroundTasks,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
):
    """Aceita ou recusa a entrega com atraso (DS-FL07-D). 403 não é o professor responsável; 409 sem atraso a
    decidir."""
    return correcoes.decidir_atraso(db, tarefas, eu, tcc_id, dados.aceita)


@router.post("/tccs/{tcc_id}/correcoes/versao-final", response_model=CorrecoesOut, status_code=201)
def enviar_versao_final(
    tcc_id: int,
    arquivo: UploadFile,
    tarefas: BackgroundTasks,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
):
    """PDF da versão final (multipart, campo "arquivo"). 403 não é o aluno; 409 sem resultado confirmado,
    reprovado ou TCC concluído; 422 vazio, acima de 20 MB ou não é PDF."""
    return correcoes.enviar_versao_final(db, tarefas, eu, tcc_id, arquivo)


@router.get("/tccs/{tcc_id}/correcoes/versao-final", response_class=Response,
            responses={200: {"content": {"application/pdf": {}}}})
def baixar_versao_final(
    tcc_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)
):
    """A versão final vigente, conferida pelo SHA-256. 403 sem vínculo; 404 não enviada; 409 arquivo adulterado."""
    nome, conteudo = correcoes.arquivo_versao_final(db, eu, tcc_id)
    return Response(content=conteudo, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})


@router.post("/correcoes/{correcao_id}/atendida", response_model=CorrecoesOut)
def marcar_atendida(
    correcao_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)
):
    """O aluno marca a correção pendente ou devolvida como atendida. 403 não é o aluno; 409 situação errada."""
    return correcoes.marcar_atendida(db, eu, correcao_id)


@router.post("/correcoes/{correcao_id}/decisao", response_model=CorrecoesOut)
def decidir(
    correcao_id: int,
    dados: DecisaoCorrecao,
    tarefas: BackgroundTasks,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
):
    """Aprova ou devolve a correção atendida (DS-FL07-B). 403 não é o professor responsável; 409 não está
    atendida; 422 devolução sem justificativa."""
    return correcoes.decidir_correcao(db, tarefas, eu, correcao_id, dados.decisao, dados.justificativa)
