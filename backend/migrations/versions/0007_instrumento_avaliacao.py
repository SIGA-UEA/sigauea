"""Instrumento de avaliação ponderado e versionado (Sprint S04): versões, componentes e critérios
(RBN10.01, RN19). Tabelas iguais às do modelo físico (SIGA_UEA_fisico_completo_46_tabelas.sql, parte 2).

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-05
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "instrumento_avaliacao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("versao", sa.Integer(), nullable=False),
        sa.Column("vigente", sa.Boolean(), nullable=False),
        sa.Column("criado_por", sa.Integer(), nullable=False),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["criado_por"], ["usuario.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("versao"),
    )
    with op.batch_alter_table("instrumento_avaliacao", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_instrumento_avaliacao_criado_por"), ["criado_por"], unique=False)

    op.create_table(
        "componente_avaliacao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("instrumento_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=60), nullable=False),
        sa.Column("pontos", sa.Numeric(precision=3, scale=1), nullable=False),
        sa.Column("ordem", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(["instrumento_id"], ["instrumento_avaliacao.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("componente_avaliacao", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_componente_avaliacao_instrumento_id"), ["instrumento_id"], unique=False)

    op.create_table(
        "criterio_avaliacao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("componente_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("peso", sa.Numeric(precision=4, scale=2), nullable=False),
        sa.Column("texto_exemplar", sa.Text(), nullable=False),
        sa.Column("texto_competente", sa.Text(), nullable=False),
        sa.Column("texto_necessita", sa.Text(), nullable=False),
        sa.Column("ordem", sa.SmallInteger(), nullable=False),
        sa.ForeignKeyConstraint(["componente_id"], ["componente_avaliacao.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("criterio_avaliacao", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_criterio_avaliacao_componente_id"), ["componente_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("criterio_avaliacao", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_criterio_avaliacao_componente_id"))
    op.drop_table("criterio_avaliacao")

    with op.batch_alter_table("componente_avaliacao", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_componente_avaliacao_instrumento_id"))
    op.drop_table("componente_avaliacao")

    with op.batch_alter_table("instrumento_avaliacao", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_instrumento_avaliacao_criado_por"))
    op.drop_table("instrumento_avaliacao")