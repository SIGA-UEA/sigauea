"""Tabelas do módulo de usuários e acesso (EP01).

Os nomes de tabelas e colunas seguem as fichas das histórias HU01.01 a HU01.08.
Usuário não tem exclusão física: é inativado; token e sessão expiram.
Só a área de interesse (RBN01.02) e a foto de perfil podem ser apagadas.
"""

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    JSON,
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
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
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
    analises: Mapped[list["AnaliseCadastro"]] = relationship(order_by="AnaliseCadastro.id")
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


# Resultados da análise do cadastro pela coordenação (RBN04.02 a RBN04.04, RN10)
RESULTADOS_ANALISE = ("APROVADO", DEVOLVIDO, "REPROVADO")


class AnaliseCadastro(Base):
    """Decisão da coordenação sobre o cadastro (DS-FL02). Cada decisão é uma linha nova: o histórico fica todo."""

    __tablename__ = "analise_cadastro"
    __table_args__ = (
        _dominio("analise_cadastro", "resultado", RESULTADOS_ANALISE),
        # Devolver e reprovar exigem parecer (RBN04.03 CA-02, RBN04.04 CA-02)
        CheckConstraint(
            "resultado = 'APROVADO' OR length(trim(parecer)) > 0", name="ck_analise_cadastro_parecer"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tcc_id: Mapped[int] = _fk("tcc.id", index=True)
    coordenador_id: Mapped[int] = _fk("docente.usuario_id", index=True)
    resultado: Mapped[str] = mapped_column(String(10))
    parecer: Mapped[str] = mapped_column(Text)
    decidido_em: Mapped[datetime] = mapped_column(default=agora)

    coordenador: Mapped[Docente] = relationship()


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


# =====================================================================
# Defesa e banca (Sprint S04 · RAN09, RBN09.01 a RBN09.09)
# Nomes iguais aos do modelo lógico e às entidades do diagrama FL04 (Defesa, BancaMembro...).
# =====================================================================

FORMATOS_DEFESA = ("PRESENCIAL", "REMOTO", "HIBRIDO")
CONFIRMADA, REMARCADA, CANCELADA = "CONFIRMADA", "REMARCADA", "CANCELADA"
SITUACOES_DEFESA = (CONFIRMADA, REMARCADA, CANCELADA, "REALIZADA")

PAPEL_AVALIADOR, PAPEL_SUPLENTE = "AVALIADOR", "SUPLENTE"
PAPEIS_BANCA = (PAPEL_AVALIADOR, PAPEL_ORIENTADOR, PAPEL_COORIENTADOR, PAPEL_SUPLENTE)
# BANCA_ALTERADA: troca de um membro antes da defesa (CA-06 do RBN09.01), com a pessoa anterior
# em valores_anteriores. Não está no SQL físico entregue; ver CR da S04.
# PUBLICACAO e RETIRADA: publicar e retirar da agenda (DS-FL05 mensagens 10 e 16); também fora do SQL físico.
EVENTOS_DEFESA = (
    "AGENDAMENTO", "REMARCACAO", "CANCELAMENTO", "SUPLENTE_CONVOCADO", "BANCA_ALTERADA", "PUBLICACAO", "RETIRADA",
)


class UsuarioExterno(Base):
    """Pessoa de fora da UEA (RN12): membro externo da banca ou coorientador externo. Guarda só a
+    instituição; o que a pessoa pode acessar fica em AcessoLimitado (RBN01.12 e RBN01.13)."""

    __tablename__ = "usuario_externo"

    usuario_id: Mapped[int] = _fk("usuario.id", primary_key=True)
    instituicao: Mapped[str] = mapped_column(String(150))

    usuario: Mapped[Usuario] = relationship()


# Escopo da conta limitada (RBN01.12 e RBN01.13): a banca de uma defesa ou a coorientação de um TCC.
ESCOPO_BANCA, ESCOPO_COORIENTACAO = "BANCA", "COORIENTACAO"
ESCOPOS_ACESSO = (ESCOPO_BANCA, ESCOPO_COORIENTACAO)


class AcessoLimitado(Base):
    """O que a pessoa externa pode acessar (DS-FL04-B mensagem 8 e DS-FL03-D mensagem 6), igual à tabela
    acesso_limitado do modelo físico: escopo BANCA aponta para a defesa; COORIENTACAO, para o TCC.

    expira_em fica vazio até a confirmação do resultado da defesa (7 dias depois dela, RBN01.12 CA-03);
    revogado_em marca o fim antes do prazo (defesa cancelada, membro trocado, vínculo encerrado)."""

    __tablename__ = "acesso_limitado"
    __table_args__ = (
        _dominio("acesso_limitado", "escopo", ESCOPOS_ACESSO),
        CheckConstraint(
            "(escopo = 'BANCA' AND defesa_id IS NOT NULL) OR (escopo = 'COORIENTACAO' AND tcc_id IS NOT NULL)",
            name="ck_acesso_limitado_alvo",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = _fk("usuario.id", index=True)
    escopo: Mapped[str] = mapped_column(String(20))
    defesa_id: Mapped[int | None] = _fk("defesa.id", nullable=True, index=True)
    tcc_id: Mapped[int | None] = _fk("tcc.id", nullable=True, index=True)
    expira_em: Mapped[datetime | None]
    revogado_em: Mapped[datetime | None]
    criado_em: Mapped[datetime] = mapped_column(default=agora)

    usuario: Mapped[Usuario] = relationship()


class LocalDefesa(Base):
    __tablename__ = "local_defesa"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True)
    descricao: Mapped[str | None] = mapped_column(String(200))


class Defesa(Base):
    __tablename__ = "defesa"
    __table_args__ = (
        _dominio("defesa", "formato", FORMATOS_DEFESA),
        _dominio("defesa", "situacao", SITUACOES_DEFESA),
        CheckConstraint("fim > inicio", name="ck_defesa_horario"),
        # RN14: presencial pede local, remoto pede link, híbrido pede os dois.
        CheckConstraint(
            "(formato = 'PRESENCIAL' AND local_id IS NOT NULL)"
            " OR (formato = 'REMOTO' AND link IS NOT NULL)"
            " OR (formato = 'HIBRIDO' AND local_id IS NOT NULL AND link IS NOT NULL)",
            name="ck_defesa_formato_destino",
        ),
        # Uma defesa vigente por TCC, mesmo com dois pedidos ao mesmo tempo; as canceladas
        # ficam de fora para o TCC poder ser agendado de novo. Não está no SQL físico entregue.
        Index(
            "uq_defesa_tcc_vigente",
            "tcc_id",
            unique=True,
            sqlite_where=text("situacao <> 'CANCELADA'"),
            postgresql_where=text("situacao <> 'CANCELADA'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tcc_id: Mapped[int] = _fk("tcc.id", index=True)
    formato: Mapped[str] = mapped_column(String(10))
    data: Mapped[date]
    inicio: Mapped[time]
    fim: Mapped[time]
    local_id: Mapped[int | None] = _fk("local_defesa.id", nullable=True, index=True)
    link: Mapped[str | None] = mapped_column(String(500))
    situacao: Mapped[str] = mapped_column(String(10), default=CONFIRMADA)
    responsavel_id: Mapped[int] = _fk("docente.usuario_id", index=True)
    publicada: Mapped[bool] = mapped_column(default=False)
    publicada_em: Mapped[datetime | None]
    divulgar_link: Mapped[bool] = mapped_column(default=False)
    revisao_banca: Mapped[bool] = mapped_column(default=False)
    lembrete_enviado_em: Mapped[datetime | None]
    criado_em: Mapped[datetime] = mapped_column(default=agora)

    tcc: Mapped[Tcc] = relationship()
    local: Mapped[LocalDefesa | None] = relationship()
    responsavel: Mapped[Docente] = relationship()
    membros: Mapped[list["BancaMembro"]] = relationship(back_populates="defesa", order_by="BancaMembro.id")
    historico: Mapped[list["HistoricoDefesa"]] = relationship(order_by="HistoricoDefesa.id")


class BancaMembro(Base):
    """Membro da banca de uma defesa (RN12). O suplente só avalia depois de convocado (RN20)."""

    __tablename__ = "banca_membro"
    __table_args__ = (
        UniqueConstraint("defesa_id", "usuario_id", name="uq_banca_membro_defesa_usuario"),
        _dominio("banca_membro", "papel", PAPEIS_BANCA),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    defesa_id: Mapped[int] = _fk("defesa.id", index=True)
    usuario_id: Mapped[int] = _fk("usuario.id", index=True)
    papel: Mapped[str] = mapped_column(String(12))
    interno: Mapped[bool]
    convite_enviado_em: Mapped[datetime | None]
    presente: Mapped[bool | None]
    convocado_em: Mapped[datetime | None]
    substitui_membro_id: Mapped[int | None] = _fk("banca_membro.id", nullable=True, index=True)
    motivo_convocacao: Mapped[str | None] = mapped_column(Text)

    defesa: Mapped[Defesa] = relationship(back_populates="membros")
    usuario: Mapped[Usuario] = relationship()


class HistoricoDefesa(Base):
    """Agendamento, remarcação, cancelamento e suplência; nada é apagado (RN14)."""

    __tablename__ = "historico_defesa"
    __table_args__ = (_dominio("historico_defesa", "evento", EVENTOS_DEFESA),)

    id: Mapped[int] = mapped_column(primary_key=True)
    defesa_id: Mapped[int] = _fk("defesa.id", index=True)
    evento: Mapped[str] = mapped_column(String(20))
    motivo: Mapped[str | None] = mapped_column(Text)
    valores_anteriores: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB(), "postgresql"))
    usuario_id: Mapped[int] = _fk("usuario.id", index=True)
    registrado_em: Mapped[datetime] = mapped_column(default=agora)

    usuario: Mapped[Usuario] = relationship()


# =====================================================================
# Ocorrências, ouvintes e documentos oficiais (RBN09.10, RN15, RN23)
# Tabelas iguais às do modelo físico (ocorrencia_defesa, ouvinte_defesa, documento_oficial) e
# entidades do DS-FL09 (OcorrenciaDefesa, OuvinteDefesa, DocumentoOficial).
# =====================================================================

DOC_ATA, DOC_FOLHA, DOC_CERTIFICADO, DOC_DECLARACAO = "ATA", "FOLHA_APROVACAO", "CERTIFICADO", "DECLARACAO_HORAS"
TIPOS_DOCUMENTO = (DOC_ATA, DOC_FOLHA, DOC_CERTIFICADO, DOC_DECLARACAO)


class OcorrenciaDefesa(Base):
    """Ocorrência da sessão em texto livre, com autor e data (RN23). A correção grava alterada_em."""

    __tablename__ = "ocorrencia_defesa"

    id: Mapped[int] = mapped_column(primary_key=True)
    defesa_id: Mapped[int] = _fk("defesa.id", index=True)
    texto: Mapped[str] = mapped_column(Text)
    autor_id: Mapped[int] = _fk("usuario.id", index=True)
    criado_em: Mapped[datetime] = mapped_column(default=agora)
    alterada_em: Mapped[datetime | None]

    autor: Mapped[Usuario] = relationship()


class OuvinteDefesa(Base):
    """Ouvinte presente (nome e matrícula), para a declaração de horas complementares (RN23)."""

    __tablename__ = "ouvinte_defesa"
    __table_args__ = (
        # CA-04 do RBN09.10: a mesma matrícula não entra duas vezes na lista da defesa, também com
        # dois pedidos ao mesmo tempo. Não está no SQL físico entregue.
        UniqueConstraint("defesa_id", "matricula", name="uq_ouvinte_defesa_matricula"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    defesa_id: Mapped[int] = _fk("defesa.id", index=True)
    nome: Mapped[str] = mapped_column(String(150))
    matricula: Mapped[str | None] = mapped_column(String(20))
    criado_em: Mapped[datetime] = mapped_column(default=agora)


class DocumentoOficial(Base):
    """Ata, Folha de Aprovação, certificado e declaração de horas. A retificação gera nova versão e
    marca a anterior como substituída (RN15). O arquivo fica em caminho, conferido pelo sha256 (RNF06)."""

    __tablename__ = "documento_oficial"
    __table_args__ = (
        _dominio("documento_oficial", "tipo", TIPOS_DOCUMENTO),
        # Uma declaração vigente por ouvinte, também com dois cliques ao mesmo tempo. Não está no SQL
        # físico entregue (ver PR do SCRUM-68).
        Index(
            "uq_documento_oficial_declaracao_vigente",
            "ouvinte_id",
            unique=True,
            sqlite_where=text("tipo = 'DECLARACAO_HORAS' AND vigente"),
            postgresql_where=text("tipo = 'DECLARACAO_HORAS' AND vigente"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    defesa_id: Mapped[int] = _fk("defesa.id", index=True)
    tipo: Mapped[str] = mapped_column(String(16))
    versao: Mapped[int]
    vigente: Mapped[bool]
    sha256: Mapped[str] = mapped_column(CHAR(64))
    caminho: Mapped[str] = mapped_column(String(500))
    membro_id: Mapped[int | None] = _fk("banca_membro.id", nullable=True, index=True)
    ouvinte_id: Mapped[int | None] = _fk("ouvinte_defesa.id", nullable=True, index=True)
    gerado_em: Mapped[datetime] = mapped_column(default=agora)
    substituido_em: Mapped[datetime | None]


# =====================================================================
# MOD04 · Instrumento de avaliação (Sprint S04, RBN10.01, RN19)
# Nomes iguais aos do modelo físico (instrumento_avaliacao, componente_avaliacao,
# criterio_avaliacao) e às entidades do DS-FL06-G (InstrumentoAvaliacao, CriterioAvaliacao).
# =====================================================================

# Conceitos de cada critério e a faixa de nota de cada um (RBN10.01, RBN10.03)
EXEMPLAR, COMPETENTE, NECESSITA = "EXEMPLAR", "COMPETENTE", "NECESSITA"
CONCEITOS = (EXEMPLAR, COMPETENTE, NECESSITA)
FAIXAS_CONCEITO = {EXEMPLAR: (8.0, 10.0), COMPETENTE: (6.0, 7.9), NECESSITA: (0.0, 5.9)}

# Pontos de cada componente: os pesos dos critérios precisam fechar esses totais (DS-FL06-G passo 7)
PONTOS_ESCRITA, PONTOS_ORAL = 7.0, 3.0


class InstrumentoAvaliacao(Base):
    """Uma versão do instrumento. Só uma é vigente; as anteriores ficam como histórico (RN19)."""

    __tablename__ = "instrumento_avaliacao"

    id: Mapped[int] = mapped_column(primary_key=True)
    versao: Mapped[int] = mapped_column(unique=True)
    vigente: Mapped[bool]
    criado_por: Mapped[int] = _fk("usuario.id", index=True)
    criado_em: Mapped[datetime] = mapped_column(default=agora)

    autor: Mapped[Usuario] = relationship()
    componentes: Mapped[list["ComponenteAvaliacao"]] = relationship(
        order_by="ComponenteAvaliacao.ordem", back_populates="instrumento"
    )


class ComponenteAvaliacao(Base):
    """Parte escrita (7,0) e parte oral (3,0)."""

    __tablename__ = "componente_avaliacao"

    id: Mapped[int] = mapped_column(primary_key=True)
    instrumento_id: Mapped[int] = _fk("instrumento_avaliacao.id", index=True)
    nome: Mapped[str] = mapped_column(String(60))
    pontos: Mapped[float] = mapped_column(Numeric(3, 1))
    ordem: Mapped[int] = mapped_column(SmallInteger)

    instrumento: Mapped[InstrumentoAvaliacao] = relationship(back_populates="componentes")
    criterios: Mapped[list["CriterioAvaliacao"]] = relationship(
        order_by="CriterioAvaliacao.ordem", back_populates="componente"
    )


class CriterioAvaliacao(Base):
    """Critério com peso e o texto descritivo dos três conceitos (RBN10.01, RBN10.03)."""

    __tablename__ = "criterio_avaliacao"

    id: Mapped[int] = mapped_column(primary_key=True)
    componente_id: Mapped[int] = _fk("componente_avaliacao.id", index=True)
    nome: Mapped[str] = mapped_column(String(120))
    peso: Mapped[float] = mapped_column(Numeric(4, 2))
    texto_exemplar: Mapped[str] = mapped_column(Text)
    texto_competente: Mapped[str] = mapped_column(Text)
    texto_necessita: Mapped[str] = mapped_column(Text)
    ordem: Mapped[int] = mapped_column(SmallInteger)

    componente: Mapped[ComponenteAvaliacao] = relationship(back_populates="criterios")


# =====================================================================
# MOD04 · Avaliação da defesa (Sprint S04, RBN10.02 a RBN10.05, RN13, RN19)
# Tabelas avaliacao e avaliacao_criterio iguais às do modelo físico e entidades do DS-FL06-A
# (Avaliacao, AvaliacaoCriterio). A avaliação é do membro da banca (banca_membro), como no DDL.
# =====================================================================

# Situação da avaliação: o membro edita o rascunho até enviar; enviada, não muda mais (RBN10.02)
ENVIADA = "ENVIADA"
STATUS_AVALIACAO = (RASCUNHO, ENVIADA)

# A nota acompanha o conceito (RBN10.03): mesma regra do CHECK do modelo físico, montada das faixas
_FAIXA_NOTA = " OR ".join(
    f"(conceito = '{c}' AND nota BETWEEN {minimo:g} AND {maximo:g})" for c, (minimo, maximo) in FAIXAS_CONCEITO.items()
)


class Avaliacao(Base):
    """Avaliação de um membro da banca numa defesa (RBN10.02). Aponta para a versão do instrumento
    usada: a primeira avaliação da defesa fixa nela a versão vigente (RN19, DS-FL06-G)."""

    __tablename__ = "avaliacao"
    __table_args__ = (
        UniqueConstraint("defesa_id", "membro_id", name="uq_avaliacao_defesa_membro"),
        _dominio("avaliacao", "status", STATUS_AVALIACAO),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    defesa_id: Mapped[int] = _fk("defesa.id", index=True)
    membro_id: Mapped[int] = _fk("banca_membro.id", index=True)
    instrumento_id: Mapped[int] = _fk("instrumento_avaliacao.id", index=True)
    status: Mapped[str] = mapped_column(String(10), default=RASCUNHO)
    parecer: Mapped[str | None] = mapped_column(Text)
    nota_total: Mapped[Decimal | None] = mapped_column(Numeric(3, 1))
    enviada_em: Mapped[datetime | None]

    defesa: Mapped[Defesa] = relationship()
    membro: Mapped[BancaMembro] = relationship()
    instrumento: Mapped[InstrumentoAvaliacao] = relationship()
    criterios: Mapped[list["AvaliacaoCriterio"]] = relationship(
        back_populates="avaliacao", order_by="AvaliacaoCriterio.criterio_id"
    )


class AvaliacaoCriterio(Base):
    """Conceito e nota de um critério (RBN10.03) e a nota ponderada = nota × peso ÷ 10 (RBN10.04)."""

    __tablename__ = "avaliacao_criterio"
    __table_args__ = (
        _dominio("avaliacao_criterio", "conceito", CONCEITOS),
        CheckConstraint(_FAIXA_NOTA, name="ck_avaliacao_criterio_nota"),
    )

    avaliacao_id: Mapped[int] = mapped_column(
        ForeignKey("avaliacao.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    criterio_id: Mapped[int] = mapped_column(
        ForeignKey("criterio_avaliacao.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    conceito: Mapped[str] = mapped_column(String(12))
    nota: Mapped[Decimal] = mapped_column(Numeric(3, 1))
    nota_ponderada: Mapped[Decimal] = mapped_column(Numeric(4, 2))

    avaliacao: Mapped[Avaliacao] = relationship(back_populates="criterios")
    criterio: Mapped[CriterioAvaliacao] = relationship()


# =====================================================================
# MOD04 · resultado da defesa (RBN09.12 · RN13, RN15)
# =====================================================================

APROVADO_DEFESA, APROVADO_COM_CORRECOES, REPROVADO_DEFESA = "APROVADO", "APROVADO_COM_CORRECOES", "REPROVADO"
RESULTADOS_DEFESA = (APROVADO_DEFESA, APROVADO_COM_CORRECOES, REPROVADO_DEFESA)


class ResultadoDefesa(Base):
    """Resultado confirmado pelo orientador (RBN09.12). Cada retificação grava uma nova versão e a anterior
    deixa de ser vigente, com quem confirmou, quando e o motivo (RN13). Média e nota final ficam com duas
    casas, o mesmo valor da consolidação (CA-06 do RBN09.11); o modelo físico entregue tem NUMERIC(3,1).

    As colunas da versão final, do prazo, da anuência e do atraso (RBN11.01 a RBN11.04) entram com as
    histórias das correções."""

    __tablename__ = "resultado_defesa"
    __table_args__ = (
        UniqueConstraint("defesa_id", "versao", name="uq_resultado_defesa_defesa_versao"),
        _dominio("resultado_defesa", "resultado", RESULTADOS_DEFESA),
        # Um resultado vigente por defesa, também com duas confirmações ao mesmo tempo (E2 do DS-FL06).
        # Não está no SQL físico entregue.
        Index(
            "uq_resultado_defesa_vigente",
            "defesa_id",
            unique=True,
            sqlite_where=text("vigente"),
            postgresql_where=text("vigente"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    defesa_id: Mapped[int] = _fk("defesa.id", index=True)
    versao: Mapped[int]
    vigente: Mapped[bool]
    media: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    nota_final: Mapped[Decimal] = mapped_column(Numeric(4, 2))
    regra_qualis: Mapped[bool]
    resultado: Mapped[str] = mapped_column(String(24))
    parecer: Mapped[str] = mapped_column(Text)
    confirmado_por: Mapped[int] = _fk("usuario.id", index=True)
    confirmado_em: Mapped[datetime] = mapped_column(default=agora)
    motivo_retificacao: Mapped[str | None] = mapped_column(Text)

    defesa: Mapped[Defesa] = relationship()
    autor: Mapped["Usuario"] = relationship()
