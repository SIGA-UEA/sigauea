"""Configuração para publicar (Render + Neon): o endereço do banco vem como o provedor entrega."""

import pytest

from app.config import url_do_banco


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("postgresql://u:s@ep-x.neon.tech/siga?sslmode=require",
         "postgresql+psycopg://u:s@ep-x.neon.tech/siga?sslmode=require"),
        ("postgres://u:s@host:5432/siga", "postgresql+psycopg://u:s@host:5432/siga"),
        ("postgresql+psycopg://u:s@host/siga", "postgresql+psycopg://u:s@host/siga"),
        ("sqlite:///siga_dev.db", "sqlite:///siga_dev.db"),
    ],
)
def test_url_do_banco_indica_o_driver_psycopg(entrada, esperado):
    assert url_do_banco(entrada) == esperado
