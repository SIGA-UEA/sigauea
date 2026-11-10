"""Conta limitada da pessoa externa (RBN01.12 e RBN01.13) · AcessoLimitado dos diagramas DS-FL04-B e DS-FL03-D.

A pessoa externa (usuario_externo) só entra no que um acesso limitado vigente lhe dá: a banca de uma defesa
(escopo BANCA) ou a coorientação de um TCC (escopo COORIENTACAO). Um acesso é vigente enquanto não foi
revogado e não passou de expira_em.

Banca (SCRUM-32): o acesso nasce quando a pessoa entra na banca gravada, isto é, na confirmação da defesa ou na
troca de membro (DS-FL04-B mensagem 8; a banca só é gravada na confirmação, decisão 59-a da RAN09), para todo
membro externo, mesmo quem já tem conta de outra defesa (decisão 32-c). Cancelar a defesa ou trocar o membro
revoga o acesso (32-k). O link vai no convite (32-h): link de ativação de 48 horas para quem ainda não tem
senha (32-a); para quem já tem, o endereço de entrada.

Escopo (CA-02 das duas fichas, decisões 32-33-a e 32-33-b): a cada requisição, a conta externa só passa pelas
rotas de ROTAS_DO_EXTERNO, e só para a defesa ou o TCC de um acesso vigente; o resto, inclusive a Agenda,
recebe 403. A conferência fica na sessão (deps.usuario_atual), antes de qualquer serviço.
"""

import re

from fastapi import Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app import config
from app.database import agora
from app.erros import ErroAPI
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


# =================================================================== escopo da conta externa (CA-02)

# Rota (método, caminho) → o que precisa estar no escopo: None (nada), "proprio" (o próprio usuário),
# "tcc" (TCC de um acesso vigente) ou "defesa" (defesa de um acesso BANCA vigente). Decisão 32-33-a.
ROTAS_DO_EXTERNO: dict[tuple[str, str], str | None] = {
    ("GET", "/api/v1/auth/me"): None,
    ("GET", "/api/v1/usuarios/me"): None,
    ("PUT", "/api/v1/usuarios/me"): None,
    ("POST", "/api/v1/usuarios/me/senha"): None,
    ("PUT", "/api/v1/usuarios/me/foto"): None,
    ("DELETE", "/api/v1/usuarios/me/foto"): None,
    ("GET", "/api/v1/usuarios/{usuario_id}/foto"): "proprio",  # o avatar do menu
    ("GET", "/api/v1/tccs"): None,  # a lista já vem filtrada pelo escopo (tccs.listar_para)
    ("GET", "/api/v1/tccs/{tcc_id}"): "tcc",
    ("GET", "/api/v1/defesas/{defesa_id}/avaliacao"): "defesa",
    ("PUT", "/api/v1/defesas/{defesa_id}/avaliacao"): "defesa",
    ("POST", "/api/v1/defesas/{defesa_id}/avaliacao/envio"): "defesa",
}

FORA_DO_ESCOPO = "Esta conta só acessa a defesa ou o TCC para os quais foi convidada."


def tccs_do_escopo(usuario: Usuario) -> set[int]:
    """Os TCCs que a pessoa externa pode ver agora (banca: o TCC da defesa; coorientação: o próprio TCC)."""
    return {a.tcc_alvo for a in usuario.acessos_limitados if a.vigente}


def defesas_do_escopo(usuario: Usuario) -> set[int]:
    return {a.defesa_id for a in usuario.acessos_limitados if a.vigente and a.escopo == ESCOPO_BANCA}


def _molde(caminho: str) -> re.Pattern:
    """"/api/v1/tccs/{tcc_id}" → expressão que casa "/api/v1/tccs/7" e guarda tcc_id = "7"."""
    return re.compile("^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", caminho) + "/?$")


_MOLDES = [(metodo, _molde(caminho), alvo) for (metodo, caminho), alvo in ROTAS_DO_EXTERNO.items()]


def exigir_escopo(usuario: Usuario, request: Request) -> None:
    """Decisões 32-33-a e 32-33-b: para a conta externa, rota fora da lista ou registro fora do escopo → 403,
    como pedem o E2 e os CT-01.12-02, CT-01.12-03 e CT-01.13-02 (exceção à regra geral do contrato, que é 404).
    Compara o endereço da requisição com os caminhos da lista, sem depender de como o FastAPI monta as rotas."""
    if usuario.externo is None:
        return
    caminho = request.url.path
    achado = next(((m.match(caminho), alvo) for metodo, m, alvo in _MOLDES
                   if metodo == request.method and m.match(caminho)), None)
    if achado is None:
        raise ErroAPI(403, FORA_DO_ESCOPO)
    parametros, alvo = achado[0].groupdict(), achado[1]
    permitido = {
        None: lambda: True,
        "proprio": lambda: parametros.get("usuario_id") == str(usuario.id),
        "tcc": lambda: parametros.get("tcc_id") in {str(i) for i in tccs_do_escopo(usuario)},
        "defesa": lambda: parametros.get("defesa_id") in {str(i) for i in defesas_do_escopo(usuario)},
    }[alvo]
    if not permitido():
        raise ErroAPI(403, FORA_DO_ESCOPO)