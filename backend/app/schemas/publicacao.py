"""Formato da publicação do artigo (RBN12.01 a RBN12.03 · DS-FL08, DS-FL08-A e DS-FL08-B, TEL15).

GET /tccs/{id}/publicacao: situação atual e histórico; POST /tccs/{id}/publicacao: novo registro;
GET /tccs/{id}/publicacoes/historico: só o histórico. Campos inválidos respondem 422 com o campo (E2), conferidos
no serviço.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.tcc import PessoaOut
from app.schemas.usuario import DataHora

SituacaoEditorial = Literal["SUBMETIDO", "EM_REVISAO", "ACEITO", "RECUSADO", "PUBLICADO"]


class RegistroEntrada(BaseModel):
    """DS-FL08 mensagem 8: {veículo, qualis, situação, link}, com a data da alteração (RBN12.01) e o tipo do veículo,
    que o modelo físico exige para uma submissão nova."""

    veiculo: str = Field(default="", max_length=300)
    tipo_veiculo: Literal["PERIODICO", "CONGRESSO"] | None = None
    qualis: str | None = Field(default=None, max_length=10)
    situacao: str = Field(default="", max_length=20)
    data: date | None = None
    link: str | None = Field(default=None, max_length=300)


class RegistroOut(BaseModel):
    """Uma linha do histórico (RBN12.02): situação, data, responsável e veículo, com o Qualis e o endereço."""

    id: int
    situacao: SituacaoEditorial
    data: date
    responsavel: PessoaOut | None  # nulo: registrado pelo sistema
    registrado_em: DataHora
    veiculo: str
    tipo_veiculo: str
    qualis: str | None
    link: str | None


class SituacaoAtualOut(BaseModel):
    veiculo: str
    tipo_veiculo: str
    qualis: str | None
    link: str | None
    situacao: SituacaoEditorial


class PublicacaoOut(BaseModel):
    """DS-FL08 mensagens 3 a 5: situação atual (para pré-preencher o formulário, CA-02) e histórico."""

    tcc_id: int
    pode_registrar: bool  # aluno autor ou orientador do TCC
    atual: SituacaoAtualOut | None
    historico: list[RegistroOut]  # do mais recente para o mais antigo (DS-FL08-B)
