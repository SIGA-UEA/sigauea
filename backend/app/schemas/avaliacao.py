"""Formato de entrada e saída da avaliação da defesa (Sprint S04 · RBN10.02 a RBN10.05).

Rotas do diagrama DS-FL06-A: GET /defesas/{id}/avaliacao devolve {instrumento, minha avaliação, envios}
(passos 3 a 7), PUT /defesas/{id}/avaliacao recebe {conceitos, notas, parecer} (passo 12) e
POST /defesas/{id}/avaliacao/envio recebe {critérios[], parecer} (passo 17).
A nota ponderada e a nota total são sempre calculadas no servidor; valores mandados pela tela são
ignorados (RBN10.04, CA-05).
"""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.instrumento import Conceito, InstrumentoOut
from app.schemas.usuario import DataHora

# NUMERIC(3,1) no banco: de 0,0 a 10,0, com uma casa decimal. A faixa de cada conceito é conferida no serviço.
Nota = Annotated[Decimal, Field(ge=0, le=10, max_digits=3, decimal_places=1)]
Parecer = Annotated[str, StringConstraints(strip_whitespace=True)]


# ---------------------------------------------------------------- entrada (PUT e POST)


class CriterioAvaliado(BaseModel):
    """Um critério preenchido: o conceito escolhido e a nota dentro da faixa dele (RBN10.03)."""

    criterio_id: int
    conceito: Conceito
    nota: Nota


class AvaliacaoEntrada(BaseModel):
    """O estado atual da avaliação na tela. No rascunho podem faltar critérios e o parecer; no envio,
    todos os critérios e o parecer com pelo menos 20 caracteres (conferidos no serviço)."""

    criterios: list[CriterioAvaliado] = Field(default_factory=list)
    parecer: Parecer | None = None


# ---------------------------------------------------------------- saída (GET e respostas do PUT e do POST)


class CriterioAvaliadoOut(BaseModel):
    criterio_id: int
    conceito: Conceito
    nota: float
    nota_ponderada: float


class MinhaAvaliacaoOut(BaseModel):
    """A avaliação de quem pede (CA-02: ninguém vê a dos outros). A nota total só aparece quando todos os
    critérios estão preenchidos (RBN10.04, CA-06); pendentes são os critérios ainda sem conceito e nota."""

    id: int
    status: Literal["RASCUNHO", "ENVIADA"]
    parecer: str | None
    criterios: list[CriterioAvaliadoOut]
    pendentes: list[int]
    nota_total: float | None
    enviada_em: DataHora | None


class EnviosOut(BaseModel):
    """"Avaliações da banca: x de y enviadas" (DS-FL06-A passo 7): só a contagem, sem as notas."""

    enviadas: int
    esperadas: int


class AvaliacaoConsulta(BaseModel):
    """Resposta do GET (passos 3 a 7). envio_liberado diz se a defesa já foi realizada: antes disso a
    avaliação abre e salva rascunho, mas não é enviada (decisão da equipe, 07/11/2026)."""

    defesa_id: int
    envio_liberado: bool
    instrumento: InstrumentoOut
    minha_avaliacao: MinhaAvaliacaoOut | None
    envios: EnviosOut
