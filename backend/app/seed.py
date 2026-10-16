"""Carga inicial mínima para desenvolvimento: python -m app.seed

Aplica as migrações (cria ou atualiza as tabelas), depois cria o núcleo, os três
cursos, as áreas de interesse, os perfis e o primeiro coordenador. Pode ser
rodado mais de uma vez.

Com --demo, cria também uma conta pronta por perfil (já ativa, senha Siga@2026),
para testar e apresentar sem depender do link de ativação:
    python -m app.seed --demo
Não use --demo no servidor de produção.

O primeiro coordenador nasce como qualquer usuário: sem senha. O script imprime
o link de ativação para você abrir no navegador e definir a senha.

O esquema do banco vem das migrações em migrations/ (Alembic), e não de
create_all, para o PostgreSQL de produção e o SQLite de desenvolvimento terem
exatamente as mesmas tabelas.
"""

import os
import sys

from sqlalchemy import select

from app import config
from app.database import SessionLocal
from app.migracoes import atualizar_banco
from app.security import gerar_hash_senha
from app.models import (
    PERFIL_ALUNO,
    PERFIL_BANCA,
    PERFIL_COORDENADOR,
    PERFIL_ORIENTADOR,
    PERFIL_PROFESSOR,
    PERFIS,
    TOKEN_ATIVACAO,
    Aluno,
    AreaInteresse,
    Curso,
    Docente,
    Nucleo,
    Perfil,
    Usuario,
    UsuarioPerfil,
)
from app.services import tokens
from app.services.usuarios import buscar_por_email

CURSOS = [
    ("EC", "Engenharia de Computação"),
    ("LC", "Licenciatura em Computação"),
    ("SI", "Sistemas de Informação"),
]
AREAS = [
    "IA",
    "Engenharia de Software",
    "Governança de TI",
    "Ciência de Dados",
    "Segurança da Informação",
    "Sistemas de Informação",
]


def carregar_base(db) -> Nucleo:
    """Núcleo, cursos, áreas e perfis. Só insere o que ainda não existe."""
    nucleo = db.scalar(select(Nucleo).where(Nucleo.sigla == "NUCOMP"))
    if nucleo is None:
        nucleo = Nucleo(sigla="NUCOMP", nome="Núcleo de Computação")
        db.add(nucleo)
        db.flush()
    for sigla, nome in CURSOS:
        if not db.scalar(select(Curso).where(Curso.sigla == sigla)):
            db.add(Curso(sigla=sigla, nome=nome, nucleo_id=nucleo.id))
    for nome in AREAS:
        if not db.scalar(select(AreaInteresse).where(AreaInteresse.nome == nome)):
            db.add(AreaInteresse(nome=nome))
    for codigo, nome in PERFIS.items():
        if not db.scalar(select(Perfil).where(Perfil.codigo == codigo)):
            db.add(Perfil(codigo=codigo, nome=nome))
    db.flush()
    return nucleo


def criar_coordenador(db, nucleo: Nucleo, nome: str, email: str) -> Usuario:
    usuario = Usuario(nome=nome, email=email.lower())
    db.add(usuario)
    db.flush()
    db.add(Docente(usuario_id=usuario.id, cargo="coordenador", nucleo_id=nucleo.id))
    for codigo in (PERFIL_COORDENADOR, PERFIL_PROFESSOR):
        perfil = db.scalar(select(Perfil).where(Perfil.codigo == codigo))
        db.add(UsuarioPerfil(usuario_id=usuario.id, perfil_id=perfil.id))
    return usuario


SENHA_DEMO = "Siga@2026"
# (nome, e-mail, cargo do docente ou None para aluno, perfis)
CONTAS_DEMO = [
    ("Carla Coordenadora", "coordenador@exemplo.com", "coordenador", [PERFIL_COORDENADOR]),
    ("Paulo Professor", "professor@exemplo.com", "professor", [PERFIL_PROFESSOR]),
    ("Olga Orientadora", "orientador@exemplo.com", "orientador", [PERFIL_ORIENTADOR]),
    ("Bruno Banca", "banca@exemplo.com", "professor", [PERFIL_BANCA]),
    ("Ana Aluna", "aluno@exemplo.com", None, [PERFIL_ALUNO]),
]


def criar_contas_demo(db, nucleo: Nucleo) -> None:
    curso = db.scalar(select(Curso).where(Curso.sigla == "EC"))
    senha_hash = gerar_hash_senha(SENHA_DEMO)
    print(f"Contas de demonstração (senha de todas: {SENHA_DEMO}):")
    for nome, email, cargo, perfis in CONTAS_DEMO:
        if buscar_por_email(db, email) is None:
            usuario = Usuario(nome=nome, email=email, senha_hash=senha_hash, ativo=True)
            db.add(usuario)
            db.flush()
            if cargo:
                # Coordenador acessa todos os cursos; os demais docentes ficam em EC.
                curso_id = None if cargo == "coordenador" else curso.id
                db.add(
                    Docente(
                        usuario_id=usuario.id, cargo=cargo, nucleo_id=nucleo.id, curso_id=curso_id
                    )
                )
            else:
                db.add(Aluno(usuario_id=usuario.id, matricula="2026000001", curso_id=curso.id))
            for codigo in perfis:
                perfil = db.scalar(select(Perfil).where(Perfil.codigo == codigo))
                db.add(UsuarioPerfil(usuario_id=usuario.id, perfil_id=perfil.id))
        print(f"  {email:<26} {', '.join(PERFIS[p] for p in perfis)}")
    print()


def main() -> None:
    atualizar_banco()
    nome = os.environ.get("SEED_COORDENADOR_NOME", "Coordenação NUCOMP")
    email = os.environ.get("SEED_COORDENADOR_EMAIL", "coordenacao@uea.edu.br")

    with SessionLocal() as db:
        nucleo = carregar_base(db)
        usuario = buscar_por_email(db, email)
        if usuario is None:
            usuario = criar_coordenador(db, nucleo, nome, email)
        if usuario.senha_hash is None:
            token = tokens.criar(db, usuario, TOKEN_ATIVACAO)
            print(f"\nPrimeiro coordenador: {usuario.email}")
            print("Abra o link abaixo para definir a senha (vale 48 horas):")
            print(f"{config.FRONTEND_URL}/ativar?token={token}\n")
        else:
            print(f"\nCarga inicial conferida. Coordenador já ativo: {usuario.email}\n")
        if "--demo" in sys.argv:
            criar_contas_demo(db, nucleo)
        db.commit()


if __name__ == "__main__":
    main()
