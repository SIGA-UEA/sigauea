"""Dependências de autenticação e autorização usadas pelas rotas."""

from collections.abc import Callable
from datetime import timedelta

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.database import agora, get_db
from app.erros import ErroAPI
from app.models import PERFIL_COORDENADOR, Sessao, Usuario
from app.security import hash_token


def token_da_requisicao(request: Request) -> str | None:
    """O navegador manda o token no cookie; outros clientes, no cabeçalho Authorization."""
    cabecalho = request.headers.get("Authorization", "")
    if cabecalho.lower().startswith("bearer "):
        return cabecalho[7:].strip()
    return request.cookies.get(config.COOKIE_SESSAO)


def usuario_atual(request: Request, db: Session = Depends(get_db, scope="function")) -> Usuario:
    """Exige sessão válida. Cada uso renova os 60 minutos (expiração deslizante)."""
    token = token_da_requisicao(request)
    sessao = (
        db.scalar(select(Sessao).where(Sessao.token_hash == hash_token(token)))
        if token
        else None
    )
    if sessao is None or sessao.expira_em <= agora() or not sessao.usuario.ativo:
        raise ErroAPI(401, "Sessão expirada. Entre novamente.")

    sessao.expira_em = agora() + timedelta(minutes=config.SESSAO_MINUTOS)
    db.commit()
    return sessao.usuario


def exigir_perfil(*perfis: str) -> Callable[..., Usuario]:
    """Cria uma dependência que só deixa passar quem tem um dos perfis (403 caso contrário)."""

    def _verificar(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
        if not set(perfis) & set(usuario.perfis):
            raise ErroAPI(403, "Seu perfil não tem permissão para esta ação.")
        return usuario

    return _verificar


coordenador = exigir_perfil(PERFIL_COORDENADOR)
