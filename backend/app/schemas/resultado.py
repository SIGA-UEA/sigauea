"""Formato da consolidação e do resultado da defesa (RBN09.11 e RBN09.12 · DS-FL06, DS-FL06-B e DS-FL06-D).

GET /defesas/{id}/resultado devolve {pendentes[]} enquanto falta avaliação (DS-FL06, "[falta avaliação]"),
{notas, média, regra de exceção, nota final} quando todas foram enviadas ("[todas enviadas]") ou o resultado
vigente com as retificações ("[resultado já confirmado]"). POST /defesas/{id}/resultado confirma o resultado e
POST /defesas/{id}/resultado/retificacao o retifica.

Média e nota final vão com duas casas, o mesmo valor em tela, ata e relatórios (CA-06 do RBN09.11).
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.tcc import PessoaOut
from app.schemas.usuario import DataHora

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
    consolidacao: NotaFinalOut | None  # só quando não há pendentes (RBN10.05, CA-05) e ainda sem resultado
    resultado: "ResultadoOut | None" = None  # [resultado já confirmado] (A2 do RBN09.12)
    # o orientador confirma e retifica; os demais (aluno, banca e coordenação) só consultam (RBN09.13)
    pode_confirmar: bool = False


# =================================================================== RBN09.12 · confirmação e retificação

Resultado = Literal["APROVADO", "APROVADO_COM_CORRECOES", "REPROVADO"]


class ConfirmacaoEntrada(BaseModel):
    """DS-FL06 mensagem 7: o resultado escolhido e o parecer do orientador (CA-02). O parecer em branco é
    recusado no serviço, com 422 e o campo."""

    resultado: Resultado
    parecer: str = Field(max_length=2000)


class RetificacaoEntrada(BaseModel):
    """DS-FL06-D mensagem 2: o novo resultado e o motivo; motivo em branco é 422 no serviço (E5)."""

    resultado: Resultado
    motivo: str = Field(max_length=1000)


class RetificacaoOut(BaseModel):
    """Uma linha da lista de retificações: de, para, quem, quando e o motivo (RN13)."""

    de: Resultado
    para: Resultado
    motivo: str
    por: PessoaOut
    em: DataHora


class ResultadoOut(BaseModel):
    """Resultado vigente, bloqueado para edição direta (CA-06): só muda por retificação."""

    versao: int
    resultado: Resultado
    parecer: str
    media: float
    nota_final: float
    regra_qualis: bool
    confirmado_por: PessoaOut  # quem confirmou a primeira versão
    confirmado_em: DataHora
    retificacoes: list[RetificacaoOut]


ResultadoConsulta.model_rebuild()
