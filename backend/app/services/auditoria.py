"""Log de auditoria (RNF03). As linhas só são inseridas, nunca alteradas."""

from sqlalchemy.orm import Session

from app.models import LogAuditoria


def registrar(
    db: Session,
    *,
    ator_id: int | None,
    acao: str,
    entidade: str = "usuario",
    entidade_id: int | None = None,
    campo: str | None = None,
    anterior: object = None,
    novo: object = None,
) -> None:
    """Adiciona uma linha ao log. Quem chama é responsável pelo commit."""
    db.add(
        LogAuditoria(
            usuario_id=ator_id,
            acao=acao,
            entidade=entidade,
            entidade_id=entidade_id,
            campo=campo,
            valor_anterior=None if anterior is None else str(anterior),
            valor_novo=None if novo is None else str(novo),
        )
    )
