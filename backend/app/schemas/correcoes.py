"""Formato da aba Correções do TCC (TEL14 · RBN11.01 a RBN11.04 · DS-FL07).

GET /tccs/{id}/correcoes devolve tudo o que a aba mostra: o resultado vigente, o prazo da versão final, as
correções exigidas pela banca, a versão final enviada, o que ainda falta para concluir o TCC e o que quem
consulta pode fazer. As ações respondem com a mesma consulta, já atualizada.
"""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

from app.schemas.tcc import PessoaOut
from app.schemas.usuario import DataHora

Texto = Annotated[str, StringConstraints(strip_whitespace=True)]
SituacaoCorrecao = Literal["PENDENTE", "ATENDIDA", "APROVADA", "DEVOLVIDA"]


class CorrecaoEntrada(BaseModel):
    """DS-FL07-A mensagem 6: a exigência de um membro da banca."""

    descricao: Texto


class DecisaoCorrecao(BaseModel):
    """DS-FL07-B mensagens 5 e 8: aprovar, ou devolver com o que falta corrigir."""

    decisao: Literal["APROVAR", "DEVOLVER"]
    justificativa: Texto = ""


class PrazoEntrada(BaseModel):
    """DS-FL07-D mensagem 7: novo prazo da versão final com o motivo (RBN11.01 CA-05)."""

    prazo: date
    motivo: Texto = ""


class AtrasoEntrada(BaseModel):
    """DS-FL07-D mensagem 2: o professor responsável aceita ou recusa a entrega com atraso."""

    aceita: bool


class CorrecaoOut(BaseModel):
    id: int
    descricao: str
    avaliador: PessoaOut  # quem exigiu (RBN11.01 CA-03)
    papel: str  # papel do avaliador na banca
    situacao: SituacaoCorrecao
    justificativa: str | None  # o que falta, quando devolvida
    criada_em: DataHora
    atendida_em: DataHora | None
    decidida_por: PessoaOut | None
    decidida_em: DataHora | None


class VersaoFinalOut(BaseModel):
    id: int
    versao: int
    nome_arquivo: str
    tamanho_bytes: int
    sha256: str
    enviado_em: DataHora
    entregue_com_atraso: bool
    atraso_aceito: bool | None  # None: ainda sem decisão (ou sem atraso)


class PermissoesOut(BaseModel):
    """O que a tela mostra para quem consulta; a API confere tudo de novo em cada ação."""

    registrar: bool  # membro da banca que avalia (DS-FL07-A)
    marcar_atendida: bool  # aluno autor (DS-FL07)
    enviar_versao_final: bool  # aluno autor (DS-FL07)
    dar_anuencia: bool  # aluno autor, resultado com correções e anuência ainda não dada (RBN09.15)
    decidir: bool  # professor responsável pela turma (DS-FL07-B, RN24)
    alterar_prazo: bool  # professor responsável pela turma (DS-FL07-D)


class CorrecoesOut(BaseModel):
    tcc_id: int
    defesa_id: int | None
    resultado: str | None  # resultado vigente da defesa; None antes da confirmação
    situacao_tcc: str
    concluido_em: DataHora | None
    prazo: date | None  # data limite da versão final
    prazo_motivo: str | None  # motivo da última alteração do prazo
    anuencia_em: DataHora | None
    professor_responsavel: PessoaOut
    correcoes: list[CorrecaoOut]
    versao_final: VersaoFinalOut | None
    pendencias: list[str]  # o que falta para concluir o TCC (RBN11.04 CA-02); vazio depois de concluído
    permissoes: PermissoesOut
