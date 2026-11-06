"""Formato de entrada e saída das ocorrências, dos ouvintes e da declaração de horas (Sprint S04 · RBN09.10).

Rotas dos diagramas DS-FL09 (GET e POST /defesas/{id}/ocorrencias, POST /defesas/{id}/ouvintes e
/ouvintes/lote), DS-FL09-A (PUT /ocorrencias/{id}, PUT e DELETE /ouvintes/{id}) e DS-FL09-B
(POST /defesas/{id}/declaracoes).

Nome e matrícula do ouvinte são conferidos no serviço, que responde 422 com o campo (E1 do DS-FL09),
e não aqui, onde a validação responde 400.
"""

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.tcc import PessoaOut
from app.schemas.usuario import DataHora

# DS-FL09: "texto com 5 caracteres ou mais?"; 800 é o limite do campo no protótipo da TEL19.
TextoOcorrencia = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=800)]


class OcorrenciaEntrada(BaseModel):
    texto: TextoOcorrencia


class OuvinteEntrada(BaseModel):
    nome: str = Field(max_length=300)
    matricula: str = Field(max_length=100)


class MatriculaEntrada(BaseModel):
    matricula: str = Field(max_length=100)


class LoteEntrada(BaseModel):
    """Uma linha por ouvinte, no formato "nome; matrícula" (também aceita vírgula ou tabulação)."""

    linhas: list[Annotated[str, Field(max_length=500)]] = Field(max_length=500)


class DeclaracaoEntrada(BaseModel):
    ouvinte_id: int


class OcorrenciaOut(BaseModel):
    id: int
    texto: str
    autor: PessoaOut
    criado_em: DataHora
    alterada_em: DataHora | None


class DeclaracaoOut(BaseModel):
    id: int
    ouvinte_id: int
    versao: int
    gerado_em: DataHora


class OuvinteOut(BaseModel):
    id: int
    nome: str
    matricula: str | None
    pronto: bool  # matrícula completa: pode emitir a declaração
    declaracao: DeclaracaoOut | None


class LinhaComProblema(BaseModel):
    linha: int  # número da linha colada, a partir de 1
    texto: str
    motivo: str


class LoteOut(BaseModel):
    """DS-FL09, mensagem 18: {adicionados, linhas com problema[]}."""

    adicionados: list[OuvinteOut]
    linhas_com_problema: list[LinhaComProblema]


class PresencaOut(BaseModel):
    """DS-FL09, mensagem 6: {ocorrências[], ouvintes[]}, com o que a tela precisa para liberar a etapa."""

    defesa_id: int
    situacao: str
    liberada: bool  # a defesa já começou ou foi realizada (E1)
    pode_emitir: bool  # a defesa já terminou ou foi realizada (RN15)
    ocorrencias: list[OcorrenciaOut]
    ouvintes: list[OuvinteOut]
    prontos: int  # "x prontos para declaração"
