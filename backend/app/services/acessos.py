"""Conta limitada da pessoa externa (RBN01.12 e RBN01.13) · AcessoLimitado dos diagramas DS-FL04-B e DS-FL03-D.

A pessoa externa (usuario_externo) só entra no que um acesso limitado vigente lhe dá: a banca de uma defesa
(escopo BANCA) ou a coorientação de um TCC (escopo COORIENTACAO). Um acesso é vigente enquanto não foi
revogado e não passou de expira_em.

Banca (SCRUM-32): o acesso nasce quando a pessoa entra na banca gravada, isto é, na confirmação da defesa ou na
troca de membro (DS-FL04-B mensagem 8; a banca só é gravada na confirmação, decisão 59-a da RAN09), para todo
membro externo, mesmo quem já tem conta de outra defesa (decisão 32-c). Cancelar a defesa ou trocar o membro
revoga o acesso (32-k). O link vai no convite (32-h): link de ativação de 48 horas para quem ainda não tem
senha (32-a); para quem já tem, o endereço de entrada.
"""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app import config
from app.database import agora
from app.models import ESCOPO_BANCA, TOKEN_ATIVACAO, AcessoLimitado, BancaMembro, Defesa, Usuario
from app.services import auditoria, tokens


def _vigente():
    """Condição de acesso vigente: não revogado e dentro do prazo (prazo vazio = ainda sem data de fim)."""
    return (
        AcessoLimitado.revogado_em.is_(None),
        or_(AcessoLimitado.expira_em.is_(None), AcessoLimitado.expira_em > agora()),
    )


def vigentes(db: Session, usuario_id: int) -> list[AcessoLimitado]:
    """Os acessos que a pessoa tem agora."""
    return list(db.scalars(
        select(AcessoLimitado).where(AcessoLimitado.usuario_id == usuario_id, *_vigente()).order_by(AcessoLimitado.id)
    ))


def _da_banca(db: Session, defesa_id: int, usuario_id: int | None = None) -> list[AcessoLimitado]:
    consulta = select(AcessoLimitado).where(
        AcessoLimitado.escopo == ESCOPO_BANCA, AcessoLimitado.defesa_id == defesa_id, *_vigente()
    )
    if usuario_id is not None:
        consulta = consulta.where(AcessoLimitado.usuario_id == usuario_id)
    return list(db.scalars(consulta.order_by(AcessoLimitado.id)))


def _descrever(defesa: Defesa) -> str:
    return f"Defesa {defesa.id} ({defesa.data.strftime('%d/%m/%Y')}): {defesa.tcc.titulo}"


def conceder_banca(db: Session, ator: Usuario, membro: BancaMembro) -> AcessoLimitado | None:
    """DS-FL04-B mensagem 8: acesso limitado à defesa para o membro externo. Membro interno não recebe nada.
    Se a pessoa já tem acesso vigente a esta defesa, ele é reaproveitado."""
    if membro.interno:
        return None
    existente = _da_banca(db, membro.defesa_id, membro.usuario_id)
    if existente:
        return existente[0]
    acesso = AcessoLimitado(usuario_id=membro.usuario_id, escopo=ESCOPO_BANCA, defesa_id=membro.defesa_id)
    db.add(acesso)
    pessoa = membro.usuario
    if pessoa.senha_hash is not None and not pessoa.ativo and pessoa.inativado_em is None:
        pessoa.ativo = True  # decisão 32-f: a conta desligada por falta de acesso volta com o acesso novo
    db.flush()
    auditoria.registrar(  # CA-05: responsável, data e hora (criado_em do log), defesa e evento
        db, ator_id=ator.id, acao="criar_acesso_banca", entidade="acesso_limitado", entidade_id=acesso.id,
        campo="defesa", novo=f"{pessoa.nome} · {_descrever(membro.defesa)}",
    )
    return acesso


def revogar_banca(db: Session, ator: Usuario, defesa: Defesa, usuario_id: int | None = None) -> None:
    """Decisão 32-k: a defesa cancelada revoga o acesso de todos os membros externos; a troca de membro,
    só o de quem saiu."""
    for acesso in _da_banca(db, defesa.id, usuario_id):
        acesso.revogado_em = agora()
        auditoria.registrar(
            db, ator_id=ator.id, acao="revogar_acesso", entidade="acesso_limitado", entidade_id=acesso.id,
            campo="defesa", anterior=f"{acesso.usuario.nome} · {_descrever(defesa)}",
        )


def link_do_convite(db: Session, pessoa: Usuario) -> str:
    """Decisões 32-a e 32-h: link de ativação (48 horas, uso único) para quem ainda não definiu a senha; para
    quem já tem senha, o endereço de entrada. Cada link novo invalida o anterior (tokens.criar)."""
    if pessoa.senha_hash is None and pessoa.inativado_em is None:
        return f"{config.FRONTEND_URL}/ativar?token={tokens.criar(db, pessoa, TOKEN_ATIVACAO)}"
    return f"{config.FRONTEND_URL}/entrar"
