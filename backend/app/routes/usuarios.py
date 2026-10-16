"""Rotas da TEL02 (Usuários e perfis). Todas exigem o perfil coordenador (403 para os demais)."""

from fastapi import APIRouter, BackgroundTasks, Depends, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import coordenador
from app.models import Usuario
from app.routes.perfil import ler_imagem
from app.schemas.usuario import AlunoCriar, DocenteCriar, UsuarioAtualizar, UsuarioOut
from app.services import perfil, usuarios

router = APIRouter(tags=["usuários"])


@router.post("/docentes", response_model=UsuarioOut, status_code=201)
def criar_docente(
    dados: DocenteCriar,
    tarefas: BackgroundTasks,
    db: Session = Depends(get_db),
    ator: Usuario = Depends(coordenador),
) -> UsuarioOut:
    return usuarios.para_saida(usuarios.criar_docente(db, tarefas, dados, ator))


@router.get("/docentes", response_model=list[UsuarioOut])
def listar_docentes(
    curso: int | None = None,
    cargo: str | None = None,
    busca: str | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(coordenador),
) -> list[UsuarioOut]:
    return [usuarios.para_saida(u) for u in usuarios.listar_docentes(db, curso, cargo, busca)]


@router.post("/alunos", response_model=UsuarioOut, status_code=201)
def criar_aluno(
    dados: AlunoCriar,
    tarefas: BackgroundTasks,
    db: Session = Depends(get_db),
    ator: Usuario = Depends(coordenador),
) -> UsuarioOut:
    return usuarios.para_saida(usuarios.criar_aluno(db, tarefas, dados, ator))


@router.get("/alunos", response_model=list[UsuarioOut])
def listar_alunos(
    curso: int | None = None,
    busca: str | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(coordenador),
) -> list[UsuarioOut]:
    return [usuarios.para_saida(u) for u in usuarios.listar_alunos(db, curso, busca)]


@router.get("/docentes/{usuario_id}", response_model=UsuarioOut)
@router.get("/alunos/{usuario_id}", response_model=UsuarioOut)
def obter_usuario(
    usuario_id: int, db: Session = Depends(get_db), _: Usuario = Depends(coordenador)
) -> UsuarioOut:
    return usuarios.para_saida(usuarios.obter(db, usuario_id))


@router.put("/usuarios/{usuario_id}", response_model=UsuarioOut)
def atualizar_usuario(
    usuario_id: int,
    dados: UsuarioAtualizar,
    db: Session = Depends(get_db),
    ator: Usuario = Depends(coordenador),
) -> UsuarioOut:
    return usuarios.para_saida(usuarios.atualizar(db, usuario_id, dados, ator))


@router.patch("/usuarios/{usuario_id}/inativar", response_model=UsuarioOut)
def inativar_usuario(
    usuario_id: int, db: Session = Depends(get_db), ator: Usuario = Depends(coordenador)
) -> UsuarioOut:
    return usuarios.para_saida(usuarios.inativar(db, usuario_id, ator))


@router.patch("/usuarios/{usuario_id}/reativar", response_model=UsuarioOut)
def reativar_usuario(
    usuario_id: int, db: Session = Depends(get_db), ator: Usuario = Depends(coordenador)
) -> UsuarioOut:
    return usuarios.para_saida(usuarios.reativar(db, usuario_id, ator))


@router.post("/usuarios/{usuario_id}/reenviar-ativacao", response_model=UsuarioOut)
def reenviar_ativacao(
    usuario_id: int,
    tarefas: BackgroundTasks,
    db: Session = Depends(get_db),
    ator: Usuario = Depends(coordenador),
) -> UsuarioOut:
    return usuarios.para_saida(usuarios.reenviar_ativacao(db, tarefas, usuario_id, ator))


# RBN01.01: a coordenação pode incluir a foto (opcional) no cadastro do docente.
@router.put("/usuarios/{usuario_id}/foto", response_model=UsuarioOut)
async def trocar_foto(
    usuario_id: int,
    foto: UploadFile,
    db: Session = Depends(get_db),
    ator: Usuario = Depends(coordenador),
) -> UsuarioOut:
    alvo = usuarios.obter(db, usuario_id)
    return usuarios.para_saida(perfil.salvar_foto(db, alvo, await ler_imagem(foto), ator))


@router.delete("/usuarios/{usuario_id}/foto", response_model=UsuarioOut)
def remover_foto(
    usuario_id: int, db: Session = Depends(get_db), ator: Usuario = Depends(coordenador)
) -> UsuarioOut:
    return usuarios.para_saida(perfil.remover_foto(db, usuarios.obter(db, usuario_id), ator))
