"""Eventos PUBLICACAO e RETIRADA no histórico da defesa (S04 · RBN14.01, DS-FL05).

Publicar e retirar a defesa da agenda ficam no histórico (mensagens 10 e 16 do DS-FL05). O SQL
físico entregue não tem esses eventos; entram na mesma lista do BANCA_ALTERADA (ver CR da S04).

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-05
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0007"
down_revision: Union[str, Sequence[str], None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ANTES = "evento IN ('AGENDAMENTO', 'REMARCACAO', 'CANCELAMENTO', 'SUPLENTE_CONVOCADO', 'BANCA_ALTERADA')"
DEPOIS = (
    "evento IN ('AGENDAMENTO', 'REMARCACAO', 'CANCELAMENTO', 'SUPLENTE_CONVOCADO', 'BANCA_ALTERADA', "
    "'PUBLICACAO', 'RETIRADA')"
)


def _trocar(para: str) -> None:
    with op.batch_alter_table("historico_defesa", schema=None) as batch_op:
        batch_op.drop_constraint("ck_historico_defesa_evento", type_="check")
        batch_op.create_check_constraint("ck_historico_defesa_evento", para)


def upgrade() -> None:
    _trocar(DEPOIS)


def downgrade() -> None:
    op.execute("DELETE FROM historico_defesa WHERE evento IN ('PUBLICACAO', 'RETIRADA')")
    _trocar(ANTES)
