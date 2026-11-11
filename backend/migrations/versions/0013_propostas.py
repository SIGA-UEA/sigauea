"""Ideias de TCC: RBN02.01 e RBN02.02, RN25.

Tabelas proposta, proposta_destinatario e comentario_proposta iguais às do modelo físico. A tabela denuncia
(RBN02.03, moderação por denúncia) fica fora: a história é Won't nesta versão.

Número 0013: vem depois da 0012_acesso_limitado (contas limitadas, RBN01.12 e RBN01.13), integrada antes.

Revision ID: 0013
Revises: 0012
Create Date: 2026-11-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0013"
down_revision: Union[str, Sequence[str], None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "proposta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("autor_id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("destino", sa.String(length=12), nullable=False),
        sa.Column("area_id", sa.Integer(), nullable=True),
        sa.Column("oculta_em", sa.DateTime(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.CheckConstraint("destino IN ('AREA', 'PROFESSORES')", name="ck_proposta_destino"),
        sa.CheckConstraint("destino <> 'AREA' OR area_id IS NOT NULL", name="ck_proposta_area"),
        sa.ForeignKeyConstraint(["autor_id"], ["usuario.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["area_id"], ["area_interesse.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("proposta", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_proposta_autor_id"), ["autor_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_proposta_area_id"), ["area_id"], unique=False)

    op.create_table(
        "proposta_destinatario",
        sa.Column("proposta_id", sa.Integer(), nullable=False),
        sa.Column("professor_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["proposta_id"], ["proposta.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["professor_id"], ["docente.usuario_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("proposta_id", "professor_id"),
    )
    with op.batch_alter_table("proposta_destinatario", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_proposta_destinatario_proposta_id"), ["proposta_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_proposta_destinatario_professor_id"), ["professor_id"], unique=False)

    op.create_table(
        "comentario_proposta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("proposta_id", sa.Integer(), nullable=False),
        sa.Column("autor_id", sa.Integer(), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("oculto_em", sa.DateTime(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.CheckConstraint("length(trim(texto)) > 0", name="ck_comentario_proposta_texto"),
        sa.ForeignKeyConstraint(["proposta_id"], ["proposta.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["autor_id"], ["usuario.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("comentario_proposta", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_comentario_proposta_proposta_id"), ["proposta_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_comentario_proposta_autor_id"), ["autor_id"], unique=False)


def downgrade() -> None:
    for tabela, indices in (
        ("comentario_proposta", ("ix_comentario_proposta_autor_id", "ix_comentario_proposta_proposta_id")),
        ("proposta_destinatario", ("ix_proposta_destinatario_professor_id", "ix_proposta_destinatario_proposta_id")),
        ("proposta", ("ix_proposta_area_id", "ix_proposta_autor_id")),
    ):
        with op.batch_alter_table(tabela, schema=None) as batch_op:
            for indice in indices:
                batch_op.drop_index(indice)
        op.drop_table(tabela)
