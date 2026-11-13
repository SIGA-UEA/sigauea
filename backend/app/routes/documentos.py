"""Rotas dos documentos da defesa (TEL13 Documentos da defesa · RBN09.14 a RBN09.17).

DS-FL06-C: GET /defesas/{id}/documentos, POST /defesas/{id}/documentos/ata e /documentos/folha.
DS-FL06-E: GET /documentos/{id}/arquivo. DS-FL06-F: POST /defesas/{id}/documentos/certificados.
POST /documentos/{id}/reenvio reenvia o certificado sem gerar outro (CA-05 do RBN09.17).
Quem pode é conferido no serviço.
"""

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual
from app.models import Usuario
from app.schemas.documento import CertificadosEntrada, DocumentosOut
from app.services import documentos_defesa

router = APIRouter(tags=["documentos da defesa"])


@router.get("/defesas/{defesa_id}/documentos", response_model=DocumentosOut)
def listar(defesa_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)):
    """Ata, folha e certificados, com as versões e o que falta. 403 sem vínculo com o TCC."""
    return documentos_defesa.listar_documentos(db, eu, defesa_id)


@router.post("/defesas/{defesa_id}/documentos/ata", response_model=DocumentosOut)
def gerar_ata(defesa_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)):
    """Gera a ata (nova versão vigente). 403 não é coordenação nem orientador; 409 resultado não confirmado ou
    dados faltando ({faltas[]}); 500 falha ao gerar, sem mudar nada."""
    return documentos_defesa.gerar_ata(db, eu, defesa_id)


@router.post("/defesas/{defesa_id}/documentos/folha", response_model=DocumentosOut)
def gerar_folha(defesa_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)):
    """Gera a Folha de Aprovação. 409 quando não se aplica, reprovado, anuência pendente ou dados faltando."""
    return documentos_defesa.gerar_folha(db, eu, defesa_id)


@router.post("/defesas/{defesa_id}/documentos/certificados", response_model=DocumentosOut)
def emitir_certificados(
    defesa_id: int,
    dados: CertificadosEntrada,
    tarefas: BackgroundTasks,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
):
    """Emite e envia por e-mail os certificados dos membros escolhidos. 409 defesa não realizada ou cancelada, ou
    membro ausente; 403 sem permissão."""
    return documentos_defesa.emitir_certificados(db, eu, defesa_id, dados, tarefas)


@router.post("/documentos/{documento_id}/reenvio", response_model=DocumentosOut)
def reenviar(
    documento_id: int,
    tarefas: BackgroundTasks,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
):
    """Reenvia o e-mail do certificado, sem gerar outro."""
    return documentos_defesa.reenviar_certificado(db, eu, documento_id, tarefas)


@router.get("/documentos/{documento_id}/arquivo", response_class=Response,
            responses={200: {"content": {"application/pdf": {}}}})
def arquivo(documento_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)):
    """O PDF conferido pelo SHA-256. 403 sem vínculo (também pela URL direta); 409 arquivo adulterado."""
    documento, conteudo = documentos_defesa.baixar(db, eu, documento_id)
    nome = f"{documento.tipo.lower()}-{documento.id}-v{documento.versao}.pdf"
    return Response(content=conteudo, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})
