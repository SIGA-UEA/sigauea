"""Tarefas e entregáveis do TCC: RBN05.05.

Tabela tarefa_tcc igual à do modelo físico entregue (SIGA_UEA_fisico_completo_46_tabelas.sql), sem acréscimos.

Revision ID: 0016
Revises: 0015
Create Date: 2026-11-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0016"
down_revision: Union[str, Sequence[str], None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tarefa_tcc",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tcc_id", sa.Integer(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("prazo", sa.Date(), nullable=False),
        sa.Column("cadastrada_por", sa.Integer(), nullable=False),
        sa.Column("entregue_em", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.CheckConstraint("status IN ('PENDENTE', 'ENTREGUE', 'ATRASADA')", name="ck_tarefa_tcc_status"),
        sa.ForeignKeyConstraint(["tcc_id"], ["tcc.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cadastrada_por"], ["usuario.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tarefa_tcc_tcc_id", "tarefa_tcc", ["tcc_id"])


def downgrade() -> None:
    op.drop_index("ix_tarefa_tcc_tcc_id", table_name="tarefa_tcc")
    op.drop_table("tarefa_tcc")
