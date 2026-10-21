from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.usuario import UsuarioOut

# Limites de tamanho só para barrar entradas absurdas; a regra de complexidade
# fica em security.validate_password.
Senha = Field(min_length=1, max_length=128)
Token = Field(min_length=10, max_length=200)


class LoginEntrada(BaseModel):
    # str simples (e não EmailStr) para um e-mail mal escrito também cair no 401 genérico.
    email: str = Field(min_length=1, max_length=254)
    senha: str = Senha


class LoginSaida(BaseModel):
    token_acesso: str
    expira_em_minutos: int
    usuario: UsuarioOut


class DefinirSenhaEntrada(BaseModel):
    token: str = Token
    senha: str = Senha


class ValidarTokenEntrada(BaseModel):
    token: str = Token
    tipo: Literal["ativacao", "recuperacao"]


class ValidarTokenSaida(BaseModel):
    valido: bool
    motivo: Literal["invalido", "expirado", "usado"] | None = None


class EsqueciSenhaEntrada(BaseModel):
    email: str = Field(min_length=1, max_length=254)


class Mensagem(BaseModel):
    detail: str
