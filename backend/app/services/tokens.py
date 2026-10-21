"""Links de ativação (48 h) e de recuperação de senha (10 min).

Cada link vale uma única vez. Pedir um novo link invalida os anteriores.
"""

from datetime import timedelta

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.database import agora
from app.erros import ErroAPI
from app.models import TOKEN_ATIVACAO, TOKEN_RECUPERACAO, TokenUsuario, Usuario
from app.security import gerar_token, hash_token
from app.services import email

_VALIDADE = {
    TOKEN_ATIVACAO: timedelta(hours=config.ATIVACAO_HORAS),
    TOKEN_RECUPERACAO: timedelta(minutes=config.RECUPERACAO_MINUTOS),
}

_MENSAGEM_LINK = {
    "invalido": "Este link não é válido.",
    "expirado": "Este link expirou.",
    "usado": "Este link já foi usado.",
}


def criar(db: Session, usuario: Usuario, tipo: str) -> str:
    """Cria o token e devolve o valor que vai no link. O banco guarda só o hash."""
    # Links anteriores do mesmo tipo, ainda não usados, deixam de valer.
    antigos = db.scalars(
        select(TokenUsuario).where(
            TokenUsuario.usuario_id == usuario.id,
            TokenUsuario.tipo == tipo,
            TokenUsuario.usado_em.is_(None),
            TokenUsuario.expira_em > agora(),
        )
    )
    for antigo in antigos:
        antigo.expira_em = agora()

    token, token_hash = gerar_token()
    db.add(
        TokenUsuario(
            usuario_id=usuario.id,
            tipo=tipo,
            token_hash=token_hash,
            expira_em=agora() + _VALIDADE[tipo],
        )
    )
    return token


def motivo_invalido(db: Session, token: str, tipo: str) -> tuple[TokenUsuario | None, str | None]:
    """Devolve (registro, None) se o link vale, ou (None, motivo) se não vale."""
    registro = db.scalar(
        select(TokenUsuario).where(
            TokenUsuario.token_hash == hash_token(token), TokenUsuario.tipo == tipo
        )
    )
    if registro is None or registro.usuario.inativado_em is not None:
        return None, "invalido"
    if registro.usado_em is not None:
        return None, "usado"
    if registro.expira_em <= agora():
        return None, "expirado"
    return registro, None


def exigir_valido(db: Session, token: str, tipo: str) -> TokenUsuario:
    registro, motivo = motivo_invalido(db, token, tipo)
    if registro is None:
        raise ErroAPI(400, _MENSAGEM_LINK[motivo], motivo=motivo)
    return registro


def enviar_ativacao(db: Session, tarefas: BackgroundTasks, usuario: Usuario) -> None:
    token = criar(db, usuario, TOKEN_ATIVACAO)
    email.enfileirar(
        db,
        tarefas,
        usuario,
        TOKEN_ATIVACAO,
        "SIGA UEA: ative a sua conta",
        f"Olá, {usuario.nome}.\n\n"
        "Sua conta no SIGA UEA foi criada pela coordenação. Para definir a sua senha, "
        f"abra o link abaixo em até {config.ATIVACAO_HORAS} horas:\n\n"
        f"{config.FRONTEND_URL}/ativar?token={token}\n\n"
        "Se o link expirar, peça um novo à coordenação.",
    )


def enviar_recuperacao(db: Session, tarefas: BackgroundTasks, usuario: Usuario) -> None:
    token = criar(db, usuario, TOKEN_RECUPERACAO)
    email.enfileirar(
        db,
        tarefas,
        usuario,
        TOKEN_RECUPERACAO,
        "SIGA UEA: redefinição de senha",
        f"Olá, {usuario.nome}.\n\n"
        "Recebemos um pedido para redefinir a sua senha. Abra o link abaixo em até "
        f"{config.RECUPERACAO_MINUTOS} minutos:\n\n"
        f"{config.FRONTEND_URL}/redefinir-senha?token={token}\n\n"
        "Se não foi você, ignore este e-mail: a sua senha continua a mesma.",
    )
