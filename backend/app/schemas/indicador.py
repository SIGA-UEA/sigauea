"""Formato dos indicadores gerenciais (RBN13.01 a RBN13.06 · DS-FL08-C, DS-FL08-D, TEL16).

- GET /indicadores/escopo: escopo e filtros do perfil (DS-FL08-D mensagens 2 e 3);
- GET /indicadores/situacao: situação dos TCCs e orientações, por etapa (mensagens 5 a 7);
- GET /indicadores/desistencias: desistências e evolução (mensagens 9 a 11);
- GET /indicadores/bancas: participações em banca (mensagens 13 a 15);
- GET /indicadores: o painel do DS-FL08-C (situação, produção científica e bancas);
- POST /indicadores/relatorio {filtros}: o relatório em PDF (RBN13.06, DS-FL08-D).
Cada indicador tem os seus filtros por perfil (fichas RBN13.02 a RBN13.05), em `filtros_indicadores`. Nenhuma
resposta traz nome de aluno (RN18, CA-05 do RBN13.01): só números, cursos, turmas e o nome dos docentes.
"""

from typing import Literal

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


class FiltrosDoIndicador(BaseModel):
    """Filtros de um indicador para o perfil (somados, para quem tem mais de um). `intervalo` é o intervalo de
    períodos da evolução das desistências (RBN13.04, só coordenação)."""

    periodo: bool
    curso: bool = False
    etapa: bool = False
    turma: bool = False
    orientador: bool = False
    intervalo: bool = False
    professor: bool = False
    papel: bool = False


class FiltrosIndicadoresOut(BaseModel):
    """Os filtros de cada indicador, como estão nas fichas (CA-04 do RBN13.02 e do RBN13.03, CA-05 do RBN13.04,
    CA-03 e CA-04 do RBN13.05)."""

    situacao: FiltrosDoIndicador
    producao: FiltrosDoIndicador
    desistencias: FiltrosDoIndicador
    bancas: FiltrosDoIndicador


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
    filtros_indicadores: FiltrosIndicadoresOut
    professores: list[PessoaOut]  # filtro "professor" das bancas (só coordenação): docentes do núcleo


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


# =================================================================== SCRUM-90 · RBN13.03 produção científica


class SituacaoEditorialOut(BaseModel):
    situacao: str  # SUBMETIDO, EM_REVISAO, ACEITO, PUBLICADO e RECUSADO (D3: pendente de decisão do PO)
    total: int


class ProducaoOut(BaseModel):
    """DS-FL08-C mensagem 5 (contarPorSituacao em PublicacaoArtigo): artigos por situação editorial."""

    periodo_id: int | None
    total: int  # TCCs de artigo com publicação registrada, cada um contado uma vez (RN18)
    situacoes: list[SituacaoEditorialOut]
    sem_dados: bool


# =================================================================== SCRUM-91 · RBN13.04 desistências


class DesistenciasCursoOut(BaseModel):
    curso: CursoOut
    total: int


class EvolucaoOut(BaseModel):
    periodo: PeriodoOut
    total: int


class DesistenciasOut(BaseModel):
    """DS-FL08-D mensagens 9 a 11: total por período e curso; a evolução só vem para a coordenação."""

    periodo_id: int | None
    total: int
    por_curso: list[DesistenciasCursoOut]
    evolucao: list[EvolucaoOut] | None  # None para professor e orientador (alt do diagrama, CA-03)
    sem_dados: bool


# =================================================================== SCRUM-92 · RBN13.05 participações em banca


class PorPapel(BaseModel):
    """Os quatro papéis da banca (CA-01); o suplente só conta se foi convocado (RN20)."""

    ORIENTADOR: int
    AVALIADOR: int
    COORIENTADOR: int
    SUPLENTE: int


class ParticipacoesOut(BaseModel):
    professor: PessoaOut
    total: PorPapel


class BancasOut(BaseModel):
    """DS-FL08-D mensagens 13 a 15: participações por professor e por papel."""

    periodo_id: int | None
    total: PorPapel
    professores: list[ParticipacoesOut]
    sem_dados: bool


# =================================================================== DS-FL08-C · painel


class IndicadoresOut(BaseModel):
    """DS-FL08-C mensagem 6: {totais, situação acadêmica, produção, bancas} (consultarIndicadores)."""

    periodo_id: int | None
    situacao: IndicadorSituacaoOut
    producao: ProducaoOut
    bancas: BancasOut


class FiltrosRelatorio(BaseModel):
    """Os filtros escolhidos na TEL16 para o relatório em PDF (RBN13.06). Cada indicador usa só os que tem."""

    periodo: int | None = None
    curso: int | None = None
    etapa: Literal["TCC1", "TCC2"] | None = None
    turma: int | None = None
    orientador: int | None = None
    professor: int | None = None
    papel: Literal["ORIENTADOR", "AVALIADOR", "COORIENTADOR", "SUPLENTE"] | None = None
    periodo_inicio: int | None = None
    periodo_fim: int | None = None
