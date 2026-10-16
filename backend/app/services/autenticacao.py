"""Login, sessão, ativação e redefinição de senha (HU01.04 a HU01.07)."""

from datetime import timedelta

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.database import agora
from app.erros import ErroAPI
from app.models import TOKEN_ATIVACAO, TOKEN_RECUPERACAO, Sessao, Usuario
from app.security import (
    gastar_tempo_de_verificacao,
    gerar_hash_senha,
    gerar_token,
    hash_token,
    validate_password,
    verificar_senha,
)
from app.services import auditoria, tokens
from app.services.usuarios import buscar_por_email

# HU01.06 R5: a mesma mensagem para e-mail inexistente, senha errada e conta inativa.
_CREDENCIAIS_INVALIDAS = "E-mail ou senha inválidos."
_BLOQUEADA = (
    f"Conta bloqueada por {config.BLOQUEIO_MINUTOS} minutos após "
    f"{config.MAX_TENTATIVAS_LOGIN} tentativas inválidas. Tente novamente mais tarde."
)


def entrar(db: Session, email: str, senha: str) -> tuple[str, Usuario]:
    """Confere as credenciais e cria a sessão. Devolve (token, usuário)."""
    usuario = buscar_por_email(db, email)

    def falhar(status: int, mensagem: str, motivo: str):
        # R7: toda tentativa fica registrada, inclusive as que falham.
        auditoria.registrar(
            db,
            ator_id=usuario.id if usuario else None,
            acao="login_falha",
            entidade_id=usuario.id if usuario else None,
            campo=motivo,
            novo=None if usuario else email[:254],
        )
        db.commit()
        return ErroAPI(status, mensagem)

    if usuario is None:
        gastar_tempo_de_verificacao(senha)
        raise falhar(401, _CREDENCIAIS_INVALIDAS, "email_inexistente")

    # R6: enquanto bloqueada, nem a senha correta entra.
    if usuario.bloqueado_ate and usuario.bloqueado_ate > agora():
        raise falhar(423, _BLOQUEADA, "conta_bloqueada")

    if usuario.senha_hash is None or not usuario.ativo:
        gastar_tempo_de_verificacao(senha)
        raise falhar(401, _CREDENCIAIS_INVALIDAS, "conta_inativa")

    if not verificar_senha(senha, usuario.senha_hash):
        usuario.tentativas_falhas += 1
        if usuario.tentativas_falhas >= config.MAX_TENTATIVAS_LOGIN:
            usuario.tentativas_falhas = 0
            usuario.bloqueado_ate = agora() + timedelta(minutes=config.BLOQUEIO_MINUTOS)
            auditoria.registrar(db, ator_id=usuario.id, acao="bloqueio", entidade_id=usuario.id)
            raise falhar(423, _BLOQUEADA, "senha_incorreta")
        raise falhar(401, _CREDENCIAIS_INVALIDAS, "senha_incorreta")

    usuario.tentativas_falhas = 0
    usuario.bloqueado_ate = None
    token, token_hash = gerar_token()
    db.add(
        Sessao(
            usuario_id=usuario.id,
            token_hash=token_hash,
            expira_em=agora() + timedelta(minutes=config.SESSAO_MINUTOS),
        )
    )
    auditoria.registrar(db, ator_id=usuario.id, acao="login_sucesso", entidade_id=usuario.id)
    db.commit()
    return token, usuario


def sair(db: Session, token: str | None) -> None:
    if not token:
        return
    sessao = db.scalar(select(Sessao).where(Sessao.token_hash == hash_token(token)))
    if sessao:
        sessao.expira_em = agora()
        auditoria.registrar(
            db, ator_id=sessao.usuario_id, acao="logout", entidade_id=sessao.usuario_id
        )
        db.commit()


def _exigir_senha_forte(senha: str) -> None:
    faltando = validate_password(senha)
    if faltando:
        raise ErroAPI(422, "A senha não atende aos critérios.", criterios=faltando)


def _encerrar_sessoes(db: Session, usuario: Usuario) -> None:
    for sessao in db.scalars(select(Sessao).where(Sessao.usuario_id == usuario.id)):
        sessao.expira_em = agora()


def ativar_conta(db: Session, token: str, senha: str) -> None:
    registro = tokens.exigir_valido(db, token, TOKEN_ATIVACAO)
    _exigir_senha_forte(senha)
    usuario = registro.usuario
    usuario.senha_hash = gerar_hash_senha(senha)
    usuario.ativo = True
    registro.usado_em = agora()  # o link vale uma única vez
    auditoria.registrar(db, ator_id=usuario.id, acao="ativar_conta", entidade_id=usuario.id)
    db.commit()


def pedir_recuperacao(db: Session, tarefas: BackgroundTasks, email: str) -> None:
    """Não devolve nada: a rota responde igual, exista o e-mail ou não (HU01.07 R4)."""
    usuario = buscar_por_email(db, email)
    # Conta inativa ou ainda não ativada não recebe link de recuperação.
    if usuario is None or not usuario.ativo:
        return
    tokens.enviar_recuperacao(db, tarefas, usuario)
    auditoria.registrar(db, ator_id=usuario.id, acao="pedir_recuperacao", entidade_id=usuario.id)
    db.commit()


def redefinir_senha(db: Session, token: str, senha: str) -> None:
    registro = tokens.exigir_valido(db, token, TOKEN_RECUPERACAO)
    _exigir_senha_forte(senha)
    usuario = registro.usuario
    usuario.senha_hash = gerar_hash_senha(senha)
    registro.usado_em = agora()
    # HU01.07 R6: a troca de senha desbloqueia a conta e zera as tentativas.
    usuario.tentativas_falhas = 0
    usuario.bloqueado_ate = None
    _encerrar_sessoes(db, usuario)
    auditoria.registrar(db, ator_id=usuario.id, acao="redefinir_senha", entidade_id=usuario.id)
    db.commit()
