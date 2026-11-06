"""Agenda de apresentações (S04 · RBN14.01 e RBN14.04, RN08): só dados que podem ser divulgados."""

from datetime import date, time

from pydantic import BaseModel

from app.schemas.defesa import Formato


class CursoAgenda(BaseModel):
    sigla: str
    nome: str


class ApresentacaoOut(BaseModel):
    """Sem matrícula, e-mail, PDF, nota nem banca (RN08, CA-04)."""

    id: int
    titulo: str
    autor: str
    orientador: str | None
    curso: CursoAgenda
    formato: Formato
    data: date
    inicio: time
    fim: time
    local: str | None
    link: str | None  # só quando a defesa autoriza divulgar o link (CA-05)
    remarcada: bool


class CondicaoOut(BaseModel):
    """Uma condição para publicar (RN09) e se já está atendida."""

    descricao: str
    atendida: bool


class DivulgacaoOut(BaseModel):
    """DS-FL05 mensagem 3: {condições, prévia, publicada}; pode_publicar falso = somente leitura (E2)."""

    defesa_id: int
    tcc_id: int
    situacao: str
    publicada: bool
    pode_publicar: bool
    condicoes: list[CondicaoOut]
    previa: ApresentacaoOut | None  # nula quando a defesa foi cancelada (E1)
