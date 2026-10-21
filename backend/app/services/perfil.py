"""Meu perfil: cada pessoa edita os próprios dados (RBN01.09 e RBN01.10), troca a
senha e cuida da foto. A coordenação também pode trocar a foto de um docente
(RBN01.01).

Nome, e-mail e matrícula ficam de fora: só a coordenação altera (RBN01.08).
"""

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.database import agora
from app.erros import ErroAPI
from app.models import (
    PERFIL_COORDENADOR,
    PERFIL_ORIENTADOR,
    PERFIL_PROFESSOR,
    FotoUsuario,
    Sessao,
    Usuario,
)
from app.schemas.usuario import MeuPerfilAtualizar, TrocarSenhaEntrada
from app.security import gerar_hash_senha, hash_token, validate_password, verificar_senha
from app.services import auditoria
from app.services.usuarios import (
    areas_validas,
    confirmar,
    curso_valido,
    exigir_curso_se_nao_coordenador,
)

# RN25: só quem orienta ou dá a disciplina escolhe as próprias áreas de interesse.
_PERFIS_COM_AREAS = {PERFIL_ORIENTADOR, PERFIL_PROFESSOR}


def atualizar(db: Session, usuario: Usuario, dados: MeuPerfilAtualizar) -> Usuario:
    enviados = dados.model_fields_set
    docente = usuario.docente
    mudancas: list[tuple[str, object, object]] = []

    if "telefone" in enviados:
        novo = dados.telefone or None
        if novo != usuario.telefone:
            mudancas.append(("telefone", usuario.telefone, novo))
            usuario.telefone = novo

    if "curso_id" in enviados:
        # RBN01.09: o curso do aluno vem do cadastro da coordenação.
        if docente is None:
            raise ErroAPI(403, "O curso só pode ser alterado pela coordenação.")
        # SCRUM-30: o coordenador pertence ao núcleo e acessa todos os cursos dele.
        if PERFIL_COORDENADOR in usuario.perfis:
            raise ErroAPI(403, "Para o coordenador o curso não se aplica.")
        if dados.curso_id != docente.curso_id:
            curso = curso_valido(db, dados.curso_id) if dados.curso_id else None
            exigir_curso_se_nao_coordenador(usuario.perfis, curso.id if curso else None)
            anterior = docente.curso.nome if docente.curso else None
            mudancas.append(("curso", anterior, curso.nome if curso else None))
            docente.curso = curso

    if dados.areas is not None:
        if docente is None or not _PERFIS_COM_AREAS & set(usuario.perfis):
            raise ErroAPI(403, "Seu perfil não escolhe áreas de interesse.")
        areas = areas_validas(db, dados.areas)
        antes = ", ".join(sorted(a.nome for a in docente.areas)) or None
        depois = ", ".join(sorted(a.nome for a in areas)) or None
        if antes != depois:
            mudancas.append(("areas", antes, depois))
            docente.areas = areas

    for campo, anterior, novo in mudancas:
        auditoria.registrar(
            db,
            ator_id=usuario.id,
            acao="editar_meu_perfil",
            entidade_id=usuario.id,
            campo=campo,
            anterior=anterior,
            novo=novo,
        )
    confirmar(db)
    db.refresh(usuario)
    return usuario


def trocar_senha(
    db: Session, usuario: Usuario, dados: TrocarSenhaEntrada, token_atual: str | None
) -> None:
    if not verificar_senha(dados.senha_atual, usuario.senha_hash):
        auditoria.registrar(
            db, ator_id=usuario.id, acao="trocar_senha_falha", entidade_id=usuario.id
        )
        db.commit()
        raise ErroAPI(
            400,
            "Confira os campos destacados.",
            campos={"senha_atual": "Senha atual incorreta."},
        )
    faltando = validate_password(dados.nova_senha)
    if faltando:
        raise ErroAPI(422, "A senha não atende aos critérios.", criterios=faltando)

    usuario.senha_hash = gerar_hash_senha(dados.nova_senha)
    # As outras sessões abertas (outro navegador, outro aparelho) são encerradas.
    hash_atual = hash_token(token_atual) if token_atual else None
    for sessao in db.scalars(select(Sessao).where(Sessao.usuario_id == usuario.id)):
        if sessao.token_hash != hash_atual:
            sessao.expira_em = agora()
    auditoria.registrar(db, ator_id=usuario.id, acao="trocar_senha", entidade_id=usuario.id)
    db.commit()


# ---------- foto ----------

# Os primeiros bytes dizem o formato de verdade, não a extensão do arquivo.
_ASSINATURAS = [
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
]


def _tipo_da_imagem(conteudo: bytes) -> str | None:
    for inicio, tipo in _ASSINATURAS:
        if conteudo.startswith(inicio):
            return tipo
    if conteudo[:4] == b"RIFF" and conteudo[8:12] == b"WEBP":
        return "image/webp"
    return None


def salvar_foto(db: Session, usuario: Usuario, conteudo: bytes, ator: Usuario) -> Usuario:
    if not conteudo:
        raise ErroAPI(400, "O arquivo está vazio.", campo="foto")
    if len(conteudo) > config.FOTO_MAX_BYTES:
        raise ErroAPI(413, "A imagem passa de 5 MB. Escolha uma menor.", campo="foto")
    tipo = _tipo_da_imagem(conteudo)
    if tipo is None:
        raise ErroAPI(415, "Escolha uma imagem JPG, PNG ou WebP.", campo="foto")

    sha256 = hashlib.sha256(conteudo).hexdigest()
    anterior = usuario.foto.sha256 if usuario.foto else None
    if usuario.foto is None:
        usuario.foto = FotoUsuario(tipo=tipo, conteudo=conteudo, sha256=sha256)
    else:
        usuario.foto.tipo, usuario.foto.conteudo, usuario.foto.sha256 = tipo, conteudo, sha256
        usuario.foto.atualizado_em = agora()
    auditoria.registrar(
        db,
        ator_id=ator.id,
        acao="alterar_foto",
        entidade_id=usuario.id,
        campo="foto_sha256",
        anterior=anterior,
        novo=sha256,
    )
    db.commit()
    return usuario


def remover_foto(db: Session, usuario: Usuario, ator: Usuario) -> Usuario:
    if usuario.foto is not None:
        auditoria.registrar(
            db,
            ator_id=ator.id,
            acao="remover_foto",
            entidade_id=usuario.id,
            campo="foto_sha256",
            anterior=usuario.foto.sha256,
        )
        usuario.foto = None
        db.commit()
    return usuario


def obter_foto(db: Session, usuario_id: int) -> FotoUsuario:
    foto = db.get(FotoUsuario, usuario_id)
    if foto is None:
        raise ErroAPI(404, "Sem foto.")
    # RNF06: o SHA-256 gravado no envio é conferido também na leitura; arquivo alterado não é entregue.
    if hashlib.sha256(foto.conteudo).hexdigest() != foto.sha256:
        raise ErroAPI(500, "O arquivo da foto não confere com o original. Envie a foto de novo.")
    return foto
