"""Formato de entrada e saída do instrumento de avaliação (Sprint S04 · RBN10.01).

Rotas do diagrama DS-FL06-G: GET /instrumento-avaliacao devolve {instrumento, versões} (passos 2 a 4)
e PUT /instrumento-avaliacao recebe {componentes, critérios, pesos, conceitos} (passo 6).
Os componentes (parte escrita 7,0 e parte oral 3,0) e as faixas dos conceitos são fixos; a
coordenação altera critérios, pesos e textos dos conceitos (passo 5).
"""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.tcc import PessoaOut
from app.schemas.usuario import DataHora

Conceito = Literal["EXEMPLAR", "COMPETENTE", "NECESSITA"]
NomeCriterio = Annotated[str, StringConstraints(
    strip_whitespace=True, min_length=1, max_length=120)]
TextoConceito = Annotated[str, StringConstraints(
    strip_whitespace=True, min_length=1)]
# NUMERIC(4,2) no banco: até duas casas decimais e maior que zero
Peso = Annotated[Decimal, Field(gt=0, max_digits=4, decimal_places=2)]


# ---------------------------------------------------------------- saída (GET e resposta do PUT)


class FaixaOut(BaseModel):
    """Faixa de nota de cada conceito (RBN10.03): Exemplar 8,0–10,0; Competente 6,0–7,9;
    Necessita de Trabalho 0,0–5,9."""

    conceito: Conceito
    rotulo: str
    minimo: float
    maximo: float


class CriterioOut(BaseModel):
    id: int
    nome: str
    peso: float
    texto_exemplar: str
    texto_competente: str
    texto_necessita: str
    ordem: int


class ComponenteOut(BaseModel):
    id: int
    nome: str
    pontos: float
    ordem: int
    criterios: list[CriterioOut]


class InstrumentoOut(BaseModel):
    id: int
    versao: int
    vigente: bool
    criado_em: DataHora
    autor: PessoaOut
    componentes: list[ComponenteOut]
    conceitos: list[FaixaOut]


class VersaoOut(BaseModel):
    """Uma linha do histórico de versões, com data e autor (CA-05)."""

    id: int
    versao: int
    vigente: bool
    criado_em: DataHora
    autor: PessoaOut


class InstrumentoConsulta(BaseModel):
    """Resposta do GET: o instrumento vigente e o histórico (DS-FL06-G, retorno do passo 2)."""

    instrumento: InstrumentoOut
    versoes: list[VersaoOut]


# ---------------------------------------------------------------- entrada (PUT)


class CriterioEntrada(BaseModel):
    nome: NomeCriterio
    peso: Peso
    texto_exemplar: TextoConceito
    texto_competente: TextoConceito
    texto_necessita: TextoConceito


class ComponenteEntrada(BaseModel):
    """O componente é identificado pelo id que veio no GET; os critérios vêm na ordem da tela."""

    id: int
    criterios: list[CriterioEntrada] = Field(min_length=1)


class InstrumentoEntrada(BaseModel):
    """DS-FL06-G passo 6: {componentes, critérios, pesos, conceitos}. Os dois componentes vêm juntos."""

    componentes: list[ComponenteEntrada] = Field(min_length=2, max_length=2)
