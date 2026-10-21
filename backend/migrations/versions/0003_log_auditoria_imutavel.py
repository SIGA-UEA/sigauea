"""Log de auditoria imutável (HT07 CA-02, RNF03): o banco recusa UPDATE e DELETE.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-16
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MENSAGEM = "log_auditoria nao pode ser alterado nem apagado (RNF03)"


def upgrade() -> None:
    if op.get_context().dialect.name == "postgresql":
        op.execute(
            f"""
            CREATE FUNCTION log_auditoria_somente_insercao() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION '{_MENSAGEM}';
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            "CREATE TRIGGER trg_log_auditoria_imutavel BEFORE UPDATE OR DELETE ON log_auditoria "
            "FOR EACH ROW EXECUTE FUNCTION log_auditoria_somente_insercao()"
        )
    else:  # SQLite (desenvolvimento)
        for operacao in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER trg_log_auditoria_sem_{operacao.lower()} "
                f"BEFORE {operacao} ON log_auditoria "
                f"BEGIN SELECT RAISE(ABORT, '{_MENSAGEM}'); END"
            )


def downgrade() -> None:
    if op.get_context().dialect.name == "postgresql":
        op.execute("DROP TRIGGER trg_log_auditoria_imutavel ON log_auditoria")
        op.execute("DROP FUNCTION log_auditoria_somente_insercao()")
    else:
        for operacao in ("update", "delete"):
            op.execute(f"DROP TRIGGER trg_log_auditoria_sem_{operacao}")
