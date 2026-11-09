"""Lembrete da véspera da defesa (SCRUM-64, RBN09.06) · ControladorLembretes do DS-FL05-D.

Uma vez por dia, o agendador (GitHub Actions, .github/workflows/lembretes-defesa.yml) chama
POST /api/v1/tarefas/lembretes-defesa. A rotina pega as defesas de amanhã (data de Manaus) que estão
confirmadas ou remarcadas e manda um lembrete a cada participante: banca e aluno.

- CA-02: defesa cancelada não recebe lembrete.
- CA-04: rodar duas vezes no mesmo dia não duplica; defesa.lembrete_enviado_em marca o envio.
- CA-05: a falha de um envio não impede os outros; ao rodar de novo, só os que falharam são repetidos.
- CA-03: a remarcação (SCRUM-65) apaga lembrete_enviado_em, então o lembrete sai com os dados novos.
"""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import agora
from app.models import Defesa, NotificacaoEmail
from app.services import auditoria, avisos_defesa, email
from app.services.defesas import ALTERAVEIS, agora_manaus

MAX_TENTATIVAS = 3  # uma falha é repetida até 3 vezes no total


def lembrar_defesas_de_amanha(db: Session, hoje: date | None = None) -> dict:
    """DS-FL05-D passos 1 a 8. Devolve o resumo: defesas, enviados, falhas, repetidos."""
    hoje = hoje or agora_manaus().date()
    amanha = hoje + timedelta(days=1)
    defesas = db.scalars(  # passo 2: listarConfirmadasEm(amanhã)
        select(Defesa).where(Defesa.data == amanha, Defesa.situacao.in_(ALTERAVEIS)).order_by(Defesa.inicio, Defesa.id)
    ).all()

    envios: list[tuple[int, str, str]] = []  # (notificação, assunto, corpo)
    repetidos = 0
    for defesa in defesas:
        textos = {p.id: avisos_defesa.texto_lembrete(defesa, p, interno) for p, interno in avisos_defesa.participantes(defesa)}
        if defesa.lembrete_enviado_em is None:
            # Marca antes de registrar: as notificações deste lembrete são as criadas a partir daqui.
            defesa.lembrete_enviado_em = agora()
            for pessoa, _ in avisos_defesa.participantes(defesa):  # passos 3 e 4
                n = email.registrar(db, pessoa, avisos_defesa.TIPO_LEMBRETE, "defesa", defesa.id)
                envios.append((n.id, *textos[pessoa.id]))
            auditoria.registrar(db, ator_id=None, acao="enviar_lembrete_defesa", entidade="defesa",
                                entidade_id=defesa.id, novo=amanha.isoformat())
            continue
        # CA-05: lembrete já registrado; repete só os envios que falharam (passo 8)
        falhas = db.scalars(select(NotificacaoEmail).where(
            NotificacaoEmail.tipo == avisos_defesa.TIPO_LEMBRETE,
            NotificacaoEmail.entidade == "defesa",
            NotificacaoEmail.entidade_id == defesa.id,
            NotificacaoEmail.status == "falha",
            NotificacaoEmail.tentativas < MAX_TENTATIVAS,
            NotificacaoEmail.criado_em >= defesa.lembrete_enviado_em,
        )).all()
        for n in falhas:
            if n.usuario_id in textos:  # a pessoa ainda participa da defesa
                envios.append((n.id, *textos[n.usuario_id]))
                repetidos += 1
    db.commit()  # grava antes de enviar: processar() usa outra sessão

    for notificacao_id, assunto, corpo in envios:  # passos 5 a 8, um por vez
        email.processar(notificacao_id, assunto, corpo)

    db.expire_all()
    ids = [n for n, _, _ in envios]
    situacoes = db.scalars(select(NotificacaoEmail.status).where(NotificacaoEmail.id.in_(ids))).all() if ids else []
    return {
        "data": amanha.isoformat(),
        "defesas": len(defesas),
        "enviados": situacoes.count("enviado"),
        "falhas": situacoes.count("falha"),
        "repetidos": repetidos,
    }
