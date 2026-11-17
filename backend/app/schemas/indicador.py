"""Formato dos indicadores gerenciais (RBN13.01 e RBN13.02 · DS-FL08-D, TEL16).

GET /indicadores/escopo devolve o escopo e os filtros do perfil (mensagens 2 e 3); GET /indicadores/situacao
devolve a situação dos TCCs e as orientações, por etapa (mensagens 5 a 7). Nenhuma resposta traz nome de aluno
(RN18, CA-05 do RBN13.01): só números, cursos, turmas e o nome dos orientadores.
"""

from pydantic import BaseModel

from app.schemas.tcc import PessoaOut


class PeriodoOut(BaseModel):
    id: int
    codigo: str
    vigente: bool


class CursoOut(BaseModel):
    id: int
    sigla: str
    nome: str


class TurmaOpcaoOut(BaseModel):
    id: int
    codigo: str


class FiltrosOut(BaseModel):
    """Quais filtros o perfil usa (CA-04 do RBN13.02). Quem tem mais de um perfil tem a soma deles."""

    periodo: bool
    curso: bool
    etapa: bool
    turma: bool
    orientador: bool


class EscopoOut(BaseModel):
    """DS-FL08-D mensagem 3: escopo e filtros do perfil."""

    perfis: list[str]  # coordenacao, professor_disciplina, orientador (os que dão escopo)
    descricao: list[tuple[str, str]]  # chips da tela: ("Coordenação", "todos os cursos do núcleo")
    periodo_vigente_id: int | None
    filtros: FiltrosOut
    periodos: list[PeriodoOut]
    cursos: list[CursoOut]
    turmas: list[TurmaOpcaoOut]
    orientadores: list[PessoaOut]


class PorEtapa(BaseModel):
    """TCC1 e TCC2 separados, nunca somados (CA-01 e CA-03 do RBN13.02)."""

    TCC1: int
    TCC2: int


class SituacaoOut(BaseModel):
    situacao: str
    total: PorEtapa


class OrientacoesOut(BaseModel):
    orientador: PessoaOut
    total: PorEtapa


class IndicadorSituacaoOut(BaseModel):
    """DS-FL08-D mensagens 5 a 7: totais por situação acadêmica e orientandos por orientador, por etapa."""

    periodo_id: int | None
    total: PorEtapa  # TCCs no escopo, cada um contado uma vez (RN18)
    situacoes: list[SituacaoOut]
    orientacoes: list[OrientacoesOut]
    sem_dados: bool  # "Sem dados para este filtro" (CA-07)
