"""Formato de entrada e saída da banca e do agendamento da defesa (Sprint S04 · RAN09).

Rotas seguem os diagramas DS-FL04-A (GET /tccs/{id}/banca), DS-FL04 (POST /tccs/{id}/defesa e
GET /defesas/conflitos, RBN09.04) e a troca de membro depois da confirmação (CA-06 do RBN09.01). A banca é montada na tela e só
é gravada junto com a defesa, porque no modelo de dados todo membro pertence a uma defesa.
"""

from datetime import date, time
from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, StringConstraints, model_validator

from app.schemas.tcc import PessoaOut
from app.schemas.usuario import DataHora, Nome

PapelBanca = Literal["AVALIADOR", "ORIENTADOR", "COORIENTADOR", "SUPLENTE"]
Formato = Literal["PRESENCIAL", "REMOTO", "HIBRIDO"]
Instituicao = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)]
Link = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class ConvidadoExterno(BaseModel):
    """DS-FL04-B: nome, e-mail e instituição são obrigatórios (RN12, CA-03)."""

    nome: Nome
    email: EmailStr
    instituicao: Instituicao


class PessoaBanca(BaseModel):
    """Quem ocupa a vaga: um docente da UEA (usuario_id) ou um convidado externo."""

    usuario_id: int | None = None
    externo: ConvidadoExterno | None = None

    @model_validator(mode="after")
    def _um_dos_dois(self):
        if (self.usuario_id is None) == (self.externo is None):
            raise ValueError("Escolha um docente da UEA ou informe um convidado externo.")
        return self


class MembroEntrada(PessoaBanca):
    papel: PapelBanca


class ValidarMembro(BaseModel):
    """Confere uma vaga contra a banca que está sendo montada na tela, sem gravar nada."""

    membro: MembroEntrada
    banca: list[MembroEntrada] = []


class DefesaCriar(BaseModel):
    """DS-FL04 passo 16, com a banca montada na tela (opção 2)."""

    banca: list[MembroEntrada]
    formato: Formato
    data: date
    inicio: time
    fim: time
    local_id: int | None = None
    link: Link | None = None


class MembroOut(BaseModel):
    id: int | None  # nulo enquanto a vaga só existe na tela (resposta de /validar)
    papel: PapelBanca
    pessoa: PessoaOut
    email: str
    interno: bool
    instituicao: str | None
    convite_enviado_em: DataHora | None = None
    # RBN09.05: situação do último convite por e-mail desta vaga
    convite: Literal["NAO_ENVIADO", "PENDENTE", "ENVIADO", "FALHA"] = "NAO_ENVIADO"


class LocalOut(BaseModel):
    id: int
    nome: str
    descricao: str | None


class DefesaOut(BaseModel):
    id: int
    titulo: str  # RBN09.03 CA-01: a defesa herda o título e o autor do TCC
    autor: PessoaOut
    situacao: str
    formato: Formato
    data: date
    inicio: time
    fim: time
    local: LocalOut | None
    link: str | None
    publicada: bool
    responsavel: PessoaOut
    membros: list[MembroOut]
    criado_em: DataHora


class BancaOut(BaseModel):
    """DS-FL04-A passo 5: {vagas, membros, pode editar}."""

    tcc_id: int
    etapa: str
    liberada: bool  # E1: cadastro aprovado
    pode_editar: bool  # E2: quem compõe neste curso (RN14)
    orientador: PessoaOut | None  # vaga fixa: o orientador do TCC
    coorientador: PessoaOut | None  # vaga fixa e opcional: o coorientador do TCC
    docentes: list[PessoaOut]  # quem pode ser escolhido como avaliador ou suplente
    locais: list[LocalOut]
    defesa: DefesaOut | None


class ConflitoOut(BaseModel):
    """RBN09.04 CA-01/CA-02: quem ou que sala já está ocupada, e em que horário.

    Não mostra o título nem o aluno da outra defesa (RNF02): só o participante ou o local."""

    tipo: Literal["PARTICIPANTE", "LOCAL"]
    nome: str  # nome do membro da banca ou do local
    data: date
    inicio: time
    fim: time


class ConflitosOut(BaseModel):
    conflitos: list[ConflitoOut]
    # CA-06: o sistema só conhece as defesas registradas nele
    aviso: str = "Compromissos fora do SIGA UEA não são verificados."
