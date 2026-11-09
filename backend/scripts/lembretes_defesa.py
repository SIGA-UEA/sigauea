"""Lembrete da véspera da defesa (RBN09.06), rodado à mão no ambiente local.

Em produção quem chama é o GitHub Actions (.github/workflows/lembretes-defesa.yml), pela rota
POST /api/v1/tarefas/lembretes-defesa. Aqui a rotina roda direto no banco do DATABASE_URL:

    cd backend
    python scripts/lembretes_defesa.py               # defesas de amanhã
    python scripts/lembretes_defesa.py 2026-11-30    # como se hoje fosse 30/11 (defesas de 01/12)

Sem SMTP_HOST nem BREVO_API_KEY, os e-mails só aparecem no terminal.
"""

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal  # noqa: E402
from app.services.lembretes import lembrar_defesas_de_amanha  # noqa: E402

if __name__ == "__main__":
    hoje = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else None
    with SessionLocal() as db:
        print(json.dumps(lembrar_defesas_de_amanha(db, hoje), ensure_ascii=False, indent=2))
