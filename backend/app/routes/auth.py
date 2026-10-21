from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.deps import token_da_requisicao, usuario_atual
from app.models import Usuario
from app.schemas.auth import (
    DefinirSenhaEntrada,
    EsqueciSenhaEntrada,
    LoginEntrada,
    LoginSaida,
    Mensagem,
    ValidarTokenEntrada,
    ValidarTokenSaida,
)
from app.schemas.usuario import UsuarioOut
from app.services import autenticacao, tokens
from app.services.usuarios import para_saida

router = APIRouter(prefix="/auth", tags=["autenticação"])


@router.post("/login", response_model=LoginSaida)
def login(dados: LoginEntrada, response: Response, db: Session = Depends(get_db, scope="function")) -> LoginSaida:
    """401 genérico para credenciais inválidas; 423 quando a conta está bloqueada."""
    token, usuario = autenticacao.entrar(db, dados.email, dados.senha)
    # httponly: o JavaScript da página não consegue ler o token da sessão.
    response.set_cookie(
        config.COOKIE_SESSAO,
        token,
        httponly=True,
        samesite="lax",
        secure=config.COOKIE_SEGURO,
        path="/",
    )
    return LoginSaida(
        token_acesso=token, expira_em_minutos=config.SESSAO_MINUTOS, usuario=para_saida(usuario)
    )


@router.post("/logout", response_model=Mensagem)
def logout(request: Request, response: Response, db: Session = Depends(get_db, scope="function")) -> Mensagem:
    autenticacao.sair(db, token_da_requisicao(request))
    response.delete_cookie(config.COOKIE_SESSAO, path="/")
    return Mensagem(detail="Você saiu do sistema.")


@router.get("/me", response_model=UsuarioOut)
def me(usuario: Usuario = Depends(usuario_atual)) -> UsuarioOut:
    return para_saida(usuario)


@router.post("/validar-token", response_model=ValidarTokenSaida)
def validar_token(dados: ValidarTokenEntrada, db: Session = Depends(get_db, scope="function")) -> ValidarTokenSaida:
    """Usado pela página do link para avisar, antes do formulário, se ele expirou ou já foi usado."""
    _, motivo = tokens.motivo_invalido(db, dados.token, dados.tipo)
    return ValidarTokenSaida(valido=motivo is None, motivo=motivo)


@router.post("/ativar", response_model=Mensagem)
def ativar(dados: DefinirSenhaEntrada, db: Session = Depends(get_db, scope="function")) -> Mensagem:
    autenticacao.ativar_conta(db, dados.token, dados.senha)
    return Mensagem(detail="Conta ativada. Entre com o seu e-mail e a nova senha.")


@router.post("/esqueci-senha", response_model=Mensagem, status_code=202)
def esqueci_senha(
    dados: EsqueciSenhaEntrada, tarefas: BackgroundTasks, db: Session = Depends(get_db, scope="function")
) -> Mensagem:
    autenticacao.pedir_recuperacao(db, tarefas, dados.email)
    return Mensagem(
        detail="Se o e-mail estiver cadastrado, enviamos um link para redefinir a senha."
    )


@router.post("/redefinir-senha", response_model=Mensagem)
def redefinir_senha(dados: DefinirSenhaEntrada, db: Session = Depends(get_db, scope="function")) -> Mensagem:
    autenticacao.redefinir_senha(db, dados.token, dados.senha)
    return Mensagem(detail="Senha alterada. Entre com a nova senha.")
