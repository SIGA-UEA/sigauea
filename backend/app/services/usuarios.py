"""Regras de cadastro, edição e inativação de usuários (HU01.01, HU01.03, HU01.08)."""

from fastapi import BackgroundTasks
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import agora
from app.erros import ErroAPI
from app.models import (
    PERFIL_ALUNO,
    PERFIL_COORDENADOR,
    PERFIS_DOCENTE,
    TOKEN_ATIVACAO,
    Aluno,
    AreaInteresse,
    Curso,
    Docente,
    Perfil,
    Sessao,
    Usuario,
    UsuarioPerfil,
)
from app.schemas.usuario import AlunoCriar, DocenteCriar, UsuarioAtualizar, UsuarioOut
from app.services import auditoria, tokens

# ---------- leitura ----------


def para_saida(usuario: Usuario) -> UsuarioOut:
    docente, aluno = usuario.docente, usuario.aluno
    ativacoes = [n for n in usuario.notificacoes if n.tipo == TOKEN_ATIVACAO]
    return UsuarioOut(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        telefone=usuario.telefone,
        tipo="aluno" if aluno else "docente",
        situacao=usuario.situacao,
        perfis=usuario.perfis,
        cargo=docente.cargo if docente else None,
        matricula=aluno.matricula if aluno else None,
        curso=(aluno.curso if aluno else docente.curso if docente else None),
        areas=docente.areas if docente else [],
        email_ativacao=ativacoes[-1].status if ativacoes else None,
        foto_versao=usuario.foto.sha256[:12] if usuario.foto else None,
        criado_em=usuario.criado_em,
    )


def buscar_por_email(db: Session, email: str) -> Usuario | None:
    return db.scalar(select(Usuario).where(func.lower(Usuario.email) == email.strip().lower()))


def obter(db: Session, usuario_id: int) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise ErroAPI(404, "Usuário não encontrado.")
    return usuario


def _contem(busca: str, *colunas):
    termo = f"%{busca.strip().lower()}%"
    return or_(*(func.lower(c).like(termo) for c in colunas))


def listar_docentes(
    db: Session, curso: int | None, cargo: str | None, busca: str | None
) -> list[Usuario]:
    consulta = select(Usuario).join(Docente).order_by(Usuario.nome)
    if curso:
        consulta = consulta.where(Docente.curso_id == curso)
    if cargo:
        consulta = consulta.where(Docente.cargo == cargo)
    if busca:
        consulta = consulta.where(_contem(busca, Usuario.nome, Usuario.email))
    return list(db.scalars(consulta))


def listar_alunos(db: Session, curso: int | None, busca: str | None) -> list[Usuario]:
    consulta = select(Usuario).join(Aluno).order_by(Usuario.nome)
    if curso:
        consulta = consulta.where(Aluno.curso_id == curso)
    if busca:
        consulta = consulta.where(_contem(busca, Usuario.nome, Usuario.email, Aluno.matricula))
    return list(db.scalars(consulta))


# ---------- validações compartilhadas ----------


def _exigir_email_livre(db: Session, email: str, exceto_id: int | None = None) -> None:
    existente = buscar_por_email(db, email)
    if existente and existente.id != exceto_id:
        raise ErroAPI(409, "Este e-mail já está cadastrado.", campo="email")


def _exigir_matricula_livre(db: Session, matricula: str, exceto_id: int | None = None) -> None:
    existente = db.scalar(select(Aluno).where(Aluno.matricula == matricula))
    if existente and existente.usuario_id != exceto_id:
        raise ErroAPI(409, "Esta matrícula já está cadastrada.", campo="matricula")


def curso_valido(db: Session, curso_id: int) -> Curso:
    # Só existem no banco os cursos contemplados (RN01), vindos da carga inicial.
    curso = db.get(Curso, curso_id)
    if curso is None:
        raise ErroAPI(400, "Confira os campos destacados.", campos={"curso_id": "Curso inválido."})
    return curso


def areas_validas(db: Session, ids: list[int]) -> list[AreaInteresse]:
    areas = list(db.scalars(select(AreaInteresse).where(AreaInteresse.id.in_(ids))))
    if len(areas) != len(set(ids)):
        raise ErroAPI(400, "Confira os campos destacados.", campos={"areas": "Área inválida."})
    return areas


def _perfis_docente(db: Session, codigos: list[str]) -> list[Perfil]:
    if not set(codigos) <= set(PERFIS_DOCENTE):
        raise ErroAPI(400, "Confira os campos destacados.", campos={"perfis": "Perfil inválido."})
    return list(db.scalars(select(Perfil).where(Perfil.codigo.in_(codigos))))


def exigir_curso_se_nao_coordenador(perfis: list[str], curso_id: int | None) -> None:
    # HU01.01 R5: o coordenador acessa todos os cursos do núcleo, então não tem curso.
    if PERFIL_COORDENADOR not in perfis and curso_id is None:
        raise ErroAPI(
            400, "Confira os campos destacados.", campos={"curso_id": "Campo obrigatório."}
        )


def confirmar(db: Session) -> None:
    """Commit. Se dois cadastros iguais chegarem juntos, o índice único do banco barra o segundo."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ErroAPI(409, "E-mail ou matrícula já cadastrados.") from None


# ---------- cadastro ----------


def criar_docente(
    db: Session, tarefas: BackgroundTasks, dados: DocenteCriar, ator: Usuario
) -> Usuario:
    _exigir_email_livre(db, dados.email)
    perfis = _perfis_docente(db, dados.perfis)
    exigir_curso_se_nao_coordenador(dados.perfis, dados.curso_id)
    curso = curso_valido(db, dados.curso_id) if dados.curso_id else None
    areas = areas_validas(db, dados.areas)

    # A conta nasce sem senha e inativa (R4); a pessoa ativa pelo link.
    usuario = Usuario(nome=dados.nome, email=dados.email.lower(), telefone=dados.telefone or None)
    db.add(usuario)
    db.flush()
    db.add(
        Docente(
            usuario_id=usuario.id,
            cargo=dados.cargo,
            nucleo_id=ator.docente.nucleo_id,  # mesmo núcleo de quem cadastra
            curso_id=curso.id if curso else None,
            areas=areas,
        )
    )
    for perfil in perfis:
        db.add(UsuarioPerfil(usuario_id=usuario.id, perfil_id=perfil.id, atribuido_por=ator.id))

    novos = {
        "nome": usuario.nome,
        "email": usuario.email,
        "telefone": usuario.telefone,
        "cargo": dados.cargo,
        "curso": curso.nome if curso else None,
        "areas": ", ".join(a.nome for a in areas) or None,
        "perfis": ", ".join(sorted(dados.perfis)),
    }
    _auditar_criacao(db, ator, usuario, "criar_docente", novos)
    tokens.enviar_ativacao(db, tarefas, usuario)
    confirmar(db)
    return usuario


def criar_aluno(db: Session, tarefas: BackgroundTasks, dados: AlunoCriar, ator: Usuario) -> Usuario:
    _exigir_matricula_livre(db, dados.matricula)
    _exigir_email_livre(db, dados.email)
    curso = curso_valido(db, dados.curso_id)
    perfil = db.scalar(select(Perfil).where(Perfil.codigo == PERFIL_ALUNO))

    usuario = Usuario(nome=dados.nome, email=dados.email.lower())
    db.add(usuario)
    db.flush()
    db.add(Aluno(usuario_id=usuario.id, matricula=dados.matricula, curso_id=curso.id))
    db.add(UsuarioPerfil(usuario_id=usuario.id, perfil_id=perfil.id, atribuido_por=ator.id))

    novos = {
        "nome": usuario.nome,
        "email": usuario.email,
        "matricula": dados.matricula,
        "curso": curso.nome,
        "perfis": PERFIL_ALUNO,
    }
    _auditar_criacao(db, ator, usuario, "criar_aluno", novos)
    tokens.enviar_ativacao(db, tarefas, usuario)
    confirmar(db)
    return usuario


def _auditar_criacao(db: Session, ator: Usuario, usuario: Usuario, acao: str, novos: dict) -> None:
    for campo, valor in novos.items():
        if valor is not None:
            auditoria.registrar(
                db, ator_id=ator.id, acao=acao, entidade_id=usuario.id, campo=campo, novo=valor
            )


# ---------- edição e inativação ----------


def atualizar(db: Session, usuario_id: int, dados: UsuarioAtualizar, ator: Usuario) -> Usuario:
    usuario = obter(db, usuario_id)
    docente, aluno = usuario.docente, usuario.aluno
    enviados = dados.model_fields_set
    mudancas: list[tuple[str, object, object]] = []  # (campo, anterior, novo)

    def mudar(campo: str, anterior: object, novo: object) -> bool:
        if anterior != novo:
            mudancas.append((campo, anterior, novo))
            return True
        return False

    if dados.nome is not None and mudar("nome", usuario.nome, dados.nome):
        usuario.nome = dados.nome

    if dados.email is not None and mudar("email", usuario.email, dados.email.lower()):
        _exigir_email_livre(db, dados.email, exceto_id=usuario.id)
        usuario.email = dados.email.lower()

    if "telefone" in enviados and mudar("telefone", usuario.telefone, dados.telefone or None):
        usuario.telefone = dados.telefone or None

    if aluno:
        if dados.matricula is not None and mudar("matricula", aluno.matricula, dados.matricula):
            _exigir_matricula_livre(db, dados.matricula, exceto_id=usuario.id)
            aluno.matricula = dados.matricula
        if dados.curso_id is not None and dados.curso_id != aluno.curso_id:
            curso = curso_valido(db, dados.curso_id)
            mudar("curso", aluno.curso.nome, curso.nome)
            aluno.curso = curso

    if docente:
        if dados.cargo is not None and mudar("cargo", docente.cargo, dados.cargo):
            docente.cargo = dados.cargo

        if dados.perfis is not None and set(dados.perfis) != set(usuario.perfis):
            # HU01.01 R2: ninguém atribui perfil a si mesmo.
            if usuario.id == ator.id:
                raise ErroAPI(403, "Você não pode alterar os seus próprios perfis.")
            novos_perfis = _perfis_docente(db, dados.perfis)
            mudar("perfis", ", ".join(usuario.perfis), ", ".join(sorted(dados.perfis)))
            atuais = {v.perfil.codigo: v for v in usuario.vinculos_perfil}
            for codigo, vinculo in atuais.items():
                if codigo not in dados.perfis:
                    db.delete(vinculo)
            for perfil in novos_perfis:
                if perfil.codigo not in atuais:
                    db.add(
                        UsuarioPerfil(
                            usuario_id=usuario.id, perfil_id=perfil.id, atribuido_por=ator.id
                        )
                    )

        if "curso_id" in enviados and dados.curso_id != docente.curso_id:
            curso = curso_valido(db, dados.curso_id) if dados.curso_id else None
            mudar("curso", docente.curso.nome if docente.curso else None, curso.nome if curso else None)
            docente.curso = curso
        perfis_finais = dados.perfis if dados.perfis is not None else usuario.perfis
        exigir_curso_se_nao_coordenador(perfis_finais, docente.curso.id if docente.curso else None)

        if dados.areas is not None:
            areas = areas_validas(db, dados.areas)
            nomes = lambda lista: ", ".join(sorted(a.nome for a in lista)) or None  # noqa: E731
            if mudar("areas", nomes(docente.areas), nomes(areas)):
                docente.areas = areas

    # HU01.08 R2: cada alteração vai para o log com o valor anterior e o novo.
    for campo, anterior, novo in mudancas:
        auditoria.registrar(
            db,
            ator_id=ator.id,
            acao="editar_usuario",
            entidade_id=usuario.id,
            campo=campo,
            anterior=anterior,
            novo=novo,
        )
    confirmar(db)
    db.refresh(usuario)
    return usuario


def inativar(db: Session, usuario_id: int, ator: Usuario) -> Usuario:
    usuario = obter(db, usuario_id)
    if usuario.id == ator.id:
        raise ErroAPI(409, "Você não pode inativar a própria conta.")
    if usuario.inativado_em is None:
        usuario.inativado_em = agora()
        usuario.ativo = False
        # Derruba as sessões abertas: o acesso é bloqueado na hora.
        for sessao in db.scalars(select(Sessao).where(Sessao.usuario_id == usuario.id)):
            sessao.expira_em = agora()
        auditoria.registrar(
            db,
            ator_id=ator.id,
            acao="inativar_usuario",
            entidade_id=usuario.id,
            campo="situacao",
            anterior="ativo" if usuario.senha_hash else "aguardando_ativacao",
            novo="inativo",
        )
        db.commit()
    return usuario


def reativar(db: Session, usuario_id: int, ator: Usuario) -> Usuario:
    usuario = obter(db, usuario_id)
    if usuario.inativado_em is not None:
        usuario.inativado_em = None
        # Quem nunca definiu senha volta para "aguardando ativação".
        usuario.ativo = usuario.senha_hash is not None
        auditoria.registrar(
            db,
            ator_id=ator.id,
            acao="reativar_usuario",
            entidade_id=usuario.id,
            campo="situacao",
            anterior="inativo",
            novo=usuario.situacao,
        )
        db.commit()
    return usuario


def reenviar_ativacao(
    db: Session, tarefas: BackgroundTasks, usuario_id: int, ator: Usuario
) -> Usuario:
    usuario = obter(db, usuario_id)
    if usuario.situacao != "aguardando_ativacao":
        raise ErroAPI(409, "Só é possível reenviar para contas que aguardam ativação.")
    tokens.enviar_ativacao(db, tarefas, usuario)
    auditoria.registrar(db, ator_id=ator.id, acao="reenviar_ativacao", entidade_id=usuario.id)
    db.commit()
    return usuario
