from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PlainSerializer, StringConstraints

# O banco guarda UTC sem fuso; o "Z" avisa o navegador para converter para a hora local.
DataHora = Annotated[datetime, PlainSerializer(lambda d: d.isoformat(timespec="seconds") + "Z")]

Nome = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=150)]
Telefone = Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)]
Matricula = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{6,20}$")]
Cargo = Literal["coordenador", "professor", "orientador"]


class CursoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sigla: str
    nome: str


class AreaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str


class AreaUsoOut(AreaOut):
    """Área na tela de gestão (RBN01.02): mostra quantos docentes a usam."""

    docentes: int


class AreaEntrada(BaseModel):
    nome: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]


class PerfilOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    nome: str


class DocenteCriar(BaseModel):
    nome: Nome
    email: EmailStr
    cargo: Cargo
    telefone: Telefone | None = None
    # Obrigatório, exceto quando o perfil coordenador está marcado (regra no serviço).
    curso_id: int | None = None
    areas: list[int] = []
    perfis: list[str] = Field(min_length=1)


class AlunoCriar(BaseModel):
    nome: Nome
    email: EmailStr
    matricula: Matricula
    curso_id: int


class UsuarioAtualizar(BaseModel):
    """Edição pela coordenação (HU01.08). Só os campos enviados são alterados."""

    nome: Nome | None = None
    email: EmailStr | None = None
    telefone: Telefone | None = None
    matricula: Matricula | None = None
    curso_id: int | None = None
    cargo: Cargo | None = None
    areas: list[int] | None = None
    perfis: list[str] | None = Field(default=None, min_length=1)


class MeuPerfilAtualizar(BaseModel):
    """Edição dos próprios dados (RBN01.09 aluno, RBN01.10 docentes). Só os campos enviados mudam.

    Nome, e-mail e matrícula não estão aqui: só a coordenação altera (RBN01.08).
    """

    model_config = ConfigDict(extra="forbid")

    telefone: Telefone | None = None
    curso_id: int | None = None  # só docentes
    areas: list[int] | None = None  # só professor da disciplina e orientador (RN25)


class TrocarSenhaEntrada(BaseModel):
    senha_atual: str = Field(min_length=1, max_length=128)
    nova_senha: str = Field(min_length=1, max_length=128)


class UsuarioOut(BaseModel):
    """Um usuário como a tela precisa. Nunca inclui senha nem hash (HU01.04 R7)."""

    id: int
    nome: str
    email: str
    telefone: str | None
    tipo: Literal["docente", "aluno"]
    situacao: Literal["ativo", "aguardando_ativacao", "inativo"]
    perfis: list[str]
    cargo: str | None
    matricula: str | None
    curso: CursoOut | None
    areas: list[AreaOut]
    # Situação do último e-mail de ativação: pendente, enviado ou falha.
    email_ativacao: str | None
    # Muda quando a foto muda; a tela usa para buscar /usuarios/{id}/foto?v=... Nulo = sem foto.
    foto_versao: str | None
    criado_em: DataHora
