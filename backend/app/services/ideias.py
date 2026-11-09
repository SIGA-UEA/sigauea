"""Ideias de TCC: o aluno cadastra a proposta e a direciona; professores destinatários consultam e comentam
(RBN02.01 e RBN02.02 · RN07, RN25 · DS-FL12 e DS-FL12-A).

Faz o papel do ControladorIdeias do diagrama de classes (MOD02). Regras de visibilidade (RN07, RN25):
- o aluno vê as próprias propostas, com a discussão (CA-05 do RBN02.02);
- destino PROFESSORES: só os professores nomeados (CA-03 do RBN02.01);
- destino AREA: os professores vinculados à área de interesse (CA-04 do RBN02.01, RN25);
- quem não é destinatário recebe 403 ao abrir ou comentar (E1 e CA-04 do RBN02.02).

A proposta serve à discussão: não gera protocolo nem cadastro de TCC (CA-01 do RBN02.01).
Propostas e comentários ocultados pela moderação (RBN02.03, fora desta versão) não aparecem.
"""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.erros import ErroAPI
from app.models import (
    DESTINO_AREA,
    DESTINO_PROFESSORES,
    PERFIL_ALUNO,
    PERFIL_ORIENTADOR,
    PERFIL_PROFESSOR,
    AreaInteresse,
    ComentarioProposta,
    Docente,
    DocenteArea,
    Perfil,
    Proposta,
    PropostaDestinatario,
    Usuario,
    UsuarioPerfil,
)
from app.schemas.ideia import (
    ComentarioEntrada,
    ComentarioOut,
    FormularioIdeia,
    PropostaDetalhe,
    PropostaEntrada,
    PropostaResumo,
)
from app.schemas.usuario import AreaOut
from app.services import auditoria
from app.services.turmas import pessoa

PERFIS_DOCENTES = (PERFIL_PROFESSOR, PERFIL_ORIENTADOR)
SO_ALUNO = "Só alunos cadastram propostas de TCC."
SO_DESTINATARIO = "Esta proposta não foi direcionada a você."


def _eh_aluno(u: Usuario) -> bool:
    return PERFIL_ALUNO in u.perfis


def _eh_docente(u: Usuario) -> bool:
    return any(p in u.perfis for p in PERFIS_DOCENTES)


def _docentes_elegiveis(db: Session) -> list[Usuario]:
    """listarDocentesElegiveis(): professores da disciplina e orientadores ativos (DS-FL12 mensagem 4)."""
    return list(db.scalars(
        select(Usuario)
        .join(Docente, Docente.usuario_id == Usuario.id)
        .join(UsuarioPerfil, UsuarioPerfil.usuario_id == Usuario.id)
        .join(Perfil, Perfil.id == UsuarioPerfil.perfil_id)
        .where(Perfil.codigo.in_(PERFIS_DOCENTES), Usuario.inativado_em.is_(None), Usuario.senha_hash.is_not(None))
        .distinct()
        .order_by(Usuario.nome)
    ))


def formulario(db: Session, usuario: Usuario) -> FormularioIdeia:
    """GET /ideias/formulario (DS-FL12 mensagens 2 a 4)."""
    if not _eh_aluno(usuario):
        raise ErroAPI(403, SO_ALUNO)
    areas = db.scalars(select(AreaInteresse).order_by(AreaInteresse.nome))
    return FormularioIdeia(areas=[AreaOut.model_validate(a) for a in areas],
                           docentes=[pessoa(u) for u in _docentes_elegiveis(db)])


# =================================================================== visibilidade (RN07, RN25)


def _visivel_ao_docente(usuario: Usuario):
    """Condição SQL: proposta nomeada ao professor ou direcionada a uma área a que ele está vinculado."""
    nomeada = select(PropostaDestinatario.proposta_id).where(PropostaDestinatario.professor_id == usuario.id)
    areas = select(DocenteArea.area_id).where(DocenteArea.docente_id == usuario.id)
    return or_(
        (Proposta.destino == DESTINO_PROFESSORES) & Proposta.id.in_(nomeada),
        (Proposta.destino == DESTINO_AREA) & Proposta.area_id.in_(areas),
    )


def _eh_destinatario(db: Session, proposta: Proposta, usuario: Usuario) -> bool:
    """ehDestinatario(idIdeia, idProfessor) (DS-FL12-A mensagem 6)."""
    if not _eh_docente(usuario):
        return False
    if proposta.destino == DESTINO_PROFESSORES:
        return any(d.professor_id == usuario.id for d in proposta.destinatarios)
    return db.get(DocenteArea, (usuario.id, proposta.area_id)) is not None


def _obter(db: Session, proposta_id: int) -> Proposta:
    proposta = db.get(Proposta, proposta_id)
    if proposta is None or proposta.oculta_em is not None:
        raise ErroAPI(404, "Proposta não encontrada.")
    return proposta


# =================================================================== saída


def _comentarios_visiveis(proposta: Proposta) -> list[ComentarioProposta]:
    return [c for c in proposta.comentarios if c.oculto_em is None]


def _resumo(p: Proposta) -> dict:
    return dict(
        id=p.id, titulo=p.titulo, autor=pessoa(p.autor), criado_em=p.criado_em,
        area=AreaOut.model_validate(p.area) if p.area else None, destino=p.destino,
        professores=[pessoa(d.professor.usuario) for d in p.destinatarios],
        comentarios=len(_comentarios_visiveis(p)),
    )


def _detalhe(db: Session, p: Proposta, usuario: Usuario) -> PropostaDetalhe:
    return PropostaDetalhe(
        **_resumo(p), descricao=p.descricao,
        discussao=[ComentarioOut(id=c.id, autor=pessoa(c.autor), texto=c.texto, criado_em=c.criado_em)
                   for c in _comentarios_visiveis(p)],
        pode_comentar=_eh_destinatario(db, p, usuario),
    )


# =================================================================== RBN02.01 · cadastrar proposta


def criar(db: Session, usuario: Usuario, dados: PropostaEntrada) -> PropostaDetalhe:
    """POST /ideias (DS-FL12 mensagens 6 a 13)."""
    if not _eh_aluno(usuario):  # E2 / CA-05: outro perfil recebe 403
        raise ErroAPI(403, SO_ALUNO)
    titulo, descricao = dados.titulo.strip(), dados.descricao.strip()
    campos: dict[str, str] = {}
    if not titulo:
        campos["titulo"] = "Informe o título."
    if not descricao:
        campos["descricao"] = "Descreva a ideia."
    area = db.get(AreaInteresse, dados.area_id) if dados.area_id is not None else None
    if area is None:
        campos["area_id"] = "Escolha a área de interesse."
    if dados.destino is None:
        campos["destino"] = "Escolha para quem enviar: professores ou a área."
    professores: list[Usuario] = []
    if dados.destino == DESTINO_PROFESSORES:
        ids = list(dict.fromkeys(dados.professores_ids))  # sem repetidos, na ordem escolhida
        elegiveis = {u.id: u for u in _docentes_elegiveis(db)}
        if not ids:
            campos["professores_ids"] = "Escolha ao menos um professor."
        elif any(i not in elegiveis for i in ids):  # verificarPerfil(idsProfessores) (mensagem 8)
            campos["professores_ids"] = "Escolha professores da disciplina ou orientadores ativos."
        else:
            professores = [elegiveis[i] for i in ids]
    if campos:  # E1 / CA-02: destaca os campos e não cria a proposta
        raise ErroAPI(400, "Confira os campos destacados.", campos=campos)

    proposta = Proposta(autor_id=usuario.id, titulo=titulo, descricao=descricao, destino=dados.destino,
                        area_id=area.id)
    db.add(proposta)
    db.flush()
    for p in professores:  # criarPorProfessor: visível só a eles (mensagem 10)
        db.add(PropostaDestinatario(proposta_id=proposta.id, professor_id=p.id))
    destino = (f"professores: {', '.join(p.nome for p in professores)}" if professores
               else f"área: {area.nome}")
    auditoria.registrar(db, ator_id=usuario.id, acao="criar_ideia", entidade="proposta", entidade_id=proposta.id,
                        novo=f"{titulo} ({destino})")
    db.commit()
    db.refresh(proposta)
    return _detalhe(db, proposta, usuario)


# =================================================================== RBN02.02 · consultar e comentar


def listar(db: Session, usuario: Usuario) -> list[PropostaResumo]:
    """GET /ideias: o aluno vê as próprias; o professor, as direcionadas a ele (DS-FL12-A mensagem 3)."""
    consulta = select(Proposta).where(Proposta.oculta_em.is_(None)).order_by(Proposta.criado_em.desc(),
                                                                          Proposta.id.desc())
    if _eh_docente(usuario):
        filtro = _visivel_ao_docente(usuario)
        if _eh_aluno(usuario):
            filtro = or_(filtro, Proposta.autor_id == usuario.id)
        consulta = consulta.where(filtro)
    elif _eh_aluno(usuario):
        consulta = consulta.where(Proposta.autor_id == usuario.id)
    else:
        raise ErroAPI(403, "Ideias de TCC são para alunos, professores da disciplina e orientadores.")
    return [PropostaResumo(**_resumo(p)) for p in db.scalars(consulta)]


def consultar(db: Session, usuario: Usuario, proposta_id: int) -> PropostaDetalhe:
    """GET /ideias/{idIdeia} (DS-FL12-A mensagens 5 a 8)."""
    proposta = _obter(db, proposta_id)
    if proposta.autor_id != usuario.id and not _eh_destinatario(db, proposta, usuario):
        raise ErroAPI(403, SO_DESTINATARIO)  # E1: nega sem mostrar a proposta
    return _detalhe(db, proposta, usuario)


def comentar(db: Session, usuario: Usuario, proposta_id: int, dados: ComentarioEntrada) -> PropostaDetalhe:
    """POST /ideias/{idIdeia}/comentarios (DS-FL12-A mensagens 10 a 12)."""
    proposta = _obter(db, proposta_id)
    if not _eh_destinatario(db, proposta, usuario):  # CA-04: só o professor destinatário comenta
        raise ErroAPI(403, SO_DESTINATARIO)
    texto = dados.texto.strip()
    if not texto:  # E2 / CA-03: vazio ou só espaços
        raise ErroAPI(400, "Confira os campos destacados.", campos={"texto": "Escreva o comentário."})
    comentario = ComentarioProposta(proposta_id=proposta.id, autor_id=usuario.id, texto=texto)
    db.add(comentario)
    db.flush()
    auditoria.registrar(db, ator_id=usuario.id, acao="comentar_ideia", entidade="comentario_proposta",
                        entidade_id=comentario.id, campo=f"proposta {proposta.id}", novo=texto)
    db.commit()
    db.refresh(proposta)
    return _detalhe(db, proposta, usuario)
