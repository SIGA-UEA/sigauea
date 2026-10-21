"""Esquema inicial do módulo de usuários e acesso (EP01, HU01.01 a HU01.08).

Revision ID: 0001
Revises:
Create Date: 2026-10-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _fk(coluna: str, alvo: str) -> sa.ForeignKeyConstraint:
    # Nada é apagado em cascata: usuário é inativado, não excluído.
    return sa.ForeignKeyConstraint([coluna], [alvo], ondelete="RESTRICT")


def upgrade() -> None:
    # ---------- catálogos ----------
    op.create_table(
        "nucleo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sigla", sa.String(20), nullable=False, unique=True),
        sa.Column("nome", sa.String(150), nullable=False),
    )
    op.create_table(
        "curso",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sigla", sa.String(10), nullable=False, unique=True),
        sa.Column("nome", sa.String(100), nullable=False, unique=True),
        sa.Column("nucleo_id", sa.Integer(), nullable=False),
        _fk("nucleo_id", "nucleo.id"),
    )
    op.create_table(
        "area_interesse",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(100), nullable=False, unique=True),
    )
    op.create_table(
        "perfil",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.String(30), nullable=False, unique=True),
        sa.Column("nome", sa.String(50), nullable=False),
    )

    # ---------- pessoas ----------
    op.create_table(
        "usuario",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("telefone", sa.String(20)),
        sa.Column("senha_hash", sa.String(60)),  # nulo até ativar a conta
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.Column("inativado_em", sa.DateTime()),
        sa.Column("tentativas_falhas", sa.Integer(), nullable=False),
        sa.Column("bloqueado_ate", sa.DateTime()),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
    )
    # HU01.01 R3: e-mail único sem diferenciar maiúsculas.
    op.create_index("uq_usuario_email_lower", "usuario", [sa.text("lower(email)")], unique=True)

    op.create_table(
        "usuario_perfil",
        sa.Column("usuario_id", sa.Integer(), primary_key=True),
        sa.Column("perfil_id", sa.Integer(), primary_key=True),
        sa.Column("atribuido_por", sa.Integer()),
        sa.Column("atribuido_em", sa.DateTime(), nullable=False),
        _fk("usuario_id", "usuario.id"),
        _fk("perfil_id", "perfil.id"),
        _fk("atribuido_por", "usuario.id"),
    )
    op.create_table(
        "docente",
        sa.Column("usuario_id", sa.Integer(), primary_key=True),
        sa.Column("cargo", sa.String(20), nullable=False),
        sa.Column("nucleo_id", sa.Integer(), nullable=False),
        sa.Column("curso_id", sa.Integer()),  # nulo para coordenador
        _fk("usuario_id", "usuario.id"),
        _fk("nucleo_id", "nucleo.id"),
        _fk("curso_id", "curso.id"),
    )
    op.create_table(
        "docente_area",
        sa.Column("docente_id", sa.Integer(), primary_key=True),
        sa.Column("area_id", sa.Integer(), primary_key=True),
        _fk("docente_id", "docente.usuario_id"),
        _fk("area_id", "area_interesse.id"),
    )
    op.create_table(
        "aluno",
        sa.Column("usuario_id", sa.Integer(), primary_key=True),
        sa.Column("matricula", sa.String(20), nullable=False, unique=True),
        sa.Column("curso_id", sa.Integer(), nullable=False),
        _fk("usuario_id", "usuario.id"),
        _fk("curso_id", "curso.id"),
    )

    # ---------- acesso ----------
    op.create_table(
        "token_usuario",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("token_hash", sa.CHAR(64), nullable=False, unique=True),
        sa.Column("expira_em", sa.DateTime(), nullable=False),
        sa.Column("usado_em", sa.DateTime()),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        _fk("usuario_id", "usuario.id"),
    )
    op.create_index("ix_token_usuario_usuario_id", "token_usuario", ["usuario_id"])

    op.create_table(
        "sessao",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.CHAR(64), nullable=False, unique=True),
        sa.Column("expira_em", sa.DateTime(), nullable=False),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        _fk("usuario_id", "usuario.id"),
    )
    op.create_index("ix_sessao_usuario_id", "sessao", ["usuario_id"])

    op.create_table(
        "notificacao_email",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("destinatario", sa.String(254), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("tentativas", sa.Integer(), nullable=False),
        sa.Column("erro", sa.Text()),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("enviado_em", sa.DateTime()),
        _fk("usuario_id", "usuario.id"),
    )
    op.create_index("ix_notificacao_email_usuario_id", "notificacao_email", ["usuario_id"])

    # ---------- auditoria (RNF03) ----------
    op.create_table(
        "log_auditoria",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer()),
        sa.Column("acao", sa.String(40), nullable=False),
        sa.Column("entidade", sa.String(40), nullable=False),
        sa.Column("entidade_id", sa.Integer()),
        sa.Column("campo", sa.String(40)),
        sa.Column("valor_anterior", sa.Text()),
        sa.Column("valor_novo", sa.Text()),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        _fk("usuario_id", "usuario.id"),
    )
    op.create_index("ix_log_auditoria_usuario_id", "log_auditoria", ["usuario_id"])
    op.create_index("ix_log_auditoria_criado_em", "log_auditoria", ["criado_em"])


def downgrade() -> None:
    for tabela in [
        "log_auditoria",
        "notificacao_email",
        "sessao",
        "token_usuario",
        "aluno",
        "docente_area",
        "docente",
        "usuario_perfil",
        "usuario",
        "perfil",
        "area_interesse",
        "curso",
        "nucleo",
    ]:
        op.drop_table(tabela)
