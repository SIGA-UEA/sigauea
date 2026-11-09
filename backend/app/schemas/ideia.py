"""Formato de entrada e saída das ideias de TCC (RBN02.01 e RBN02.02 · DS-FL12 e DS-FL12-A, TEL03).

GET /ideias/formulario {áreas, docentes}; POST /ideias {titulo, descricao, area_id, destino, professores_ids};
GET /ideias {propostas}; GET /ideias/{id} {proposta, comentários}; POST /ideias/{id}/comentarios {texto}.

Campos obrigatórios ausentes respondem 400 com o campo (E1 do DS-FL12 e E2 do DS-FL12-A), conferidos no serviço
para valer também para texto só com espaços.
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.tcc import PessoaOut
from app.schemas.usuario import AreaOut, DataHora

Destino = Literal["AREA", "PROFESSORES"]


class FormularioIdeia(BaseModel):
    """DS-FL12 mensagens 2 a 4: áreas de interesse e professores da disciplina e orientadores ativos."""

    areas: list[AreaOut]
    docentes: list[PessoaOut]


class PropostaEntrada(BaseModel):
    titulo: str = Field(default="", max_length=200)
    descricao: str = Field(default="", max_length=5000)
    area_id: int | None = None
    destino: Destino | None = None
    professores_ids: list[int] = Field(default_factory=list, max_length=20)


class ComentarioEntrada(BaseModel):
    texto: str = Field(default="", max_length=2000)


class ComentarioOut(BaseModel):
    id: int
    autor: PessoaOut
    texto: str
    criado_em: DataHora


class PropostaResumo(BaseModel):
    """Linha da lista de TEL03: o suficiente para escolher qual abrir."""

    id: int
    titulo: str
    autor: PessoaOut
    criado_em: DataHora
    area: AreaOut | None
    destino: Destino
    professores: list[PessoaOut]  # só quando destino = PROFESSORES
    comentarios: int


class PropostaDetalhe(PropostaResumo):
    """DS-FL12-A mensagens 5 a 8: autor, data, texto e a discussão."""

    descricao: str
    discussao: list[ComentarioOut]
    pode_comentar: bool  # professor destinatário (RBN02.02); o aluno autor só lê (CA-05)
