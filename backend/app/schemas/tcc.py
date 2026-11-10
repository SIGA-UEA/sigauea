"""Formato de entrada e saída do cadastro de TCC (Sprint S03).

Rotas e nomes seguem os diagramas de sequência DS-FL01 (formulário, rascunho,
submissão) e DS-FL03 (orientador responde, indicar orientador).
"""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints, field_validator, model_validator

from app.schemas.usuario import AreaOut, CursoOut, DataHora, Nome

Texto = Annotated[str, StringConstraints(strip_whitespace=True)]
Disciplina = Literal["TCC1", "TCC2"]
Modalidade = Literal["ARTIGO", "MONOGRAFIA"]
SituacaoEditorial = Literal["SUBMETIDO", "EM_REVISAO", "ACEITO", "RECUSADO", "PUBLICADO"]
SituacaoMatricula = Literal["MATRICULADO", "DESISTENTE", "APROVADO", "REPROVADO"]

MAX_PALAVRAS_RESUMO = 500
MAX_PALAVRAS_CHAVE = 10


# ---------------------------------------------------------------- turmas (RAN08)


class PeriodoCriar(BaseModel):
    codigo: Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{4}/[12]$")]
    inicio: date
    fim: date
    prazo_versao_final: date | None = None


class PeriodoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    inicio: date
    fim: date
    prazo_versao_final: date | None


class PessoaOut(BaseModel):
    id: int
    nome: str


class TurmaCriar(BaseModel):
    disciplina: Disciplina
    curso_id: int
    periodo_id: int
    professor_id: int


class TccDaTurma(BaseModel):
    """O TCC de um aluno, como aparece na turma (sem resumo nem histórico)."""

    id: int
    titulo: str
    situacao: str
    protocolo: str | None
    orientador: PessoaOut | None
    orientacao: str | None  # status do vínculo com o orientador (PENDENTE, ACEITA...)


class MatriculaOut(BaseModel):
    id: int
    aluno: PessoaOut
    matricula: str
    curso: CursoOut  # o curso do aluno, mesmo se diferente do da turma (RBN08.02)
    situacao: SituacaoMatricula
    incluido_em: DataHora
    tcc: TccDaTurma | None = None


class TurmaCartao(BaseModel):
    """Cartão de Minhas turmas: o professor vê as que conduz; o aluno, a sua."""

    id: int
    codigo: str
    disciplina: Disciplina
    curso: CursoOut
    periodo: str
    professor: PessoaOut
    encerrada: bool
    alunos: int
    com_tcc: int
    pendentes: int  # pedidos de orientação desta turma esperando a resposta de quem vê
    minha_matricula: SituacaoMatricula | None = None  # só para o aluno
    meu_tcc: TccDaTurma | None = None  # só para o aluno


class TurmaOut(BaseModel):
    id: int
    codigo: str
    disciplina: Disciplina
    curso: CursoOut
    periodo: PeriodoOut
    professor: PessoaOut
    encerrada: bool
    alunos: list[MatriculaOut]


class MatriculaCriar(BaseModel):
    aluno_id: int


class MatriculaAtualizar(BaseModel):
    situacao: SituacaoMatricula


# ---------------------------------------------------------------- TCC (RAN03)


class ArtigoEntrada(BaseModel):
    """Informações do artigo (RBN03.02). DOI só é obrigatório se publicado."""

    tipo_veiculo: Literal["PERIODICO", "CONGRESSO"]
    veiculo: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=200)]
    situacao: SituacaoEditorial
    doi: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] | None = None
    qualis: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2)] | None = None


class TccSalvar(BaseModel):
    """Rascunho (DS-FL01-B). Campos incompletos são aceitos: a checagem completa é na submissão."""

    model_config = ConfigDict(extra="forbid")

    titulo: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=300)]
    subtitulo: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = None
    resumo: Texto = ""
    palavras_chave: list[
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
    ] = []
    area_id: int
    modalidade: Modalidade
    orientador_id: int | None = None
    coorientador_id: int | None = None
    artigo: ArtigoEntrada | None = None

    @field_validator("resumo")
    @classmethod
    def _resumo_ate_500_palavras(cls, v: str) -> str:
        if len(v.split()) > MAX_PALAVRAS_RESUMO:
            raise ValueError(f"O resumo passa de {MAX_PALAVRAS_RESUMO} palavras.")
        return v

    @field_validator("palavras_chave")
    @classmethod
    def _ate_10_palavras(cls, v: list[str]) -> list[str]:
        if len(v) > MAX_PALAVRAS_CHAVE:
            raise ValueError(f"Use no máximo {MAX_PALAVRAS_CHAVE} palavras-chave.")
        if len({p.lower() for p in v}) != len(v):
            raise ValueError("Há palavras-chave repetidas.")
        return v


class VinculoOut(BaseModel):
    id: int
    professor: PessoaOut
    papel: Literal["ORIENTADOR", "COORIENTADOR"]
    status: Literal["PENDENTE", "ACEITA", "RECUSADA", "SUBSTITUIDA"]
    solicitado_em: DataHora
    respondido_em: DataHora | None
    motivo_recusa: str | None
    # Coorientador externo (RBN01.13): PENDENTE + externo = "Aguardando ativação" na tela.
    externo: bool = False
    instituicao: str | None = None
    # Fim do vínculo (DS-FL03-D mensagens 15 e 17): o histórico fica preservado (RN16).
    encerrado_em: DataHora | None = None
    justificativa_encerramento: str | None = None 


class ArtigoOut(BaseModel):
    tipo_veiculo: str
    veiculo: str
    situacao: SituacaoEditorial
    doi: str | None
    qualis: str | None


class HistoricoOut(BaseModel):
    situacao_anterior: str | None
    situacao_nova: str
    usuario: PessoaOut
    registrado_em: DataHora


class TurmaResumo(BaseModel):
    id: int
    codigo: str
    disciplina: Disciplina
    periodo: str
    professor: PessoaOut


class DecisaoOut(BaseModel):
    """Uma decisão da coordenação sobre o cadastro (DS-FL02 e DS-FL02-B)."""

    resultado: str
    parecer: str
    coordenador: PessoaOut
    decidido_em: DataHora


class TccOut(BaseModel):
    id: int
    protocolo: str | None
    situacao: str
    etapa: Disciplina
    modalidade: Modalidade
    titulo: str
    subtitulo: str | None
    resumo: str
    palavras_chave: list[str]
    area: AreaOut
    turma: TurmaResumo
    aluno: PessoaOut
    matricula: str
    curso: CursoOut
    orientador: VinculoOut | None
    coorientador: VinculoOut | None
    artigo: ArtigoOut | None
    submetido_em: DataHora | None
    criado_em: DataHora
    atualizado_em: DataHora
    # O que ainda falta para poder submeter (vazio = pode submeter).
    pendencias: list[str]
    historico: list[HistoricoOut]
    # Decisões da coordenação, da mais antiga para a mais nova (RBN04.05 CA-07).
    decisoes: list[DecisaoOut]


class SubmissaoOut(BaseModel):
    """Resposta do DS-FL01: protocolo, situação e se o aviso ao orientador ficou pendente."""

    protocolo: str
    situacao: str
    aviso_pendente: bool
    tcc: TccOut


class FormularioOut(BaseModel):
    """GET /tccs/formulario (DS-FL01-A)."""

    turma: TurmaResumo
    situacao_matricula: SituacaoMatricula
    tcc: TccOut | None  # cadastro em andamento no período, se houver
    origem: dict | None  # dados do TCC1 para pré-preencher o TCC2 (RBN08.04)
    orientadores: list[PessoaOut]
    coorientadores: list[PessoaOut]
    areas: list[AreaOut]


# ---------------------------------------------------------------- orientação (RAN06)


Instituicao = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)]


class CoorientadorExterno(BaseModel):
    """DS-FL03-D mensagem 2: nome, e-mail e instituição, todos obrigatórios (RBN06.02 CA-03, RN12)."""

    nome: Nome
    email: EmailStr
    instituicao: Instituicao


class IndicarOrientador(BaseModel):
    """O aluno indica um docente (professor_id). A coordenação e o orientador do TCC informam o coorientador:
    um docente da UEA (professor_id) ou um externo (DS-FL03-D, RBN01.13)."""

    professor_id: int | None = None
    externo: CoorientadorExterno | None = None
    papel: Literal["ORIENTADOR", "COORIENTADOR"] = "ORIENTADOR"

    @model_validator(mode="after")
    def _um_dos_dois(self):
        if (self.professor_id is None) == (self.externo is None):
            raise ValueError("Escolha um docente da UEA ou informe o coorientador externo.")
        return self


class EncerrarOrientacao(BaseModel):
    """DS-FL03-D mensagem 14: a justificativa do fim do vínculo (mensagem 15)."""

    justificativa: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)]


class RespostaOrientacao(BaseModel):
    decisao: Literal["ACEITAR", "RECUSAR"]
    motivo: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] | None = None


class SolicitacaoOut(BaseModel):
    """Uma solicitação de orientação, como o orientador vê (DS-FL03-A)."""

    id: int
    papel: str
    status: str
    solicitado_em: DataHora
    respondido_em: DataHora | None
    motivo_recusa: str | None
    tcc: TccOut


class SituacaoOut(BaseModel):
    status: str


# ---------------------------------------------------------------- análise do cadastro (RAN04)

ResultadoAnalise = Literal["APROVADO", "DEVOLVIDO", "REPROVADO"]


class CadastroResumo(BaseModel):
    """Um cadastro na fila ou na aba "Já analisados" (DS-FL02-A passos 3 e 14)."""

    id: int
    protocolo: str
    titulo: str
    aluno: PessoaOut
    matricula: str
    curso: CursoOut
    etapa: Disciplina
    modalidade: Modalidade
    periodo: str
    situacao: str
    submetido_em: DataHora | None
    dias_aguardando: int
    decisao: DecisaoOut | None  # a última decisão, se houver


class DocumentoOut(BaseModel):
    nome: str


class CadastroOut(BaseModel):
    """GET /cadastros/{id} (DS-FL02-A passos 7 a 10): dados, PDF e a última decisão."""

    tcc: TccOut
    documento: DocumentoOut | None  # PDF preliminar vigente; vazio quando o aluno ainda não enviou
    decisao: DecisaoOut | None


class DecisaoEntrada(BaseModel):
    """POST /cadastros/{id}/decisao (DS-FL02 passo 4). Parecer opcional só para aprovar."""

    resultado: ResultadoAnalise
    parecer: Annotated[str, StringConstraints(strip_whitespace=True, max_length=1000)] = ""
