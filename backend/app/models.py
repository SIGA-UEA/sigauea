"""Tabelas do módulo de usuários e acesso (EP01).

Os nomes de tabelas e colunas seguem as fichas das histórias HU01.01 a HU01.08.
Usuário não tem exclusão física: é inativado; token e sessão expiram.
Só a área de interesse (RBN01.02) e a foto de perfil podem ser apagadas.
"""

from datetime import datetime

from sqlalchemy import CHAR, ForeignKey, Index, LargeBinary, String, Text, func
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
    tipo: Mapped[str] = mapped_column(String(20))
    destinatario: Mapped[str] = mapped_column(String(254))
    status: Mapped[str] = mapped_column(String(10), default="pendente")  # pendente, enviado, falha
    tentativas: Mapped[int] = mapped_column(default=0)
    erro: Mapped[str | None] = mapped_column(Text)
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
