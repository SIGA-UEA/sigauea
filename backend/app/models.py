"""Tabelas do módulo de usuários e acesso (EP01).

Os nomes de tabelas e colunas seguem as fichas das histórias HU01.01 a HU01.08.
Usuário não tem exclusão física: é inativado; token e sessão expiram.
Só a área de interesse (RBN01.02) e a foto de perfil podem ser apagadas.
"""

from datetime import date, datetime

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    ForeignKey,
    Index,
    LargeBinary,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, agora

# Códigos dos perfis (RN07). Uma pessoa pode ter mais de um.
PERFIL_ALUNO = "aluno"
PERFIL_ORIENTADOR = "orientador"
PERFIL_PROFESSOR = "professor_disciplina"
PERFIL_COORDENADOR = "coordenador"
PERFIL_BANCA = "membro_banca"

PERFIS = {
    PERFIL_ALUNO: "Aluno",
    PERFIL_ORIENTADOR: "Orientador",
    PERFIL_PROFESSOR: "Professor da disciplina",
    PERFIL_COORDENADOR: "Coordenador",
    PERFIL_BANCA: "Membro da banca",
}
# Perfis que um docente pode receber (o perfil aluno vem do cadastro de aluno).
PERFIS_DOCENTE = [PERFIL_ORIENTADOR, PERFIL_PROFESSOR, PERFIL_COORDENADOR, PERFIL_BANCA]

TOKEN_ATIVACAO = "ativacao"
TOKEN_RECUPERACAO = "recuperacao"


def _fk(alvo: str, **kw) -> Mapped[int]:
    return mapped_column(ForeignKey(alvo, ondelete="RESTRICT"), **kw)


class Nucleo(Base):
    __tablename__ = "nucleo"

    id: Mapped[int] = mapped_column(primary_key=True)
    sigla: Mapped[str] = mapped_column(String(20), unique=True)
    nome: Mapped[str] = mapped_column(String(150))


class Curso(Base):
    __tablename__ = "curso"

    id: Mapped[int] = mapped_column(primary_key=True)
    sigla: Mapped[str] = mapped_column(String(10), unique=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True)
    nucleo_id: Mapped[int] = _fk("nucleo.id")


class AreaInteresse(Base):
    __tablename__ = "area_interesse"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True)


class Perfil(Base):
    __tablename__ = "perfil"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    nome: Mapped[str] = mapped_column(String(50))


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(254))
    telefone: Mapped[str | None] = mapped_column(String(20))
    # Nulo até a pessoa ativar a conta pelo link (HU01.05).
    senha_hash: Mapped[str | None] = mapped_column(String(60))
    # Só entra no sistema quem está ativo (HU01.06 R4).
    ativo: Mapped[bool] = mapped_column(default=False)
    # Preenchido quando a coordenação inativa o cadastro (HU01.08).
    inativado_em: Mapped[datetime | None]
    tentativas_falhas: Mapped[int] = mapped_column(default=0)
    bloqueado_ate: Mapped[datetime | None]
    criado_em: Mapped[datetime] = mapped_column(default=agora)

    vinculos_perfil: Mapped[list["UsuarioPerfil"]] = relationship(
        foreign_keys="UsuarioPerfil.usuario_id", back_populates="usuario"
    )
    docente: Mapped["Docente | None"] = relationship(back_populates="usuario")
    aluno: Mapped["Aluno | None"] = relationship(back_populates="usuario")
    notificacoes: Mapped[list["NotificacaoEmail"]] = relationship(
        order_by="NotificacaoEmail.id"
    )
    foto: Mapped["FotoUsuario | None"] = relationship(cascade="all, delete-orphan")

    @property
    def perfis(self) -> list[str]:
        return sorted(v.perfil.codigo for v in self.vinculos_perfil)

    @property
    def situacao(self) -> str:
        if self.inativado_em is not None:
            return "inativo"
        if self.senha_hash is None:
            return "aguardando_ativacao"
        return "ativo"


# Não aceita dois usuários com o mesmo e-mail, ignorando maiúsculas (HU01.01 R3).
Index("uq_usuario_email_lower", func.lower(Usuario.email), unique=True)


class UsuarioPerfil(Base):
    __tablename__ = "usuario_perfil"

    usuario_id: Mapped[int] = _fk("usuario.id", primary_key=True)
    perfil_id: Mapped[int] = _fk("perfil.id", primary_key=True)
    # Quem atribuiu o perfil. Nulo apenas na carga inicial.
    atribuido_por: Mapped[int | None] = _fk("usuario.id", nullable=True)
    atribuido_em: Mapped[datetime] = mapped_column(default=agora)

    usuario: Mapped[Usuario] = relationship(
        foreign_keys=[usuario_id], back_populates="vinculos_perfil"
    )
    perfil: Mapped[Perfil] = relationship()


class Docente(Base):
    __tablename__ = "docente"

    usuario_id: Mapped[int] = _fk("usuario.id", primary_key=True)
    cargo: Mapped[str] = mapped_column(String(20))  # coordenador, professor ou orientador
    nucleo_id: Mapped[int] = _fk("nucleo.id")
    # Nulo para coordenador, que acessa todos os cursos do núcleo (HU01.01 R5).
    curso_id: Mapped[int | None] = _fk("curso.id", nullable=True)

    usuario: Mapped[Usuario] = relationship(back_populates="docente")
    curso: Mapped[Curso | None] = relationship()
    areas: Mapped[list[AreaInteresse]] = relationship(
        secondary="docente_area", order_by="AreaInteresse.nome"
    )


class DocenteArea(Base):
    __tablename__ = "docente_area"

    docente_id: Mapped[int] = _fk("docente.usuario_id", primary_key=True)
    area_id: Mapped[int] = _fk("area_interesse.id", primary_key=True)


class Aluno(Base):
    __tablename__ = "aluno"

    usuario_id: Mapped[int] = _fk("usuario.id", primary_key=True)
    matricula: Mapped[str] = mapped_column(String(20), unique=True)
    curso_id: Mapped[int] = _fk("curso.id")

    usuario: Mapped[Usuario] = relationship(back_populates="aluno")
    curso: Mapped[Curso] = relationship()


class FotoUsuario(Base):
    """Foto de perfil (opcional). Fica no banco para a hospedagem não depender de disco."""

    __tablename__ = "foto_usuario"

    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuario.id", ondelete="CASCADE"), primary_key=True
    )
    tipo: Mapped[str] = mapped_column(String(20))  # image/jpeg, image/png ou image/webp
    # deferred: listar usuários não carrega os bytes da imagem.
    conteudo: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    sha256: Mapped[str] = mapped_column(CHAR(64))  # RNF06
    atualizado_em: Mapped[datetime] = mapped_column(default=agora)


class TokenUsuario(Base):
    """Link de ativação ou de recuperação. Só o hash do token é gravado."""

    __tablename__ = "token_usuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = _fk("usuario.id", index=True)
    tipo: Mapped[str] = mapped_column(String(20))
    token_hash: Mapped[str] = mapped_column(CHAR(64), unique=True)
    expira_em: Mapped[datetime]
    usado_em: Mapped[datetime | None]
    criado_em: Mapped[datetime] = mapped_column(default=agora)

    usuario: Mapped[Usuario] = relationship()


class NotificacaoEmail(Base):
    """Fila de e-mails. O texto do e-mail não é gravado porque contém o link."""

    __tablename__ = "notificacao_email"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = _fk("usuario.id", index=True)
    tipo: Mapped[str] = mapped_column(String(30))
    destinatario: Mapped[str] = mapped_column(String(254))
    status: Mapped[str] = mapped_column(String(10), default="pendente")  # pendente, enviado, falha
    tentativas: Mapped[int] = mapped_column(default=0)
    erro: Mapped[str | None] = mapped_column(Text)
    # A que o e-mail se refere (ex.: entidade="tcc", entidade_id=12). Nulo nos e-mails de conta.
    entidade: Mapped[str | None] = mapped_column(String(40))
    entidade_id: Mapped[int | None]
    criado_em: Mapped[datetime] = mapped_column(default=agora)
    enviado_em: Mapped[datetime | None]


class Sessao(Base):
    """Sessão de login. Cada requisição autenticada empurra expira_em para frente."""

    __tablename__ = "sessao"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = _fk("usuario.id", index=True)
    token_hash: Mapped[str] = mapped_column(CHAR(64), unique=True)
    expira_em: Mapped[datetime]
    criado_em: Mapped[datetime] = mapped_column(default=agora)

    usuario: Mapped[Usuario] = relationship()


class LogAuditoria(Base):
    """RNF03: quem fez, quando, em qual campo, valor anterior e valor novo."""

    __tablename__ = "log_auditoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Quem fez a ação. Nulo quando não há usuário identificado (ex.: login com e-mail inexistente).
    usuario_id: Mapped[int | None] = _fk("usuario.id", nullable=True, index=True)
    acao: Mapped[str] = mapped_column(String(40))
    entidade: Mapped[str] = mapped_column(String(40))
    entidade_id: Mapped[int | None]
    campo: Mapped[str | None] = mapped_column(String(40))
    valor_anterior: Mapped[str | None] = mapped_column(Text)
    valor_novo: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(default=agora, index=True)


# =====================================================================
# MOD03 · Cadastro e acompanhamento do TCC (Sprint S03)
# Nomes iguais aos do modelo lógico (Documento do Modelo de Dados) e às entidades dos
# diagramas de sequência FL01 e FL03 (MatriculaTurma, TCC, Orientacao...).
# =====================================================================

DISCIPLINAS = ("TCC1", "TCC2")
MATRICULADO = "MATRICULADO"
SITUACOES_MATRICULA = (MATRICULADO, "DESISTENTE", "APROVADO", "REPROVADO")
MODALIDADES = ("ARTIGO", "MONOGRAFIA")

# Situações acadêmicas do cadastro (RN10)
RASCUNHO, EM_ANALISE, DEVOLVIDO = "RASCUNHO", "EM_ANALISE", "DEVOLVIDO"
SITUACOES_TCC = (RASCUNHO, EM_ANALISE, "APROVADO", DEVOLVIDO, "REPROVADO", "CONCLUIDO", "DESISTENCIA")

PAPEL_ORIENTADOR, PAPEL_COORIENTADOR = "ORIENTADOR", "COORIENTADOR"
PENDENTE, ACEITA, RECUSADA = "PENDENTE", "ACEITA", "RECUSADA"
STATUS_ORIENTACAO = (PENDENTE, ACEITA, RECUSADA, "SUBSTITUIDA")

# Situações editoriais do artigo (RN03), separadas da situação acadêmica
SITUACOES_EDITORIAIS = ("SUBMETIDO", "EM_REVISAO", "ACEITO", "RECUSADO", "PUBLICADO")
TIPOS_VEICULO = ("PERIODICO", "CONGRESSO")


def _dominio(tabela: str, coluna: str, valores) -> CheckConstraint:
    lista = ", ".join(f"'{v}'" for v in valores)
    return CheckConstraint(f"{coluna} IN ({lista})", name=f"ck_{tabela}_{coluna}")


class PeriodoLetivo(Base):
    __tablename__ = "periodo_letivo"
    __table_args__ = (CheckConstraint("fim > inicio", name="ck_periodo_letivo_datas"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(6), unique=True)  # AAAA/N, ex.: 2026/2
    inicio: Mapped[date]
    fim: Mapped[date]
    prazo_versao_final: Mapped[date | None]


class Turma(Base):
    __tablename__ = "turma"
    __table_args__ = (
        UniqueConstraint("curso_id", "disciplina", "periodo_id", "professor_id", name="uq_turma"),
        _dominio("turma", "disciplina", DISCIPLINAS),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True)
    disciplina: Mapped[str] = mapped_column(String(4))
    curso_id: Mapped[int] = _fk("curso.id")
    periodo_id: Mapped[int] = _fk("periodo_letivo.id")
    # No TCC1 é o professor da disciplina; no TCC2, o orientador (RN26).
    professor_id: Mapped[int] = _fk("docente.usuario_id")
    encerrada_em: Mapped[datetime | None]
    criado_em: Mapped[datetime] = mapped_column(default=agora)

    curso: Mapped[Curso] = relationship()
    periodo: Mapped[PeriodoLetivo] = relationship()
    professor: Mapped[Docente] = relationship()
    matriculas: Mapped[list["MatriculaTurma"]] = relationship(
        back_populates="turma", order_by="MatriculaTurma.id"
    )
    # Só leitura: os TCCs cadastrados pelos alunos desta turma (Minhas turmas).
    tccs: Mapped[list["Tcc"]] = relationship(viewonly=True)


class MatriculaTurma(Base):
    __tablename__ = "matricula_turma"
    __table_args__ = (
        UniqueConstraint("turma_id", "aluno_id", name="uq_matricula_turma"),
        _dominio("matricula_turma", "situacao", SITUACOES_MATRICULA),
        CheckConstraint("nota_final IS NULL OR nota_final BETWEEN 0 AND 10", name="ck_matricula_turma_nota"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    turma_id: Mapped[int] = _fk("turma.id", index=True)
    aluno_id: Mapped[int] = _fk("aluno.usuario_id", index=True)
    situacao: Mapped[str] = mapped_column(String(12), default=MATRICULADO)
    nota_final: Mapped[float | None] = mapped_column(Numeric(3, 1))
    incluido_por: Mapped[int] = _fk("usuario.id")
    incluido_em: Mapped[datetime] = mapped_column(default=agora)
    situacao_alterada_em: Mapped[datetime | None]

    turma: Mapped[Turma] = relationship(back_populates="matriculas")
    aluno: Mapped[Aluno] = relationship()


class Tcc(Base):
    __tablename__ = "tcc"
    __table_args__ = (
        # RN04: um aluno não mantém dois cadastros no mesmo período letivo.
        UniqueConstraint("aluno_id", "periodo_id", name="uq_tcc_aluno_periodo"),
        _dominio("tcc", "etapa", DISCIPLINAS),
        _dominio("tcc", "modalidade", MODALIDADES),
        _dominio("tcc", "situacao", SITUACOES_TCC),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    aluno_id: Mapped[int] = _fk("aluno.usuario_id", index=True)
    turma_id: Mapped[int] = _fk("turma.id")
    periodo_id: Mapped[int] = _fk("periodo_letivo.id")
    etapa: Mapped[str] = mapped_column(String(4))
    modalidade: Mapped[str] = mapped_column(String(10))
    titulo: Mapped[str] = mapped_column(String(300))
    subtitulo: Mapped[str | None] = mapped_column(String(300))
    resumo: Mapped[str] = mapped_column(Text)
    area_id: Mapped[int] = _fk("area_interesse.id")
    situacao: Mapped[str] = mapped_column(String(12), default=RASCUNHO)
    # Só existe depois da primeira submissão (RBN03.04); único no banco (RNF06).
    protocolo: Mapped[str | None] = mapped_column(String(20), unique=True)
    submetido_em: Mapped[datetime | None]
    concluido_em: Mapped[datetime | None]
    desistencia_motivo: Mapped[str | None] = mapped_column(Text)
    tcc_origem_id: Mapped[int | None] = _fk("tcc.id", nullable=True)  # TCC1 que originou o TCC2
    criado_em: Mapped[datetime] = mapped_column(default=agora)
    atualizado_em: Mapped[datetime] = mapped_column(default=agora)

    aluno: Mapped[Aluno] = relationship()
    turma: Mapped[Turma] = relationship()
    periodo: Mapped[PeriodoLetivo] = relationship()
    area: Mapped[AreaInteresse] = relationship()
    palavras: Mapped[list["TccPalavraChave"]] = relationship(
        order_by="TccPalavraChave.ordem", cascade="all, delete-orphan"
    )
    orientacoes: Mapped[list["Orientacao"]] = relationship(back_populates="tcc", order_by="Orientacao.id")
    historico: Mapped[list["HistoricoSituacao"]] = relationship(order_by="HistoricoSituacao.id")
    publicacoes: Mapped[list["PublicacaoArtigo"]] = relationship(order_by="PublicacaoArtigo.id")


class TccPalavraChave(Base):
    __tablename__ = "tcc_palavra_chave"
    __table_args__ = (CheckConstraint("ordem BETWEEN 1 AND 10", name="ck_tcc_palavra_chave_ordem"),)

    tcc_id: Mapped[int] = _fk("tcc.id", primary_key=True)
    ordem: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    palavra: Mapped[str] = mapped_column(String(60))


class HistoricoSituacao(Base):
    __tablename__ = "historico_situacao"

    id: Mapped[int] = mapped_column(primary_key=True)
    tcc_id: Mapped[int] = _fk("tcc.id", index=True)
    situacao_anterior: Mapped[str | None] = mapped_column(String(12))
    situacao_nova: Mapped[str] = mapped_column(String(12))
    usuario_id: Mapped[int] = _fk("usuario.id")
    observacao: Mapped[str | None] = mapped_column(Text)
    registrado_em: Mapped[datetime] = mapped_column(default=agora)

    usuario: Mapped[Usuario] = relationship()


class Orientacao(Base):
    """Vínculo de orientação ou coorientação (RN16). A orientação só vale depois do aceite."""

    __tablename__ = "orientacao"
    __table_args__ = (
        _dominio("orientacao", "papel", (PAPEL_ORIENTADOR, PAPEL_COORIENTADOR)),
        _dominio("orientacao", "status", STATUS_ORIENTACAO),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tcc_id: Mapped[int] = _fk("tcc.id", index=True)
    professor_id: Mapped[int] = _fk("usuario.id", index=True)
    papel: Mapped[str] = mapped_column(String(12))
    status: Mapped[str] = mapped_column(String(12), default=PENDENTE)
    solicitado_em: Mapped[datetime] = mapped_column(default=agora)
    respondido_em: Mapped[datetime | None]
    motivo_recusa: Mapped[str | None] = mapped_column(Text)
    encerrado_em: Mapped[datetime | None]
    justificativa_encerramento: Mapped[str | None] = mapped_column(Text)

    tcc: Mapped[Tcc] = relationship(back_populates="orientacoes")
    professor: Mapped[Usuario] = relationship()


class PublicacaoArtigo(Base):
    """Informações do artigo informadas no cadastro (RBN03.02); acompanhadas no MOD05."""

    __tablename__ = "publicacao_artigo"
    __table_args__ = (
        _dominio("publicacao_artigo", "tipo_veiculo", TIPOS_VEICULO),
        _dominio("publicacao_artigo", "situacao_atual", SITUACOES_EDITORIAIS),
        CheckConstraint(
            "situacao_atual <> 'PUBLICADO' OR doi IS NOT NULL", name="ck_publicacao_artigo_doi"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tcc_id: Mapped[int] = _fk("tcc.id", index=True)
    tipo_veiculo: Mapped[str] = mapped_column(String(10))
    veiculo: Mapped[str] = mapped_column(String(200))
    qualis: Mapped[str | None] = mapped_column(String(2))
    doi: Mapped[str | None] = mapped_column(String(200))
    situacao_atual: Mapped[str] = mapped_column(String(12))
    criado_em: Mapped[datetime] = mapped_column(default=agora)


class HistoricoPublicacao(Base):
    __tablename__ = "historico_publicacao"
    __table_args__ = (_dominio("historico_publicacao", "situacao", SITUACOES_EDITORIAIS),)

    id: Mapped[int] = mapped_column(primary_key=True)
    publicacao_id: Mapped[int] = _fk("publicacao_artigo.id", index=True)
    situacao: Mapped[str] = mapped_column(String(12))
    data: Mapped[date]
    usuario_id: Mapped[int | None] = _fk("usuario.id", nullable=True)  # nulo = sistema
    registrado_em: Mapped[datetime] = mapped_column(default=agora)
