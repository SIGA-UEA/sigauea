"""Foto de perfil (RBN01.01, RBN01.09 e RBN01.10).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "foto_usuario",
        sa.Column("usuario_id", sa.Integer(), primary_key=True),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("conteudo", sa.LargeBinary(), nullable=False),
        sa.Column("sha256", sa.CHAR(64), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("foto_usuario")
