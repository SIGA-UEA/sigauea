"""Banca e agendamento da defesa (Sprint S04 · RBN09.01, RN07, RN12, RN14).

ControladorAgendamentoDefesa dos diagramas FL04. A banca é montada na tela (DS-FL04-A/B) e
gravada junto com a defesa na confirmação (DS-FL04 passo 16), porque no modelo de dados todo
membro da banca pertence a uma defesa (banca_membro.defesa_id obrigatório).

Ficam para as próximas histórias: conflitos de agenda (SCRUM-62), validações completas de data,
link e duração (SCRUM-61), convites por e-mail (SCRUM-63) e a conta limitada do externo (SCRUM-32).

Pendência: o DS-FL04 (passo 5) confere a versão do PDF para banca antes de agendar. A tabela
documento_tcc ainda não existe; a conferência entra junto com o envio do PDF (SCRUM-55, RBN07.01).

Quem agenda (RN14): professor da disciplina em SI, orientador nos demais cursos e a coordenação,
como pedem o E4 e o CA-05 da ficha RBN09.01 e a planilha de requisitos (FL04).
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.erros import ErroAPI
from app.models import (
    ACEITA,
    CANCELADA,
    CONFIRMADA,
    PAPEL_AVALIADOR,
    PAPEL_COORIENTADOR,
    PAPEL_ORIENTADOR,
    PAPEL_SUPLENTE,
    PERFIL_BANCA,
    PERFIL_COORDENADOR,
    PERFIL_PROFESSOR,
    REMARCADA,
    BancaMembro,
    Defesa,
    HistoricoDefesa,
    LocalDefesa,
    Orientacao,
    Perfil,
    Tcc,
    Usuario,
    UsuarioExterno,
    UsuarioPerfil,
)
from app.schemas.defesa import (
    BancaOut,
    DefesaCriar,
    DefesaOut,
    LocalOut,
    MembroEntrada,
    MembroOut,
    PessoaBanca,
    ValidarMembro,
)
from app.schemas.tcc import PessoaOut
from app.services import auditoria
from app.services.tccs import obter_para
from app.services.turmas import pessoa
from app.services.usuarios import buscar_por_email

APROVADO = "APROVADO"
CURSO_PROFESSOR_AGENDA = "SI"  # RN14: em SI quem agenda é o professor da disciplina
ALTERAVEIS = (CONFIRMADA, REMARCADA)  # CA-06: a banca pode mudar antes da defesa acontecer


# =================================================================== RN14 · quem compõe e agenda


def _orientacao_aceita(tcc: Tcc, papel: str) -> Orientacao | None:
    return next(
        (o for o in tcc.orientacoes if o.papel == papel and o.status == ACEITA and o.encerrado_em is None),
        None,
    )


def pode_agendar(usuario: Usuario, tcc: Tcc) -> bool:
    """RN14: professor da disciplina em SI; orientador nos demais cursos; a coordenação sempre."""
    if PERFIL_COORDENADOR in usuario.perfis:
        return True
    if tcc.aluno.curso.sigla == CURSO_PROFESSOR_AGENDA:
        return PERFIL_PROFESSOR in usuario.perfis and tcc.turma.professor_id == usuario.id
    orientador = _orientacao_aceita(tcc, PAPEL_ORIENTADOR)
    return orientador is not None and orientador.professor_id == usuario.id


def _exigir_responsavel(usuario: Usuario, tcc: Tcc) -> None:
    if not pode_agendar(usuario, tcc):  # DS-FL04-A E4 · DS-FL04 passo 17
        raise ErroAPI(403, "Neste curso, quem compõe a banca e agenda a defesa é outro responsável (RN14).")
    if tcc.situacao != APROVADO:  # DS-FL04-A E1
        raise ErroAPI(409, "Etapa ainda não liberada: o cadastro do TCC precisa estar aprovado.")


def defesa_vigente(tcc_id: int, db: Session) -> Defesa | None:
    """A defesa que vale para o TCC: a mais recente que não foi cancelada."""
    return db.scalar(
        select(Defesa)
        .where(Defesa.tcc_id == tcc_id, Defesa.situacao != CANCELADA)
        .order_by(Defesa.id.desc())
        .limit(1)
    )


# =================================================================== saída


def _local_out(local: LocalDefesa | None) -> LocalOut | None:
    return LocalOut(id=local.id, nome=local.nome, descricao=local.descricao) if local else None


def _instituicao(db: Session, usuario: Usuario) -> str | None:
    externo = db.get(UsuarioExterno, usuario.id)
    return externo.instituicao if externo else None


def _membro_out(db: Session, m: BancaMembro) -> MembroOut:
    return MembroOut(
        id=m.id,
        papel=m.papel,
        pessoa=pessoa(m.usuario),
        email=m.usuario.email,
        interno=m.interno,
        instituicao=None if m.interno else _instituicao(db, m.usuario),
        convite_enviado_em=m.convite_enviado_em,
    )


# Ordem de exibição da banca: as vagas fixas, os dois avaliadores e, por último, o suplente.
ORDEM_PAPEIS = {p: i for i, p in enumerate((PAPEL_ORIENTADOR, PAPEL_COORIENTADOR, PAPEL_AVALIADOR, PAPEL_SUPLENTE))}


def defesa_out(db: Session, d: Defesa) -> DefesaOut:
    return DefesaOut(
        id=d.id,
        situacao=d.situacao,
        formato=d.formato,
        data=d.data,
        inicio=d.inicio,
        fim=d.fim,
        local=_local_out(d.local),
        link=d.link,
        publicada=d.publicada,
        responsavel=pessoa(d.responsavel.usuario),
        membros=[_membro_out(db, m) for m in sorted(d.membros, key=lambda m: (ORDEM_PAPEIS[m.papel], m.id))],
        criado_em=d.criado_em,
    )


def _avaliadores_elegiveis(db: Session, tcc: Tcc) -> list[Usuario]:
    """Decisão E: qualquer docente ativo pode ser avaliador ou suplente; o autor do TCC não."""
    docentes = db.scalars(select(Usuario).join(Usuario.docente).where(Usuario.ativo.is_(True)).order_by(Usuario.nome))
    return [u for u in docentes if u.id != tcc.aluno_id]


# =================================================================== DS-FL04-A · consultar a banca


def consultar(db: Session, usuario: Usuario, tcc_id: int) -> BancaOut:
    """GET /tccs/{id}/banca (passos 3 a 5). Quem não vê o TCC recebe 404 (RN07)."""
    tcc = obter_para(db, usuario, tcc_id)
    defesa = defesa_vigente(tcc.id, db)
    liberada = tcc.situacao == APROVADO
    orientador = _orientacao_aceita(tcc, PAPEL_ORIENTADOR)
    coorientador = _orientacao_aceita(tcc, PAPEL_COORIENTADOR)
    return BancaOut(
        tcc_id=tcc.id,
        etapa=tcc.etapa,
        liberada=liberada,
        pode_editar=liberada and pode_agendar(usuario, tcc),
        orientador=pessoa(orientador.professor) if orientador else None,
        coorientador=pessoa(coorientador.professor) if coorientador else None,
        docentes=[pessoa(u) for u in _avaliadores_elegiveis(db, tcc)],
        locais=[_local_out(l) for l in db.scalars(select(LocalDefesa).order_by(LocalDefesa.nome))],
        defesa=defesa_out(db, defesa) if defesa else None,
    )


# =================================================================== RN12 · composição


def _resolver(db: Session, tcc: Tcc, p: PessoaBanca) -> tuple[Usuario | None, bool, str | None]:
    """Quem ocupa a vaga: (usuário já cadastrado ou None se o externo é novo, interno?, instituição)."""
    if p.usuario_id is not None:
        usuario = db.get(Usuario, p.usuario_id)
        if usuario is None or usuario.docente is None or not usuario.ativo:  # DS-FL04-A passo 9
            raise ErroAPI(422, "Escolha um docente ativo da UEA.", campo="usuario_id")
        if usuario.id == tcc.aluno_id:
            raise ErroAPI(422, "O autor do TCC não pode fazer parte da banca.", campo="usuario_id")
        return usuario, True, None

    externo = p.externo
    usuario = buscar_por_email(db, externo.email)  # DS-FL04-B passo 5
    if usuario is not None and db.get(UsuarioExterno, usuario.id) is None:
        raise ErroAPI(
            422,
            "Este e-mail já é de alguém da UEA. Escolha a pessoa em \"Docente da UEA\".",
            campo="email",
        )
    return usuario, False, externo.instituicao


def _chave(p: PessoaBanca) -> str:
    """Identifica a pessoa da vaga para achar repetições: o id do docente ou o e-mail do externo."""
    return f"u{p.usuario_id}" if p.usuario_id is not None else f"e{p.externo.email.lower()}"


def _chave_usuario(u: Usuario) -> str:
    return f"u{u.id}" if u.docente is not None else f"e{u.email.lower()}"


def _conferir_vaga(db: Session, tcc: Tcc, m: MembroEntrada) -> tuple[Usuario | None, bool, str | None]:
    """Regras de uma vaga isolada: pessoa válida e, nas vagas fixas, a pessoa vinculada ao TCC."""
    usuario, interno, instituicao = _resolver(db, tcc, m)
    for papel, rotulo in ((PAPEL_ORIENTADOR, "orientador"), (PAPEL_COORIENTADOR, "coorientador")):
        if m.papel != papel:
            continue
        vinculo = _orientacao_aceita(tcc, papel)
        if vinculo is None:
            raise ErroAPI(422, f"Este TCC não tem {rotulo} vinculado.", campo="papel")
        if usuario is None or usuario.id != vinculo.professor_id:  # CA-04
            raise ErroAPI(422, f"O {rotulo} da banca deve ser o mesmo vinculado ao TCC.", campo="usuario_id")
    return usuario, interno, instituicao


def _repetida(m: MembroEntrada, outros: list[MembroEntrada]) -> bool:
    return any(_chave(o) == _chave(m) for o in outros)


def pendencias(banca: list[MembroEntrada]) -> list[str]:
    """RN12 / CA-02: 2 avaliadores e o orientador; coorientador e suplente são opcionais (um de cada)."""
    conta = {papel: sum(1 for m in banca if m.papel == papel) for papel in
             (PAPEL_AVALIADOR, PAPEL_ORIENTADOR, PAPEL_COORIENTADOR, PAPEL_SUPLENTE)}
    faltas = []
    if conta[PAPEL_ORIENTADOR] == 0:
        faltas.append("Falta o orientador.")
    if conta[PAPEL_AVALIADOR] < 2:
        faltas.append(f"Faltam {2 - conta[PAPEL_AVALIADOR]} avaliador(es): a banca precisa de 2.")
    if conta[PAPEL_AVALIADOR] > 2:
        faltas.append("A banca tem só 2 avaliadores.")
    for papel, rotulo in ((PAPEL_ORIENTADOR, "orientador"), (PAPEL_COORIENTADOR, "coorientador"),
                          (PAPEL_SUPLENTE, "suplente")):
        if conta[papel] > 1:
            faltas.append(f"A banca tem só um {rotulo}.")
    return faltas


def _conferir_banca(db: Session, tcc: Tcc, banca: list[MembroEntrada]) -> list[tuple[MembroEntrada, Usuario | None, bool, str | None]]:
    for i, m in enumerate(banca):
        if _repetida(m, banca[:i]):  # RBN09.02 · DS-FL04-A passo 10
            raise ErroAPI(422, "Esta pessoa já faz parte da banca.", campo="usuario_id")
    resolvidos = [(m, *_conferir_vaga(db, tcc, m)) for m in banca]
    faltas = pendencias(banca)
    if faltas:
        raise ErroAPI(422, "A banca ainda não está completa.", pendencias=faltas)
    return resolvidos


def validar_membro(db: Session, usuario: Usuario, tcc_id: int, dados: ValidarMembro) -> MembroOut:
    """POST /tccs/{id}/banca/validar: confere a vaga contra a banca da tela, sem gravar (opção 2)."""
    tcc = obter_para(db, usuario, tcc_id)
    _exigir_responsavel(usuario, tcc)
    m = dados.membro
    if _repetida(m, dados.banca):
        raise ErroAPI(422, "Esta pessoa já faz parte da banca.", campo="usuario_id")
    pessoa_vaga, interno, instituicao = _conferir_vaga(db, tcc, m)
    if pessoa_vaga is not None:
        alvo = pessoa(pessoa_vaga)
        email = pessoa_vaga.email
        instituicao = instituicao if interno else (_instituicao(db, pessoa_vaga) or instituicao)
    else:
        alvo = PessoaOut(id=0, nome=m.externo.nome)  # convidado novo: a conta só nasce na confirmação
        email = m.externo.email.lower()
    return MembroOut(id=None, papel=m.papel, pessoa=alvo, email=email, interno=interno, instituicao=instituicao)


# =================================================================== DS-FL04 · confirmar a defesa


def _criar_externo(db: Session, dados, ator: Usuario) -> Usuario:
    """DS-FL04-B passos 6 e 7 (decisão C): conta sem senha e inativa, com a instituição e o perfil
    de membro da banca. O link de acesso e o acesso limitado ficam com o SCRUM-32."""
    usuario = Usuario(nome=dados.nome, email=dados.email.lower())
    db.add(usuario)
    db.flush()
    db.add(UsuarioExterno(usuario_id=usuario.id, instituicao=dados.instituicao))
    perfil = db.scalar(select(Perfil).where(Perfil.codigo == PERFIL_BANCA))
    db.add(UsuarioPerfil(usuario_id=usuario.id, perfil_id=perfil.id, atribuido_por=ator.id))
    auditoria.registrar(
        db, ator_id=ator.id, acao="criar_convidado_externo", entidade="usuario", entidade_id=usuario.id,
        novo=f"{usuario.nome} <{usuario.email}> · {dados.instituicao}",
    )
    return usuario


def _conferir_agenda(db: Session, dados: DefesaCriar) -> LocalDefesa | None:
    """O mínimo para gravar (RN14 e restrições do banco). Data passada, link https e duração
    mínima (RN22) entram no SCRUM-61; conflitos de agenda, no SCRUM-62."""
    campos = {}
    if dados.fim <= dados.inicio:
        campos["fim"] = "O término deve ser depois do início."
    precisa_local = dados.formato in ("PRESENCIAL", "HIBRIDO")
    precisa_link = dados.formato in ("REMOTO", "HIBRIDO")
    local = db.get(LocalDefesa, dados.local_id) if dados.local_id is not None else None
    if precisa_local and local is None:
        campos["local_id"] = "Escolha o local da defesa."
    if precisa_link and not dados.link:
        campos["link"] = "Informe o link da sala virtual."
    if campos:
        raise ErroAPI(400, "Confira os campos destacados.", campos=campos)
    return local if precisa_local else None


def agendar(db: Session, usuario: Usuario, tcc_id: int, dados: DefesaCriar) -> Defesa:
    """POST /tccs/{id}/defesa (passos 16 a 21): grava defesa, banca, histórico e auditoria juntos."""
    tcc = obter_para(db, usuario, tcc_id)
    _exigir_responsavel(usuario, tcc)  # passo 17
    if defesa_vigente(tcc.id, db) is not None:
        raise ErroAPI(409, "Este TCC já tem uma defesa agendada.")
    resolvidos = _conferir_banca(db, tcc, dados.banca)
    local = _conferir_agenda(db, dados)

    defesa = Defesa(  # passo 18: CONFIRMADA e não publicada
        tcc_id=tcc.id,
        formato=dados.formato,
        data=dados.data,
        inicio=dados.inicio,
        fim=dados.fim,
        local_id=local.id if local else None,
        link=dados.link if dados.formato != "PRESENCIAL" else None,
        situacao=CONFIRMADA,
        responsavel_id=usuario.id,
    )
    db.add(defesa)
    try:
        # Dois pedidos ao mesmo tempo passam juntos pela checagem de defesa vigente acima; o índice
        # uq_defesa_tcc_vigente barra o segundo aqui (no PostgreSQL, ele espera o primeiro gravar).
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ErroAPI(409, "Este TCC já tem uma defesa agendada.") from None
    for m, pessoa_vaga, interno, _ in resolvidos:
        if pessoa_vaga is None:
            pessoa_vaga = _criar_externo(db, m.externo, usuario)
        membro = BancaMembro(defesa_id=defesa.id, usuario_id=pessoa_vaga.id, papel=m.papel, interno=interno)
        db.add(membro)
        db.flush()
        auditoria.registrar(  # DS-FL04-A passo 12
            db, ator_id=usuario.id, acao="incluir_membro_banca", entidade="banca_membro",
            entidade_id=membro.id, campo=m.papel, novo=pessoa_vaga.nome,
        )
    db.add(HistoricoDefesa(defesa_id=defesa.id, evento="AGENDAMENTO", usuario_id=usuario.id))  # passo 19
    auditoria.registrar(  # passo 21
        db, ator_id=usuario.id, acao="agendar_defesa", entidade="defesa", entidade_id=defesa.id,
        novo=f"{dados.data.isoformat()} {dados.inicio.isoformat('minutes')}-{dados.fim.isoformat('minutes')} {dados.formato}",
    )
    _confirmar(db, "Este TCC já tem uma defesa agendada.")
    db.refresh(defesa)
    return defesa


def _confirmar(db: Session, conflito: str) -> None:
    """Grava a transação; se uma restrição única do banco barrar (pedido simultâneo), devolve 409.

    No agendamento, o índice uq_defesa_tcc_vigente (uma defesa não cancelada por TCC). Na troca de
    membro, uq_banca_membro_defesa_usuario (a mesma pessoa duas vezes na mesma banca)."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ErroAPI(409, conflito) from None


# =================================================================== CA-06 · trocar um membro


def trocar_membro(db: Session, usuario: Usuario, defesa_id: int, membro_id: int, dados: PessoaBanca) -> Defesa:
    """PUT /defesas/{id}/banca/{membro}: troca a pessoa de uma vaga e revalida a banca (RN12).
    A pessoa anterior fica no histórico da defesa (BANCA_ALTERADA, CA-06) e no log de auditoria."""
    defesa = db.get(Defesa, defesa_id)
    if defesa is None:
        raise ErroAPI(404, "Defesa não encontrada.")
    tcc = obter_para(db, usuario, defesa.tcc_id)  # 404 para quem não vê o TCC (RN07)
    _exigir_responsavel(usuario, tcc)
    if defesa.situacao not in ALTERAVEIS:
        raise ErroAPI(409, "A banca desta defesa não pode mais ser alterada.")
    membro = next((m for m in defesa.membros if m.id == membro_id), None)
    if membro is None:
        raise ErroAPI(404, "Membro da banca não encontrado.")
    if membro.papel in (PAPEL_ORIENTADOR, PAPEL_COORIENTADOR):
        raise ErroAPI(422, "O orientador e o coorientador da banca são os vinculados ao TCC.", campo="papel")

    nova = MembroEntrada(papel=membro.papel, usuario_id=dados.usuario_id, externo=dados.externo)
    outros = [m for m in defesa.membros if m.id != membro.id]
    if any(_chave_usuario(o.usuario) == _chave(nova) for o in outros):  # RBN09.02
        raise ErroAPI(422, "Esta pessoa já faz parte da banca.", campo="usuario_id")
    pessoa_vaga, interno, _ = _conferir_vaga(db, tcc, nova)
    if pessoa_vaga is None:
        pessoa_vaga = _criar_externo(db, nova.externo, usuario)

    anterior = membro.usuario.nome
    db.add(HistoricoDefesa(  # CA-06: histórico preservado
        defesa_id=defesa.id,
        evento="BANCA_ALTERADA",
        usuario_id=usuario.id,
        valores_anteriores={
            "membro_id": membro.id,
            "papel": membro.papel,
            "usuario_id": membro.usuario_id,
            "nome": anterior,
            "interno": membro.interno,
            "convite_enviado_em": membro.convite_enviado_em.isoformat() if membro.convite_enviado_em else None,
        },
    ))
    membro.usuario = pessoa_vaga
    membro.interno = interno
    membro.convite_enviado_em = None  # a pessoa nova ainda não foi convidada (SCRUM-63)
    auditoria.registrar(
        db, ator_id=usuario.id, acao="trocar_membro_banca", entidade="banca_membro", entidade_id=membro.id,
        campo=membro.papel, anterior=anterior, novo=pessoa_vaga.nome,
    )
    _confirmar(db, "A banca mudou enquanto você editava. Abra a página de novo.")
    db.refresh(defesa)
    return defesa
