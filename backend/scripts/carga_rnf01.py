"""Teste de carga do RNF01 e do CT-03.04-05: 30 submissões simultâneas do cadastro de TCC.

Meta: p95 abaixo de 3 s, do envio até o retorno do protocolo, e nenhum protocolo repetido (RNF06).

Use um banco de teste, nunca o de produção: o script cria 30 alunos (carga00@exemplo.com...)
direto no banco e matricula todos na turma de demonstração. O resto é feito pela API HTTP,
como o navegador faria.

    cd backend
    $env:DATABASE_URL = "postgresql+psycopg://usuario:senha@localhost:5432/siga_carga"
    python -m app.seed --demo
    uvicorn app.main:app --port 8000          # em outro terminal, com o mesmo DATABASE_URL
    python scripts/carga_rnf01.py             # SIGA_API muda o endereço da API

Resultado medido em 17/10/2026 (PostgreSQL 16, máquina local): p95 de 0,76 s, 30 protocolos distintos.
"""

import asyncio
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    MATRICULADO,
    PERFIL_ALUNO,
    Aluno,
    AreaInteresse,
    Curso,
    MatriculaTurma,
    Perfil,
    Turma,
    Usuario,
    UsuarioPerfil,
)
from app.security import gerar_hash_senha  # noqa: E402

API = os.environ.get("SIGA_API", "http://127.0.0.1:8000/api/v1")
N = 30
SENHA = "Siga@2026"
META_P95 = 3.0


def preparar_banco() -> tuple[int, int]:
    """Cria os 30 alunos matriculados (se ainda não existem). Devolve a área e a orientadora."""
    with SessionLocal() as db:
        curso = db.scalar(select(Curso).where(Curso.sigla == "EC"))
        turma = db.scalar(select(Turma).where(Turma.codigo == "TCC1-EC-2026/2-1"))
        if turma is None:
            sys.exit("Turma de demonstração não encontrada. Rode antes: python -m app.seed --demo")
        perfil = db.scalar(select(Perfil).where(Perfil.codigo == PERFIL_ALUNO))
        area_id = db.scalar(select(AreaInteresse.id))
        orientador_id = db.scalar(select(Usuario.id).where(Usuario.email == "orientador@exemplo.com"))
        senha_hash = gerar_hash_senha(SENHA)
        for i in range(N):
            email = f"carga{i:02d}@exemplo.com"
            if db.scalar(select(Usuario).where(Usuario.email == email)):
                continue
            u = Usuario(nome=f"Aluno Carga {i:02d}", email=email, senha_hash=senha_hash, ativo=True)
            db.add(u)
            db.flush()
            db.add(Aluno(usuario_id=u.id, matricula=f"20269{i:05d}", curso_id=curso.id))
            db.add(UsuarioPerfil(usuario_id=u.id, perfil_id=perfil.id))
            db.add(MatriculaTurma(turma_id=turma.id, aluno_id=u.id, situacao=MATRICULADO,
                                  incluido_por=turma.professor_id))
        db.commit()
        return area_id, orientador_id


async def entrar(cliente: httpx.AsyncClient, email: str) -> None:
    r = await cliente.post(f"{API}/auth/login", json={"email": email, "senha": SENHA})
    r.raise_for_status()


async def main() -> int:
    area_id, orientador_id = preparar_banco()

    async def rascunho(i: int) -> tuple[httpx.AsyncClient, int]:
        cliente = httpx.AsyncClient(timeout=60)
        await entrar(cliente, f"carga{i:02d}@exemplo.com")
        r = await cliente.post(f"{API}/tccs", json={
            "titulo": f"Trabalho de carga {i}", "resumo": "Resumo do trabalho de carga.",
            "palavras_chave": ["carga", "teste"], "area_id": area_id, "modalidade": "MONOGRAFIA",
            "orientador_id": orientador_id,
        })
        if r.status_code == 409:
            sys.exit("Os alunos de carga já têm TCC neste banco. Use um banco novo.")
        r.raise_for_status()
        return cliente, r.json()["id"]

    alunos = await asyncio.gather(*(rascunho(i) for i in range(N)))

    # A submissão exige o aceite do orientador (RBN03.03).
    async with httpx.AsyncClient(timeout=60) as orientadora:
        await entrar(orientadora, "orientador@exemplo.com")
        pendentes = (await orientadora.get(f"{API}/orientacoes", params={"status": "PENDENTE"})).json()
        for s in pendentes:
            r = await orientadora.post(f"{API}/orientacoes/{s['id']}/resposta", json={"decisao": "ACEITAR"})
            r.raise_for_status()

    async def submeter(cliente: httpx.AsyncClient, tcc_id: int):
        inicio = time.perf_counter()
        r = await cliente.post(f"{API}/tccs/{tcc_id}/submissao")
        return time.perf_counter() - inicio, r.status_code, r.json().get("protocolo")

    resultados = await asyncio.gather(*(submeter(c, t) for c, t in alunos))
    for cliente, _ in alunos:
        await cliente.aclose()

    tempos = [r[0] for r in resultados]
    codigos = {r[1] for r in resultados}
    protocolos = {r[2] for r in resultados}
    p95 = statistics.quantiles(tempos, n=20)[-1]
    print(f"{N} submissões simultâneas · respostas {sorted(codigos)}")
    print(f"média {statistics.mean(tempos):.3f} s · p95 {p95:.3f} s · máximo {max(tempos):.3f} s")
    print(f"protocolos distintos: {len(protocolos)} de {N}")
    rnf01 = p95 < META_P95 and codigos == {200}
    rnf06 = len(protocolos) == N
    print("RNF01", "OK" if rnf01 else "FALHOU", "· RNF06 / CT-03.04-05", "OK" if rnf06 else "FALHOU")
    return 0 if rnf01 and rnf06 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
