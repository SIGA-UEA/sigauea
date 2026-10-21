"""Meu perfil (RBN01.09 e RBN01.10): qualquer pessoa logada edita os próprios dados.

Fica registrado antes do router de usuários: senão /usuarios/me cairia em /usuarios/{usuario_id}.
"""

from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.deps import token_da_requisicao, usuario_atual
from app.models import Usuario
from app.schemas.auth import Mensagem
from app.schemas.usuario import MeuPerfilAtualizar, TrocarSenhaEntrada, UsuarioOut
from app.services import perfil
from app.services.usuarios import para_saida

router = APIRouter(prefix="/usuarios", tags=["meu perfil"])


async def ler_imagem(foto: UploadFile) -> bytes:
    # Lê um byte além do limite: basta para saber se passou, sem carregar arquivos enormes.
    return await foto.read(config.FOTO_MAX_BYTES + 1)


@router.get("/me", response_model=UsuarioOut)
def meu_perfil(eu: Usuario = Depends(usuario_atual)) -> UsuarioOut:
    return para_saida(eu)


@router.put("/me", response_model=UsuarioOut)
def atualizar_meu_perfil(
    dados: MeuPerfilAtualizar, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)
) -> UsuarioOut:
    return para_saida(perfil.atualizar(db, eu, dados))


@router.post("/me/senha", response_model=Mensagem)
def trocar_senha(
    dados: TrocarSenhaEntrada,
    request: Request,
    db: Session = Depends(get_db, scope="function"),
    eu: Usuario = Depends(usuario_atual),
) -> Mensagem:
    perfil.trocar_senha(db, eu, dados, token_da_requisicao(request))
    return Mensagem(detail="Senha alterada. As outras sessões abertas foram encerradas.")


@router.put("/me/foto", response_model=UsuarioOut)
async def trocar_minha_foto(
    foto: UploadFile, db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)
) -> UsuarioOut:
    return para_saida(perfil.salvar_foto(db, eu, await ler_imagem(foto), eu))


@router.delete("/me/foto", response_model=UsuarioOut)
def remover_minha_foto(
    db: Session = Depends(get_db, scope="function"), eu: Usuario = Depends(usuario_atual)
) -> UsuarioOut:
    return para_saida(perfil.remover_foto(db, eu, eu))


@router.get("/{usuario_id}/foto", dependencies=[Depends(usuario_atual)])
def ver_foto(usuario_id: int, db: Session = Depends(get_db, scope="function")) -> Response:
    foto = perfil.obter_foto(db, usuario_id)
    # A tela pede com ?v=<versão>; quando a foto muda, a versão muda, então pode guardar em cache.
    return Response(
        foto.conteudo,
        media_type=foto.tipo,
        headers={"Cache-Control": "private, max-age=86400", "ETag": f'"{foto.sha256}"'},
    )
