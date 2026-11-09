"""Resultado da defesa: RBN09.12, RN13.

Tabela resultado_defesa com as colunas do modelo físico usadas na confirmação e na retificação do resultado
(DS-FL06 e DS-FL06-D). Diferenças em relação ao SQL físico entregue:
- media e nota_final em NUMERIC(4,2), as duas casas da consolidação (CA-06 do RBN09.11), no lugar de (3,1);
- índice único parcial uq_resultado_defesa_vigente: um resultado vigente por defesa, mesmo com duas
  confirmações ao mesmo tempo;
- as colunas da versão final, do prazo, da anuência e do atraso (RBN11.01 a RBN11.04) ficam para as
  histórias das correções, que as usam.

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: Union[str, Sequence[str], None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resultado_defesa",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("defesa_id", sa.Integer(), nullable=False),
        sa.Column("versao", sa.Integer(), nullable=False),
        sa.Column("vigente", sa.Boolean(), nullable=False),
        sa.Column("media", sa.Numeric(4, 2), nullable=False),
        sa.Column("nota_final", sa.Numeric(4, 2), nullable=False),
        sa.Column("regra_qualis", sa.Boolean(), nullable=False),
        sa.Column("resultado", sa.String(length=24), nullable=False),
        sa.Column("parecer", sa.Text(), nullable=False),
        sa.Column("confirmado_por", sa.Integer(), nullable=False),
        sa.Column("confirmado_em", sa.DateTime(), nullable=False),
        sa.Column("motivo_retificacao", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "resultado IN ('APROVADO', 'APROVADO_COM_CORRECOES', 'REPROVADO')", name="ck_resultado_defesa_resultado"
        ),
        sa.ForeignKeyConstraint(["defesa_id"], ["defesa.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["confirmado_por"], ["usuario.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("defesa_id", "versao", name="uq_resultado_defesa_defesa_versao"),
    )
    with op.batch_alter_table("resultado_defesa", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_resultado_defesa_defesa_id"), ["defesa_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_resultado_defesa_confirmado_por"), ["confirmado_por"], unique=False)
        batch_op.create_index(
            "uq_resultado_defesa_vigente",
            ["defesa_id"],
            unique=True,
            sqlite_where=sa.text("vigente"),
            postgresql_where=sa.text("vigente"),
        )


def downgrade() -> None:
    with op.batch_alter_table("resultado_defesa", schema=None) as batch_op:
        batch_op.drop_index("uq_resultado_defesa_vigente")
        batch_op.drop_index(batch_op.f("ix_resultado_defesa_confirmado_por"))
        batch_op.drop_index(batch_op.f("ix_resultado_defesa_defesa_id"))
    op.drop_table("resultado_defesa")
