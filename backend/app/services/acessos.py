"""Conta limitada da pessoa externa (RBN01.12 e RBN01.13) · AcessoLimitado dos diagramas DS-FL04-B e DS-FL03-D.

A pessoa externa (usuario_externo) só entra no que um acesso limitado vigente lhe dá: a banca de uma defesa
(escopo BANCA) ou a coorientação de um TCC (escopo COORIENTACAO). Um acesso é vigente enquanto não foi
revogado e não passou de expira_em.

Banca (SCRUM-32): o acesso nasce quando a pessoa entra na banca gravada, isto é, na confirmação da defesa ou na
troca de membro (DS-FL04-B mensagem 8; a banca só é gravada na confirmação, decisão 59-a da RAN09), para todo
membro externo, mesmo quem já tem conta de outra defesa (decisão 32-c). Cancelar a defesa ou trocar o membro
revoga o acesso (32-k). O link vai no convite (32-h): link de ativação de 48 horas para quem ainda não tem
senha (32-a); para quem já tem, o endereço de entrada.

Coorientação (SCRUM-33, DS-FL03-D): quando a coordenação ou o orientador informam um coorientador externo, a
pessoa ganha conta sem senha (se ainda não tem), acesso limitado ao TCC (escopo COORIENTACAO) e o link de
ativação de 48 horas (RBN01.05). Ativar a conta vale como aceite da coorientação (decisão 33-b). O fim do
vínculo revoga o acesso (CA-04, RN16) e, sem outro acesso válido, desliga a conta.

Expiração (CA-03 da ficha 32, decisões 32-d, 32-e e 32-f): ao confirmar o resultado da defesa (SCRUM-70), o
acesso da banca ganha expira_em = confirmação + 7 dias; a retificação não reinicia o prazo. Uma vez por dia,
POST /tarefas/expirar-acessos (ControladorAcesso.revogarAcessosVencidos do diagrama de classes, no padrão do
DS-FL10-H) registra os acessos vencidos e desliga a conta que não tem mais nenhum acesso válido, encerrando
as sessões abertas. A conta também é desligada quando o último acesso é revogado.

Escopo (CA-02 das duas fichas, decisões 32-33-a e 32-33-b): a cada requisição, a conta externa só passa pelas
rotas de ROTAS_DO_EXTERNO, e só para a defesa ou o TCC de um acesso vigente; o resto, inclusive a Agenda,
recebe 403. A conferência fica na sessão (deps.usuario_atual), antes de qualquer serviço.
"""

import re
from datetime import datetime, timedelta

from fastapi import BackgroundTasks, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app import config
from app.database import agora
from app.erros import ErroAPI
from app.models import (
    ACEITA,
    ESCOPO_BANCA,
    ESCOPO_COORIENTACAO,
    PAPEL_COORIENTADOR,
    PENDENTE,
    TOKEN_ATIVACAO,
    AcessoLimitado,
    BancaMembro,
    Defesa,
    LogAuditoria,
    Orientacao,
    Sessao,
    Tcc,
    Usuario,
    UsuarioExterno,
)
from app.services import auditoria, email, tokens

DIAS_DEPOIS_DO_RESULTADO = 7  # RBN01.12: a conta expira 7 dias após a confirmação do resultado da defesa


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
    só o de quem saiu. Quem fica sem nenhum acesso válido tem a conta desligada (32-f)."""
    for acesso in _da_banca(db, defesa.id, usuario_id):
        acesso.revogado_em = agora()
        auditoria.registrar(
            db, ator_id=ator.id, acao="revogar_acesso", entidade="acesso_limitado", entidade_id=acesso.id,
            campo="defesa", anterior=f"{acesso.usuario.nome} · {_descrever(defesa)}",
        )
        db.flush()
        desligar_se_sem_acesso(db, acesso.usuario, ator)


def definir_prazo_banca(db: Session, defesa: Defesa, confirmado_em: datetime) -> None:
    """Decisão 32-d (opção A): na confirmação do resultado, o acesso da banca vence 7 dias depois. Só o acesso
    ainda sem prazo recebe a data, então a retificação (outra versão do resultado) não reinicia a contagem."""
    for acesso in _da_banca(db, defesa.id):
        if acesso.expira_em is None:
            acesso.expira_em = confirmado_em + timedelta(days=DIAS_DEPOIS_DO_RESULTADO)


def desligar_se_sem_acesso(db: Session, pessoa: Usuario, ator: Usuario | None) -> bool:
    """Decisão 32-f: a conta externa sem nenhum acesso válido é desligada (ativo falso, login negado pelo
    DS-FL10) e as sessões abertas são encerradas. inativado_em fica vazio: não é a inativação da coordenação."""
    if pessoa.externo is None or not pessoa.ativo or vigentes(db, pessoa.id):
        return False
    pessoa.ativo = False
    for sessao in db.scalars(select(Sessao).where(Sessao.usuario_id == pessoa.id, Sessao.expira_em > agora())):
        sessao.expira_em = agora()
    auditoria.registrar(
        db, ator_id=ator.id if ator else None, acao="desligar_conta_externa", entidade="usuario",
        entidade_id=pessoa.id, campo="ativo", anterior="ativo", novo="sem acesso válido",
    )
    return True


def expirar_vencidos(db: Session) -> dict:
    """POST /tarefas/expirar-acessos (CA-03, ControladorAcesso.revogarAcessosVencidos, no padrão do DS-FL10-H).

    1. Lista os acessos que venceram e ainda não foram registrados como expirados (o log expirar_acesso é a marca:
       rodar duas vezes no mesmo dia não repete nada).
    2. Registra cada um no log (CA-05: data e hora, defesa e evento; o responsável é a rotina, sem usuário).
    3. Desliga a conta de quem ficou sem nenhum acesso válido e encerra as sessões."""
    ja_registrados = select(LogAuditoria.entidade_id).where(
        LogAuditoria.acao == "expirar_acesso", LogAuditoria.entidade == "acesso_limitado"
    )
    vencidos = db.scalars(  # passo 1
        select(AcessoLimitado).where(
            AcessoLimitado.revogado_em.is_(None),
            AcessoLimitado.expira_em <= agora(),
            AcessoLimitado.id.not_in(ja_registrados),
        ).order_by(AcessoLimitado.id)
    ).all()
    pessoas: dict[int, Usuario] = {}
    for acesso in vencidos:  # passo 2
        alvo = _descrever(acesso.defesa) if acesso.defesa else f"TCC {acesso.tcc_id}"
        auditoria.registrar(
            db, ator_id=None, acao="expirar_acesso", entidade="acesso_limitado", entidade_id=acesso.id,
            campo="defesa" if acesso.defesa else "tcc", anterior=f"{acesso.usuario.nome} · {alvo}",
            novo=f"expirou em {acesso.expira_em.isoformat(timespec='minutes')}",
        )
        pessoas[acesso.usuario_id] = acesso.usuario
    db.flush()
    desligadas = sum(desligar_se_sem_acesso(db, p, None) for p in pessoas.values())  # passo 3
    db.commit()
    return {"expirados": len(vencidos), "contas_desligadas": desligadas}


def link_do_convite(db: Session, pessoa: Usuario) -> str:
    """Decisões 32-a e 32-h: link de ativação (48 horas, uso único) para quem ainda não definiu a senha; para
    quem já tem senha, o endereço de entrada. Cada link novo invalida o anterior (tokens.criar)."""
    if pessoa.senha_hash is None and pessoa.inativado_em is None:
        return f"{config.FRONTEND_URL}/ativar?token={tokens.criar(db, pessoa, TOKEN_ATIVACAO)}"
    return f"{config.FRONTEND_URL}/entrar"


# =================================================================== coorientação externa (SCRUM-33, DS-FL03-D)


def criar_externo(db: Session, nome: str, email_: str, instituicao: str) -> Usuario:
    """DS-FL03-D mensagem 5: conta sem senha, aguardando ativação, com a instituição (RN12). Sem perfil: o que a
    pessoa pode fazer vem do acesso limitado."""
    pessoa = Usuario(nome=nome, email=email_.lower())
    db.add(pessoa)
    db.flush()
    db.add(UsuarioExterno(usuario_id=pessoa.id, instituicao=instituicao))
    db.flush()
    db.refresh(pessoa)
    return pessoa


def _descrever_tcc(tcc: Tcc) -> str:
    return f"TCC {tcc.id}: {tcc.titulo}"


def conceder_coorientacao(db: Session, ator: Usuario, pessoa: Usuario, tcc: Tcc) -> AcessoLimitado:
    """DS-FL03-D mensagens 6 e 10: acesso limitado ao TCC (visualizar) e o registro no log."""
    acesso = AcessoLimitado(usuario_id=pessoa.id, escopo=ESCOPO_COORIENTACAO, tcc_id=tcc.id)
    db.add(acesso)
    if pessoa.senha_hash is not None and not pessoa.ativo and pessoa.inativado_em is None:
        pessoa.ativo = True  # decisão 32-f: a conta desligada por falta de acesso volta com o acesso novo
    db.flush()
    auditoria.registrar(
        db, ator_id=ator.id, acao="criar_conta_coorientador", entidade="acesso_limitado", entidade_id=acesso.id,
        campo="tcc", novo=f"{pessoa.nome} · {_descrever_tcc(tcc)}",
    )
    return acesso


def avisar_coorientador(db: Session, tarefas: BackgroundTasks, ator: Usuario, pessoa: Usuario, tcc: Tcc) -> None:
    """DS-FL03-D mensagens 8 e 9: o e-mail com o link de ativação (48 horas) ou, para quem já tem senha, a entrada."""
    link = link_do_convite(db, pessoa)
    if "/ativar?" in link:
        acesso = (f"Para acessar o trabalho no SIGA UEA, crie a sua senha pelo link abaixo, em até "
                  f"{config.ATIVACAO_HORAS} horas:\n\n{link}\n\nAo criar a senha, você aceita a coorientação.")
    else:
        acesso = f"Para acessar o trabalho no SIGA UEA, entre com o seu e-mail e a sua senha: {link}"
    corpo = (
        f"Olá, {pessoa.nome}.\n\n"
        f"{ator.nome} informou você como coorientador(a) do TCC \"{tcc.titulo}\", de {tcc.aluno.usuario.nome}.\n\n"
        f"{acesso}\n\nA conta dá acesso só a este trabalho."
    )
    email.enfileirar(db, tarefas, pessoa, "COORIENTACAO_EXTERNA", "SIGA UEA: coorientação de TCC", corpo,
                     entidade="tcc", entidade_id=tcc.id)


def aceitar_coorientacoes(db: Session, pessoa: Usuario) -> None:
    """Decisão 33-b: a pessoa externa que ativa a conta aceita as coorientações pendentes dela."""
    if pessoa.externo is None:
        return
    pendentes = db.scalars(select(Orientacao).where(
        Orientacao.professor_id == pessoa.id, Orientacao.papel == PAPEL_COORIENTADOR,
        Orientacao.status == PENDENTE, Orientacao.encerrado_em.is_(None),
    ))
    for o in pendentes:
        o.status, o.respondido_em = ACEITA, agora()
        auditoria.registrar(
            db, ator_id=pessoa.id, acao="responder_orientacao", entidade="tcc", entidade_id=o.tcc_id,
            campo="coorientador", anterior=PENDENTE, novo=f"{ACEITA} (ativação da conta)",
        )


def revogar_coorientacao(db: Session, ator: Usuario, pessoa: Usuario, tcc: Tcc) -> None:
    """DS-FL03-D mensagem 16 (CA-04): o fim do vínculo encerra o acesso ao TCC; sem outro acesso, a conta é desligada."""
    acessos_do_tcc = db.scalars(select(AcessoLimitado).where(
        AcessoLimitado.usuario_id == pessoa.id, AcessoLimitado.escopo == ESCOPO_COORIENTACAO,
        AcessoLimitado.tcc_id == tcc.id, *_vigente(),
    )).all()
    for acesso in acessos_do_tcc:
        acesso.revogado_em = agora()
        auditoria.registrar(
            db, ator_id=ator.id, acao="revogar_acesso", entidade="acesso_limitado", entidade_id=acesso.id,
            campo="tcc", anterior=f"{pessoa.nome} · {_descrever_tcc(tcc)}",
        )
    db.flush()
    desligar_se_sem_acesso(db, pessoa, ator)


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
    ("GET", "/api/v1/defesas/{defesa_id}/resultado"): "defesa",  # RBN09.13 (PR #19)
    ("GET", "/api/v1/defesas/{defesa_id}/documentos"): "defesa",  # RBN09.16 e "Seu certificado"
    ("GET", "/api/v1/documentos/{documento_id}/arquivo"): None,  # baixar() confere o vínculo e o próprio certificado
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