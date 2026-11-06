"""Ocorrências, ouvintes e documentos oficiais da defesa (Sprint S04): RBN09.10, RN15, RN23.

Tabelas ocorrencia_defesa, ouvinte_defesa e documento_oficial iguais às do modelo físico, com um
acréscimo: a restrição única uq_ouvinte_defesa_matricula (CA-04 do RBN09.10, sem matrícula repetida
na lista da mesma defesa).

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, Sequence[str], None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ocorrencia_defesa",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("defesa_id", sa.Integer(), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("autor_id", sa.Integer(), nullable=False),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("alterada_em", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["defesa_id"], ["defesa.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["autor_id"], ["usuario.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("ocorrencia_defesa", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ocorrencia_defesa_defesa_id"), ["defesa_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_ocorrencia_defesa_autor_id"), ["autor_id"], unique=False)

    op.create_table(
        "ouvinte_defesa",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("defesa_id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=150), nullable=False),
        sa.Column("matricula", sa.String(length=20), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["defesa_id"], ["defesa.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("defesa_id", "matricula", name="uq_ouvinte_defesa_matricula"),
    )
    with op.batch_alter_table("ouvinte_defesa", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_ouvinte_defesa_defesa_id"), ["defesa_id"], unique=False)

    op.create_table(
        "documento_oficial",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("defesa_id", sa.Integer(), nullable=False),
        sa.Column("tipo", sa.String(length=16), nullable=False),
        sa.Column("versao", sa.Integer(), nullable=False),
        sa.Column("vigente", sa.Boolean(), nullable=False),
        sa.Column("sha256", sa.CHAR(length=64), nullable=False),
        sa.Column("caminho", sa.String(length=500), nullable=False),
        sa.Column("membro_id", sa.Integer(), nullable=True),
        sa.Column("ouvinte_id", sa.Integer(), nullable=True),
        sa.Column("gerado_em", sa.DateTime(), nullable=False),
        sa.Column("substituido_em", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "tipo IN ('ATA', 'FOLHA_APROVACAO', 'CERTIFICADO', 'DECLARACAO_HORAS')",
            name="ck_documento_oficial_tipo",
        ),
        sa.ForeignKeyConstraint(["defesa_id"], ["defesa.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["membro_id"], ["banca_membro.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ouvinte_id"], ["ouvinte_defesa.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("documento_oficial", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_documento_oficial_defesa_id"), ["defesa_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_documento_oficial_membro_id"), ["membro_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_documento_oficial_ouvinte_id"), ["ouvinte_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("documento_oficial", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_documento_oficial_ouvinte_id"))
        batch_op.drop_index(batch_op.f("ix_documento_oficial_membro_id"))
        batch_op.drop_index(batch_op.f("ix_documento_oficial_defesa_id"))
    op.drop_table("documento_oficial")

    with op.batch_alter_table("ouvinte_defesa", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ouvinte_defesa_defesa_id"))
    op.drop_table("ouvinte_defesa")

    with op.batch_alter_table("ocorrencia_defesa", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_ocorrencia_defesa_autor_id"))
        batch_op.drop_index(batch_op.f("ix_ocorrencia_defesa_defesa_id"))
    op.drop_table("ocorrencia_defesa")
