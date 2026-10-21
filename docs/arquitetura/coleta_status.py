"""Plugin do pytest: registra os códigos de resposta que cada rota devolveu durante a suíte.

Alimenta o contrato da API com os códigos observados de verdade (o OpenAPI automático do
FastAPI só lista 200 e 422, e a API responde 400 na validação, ver app/erros.py).

    cd backend
    pytest -q -p coleta_status        # com docs/arquitetura no PYTHONPATH (ver contrato_api.py)

O middleware só é instalado depois que o conftest apontou a API para o banco de teste,
para o plugin nunca abrir o banco de desenvolvimento.
"""

import json
from collections import defaultdict
from pathlib import Path

SAIDA = Path(__file__).resolve().parent / "status-observados.json"
_vistos: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))


class _Registrador:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        status = {}

        async def enviar(msg):
            if msg["type"] == "http.response.start":
                status["codigo"] = msg["status"]
            await send(msg)

        await self.app(scope, receive, enviar)
        rota = scope.get("route")
        if rota is not None and "codigo" in status:
            _vistos[f"{scope['method']} {rota.path}"][status["codigo"]] += 1


def pytest_collection_finish(session):
    from app.main import app  # já importado pelo conftest, com o banco de teste

    app.add_middleware(_Registrador)


def pytest_sessionfinish(session, exitstatus):
    dados = {rota: dict(sorted(cods.items())) for rota, cods in sorted(_vistos.items())}
    SAIDA.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf8")
