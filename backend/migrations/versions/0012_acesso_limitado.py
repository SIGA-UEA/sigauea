"""Conta limitada da pessoa externa: RBN01.12 (membro externo da banca) e RBN01.13 (coorientador externo).

Tabela acesso_limitado igual à do modelo físico entregue (SIGA_UEA_fisico_completo_46_tabelas.sql, parte 2):
escopo BANCA com defesa_id ou COORIENTACAO com tcc_id, expira_em e revogado_em. Sem acréscimos.

Revision ID: 0012
Revises: 0011
Create Date: 2026-11-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0012"
down_revision: Union[str, Sequence[str], None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "acesso_limitado",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("escopo", sa.String(length=20), nullable=False),
        sa.Column("defesa_id", sa.Integer(), nullable=True),
        sa.Column("tcc_id", sa.Integer(), nullable=True),
        sa.Column("expira_em", sa.DateTime(), nullable=True),
        sa.Column("revogado_em", sa.DateTime(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.CheckConstraint("escopo IN ('BANCA', 'COORIENTACAO')", name="ck_acesso_limitado_escopo"),
        sa.CheckConstraint(
            "(escopo = 'BANCA' AND defesa_id IS NOT NULL) OR (escopo = 'COORIENTACAO' AND tcc_id IS NOT NULL)",
            name="ck_acesso_limitado_alvo",
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["defesa_id"], ["defesa.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tcc_id"], ["tcc.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("acesso_limitado", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_acesso_limitado_usuario_id"), ["usuario_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_acesso_limitado_defesa_id"), ["defesa_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_acesso_limitado_tcc_id"), ["tcc_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("acesso_limitado", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_acesso_limitado_tcc_id"))
        batch_op.drop_index(batch_op.f("ix_acesso_limitado_defesa_id"))
        batch_op.drop_index(batch_op.f("ix_acesso_limitado_usuario_id"))
    op.drop_table("acesso_limitado")
