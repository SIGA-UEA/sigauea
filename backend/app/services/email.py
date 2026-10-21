"""Fila de e-mails (HU01.05 R6).

O cadastro grava uma linha em notificacao_email com status "pendente" e
responde na hora. O envio acontece depois da resposta (BackgroundTasks do
FastAPI). Se falhar, o cadastro continua valendo: a linha fica com status
"falha" e a coordenação pode reenviar.
"""

import json
import smtplib
import urllib.request
from email.message import EmailMessage
from email.utils import parseaddr

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app import config
from app.database import SessionLocal, agora
from app.models import NotificacaoEmail, Usuario


def enfileirar(
    db: Session,
    tarefas: BackgroundTasks,
    usuario: Usuario,
    tipo: str,
    assunto: str,
    corpo: str,
    entidade: str | None = None,
    entidade_id: int | None = None,
) -> None:
    """Registra a pendência e agenda o envio para depois da resposta."""
    notificacao = NotificacaoEmail(
        usuario_id=usuario.id,
        tipo=tipo,
        destinatario=usuario.email,
        entidade=entidade,
        entidade_id=entidade_id,
    )
    db.add(notificacao)
    db.flush()  # gera o id sem encerrar a transação do cadastro
    tarefas.add_task(processar, notificacao.id, assunto, corpo)


def processar(notificacao_id: int, assunto: str, corpo: str) -> None:
    """Tenta enviar e grava o resultado. Roda fora da requisição, com sessão própria."""
    with SessionLocal() as db:
        notificacao = db.get(NotificacaoEmail, notificacao_id)
        if notificacao is None:  # o cadastro não foi concluído
            return
        notificacao.tentativas += 1
        try:
            entregar(notificacao.destinatario, assunto, corpo)
            notificacao.status = "enviado"
            notificacao.enviado_em = agora()
            notificacao.erro = None
        except Exception as erro:  # qualquer falha de envio vira pendência
            notificacao.status = "falha"
            notificacao.erro = str(erro)[:500]
            # Aparece nos logs do servidor (Render), não só no banco.
            print(f"Falha no e-mail para {notificacao.destinatario}: {erro!r}", flush=True)
        db.commit()


def entregar(destinatario: str, assunto: str, corpo: str) -> None:
    """Envia pela API da Brevo (se houver chave) ou por SMTP. Sem nenhum dos dois
    (desenvolvimento), imprime no terminal."""
    if config.BREVO_API_KEY:
        _entregar_brevo(destinatario, assunto, corpo)
        return
    if not config.SMTP_HOST:
        print(f"\n--- E-mail para {destinatario} ---\n{assunto}\n\n{corpo}\n---\n", flush=True)
        return

    mensagem = EmailMessage()
    mensagem["From"] = config.EMAIL_REMETENTE
    mensagem["To"] = destinatario
    mensagem["Subject"] = assunto
    mensagem.set_content(corpo)
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORTA, timeout=15) as smtp:
        smtp.starttls()
        if config.SMTP_USUARIO:
            smtp.login(config.SMTP_USUARIO, config.SMTP_SENHA)
        smtp.send_message(mensagem)


def _entregar_brevo(destinatario: str, assunto: str, corpo: str) -> None:
    """Envio por HTTPS: serve onde a hospedagem bloqueia as portas de SMTP (Render grátis)."""
    nome, endereco = parseaddr(config.EMAIL_REMETENTE)
    dados = {
        "sender": {"name": nome or "SIGA UEA", "email": endereco},
        "to": [{"email": destinatario}],
        "subject": assunto,
        "textContent": corpo,
    }
    pedido = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email",
        data=json.dumps(dados).encode(),
        headers={"api-key": config.BREVO_API_KEY, "Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(pedido, timeout=15):  # 4xx/5xx vira HTTPError e cai em "falha"
        pass
