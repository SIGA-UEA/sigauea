"""E-mails da defesa: convite à banca (SCRUM-63, RBN09.05) e lembrete da véspera (SCRUM-64, RBN09.06).

Cada aviso usa a fila de e-mails (services/email.py): a linha em notificacao_email nasce "pendente",
vira "enviado" ou "falha", e uma falha não desfaz o que foi gravado (E5 do DS-FL04).

O texto leva só o necessário para a pessoa comparecer: título e autor do trabalho, data, horário,
formato, local ou link e o papel na banca. Nada de nota, matrícula ou contato pessoal (RBN09.05 CA-02).
As remarcações, cancelamentos e convocação de suplente (SCRUM-65 a 67) reaproveitam este módulo.
"""

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.models import BancaMembro, Defesa, NotificacaoEmail, Usuario
from app.services import email

TIPO_CONVITE = email.TIPO_CONVITE_BANCA
TIPO_LEMBRETE = "LEMBRETE_DEFESA"

NOME_FORMATO = {"PRESENCIAL": "Presencial", "REMOTO": "Remoto", "HIBRIDO": "Híbrido"}
NOME_PAPEL = {
    "ORIENTADOR": "orientador(a)",
    "COORIENTADOR": "coorientador(a)",
    "AVALIADOR": "avaliador(a)",
    "SUPLENTE": "suplente",
}


def _hora(h) -> str:
    return h.isoformat("minutes")


def descrever(defesa: Defesa) -> str:
    """Bloco com os dados da defesa, igual em todos os avisos."""
    linhas = [
        f"Trabalho: {defesa.tcc.titulo}",
        f"Autor(a): {defesa.tcc.aluno.usuario.nome}",
        f"Data: {defesa.data.strftime('%d/%m/%Y')}",
        f"Horário: {_hora(defesa.inicio)} às {_hora(defesa.fim)} (horário de Manaus)",
        f"Formato: {NOME_FORMATO.get(defesa.formato, defesa.formato)}",
    ]
    if defesa.local is not None:
        linhas.append(f"Local: {defesa.local.nome}")
    if defesa.link:
        linhas.append(f"Link da sala virtual: {defesa.link}")
    return "\n".join(linhas)


def _rodape(defesa: Defesa, interno: bool) -> str:
    if interno:
        return f"Detalhes no SIGA UEA: {config.FRONTEND_URL}/tccs/{defesa.tcc_id}"
    # O link de acesso da conta limitada do convidado externo é da SCRUM-32.
    return "O link de acesso ao SIGA UEA será enviado em mensagem separada."


def participantes(defesa: Defesa) -> list[tuple[Usuario, bool]]:
    """Quem é avisado da defesa: a banca (com o suplente) e o aluno, uma vez cada (DS-FL05-D passo 3).
    Devolve (pessoa, interno)."""
    vistos: set[int] = set()
    lista: list[tuple[Usuario, bool]] = []
    for m in sorted(defesa.membros, key=lambda m: m.id):
        if m.usuario_id not in vistos:
            vistos.add(m.usuario_id)
            lista.append((m.usuario, m.interno))
    aluno = defesa.tcc.aluno.usuario
    if aluno.id not in vistos:
        lista.append((aluno, True))
    return lista


# =================================================================== RBN09.05 · convite à banca


def texto_convite(defesa: Defesa, membro: BancaMembro) -> tuple[str, str]:
    papel = NOME_PAPEL.get(membro.papel, membro.papel.lower())
    corpo = (
        f"Olá, {membro.usuario.nome}.\n\n"
        f"Você foi convidado(a) para a banca de defesa de TCC como {papel}.\n\n"
        f"{descrever(defesa)}\n\n"
    )
    if membro.papel == "SUPLENTE":
        corpo += "Como suplente, você só avalia se for convocado(a) no lugar de um avaliador titular.\n\n"
    corpo += _rodape(defesa, membro.interno)
    return f"Convite para banca de defesa de TCC – {defesa.data.strftime('%d/%m/%Y')}", corpo


def convidar(db: Session, tarefas: BackgroundTasks, defesa: Defesa, membro: BancaMembro) -> None:
    """DS-FL04 passos 22 a 26: um convite por membro, enviado depois da resposta."""
    assunto, corpo = texto_convite(defesa, membro)
    email.enfileirar(db, tarefas, membro.usuario, TIPO_CONVITE, assunto, corpo,
                     entidade="banca_membro", entidade_id=membro.id)


def situacao_convite(db: Session, membro: BancaMembro) -> str:
    """NAO_ENVIADO, PENDENTE, ENVIADO ou FALHA: o último convite desta vaga para a pessoa atual
    (depois de uma troca de membro, os convites da pessoa anterior não contam)."""
    ultimo = db.scalar(
        select(NotificacaoEmail)
        .where(
            NotificacaoEmail.tipo == TIPO_CONVITE,
            NotificacaoEmail.entidade == "banca_membro",
            NotificacaoEmail.entidade_id == membro.id,
            NotificacaoEmail.usuario_id == membro.usuario_id,
        )
        .order_by(NotificacaoEmail.id.desc())
        .limit(1)
    )
    if ultimo is None:
        return "NAO_ENVIADO"
    return {"pendente": "PENDENTE", "enviado": "ENVIADO", "falha": "FALHA"}.get(ultimo.status, "PENDENTE")


# =================================================================== RBN09.06 · lembrete da véspera


def texto_lembrete(defesa: Defesa, pessoa: Usuario, interno: bool) -> tuple[str, str]:
    corpo = (
        f"Olá, {pessoa.nome}.\n\n"
        "Lembrete: a defesa de TCC abaixo acontece amanhã.\n\n"
        f"{descrever(defesa)}\n\n"
        f"{_rodape(defesa, interno)}"
    )
    return f"Lembrete: defesa de TCC amanhã, {_hora(defesa.inicio)}", corpo
