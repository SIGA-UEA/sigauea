"""Defesa e banca (Sprint S04): local da defesa, defesa, membros da banca, histórico da defesa
e convidado externo (RBN09.01 a RBN09.09, RN12, RN14, RN20, RN22).

Segue o modelo físico entregue (SIGA_UEA_fisico_completo_46_tabelas.sql, parte 2).

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, Sequence[str], None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usuario_externo",
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("instituicao", sa.String(length=150), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("usuario_id"),
    )
    op.create_table(
        "local_defesa",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=100), nullable=False),
        sa.Column("descricao", sa.String(length=200), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nome"),
    )
    op.create_table(
        "defesa",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tcc_id", sa.Integer(), nullable=False),
        sa.Column("formato", sa.String(length=10), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("inicio", sa.Time(), nullable=False),
        sa.Column("fim", sa.Time(), nullable=False),
        sa.Column("local_id", sa.Integer(), nullable=True),
        sa.Column("link", sa.String(length=500), nullable=True),
        sa.Column("situacao", sa.String(length=10), nullable=False),
        sa.Column("responsavel_id", sa.Integer(), nullable=False),
        sa.Column("publicada", sa.Boolean(), nullable=False),
        sa.Column("publicada_em", sa.DateTime(), nullable=True),
        sa.Column("divulgar_link", sa.Boolean(), nullable=False),
        sa.Column("revisao_banca", sa.Boolean(), nullable=False),
        sa.Column("lembrete_enviado_em", sa.DateTime(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "formato IN ('PRESENCIAL', 'REMOTO', 'HIBRIDO')", name="ck_defesa_formato"
        ),
        sa.CheckConstraint(
            "situacao IN ('CONFIRMADA', 'REMARCADA', 'CANCELADA', 'REALIZADA')",
            name="ck_defesa_situacao",
        ),
        sa.CheckConstraint("fim > inicio", name="ck_defesa_horario"),
        sa.CheckConstraint(
            "(formato = 'PRESENCIAL' AND local_id IS NOT NULL)"
            " OR (formato = 'REMOTO' AND link IS NOT NULL)"
            " OR (formato = 'HIBRIDO' AND local_id IS NOT NULL AND link IS NOT NULL)",
            name="ck_defesa_formato_destino",
        ),
        sa.ForeignKeyConstraint(["tcc_id"], ["tcc.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["local_id"], ["local_defesa.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["responsavel_id"], ["docente.usuario_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_defesa_tcc_id", "defesa", ["tcc_id"])
    op.create_index("ix_defesa_local_id", "defesa", ["local_id"])
    op.create_index("ix_defesa_responsavel_id", "defesa", ["responsavel_id"])

    op.create_table(
        "banca_membro",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("defesa_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("papel", sa.String(length=12), nullable=False),
        sa.Column("interno", sa.Boolean(), nullable=False),
        sa.Column("convite_enviado_em", sa.DateTime(), nullable=True),
        sa.Column("presente", sa.Boolean(), nullable=True),
        sa.Column("convocado_em", sa.DateTime(), nullable=True),
        sa.Column("substitui_membro_id", sa.Integer(), nullable=True),
        sa.Column("motivo_convocacao", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "papel IN ('AVALIADOR', 'ORIENTADOR', 'COORIENTADOR', 'SUPLENTE')",
            name="ck_banca_membro_papel",
        ),
        sa.ForeignKeyConstraint(["defesa_id"], ["defesa.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["substitui_membro_id"], ["banca_membro.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("defesa_id", "usuario_id", name="uq_banca_membro_defesa_usuario"),
    )
    op.create_index("ix_banca_membro_defesa_id", "banca_membro", ["defesa_id"])
    op.create_index("ix_banca_membro_usuario_id", "banca_membro", ["usuario_id"])
    op.create_index("ix_banca_membro_substitui_membro_id", "banca_membro", ["substitui_membro_id"])

    op.create_table(
        "historico_defesa",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("defesa_id", sa.Integer(), nullable=False),
        sa.Column("evento", sa.String(length=20), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column(
            "valores_anteriores",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("registrado_em", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "evento IN ('AGENDAMENTO', 'REMARCACAO', 'CANCELAMENTO', 'SUPLENTE_CONVOCADO')",
            name="ck_historico_defesa_evento",
        ),
        sa.ForeignKeyConstraint(["defesa_id"], ["defesa.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_historico_defesa_defesa_id", "historico_defesa", ["defesa_id"])
    op.create_index("ix_historico_defesa_usuario_id", "historico_defesa", ["usuario_id"])


def downgrade() -> None:
    op.drop_table("historico_defesa")
    op.drop_table("banca_membro")
    op.drop_table("defesa")
    op.drop_table("local_defesa")
    op.drop_table("usuario_externo")
