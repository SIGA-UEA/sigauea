"""Popula o ambiente de demonstração com TCCs aprovados, defesas agendadas e algumas publicadas.

Pré-requisito: python -m app.seed --demo. Usa a própria API (TestClient) e o banco configurado em
DATABASE_URL. Pode ser repetido: o que já existe é ignorado. Não usar em produção.
"""

import sys

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models import Tcc, Usuario
from app.security import gerar_hash_senha

SENHA = "Siga@2026"
DOCENTES = [
    {"nome": "Otto Orientador", "email": "otto@exemplo.com", "cargo": "orientador", "curso_id": 1, "perfis": ["orientador"]},
]
ALUNOS = [
    {"nome": "Bia Barbosa", "email": "bia@exemplo.com", "matricula": "2026000002", "curso_id": 1},
    {"nome": "Caio Cardoso", "email": "caio@exemplo.com", "matricula": "2026000003", "curso_id": 1},
]
TITULOS = {
    "aluno@exemplo.com": "Detecção de fraudes com aprendizado de máquina",
    "bia@exemplo.com": "Acessibilidade em aplicativos móveis para a educação básica",
    "caio@exemplo.com": "Monitoramento de qualidade do ar com sensores de baixo custo",
}
# (aluno, data, início, fim, publicar)
DEFESAS = [
    ("aluno@exemplo.com", "2026-11-25", "14:00", "14:20", True),
    ("bia@exemplo.com", "2026-11-23", "09:00", "09:20", True),
    ("caio@exemplo.com", "2026-12-02", "10:00", "10:20", False),
]


def entrar(email):
    c = TestClient(app)
    r = c.post("/api/v1/auth/login", json={"email": email, "senha": SENHA})
    assert r.status_code == 200, (email, r.status_code, r.json())
    return c


def definir_senha(emails):
    with SessionLocal() as db:
        for u in db.scalars(select(Usuario).where(Usuario.email.in_(emails))):
            u.senha_hash, u.ativo = gerar_hash_senha(SENHA), True
        db.commit()


def main():
    coord = entrar("coordenador@exemplo.com")
    turma = next(t for t in coord.get("/api/v1/turmas").json() if t["codigo"].startswith("TCC1-EC-2026/2"))
    for d in DOCENTES:
        if coord.post("/api/v1/docentes", json=d).status_code == 201:
            print("docente criado:", d["email"])
    for a in ALUNOS:
        r = coord.post("/api/v1/alunos", json=a)
        if r.status_code == 201:
            coord.post(f"/api/v1/turmas/{turma['id']}/alunos", json={"aluno_id": r.json()["id"]})
            print("aluno criado e matriculado:", a["email"])
    definir_senha([d["email"] for d in DOCENTES] + [a["email"] for a in ALUNOS])

    ids = {}
    for email in ("orientador@exemplo.com", "professor@exemplo.com", "otto@exemplo.com"):
        ids[email] = entrar(email).get("/api/v1/perfil").json().get("id")
    olga = entrar("orientador@exemplo.com")
    area = coord.get("/api/v1/areas").json()[0]
    orientador_id = next(d["id"] for d in coord.get("/api/v1/docentes").json() if d["email"] == "orientador@exemplo.com")

    tccs = {}
    for email, titulo in TITULOS.items():
        aluno = entrar(email)
        r = aluno.post("/api/v1/tccs", json={"titulo": titulo, "resumo": "Resumo de demonstração.",
            "palavras_chave": ["demonstração"], "area_id": area["id"], "modalidade": "MONOGRAFIA",
            "orientador_id": orientador_id})
        if r.status_code == 201:
            tccs[email] = r.json()["id"]
            print("TCC criado:", titulo)
        else:
            print("TCC já existe ou foi recusado:", email, r.status_code)
    for pendente in olga.get("/api/v1/orientacoes?status=PENDENTE").json():
        olga.post(f"/api/v1/orientacoes/{pendente['id']}/resposta", json={"decisao": "ACEITAR"})
    with SessionLocal() as db:
        for tid in tccs.values():
            db.get(Tcc, tid).situacao = "APROVADO"
        db.commit()

    otto = next(d for d in coord.get("/api/v1/docentes").json() if d["email"] == "otto@exemplo.com")
    paulo = next(d for d in coord.get("/api/v1/docentes").json() if d["email"] == "professor@exemplo.com")
    banca = [{"papel": "ORIENTADOR", "usuario_id": orientador_id},
             {"papel": "AVALIADOR", "usuario_id": otto["id"]}, {"papel": "AVALIADOR", "usuario_id": paulo["id"]}]
    for email, data, ini, fim, publicar in DEFESAS:
        if email not in tccs:
            continue
        r = olga.post(f"/api/v1/tccs/{tccs[email]}/defesa", json={"formato": "REMOTO", "data": data, "inicio": ini,
            "fim": fim, "link": "https://meet.exemplo.com/defesa", "banca": banca})
        if r.status_code != 201:
            print("defesa recusada:", email, r.status_code, r.json()); continue
        print("defesa agendada:", email, data, ini)
        if publicar:
            p = olga.post(f"/api/v1/defesas/{r.json()['id']}/publicacao")
            print("  publicada:", p.status_code)


if __name__ == "__main__":
    sys.exit(main())
