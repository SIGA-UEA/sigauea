"""Formato de saída da consolidação da nota final (RBN09.11 · DS-FL06-B, dentro do DS-FL06).

GET /defesas/{id}/resultado devolve {pendentes[]} enquanto falta avaliação (DS-FL06, "[falta avaliação]") ou
{notas, média, regra de exceção, nota final} quando todas foram enviadas ("[todas enviadas]"). O ramo
"[resultado já confirmado]" e o POST da confirmação chegam com o SCRUM-70 (RBN09.12).

Média e nota final vão com duas casas, o mesmo valor em tela, ata e relatórios (CA-06 do RBN09.11).
"""

from typing import Literal

from pydantic import BaseModel

from app.schemas.tcc import PessoaOut

Papel = Literal["ORIENTADOR", "AVALIADOR", "SUPLENTE"]


class MembroPendenteOut(BaseModel):
    """Quem ainda não enviou a avaliação ("Aguardando avaliações. Faltam: ...")."""

    membro_id: int
    papel: Papel
    pessoa: PessoaOut


class NotaDoMembroOut(BaseModel):
    membro_id: int
    papel: Papel
    pessoa: PessoaOut
    nota: float  # nota total enviada pelo membro (RBN10.04), uma casa


class RegraExcecaoOut(BaseModel):
    """RN21: se a regra do artigo Qualis A ou B foi aplicada e o porquê, com a situação editorial e o Qualis
    considerados (A1 do RBN09.11)."""

    aplicada: bool
    porque: str
    modalidade: Literal["ARTIGO", "MONOGRAFIA"]
    situacao_editorial: str | None
    qualis: str | None


class NotaFinalOut(BaseModel):
    """DS-FL06-B, mensagem final: {média, nota final, regra aplicada e o porquê}."""

    notas: list[NotaDoMembroOut]
    media: float
    regra: RegraExcecaoOut
    nota_final: float


class ResultadoConsulta(BaseModel):
    defesa_id: int
    pendentes: list[MembroPendenteOut]
    consolidacao: NotaFinalOut | None  # só quando não há pendentes (RBN10.05, CA-05)
