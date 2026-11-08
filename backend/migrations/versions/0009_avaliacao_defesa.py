"""Avaliação da defesa (Sprint S04): avaliação de cada membro da banca e conceito e nota por critério
(RBN10.02 a RBN10.05, RN13, RN19). Tabelas iguais às do modelo físico (SIGA_UEA_fisico_completo_46_tabelas.sql,
parte 2).

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: Union[str, Sequence[str], None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "avaliacao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("defesa_id", sa.Integer(), nullable=False),
        sa.Column("membro_id", sa.Integer(), nullable=False),
        sa.Column("instrumento_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("parecer", sa.Text(), nullable=True),
        sa.Column("nota_total", sa.Numeric(precision=3, scale=1), nullable=True),
        sa.Column("enviada_em", sa.DateTime(), nullable=True),
        sa.CheckConstraint("status IN ('RASCUNHO', 'ENVIADA')", name="ck_avaliacao_status"),
        sa.ForeignKeyConstraint(["defesa_id"], ["defesa.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["membro_id"], ["banca_membro.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["instrumento_id"], ["instrumento_avaliacao.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("defesa_id", "membro_id", name="uq_avaliacao_defesa_membro"),
    )
    with op.batch_alter_table("avaliacao", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_avaliacao_defesa_id"), ["defesa_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_avaliacao_membro_id"), ["membro_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_avaliacao_instrumento_id"), ["instrumento_id"], unique=False)

    op.create_table(
        "avaliacao_criterio",
        sa.Column("avaliacao_id", sa.Integer(), nullable=False),
        sa.Column("criterio_id", sa.Integer(), nullable=False),
        sa.Column("conceito", sa.String(length=12), nullable=False),
        sa.Column("nota", sa.Numeric(precision=3, scale=1), nullable=False),
        sa.Column("nota_ponderada", sa.Numeric(precision=4, scale=2), nullable=False),
        sa.CheckConstraint(
            "conceito IN ('EXEMPLAR', 'COMPETENTE', 'NECESSITA')", name="ck_avaliacao_criterio_conceito"
        ),
        sa.CheckConstraint(
            "(conceito = 'EXEMPLAR' AND nota BETWEEN 8 AND 10)"
            " OR (conceito = 'COMPETENTE' AND nota BETWEEN 6 AND 7.9)"
            " OR (conceito = 'NECESSITA' AND nota BETWEEN 0 AND 5.9)",
            name="ck_avaliacao_criterio_nota",
        ),
        sa.ForeignKeyConstraint(["avaliacao_id"], ["avaliacao.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["criterio_id"], ["criterio_avaliacao.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("avaliacao_id", "criterio_id"),
    )
    with op.batch_alter_table("avaliacao_criterio", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_avaliacao_criterio_avaliacao_id"), ["avaliacao_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_avaliacao_criterio_criterio_id"), ["criterio_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("avaliacao_criterio", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_avaliacao_criterio_criterio_id"))
        batch_op.drop_index(batch_op.f("ix_avaliacao_criterio_avaliacao_id"))
    op.drop_table("avaliacao_criterio")

    with op.batch_alter_table("avaliacao", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_avaliacao_instrumento_id"))
        batch_op.drop_index(batch_op.f("ix_avaliacao_membro_id"))
        batch_op.drop_index(batch_op.f("ix_avaliacao_defesa_id"))
    op.drop_table("avaliacao")
