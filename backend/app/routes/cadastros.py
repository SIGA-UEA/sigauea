"""Rotas da análise do cadastro de TCC pela coordenação (TEL07).

Os caminhos são os dos diagramas de sequência: DS-FL02-A (GET /cadastros, GET /cadastros/{id},
GET /cadastros/{id}/documento) e DS-FL02 (POST /cadastros/{id}/decisao). Só o perfil
Coordenação usa estas rotas; os demais recebem 403 e nenhum dado (RN06, RN07).
"""

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import exigir_perfil
from app.models import PERFIL_COORDENADOR, Usuario
from app.schemas.tcc import CadastroOut, CadastroResumo, DecisaoEntrada, DecisaoOut
from app.services import analise

router = APIRouter(tags=["análise do cadastro de TCC"])
coordenador = exigir_perfil(PERFIL_COORDENADOR)


@router.get("/cadastros", response_model=list[CadastroResumo])
def listar(
    situacao: str | None = None,
    curso: int | None = None,
    periodo: str | None = None,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(coordenador),
) -> list[CadastroResumo]:
    """situacao: uma ou mais separadas por vírgula (ex.: APROVADO,DEVOLVIDO,REPROVADO); periodo: AAAA/N."""
    return analise.listar(db, eu, situacao, curso, periodo)


@router.get("/cadastros/{tcc_id}", response_model=CadastroOut)
def obter(tcc_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(coordenador)) -> CadastroOut:
    """404 quando o cadastro não existe, não foi enviado ou é de curso de outro núcleo (RN07)."""
    return analise.obter(db, eu, tcc_id)


@router.get("/cadastros/{tcc_id}/documento")
def abrir_documento(tcc_id: int, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(coordenador)) -> None:
    """O PDF preliminar do cadastro; 404 enquanto o aluno não enviar o PDF."""
    analise.documento(db, eu, tcc_id)


@router.post("/cadastros/{tcc_id}/decisao", response_model=DecisaoOut)
def decidir(
    tcc_id: int,
    dados: DecisaoEntrada,
    tarefas: BackgroundTasks,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(coordenador),
) -> DecisaoOut:
    """409 quando o cadastro já não está em análise (outra pessoa decidiu); 422 devolver ou reprovar sem parecer."""
    return analise.decidir(db, tarefas, eu, tcc_id, dados)
