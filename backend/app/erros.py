"""Formato único das respostas de erro da API.

Toda resposta de erro tem "detail" (mensagem para mostrar na tela) e pode ter:
- "campo": nome do campo com problema (ex.: e-mail duplicado, 409)
- "campos": {campo: mensagem} quando a validação falha (400)
- "criterios": critérios de senha não atendidos (422)
- "motivo": por que um link não vale mais (expirado, usado, invalido)
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ErroAPI(Exception):
    def __init__(self, status: int, mensagem: str, **extras) -> None:
        self.status = status
        self.corpo = {"detail": mensagem, **extras}


_MENSAGENS = {
    "missing": "Campo obrigatório.",
    "string_too_short": "Texto curto demais.",
    "string_too_long": "Texto longo demais.",
    "too_short": "Escolha ao menos uma opção.",
}


def registrar_tratadores(app: FastAPI) -> None:
    @app.exception_handler(ErroAPI)
    def _erro_api(_: Request, erro: ErroAPI) -> JSONResponse:
        return JSONResponse(erro.corpo, status_code=erro.status)

    @app.exception_handler(RequestValidationError)
    def _validacao(_: Request, erro: RequestValidationError) -> JSONResponse:
        # O FastAPI responde 422 por padrão; as fichas pedem 400 para validação.
        def mensagem(e) -> str:
            # Validadores próprios (ex.: "O resumo passa de 500 palavras.") têm texto pronto.
            if e["type"] == "value_error":
                return str(e["msg"]).removeprefix("Value error, ")
            return _MENSAGENS.get(e["type"], "Valor inválido.")

        campos = {}
        for e in erro.errors():
            # Em listas o último item do caminho é o índice; o campo é o nome antes dele.
            nomes = [str(p) for p in e["loc"] if not isinstance(p, int)]
            campos.setdefault(nomes[-1] if nomes else "corpo", mensagem(e))
        return JSONResponse(
            {"detail": "Confira os campos destacados.", "campos": campos}, status_code=400
        )
