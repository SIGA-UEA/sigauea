"""Senhas e tokens.

- A senha é gravada com bcrypt (RNF02) e nunca é devolvida nem escrita em log.
- Tokens (sessão, ativação, recuperação) são aleatórios; o banco guarda só o
  SHA-256 deles, então quem lê o banco não consegue usar um link ou uma sessão.
"""

import hashlib
import re
import secrets

import bcrypt

from app import config

# HU01.04: regra única de complexidade, usada na ativação e na redefinição.
# O frontend mostra os mesmos critérios (lib/senha.ts).
CRITERIOS_SENHA = [
    ("tamanho", "Mínimo de 8 caracteres", lambda s: len(s) >= 8),
    ("maiuscula", "Ao menos 1 letra maiúscula", lambda s: re.search(r"[A-Z]", s) is not None),
    ("numero", "Ao menos 1 número", lambda s: re.search(r"[0-9]", s) is not None),
    ("especial", "Ao menos 1 caractere especial", lambda s: re.search(r"[^A-Za-z0-9]", s) is not None),
]


def validate_password(senha: str) -> list[dict[str, str]]:
    """Devolve os critérios que a senha NÃO atende. Lista vazia = senha aceita."""
    return [
        {"codigo": codigo, "descricao": descricao}
        for codigo, descricao, atende in CRITERIOS_SENHA
        if not atende(senha)
    ]


def _bytes(senha: str) -> bytes:
    # O bcrypt usa no máximo 72 bytes da senha.
    return senha.encode("utf-8")[:72]


def gerar_hash_senha(senha: str) -> str:
    return bcrypt.hashpw(_bytes(senha), bcrypt.gensalt(config.BCRYPT_CUSTO)).decode()


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(_bytes(senha), senha_hash.encode())


# Usado quando o e-mail não existe, para o login demorar o mesmo tempo
# e não revelar quais e-mails têm cadastro.
_HASH_FALSO = gerar_hash_senha("senha-que-ninguem-usa")


def gastar_tempo_de_verificacao(senha: str) -> None:
    verificar_senha(senha, _HASH_FALSO)


def gerar_token() -> tuple[str, str]:
    """Devolve (token, hash). O token vai para o usuário; o hash vai para o banco."""
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
