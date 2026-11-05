"""Análise do cadastro de TCC pela coordenação (Sprint S04): decisão, parecer, quem decidiu e quando
(RBN04.01 a RBN04.05, RN06, RN10). Tabela analise_cadastro igual à do modelo físico.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, Sequence[str], None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analise_cadastro",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tcc_id", sa.Integer(), nullable=False),
        sa.Column("coordenador_id", sa.Integer(), nullable=False),
        sa.Column("resultado", sa.String(length=10), nullable=False),
        sa.Column("parecer", sa.Text(), nullable=False),
        sa.Column("decidido_em", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "resultado IN ('APROVADO', 'DEVOLVIDO', 'REPROVADO')", name="ck_analise_cadastro_resultado"
        ),
        sa.CheckConstraint(
            "resultado = 'APROVADO' OR length(trim(parecer)) > 0", name="ck_analise_cadastro_parecer"
        ),
        sa.ForeignKeyConstraint(["coordenador_id"], ["docente.usuario_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tcc_id"], ["tcc.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("analise_cadastro", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_analise_cadastro_tcc_id"), ["tcc_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_analise_cadastro_coordenador_id"), ["coordenador_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("analise_cadastro", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_analise_cadastro_coordenador_id"))
        batch_op.drop_index(batch_op.f("ix_analise_cadastro_tcc_id"))

    op.drop_table("analise_cadastro")
