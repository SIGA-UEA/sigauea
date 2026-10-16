"""Configurações da API, lidas de variáveis de ambiente.

Todos os valores têm um padrão que funciona em desenvolvimento, então a API
sobe sem nenhum arquivo .env. Em produção, defina as variáveis no servidor.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Banco: SQLite em desenvolvimento; em produção use PostgreSQL, por exemplo
# postgresql+psycopg://usuario:senha@host:5432/siga
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'siga_dev.db'}")

# Endereço do frontend, usado para montar os links enviados por e-mail.
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")

# Regras de acesso (RBN01.05 a RBN01.07)
SESSAO_MINUTOS = 60  # sessão expira após 60 min de inatividade
ATIVACAO_HORAS = 48  # validade do link de ativação
RECUPERACAO_MINUTOS = 10  # validade do link de recuperação de senha (RBN01.07)
MAX_TENTATIVAS_LOGIN = 3  # tentativas inválidas seguidas até bloquear
BLOQUEIO_MINUTOS = 15  # duração do bloqueio

# Foto de perfil (RBN01.01, RBN01.09, RBN01.10): JPG, PNG ou WebP de até 5 MB.
FOTO_MAX_BYTES = 5 * 1024 * 1024

# RNF02: bcrypt com custo mínimo 10.
BCRYPT_CUSTO = max(10, int(os.environ.get("BCRYPT_CUSTO", "12")))

# Cookie de sessão. Em produção (HTTPS) defina COOKIE_SEGURO=1.
COOKIE_SESSAO = "siga_sessao"
COOKIE_SEGURO = os.environ.get("COOKIE_SEGURO", "0") == "1"

# E-mail. Sem SMTP_HOST, o e-mail é apenas impresso no terminal da API.
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORTA = int(os.environ.get("SMTP_PORTA", "587"))
SMTP_USUARIO = os.environ.get("SMTP_USUARIO", "")
SMTP_SENHA = os.environ.get("SMTP_SENHA", "")
EMAIL_REMETENTE = os.environ.get("EMAIL_REMETENTE", "SIGA UEA <nao-responda@uea.edu.br>")
