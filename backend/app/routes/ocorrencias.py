"""Rotas das ocorrências, dos ouvintes e da declaração de horas (TEL19 Ocorrências e frequência · RBN09.10).

Caminhos dos diagramas DS-FL09 (GET e POST /defesas/{id}/ocorrencias, POST /defesas/{id}/ouvintes e
/defesas/{id}/ouvintes/lote), DS-FL09-A (PUT /defesas/{id}/ocorrencias/{id}, PUT e DELETE
/defesas/{id}/ouvintes/{id}) e DS-FL09-B (POST /defesas/{id}/declaracoes). GET .../declaracoes/{id}/arquivo
entrega o PDF emitido. Quem pode é conferido no serviço (CA-05 e CA-06).
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import usuario_atual
from app.models import Usuario
from app.schemas.ocorrencia import (
    DeclaracaoEntrada,
    DeclaracaoOut,
    LoteEntrada,
    LoteOut,
    MembroPresencaOut,
    PresencaBancaEntrada,
    MatriculaEntrada,
    OcorrenciaEntrada,
    OcorrenciaOut,
    OuvinteEntrada,
    OuvinteOut,
    PresencaOut,
)
from app.services import ocorrencias

router = APIRouter(tags=["ocorrências e ouvintes da defesa"])


@router.get("/defesas/{defesa_id}/ocorrencias", response_model=PresencaOut)
def consultar(defesa_id: int, db: Session = Depends(get_db, scope="function"),
              eu: Usuario = Depends(usuario_atual)) -> PresencaOut:
    """DS-FL09 msgs 2 a 6: ocorrências e ouvintes. 403 sem vínculo (CA-05, CA-06); 404 sem acesso ao TCC."""
    return ocorrencias.consultar_ocorrencias(db, eu, defesa_id)


@router.post("/defesas/{defesa_id}/ocorrencias", response_model=OcorrenciaOut, status_code=201)
def registrar_ocorrencia(defesa_id: int, dados: OcorrenciaEntrada, db: Session = Depends(get_db, scope="function"),
                         eu: Usuario = Depends(usuario_atual)) -> OcorrenciaOut:
    """DS-FL09 msgs 8 a 11. 403 sem vínculo; 409 defesa cancelada ou ainda não iniciada (E1, E2)."""
    return ocorrencias.registrar_ocorrencia(db, eu, defesa_id, dados.texto)


@router.put("/defesas/{defesa_id}/ocorrencias/{ocorrencia_id}", response_model=OcorrenciaOut)
def corrigir_ocorrencia(defesa_id: int, ocorrencia_id: int, dados: OcorrenciaEntrada,
                        db: Session = Depends(get_db, scope="function"),
                        eu: Usuario = Depends(usuario_atual)) -> OcorrenciaOut:
    """DS-FL09-A msgs 1 a 4: texto corrigido, com "corrigido em" e o anterior no log (RNF03)."""
    return ocorrencias.corrigir_ocorrencia(db, eu, defesa_id, ocorrencia_id, dados.texto)


@router.post("/defesas/{defesa_id}/ouvintes", response_model=OuvinteOut, status_code=201)
def registrar_ouvinte(defesa_id: int, dados: OuvinteEntrada, db: Session = Depends(get_db, scope="function"),
                      eu: Usuario = Depends(usuario_atual)) -> OuvinteOut:
    """DS-FL09 msgs 12 a 15. 422 com o campo para matrícula repetida ou dado inválido (E1, CA-04)."""
    return ocorrencias.registrar_ouvinte(db, eu, defesa_id, dados)


@router.post("/defesas/{defesa_id}/ouvintes/lote", response_model=LoteOut)
def registrar_ouvintes_em_lote(defesa_id: int, dados: LoteEntrada, db: Session = Depends(get_db, scope="function"),
                               eu: Usuario = Depends(usuario_atual)) -> LoteOut:
    """DS-FL09 msgs 16 a 18: {adicionados, linhas com problema[]}."""
    return ocorrencias.registrar_ouvintes_em_lote(db, eu, defesa_id, dados)


@router.put("/defesas/{defesa_id}/ouvintes/{ouvinte_id}", response_model=OuvinteOut)
def corrigir_ouvinte(defesa_id: int, ouvinte_id: int, dados: MatriculaEntrada,
                     db: Session = Depends(get_db, scope="function"),
                     eu: Usuario = Depends(usuario_atual)) -> OuvinteOut:
    """DS-FL09-A msgs 5 a 9: corrige a matrícula. 409 se a declaração já saiu com a matrícula antiga."""
    return ocorrencias.corrigir_ouvinte(db, eu, defesa_id, ouvinte_id, dados.matricula)


@router.delete("/defesas/{defesa_id}/ouvintes/{ouvinte_id}", response_model=OuvinteOut)
def remover_ouvinte(defesa_id: int, ouvinte_id: int, db: Session = Depends(get_db, scope="function"),
                    eu: Usuario = Depends(usuario_atual)) -> OuvinteOut:
    """DS-FL09-A msgs 10 a 12: tira da lista e devolve o removido, para o "Desfazer"."""
    return ocorrencias.remover_ouvinte(db, eu, defesa_id, ouvinte_id)


@router.post("/defesas/{defesa_id}/declaracoes", response_model=DeclaracaoOut)
def emitir_declaracao(defesa_id: int, dados: DeclaracaoEntrada, db: Session = Depends(get_db, scope="function"),
                      eu: Usuario = Depends(usuario_atual)) -> DeclaracaoOut:
    """DS-FL09-B msgs 1 a 5. 409 defesa não realizada (RN15) ou já emitida; 422 matrícula incompleta."""
    return ocorrencias.emitir_declaracao(db, eu, defesa_id, dados.ouvinte_id)


@router.get("/defesas/{defesa_id}/declaracoes/{declaracao_id}/arquivo", response_class=Response,
            responses={200: {"content": {"application/pdf": {}}}})
def baixar_declaracao(defesa_id: int, declaracao_id: int, db: Session = Depends(get_db, scope="function"),
                      eu: Usuario = Depends(usuario_atual)) -> Response:
    """O PDF da declaração, conferido pelo SHA-256 (RNF06)."""
    conteudo = ocorrencias.arquivo_da_declaracao(db, eu, defesa_id, declaracao_id)
    return Response(conteudo, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="declaracao-{declaracao_id}.pdf"'})


@router.put("/defesas/{defesa_id}/banca/{membro_id}/presenca", response_model=MembroPresencaOut)
def registrar_presenca_banca(
    defesa_id: int,
    membro_id: int,
    dados: PresencaBancaEntrada,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
) -> MembroPresencaOut:
    """Marca o membro da banca presente ou ausente na sessão (base do certificado, RBN09.17). 403 sem vínculo;
    404 membro de outra defesa ou suplente não convocado; 409 defesa cancelada ou que ainda não começou."""
    return ocorrencias.registrar_presenca_banca(db, eu, defesa_id, membro_id, dados)
