"""Simula um instrumento já usado em avaliações para ver o versionamento N+1 (SCRUM-76, DS-FL06-G passos 8 a 10).

A tabela de avaliação só chega com a SCRUM-77, então aqui o passo 8 é trocado por "sim" apenas neste processo.
As versões criadas são reais no banco. Pré-requisito: python -m app.seed --demo. Não usar em produção.
"""

import sys

from fastapi.testclient import TestClient

from app.main import app
from app.services import instrumento as servico

SENHA = "Siga@2026"
CAMPOS = ("nome", "peso", "texto_exemplar", "texto_competente", "texto_necessita")
URL = "/api/v1/instrumento-avaliacao"


def corpo(consulta):
    return {"componentes": [{"id": c["id"], "criterios": [{k: x[k] for k in CAMPOS} for x in c["criterios"]]}
                            for c in consulta["instrumento"]["componentes"]]}


def salvar(c, alterar, descricao):
    atual = c.get(URL).json()
    novo = corpo(atual)
    alterar(novo)
    r = c.put(URL, json=novo)
    print(f"{descricao}: HTTP {r.status_code} -> versão {r.json().get('versao')}" if r.status_code == 200
          else f"{descricao}: HTTP {r.status_code} {r.json()}")


def main():
    servico.existe_avaliacao = lambda db, instrumento_id: True  # passo 8 = "sim" (simulação)
    c = TestClient(app)
    r = c.post("/api/v1/auth/login", json={"email": "coordenador@exemplo.com", "senha": SENHA})
    assert r.status_code == 200, r.json()

    def v2(b):
        k = b["componentes"][0]["criterios"]
        k[0]["peso"], k[1]["peso"] = "1.0", "1.5"

    def v3(b):
        b["componentes"][0]["criterios"][2]["texto_exemplar"] += " (texto revisado na versão 3)"

    def v4(b):
        k = b["componentes"][1]["criterios"]
        k[0]["nome"] = k[0]["nome"] + " e clareza"

    salvar(c, v2, "Mudar pesos de Relevância e Metodologia")
    salvar(c, v3, "Revisar o texto Exemplar de um critério")
    salvar(c, v4, "Renomear o primeiro critério da parte oral")
    h = c.get(URL).json()["versoes"]
    print("Histórico:", [(v["versao"], "vigente" if v["vigente"] else "anterior") for v in h])


if __name__ == "__main__":
    sys.exit(main())
