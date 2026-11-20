"""Documentos da defesa: RBN09.14 a RBN09.17, RN15.

- resultado_defesa.anuencia_em, do modelo físico: a anuência do aluno às correções libera a Folha de
  Aprovação quando o resultado é "aprovado com correções" (RBN09.15 CA-03);
- índices únicos parciais em documento_oficial (não estão no SQL físico entregue): uma ata e uma Folha de
  Aprovação vigentes por defesa e um certificado por membro da banca, também com dois cliques ao mesmo tempo.

Revision ID: 0014
Revises: 0013
Create Date: 2026-11-11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0014"
down_revision: Union[str, Sequence[str], None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("resultado_defesa", schema=None) as batch_op:
        batch_op.add_column(sa.Column("anuencia_em", sa.DateTime(), nullable=True))
    with op.batch_alter_table("documento_oficial", schema=None) as batch_op:
        batch_op.create_index(
            "uq_documento_oficial_ata_folha_vigente",
            ["defesa_id", "tipo"],
            unique=True,
            sqlite_where=sa.text("tipo IN ('ATA', 'FOLHA_APROVACAO') AND vigente"),
            postgresql_where=sa.text("tipo IN ('ATA', 'FOLHA_APROVACAO') AND vigente"),
        )
        batch_op.create_index(
            "uq_documento_oficial_certificado_vigente",
            ["membro_id"],
            unique=True,
            sqlite_where=sa.text("tipo = 'CERTIFICADO' AND vigente"),
            postgresql_where=sa.text("tipo = 'CERTIFICADO' AND vigente"),
        )


def downgrade() -> None:
    with op.batch_alter_table("documento_oficial", schema=None) as batch_op:
        batch_op.drop_index("uq_documento_oficial_certificado_vigente")
        batch_op.drop_index("uq_documento_oficial_ata_folha_vigente")
    with op.batch_alter_table("resultado_defesa", schema=None) as batch_op:
        batch_op.drop_column("anuencia_em")
