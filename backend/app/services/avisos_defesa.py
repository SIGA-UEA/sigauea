"""E-mails da defesa: convite à banca (SCRUM-63, RBN09.05) e lembrete da véspera (SCRUM-64, RBN09.06).

Cada aviso usa a fila de e-mails (services/email.py): a linha em notificacao_email nasce "pendente",
vira "enviado" ou "falha", e uma falha não desfaz o que foi gravado (E5 do DS-FL04).

O texto leva só o necessário para a pessoa comparecer: título e autor do trabalho, data, horário,
formato, local ou link e o papel na banca. Nada de nota, matrícula ou contato pessoal (RBN09.05 CA-02).
Remarcação (SCRUM-65), cancelamento (SCRUM-66) e convocação do suplente (SCRUM-67) usam o mesmo
bloco de dados e a mesma fila.
"""

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.models import BancaMembro, Defesa, NotificacaoEmail, Usuario
from app.services import email

TIPO_CONVITE = email.TIPO_CONVITE_BANCA
TIPO_LEMBRETE = "LEMBRETE_DEFESA"
TIPO_REMARCADA = "DEFESA_REMARCADA"
TIPO_CANCELADA = "DEFESA_CANCELADA"
TIPO_SUPLENTE = "SUPLENTE_CONVOCADO"

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
    if membro.convocado_em is not None:  # RBN09.09: reenvio ao suplente que já avalia
        titular = next((m for m in defesa.membros if m.id == membro.substitui_membro_id), None)
        corpo += f"Você foi convocado(a) para avaliar no lugar de {titular.usuario.nome if titular else 'um avaliador titular'}.\n\n"
    elif membro.papel == "SUPLENTE":
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


# =================================================================== FL05 · remarcação, cancelamento, suplente


def _quando(dados: dict) -> str:
    """Data e horário de um retrato anterior da defesa (valores_anteriores do histórico)."""
    data = dados["data"]
    return f"{data[8:10]}/{data[5:7]}/{data[0:4]}, das {dados['inicio'][:5]} às {dados['fim'][:5]}"


def avisar(db: Session, tarefas: BackgroundTasks, defesa: Defesa, tipo: str, pessoas, texto) -> None:
    """Um e-mail por pessoa, depois da resposta. `texto(pessoa, interno)` devolve (assunto, corpo)."""
    for pessoa, interno in pessoas:
        assunto, corpo = texto(pessoa, interno)
        email.enfileirar(db, tarefas, pessoa, tipo, assunto, corpo, entidade="defesa", entidade_id=defesa.id)


def avisar_remarcacao(db: Session, tarefas: BackgroundTasks, defesa: Defesa, anteriores: dict, motivo: str) -> None:
    """DS-FL05-B mensagens 14 a 19: banca e aluno recebem a nova data, a anterior e o motivo."""
    def texto(pessoa: Usuario, interno: bool) -> tuple[str, str]:
        corpo = (
            f"Olá, {pessoa.nome}.\n\n"
            f"A defesa de TCC abaixo foi remarcada. Antes: {_quando(anteriores)}.\n"
            f"Motivo: {motivo}\n\n"
            f"Novos dados:\n{descrever(defesa)}\n\n"
            f"{_rodape(defesa, interno)}"
        )
        return f"Defesa de TCC remarcada para {defesa.data.strftime('%d/%m/%Y')}", corpo

    avisar(db, tarefas, defesa, TIPO_REMARCADA, participantes(defesa), texto)


def avisar_cancelamento(db: Session, tarefas: BackgroundTasks, defesa: Defesa, justificativa: str) -> None:
    """DS-FL05-C mensagens 7 a 12: banca e aluno recebem o cancelamento com o motivo."""
    def texto(pessoa: Usuario, interno: bool) -> tuple[str, str]:
        corpo = (
            f"Olá, {pessoa.nome}.\n\n"
            "A defesa de TCC abaixo foi cancelada.\n"
            f"Motivo: {justificativa}\n\n"
            f"{descrever(defesa)}\n\n"
            "Se uma nova data for marcada, você receberá outro convite."
        )
        return f"Defesa de TCC cancelada – {defesa.data.strftime('%d/%m/%Y')}", corpo

    avisar(db, tarefas, defesa, TIPO_CANCELADA, participantes(defesa), texto)


def avisar_convocacao(
    db: Session, tarefas: BackgroundTasks, defesa: Defesa, suplente: BancaMembro, titular: BancaMembro, motivo: str
) -> None:
    """DS-FL05-E mensagens 8 a 12: o suplente, o titular e o aluno (fluxo da ficha, passo 2)."""
    aluno = defesa.tcc.aluno.usuario
    pessoas = [(suplente.usuario, suplente.interno), (titular.usuario, titular.interno), (aluno, True)]

    def texto(pessoa: Usuario, interno: bool) -> tuple[str, str]:
        if pessoa.id == suplente.usuario_id:
            abertura = (f"Você foi convocado(a) como suplente para avaliar a defesa abaixo, "
                        f"no lugar de {titular.usuario.nome}.")
        elif pessoa.id == titular.usuario_id:
            abertura = f"{suplente.usuario.nome}, suplente da banca, foi convocado(a) para avaliar no seu lugar."
        else:
            abertura = f"{suplente.usuario.nome}, suplente da banca, vai avaliar no lugar de {titular.usuario.nome}."
        corpo = (
            f"Olá, {pessoa.nome}.\n\n{abertura}\nMotivo: {motivo}\n\n"
            f"{descrever(defesa)}\n\n{_rodape(defesa, interno)}"
        )
        return "Suplente convocado para a banca de defesa de TCC", corpo

    avisar(db, tarefas, defesa, TIPO_SUPLENTE, pessoas, texto)
