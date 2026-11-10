"""Banca e agendamento da defesa (Sprint S04 · RBN09.01, RN07, RN12, RN14).

ControladorAgendamentoDefesa dos diagramas FL04. A banca é montada na tela (DS-FL04-A/B) e
gravada junto com a defesa na confirmação (DS-FL04 passo 16), porque no modelo de dados todo
membro da banca pertence a uma defesa (banca_membro.defesa_id obrigatório).

Composição da banca (SCRUM-60, RBN09.02): pessoa repetida, composição mínima e papéis, conferidos
aqui e não só na tela (CA-05). Agendamento (SCRUM-61, RBN09.03): data não passada, término depois do
início, local e/ou link https:// conforme o formato; a duração de 15/20 min (RN22) é só sugerida.
Conflitos de agenda (SCRUM-62, RBN09.04): mesmo participante ou mesmo local em horários que se
sobrepõem, sem contar as defesas canceladas nem a própria defesa (remarcação).

Convites (SCRUM-63, RBN09.05): ao confirmar, cada membro recebe o convite por e-mail; a situação
do envio aparece na vaga e o convite pode ser reenviado sem refazer a defesa.

Remarcação (SCRUM-65, RBN09.07), cancelamento (SCRUM-66, RBN09.08) e convocação do suplente
(SCRUM-67, RBN09.09): mudam a mesma defesa, guardam o histórico com o motivo, entram no log de
auditoria e avisam os participantes por e-mail. Defesa cancelada ou já realizada não muda mais (409).

Conta limitada do membro externo (SCRUM-32, RBN01.12): o acesso à defesa nasce quando ele entra na banca
gravada (confirmação ou troca) e é revogado quando a defesa é cancelada ou ele sai da banca (services/acessos.py).

Pendência: o DS-FL04 (passo 5) confere a versão do PDF para banca antes de agendar. A tabela
documento_tcc ainda não existe; a conferência entra junto com o envio do PDF (SCRUM-55, RBN07.01).

Quem agenda (RN14): professor da disciplina em SI, orientador nos demais cursos e a coordenação,
como pedem o E4 e o CA-05 da ficha RBN09.01 e a planilha de requisitos (FL04).
"""

from datetime import date, datetime, time, timedelta
from urllib.parse import urlsplit

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import agora
from app.erros import ErroAPI
from app.models import (
    ACEITA,
    CANCELADA,
    CONFIRMADA,
    ENVIADA,
    PAPEL_AVALIADOR,
    PAPEL_COORIENTADOR,
    PAPEL_ORIENTADOR,
    PAPEL_SUPLENTE,
    PERFIL_BANCA,
    PERFIL_COORDENADOR,
    PERFIL_PROFESSOR,
    REMARCADA,
    Avaliacao,
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
    DefesaCancelar,
    DefesaRemarcar,
    EventoDefesaOut,
    SuplenteConvocar,
    BancaOut,
    ConflitoOut,
    ConflitosOut,
    DefesaCriar,
    DefesaOut,
    LocalOut,
    MembroEntrada,
    MembroOut,
    PessoaBanca,
    ValidarMembro,
)
from app.schemas.tcc import PessoaOut
from app.services import acessos, auditoria, avisos_defesa
from app.services.tccs import obter_para
from app.services.turmas import pessoa
from app.services.usuarios import buscar_por_email

APROVADO = "APROVADO"
CURSO_PROFESSOR_AGENDA = "SI"  # RN14: em SI quem agenda é o professor da disciplina
ALTERAVEIS = (CONFIRMADA, REMARCADA)  # CA-06: a banca pode mudar antes da defesa acontecer
FUSO_MANAUS = timedelta(hours=-4)  # America/Manaus não tem horário de verão (mesma regra da SCRUM-68)


def agora_manaus() -> datetime:
    return agora() + FUSO_MANAUS


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


def pode_convocar(usuario: Usuario, tcc: Tcc) -> bool:
    """RBN09.09: a coordenação ou o orientador do TCC convocam o suplente (CA-05)."""
    if PERFIL_COORDENADOR in usuario.perfis:
        return True
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
        convite=avisos_defesa.situacao_convite(db, m),
        convocado_em=m.convocado_em,
        substitui_membro_id=m.substitui_membro_id,
        substituido_por_id=next(
            (s.id for s in m.defesa.membros if s.substitui_membro_id == m.id and s.convocado_em is not None), None
        ),
    )


# Ordem de exibição da banca: as vagas fixas, os dois avaliadores e, por último, o suplente.
ORDEM_PAPEIS = {p: i for i, p in enumerate((PAPEL_ORIENTADOR, PAPEL_COORIENTADOR, PAPEL_AVALIADOR, PAPEL_SUPLENTE))}


def defesa_out(db: Session, d: Defesa) -> DefesaOut:
    return DefesaOut(
        id=d.id,
        titulo=d.tcc.titulo,
        autor=pessoa(d.tcc.aluno.usuario),
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
        historico=[
            EventoDefesaOut(evento=h.evento, motivo=h.motivo, valores_anteriores=h.valores_anteriores,
                            por=pessoa(h.usuario), registrado_em=h.registrado_em)
            for h in sorted(d.historico, key=lambda h: h.id, reverse=True)
        ],
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
    cancelada = None if defesa else db.scalar(  # RBN09.08: a última cancelada, para o aviso na tela
        select(Defesa).where(Defesa.tcc_id == tcc.id, Defesa.situacao == CANCELADA).order_by(Defesa.id.desc()).limit(1)
    )
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
        pode_convocar=pode_convocar(usuario, tcc),
        cancelada=defesa_out(db, cancelada) if cancelada else None,
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
    de membro da banca. O acesso limitado (passo 8) e o link no convite são do services/acessos.py."""
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


def _tem_endereco(link: str) -> bool:
    """O link traz um endereço depois do https:// (só "https://" não leva a lugar nenhum)."""
    try:
        return bool(urlsplit(link).hostname)
    except ValueError:
        return False


def _conferir_agenda(db: Session, dados: DefesaCriar | DefesaRemarcar) -> LocalDefesa | None:
    """RBN09.03 / RN14: data não passada, término depois do início (CA-03) e, conforme o formato,
    local e/ou link https:// (CA-02; DS-FL04 mensagens 8 e 10). A duração não é limitada (RN22, CA-04)."""
    campos = {}
    agora_local = agora_manaus()
    if dados.data < agora_local.date():
        campos["data"] = "A data da defesa não pode estar no passado."
    elif dados.data == agora_local.date() and dados.inicio < agora_local.time():
        # A avaliação libera o envio quando o horário passa (RBN10.02): a defesa nasceria já realizada.
        campos["inicio"] = "O início da defesa não pode estar no passado."
    if dados.fim <= dados.inicio:
        campos["fim"] = "O término deve ser depois do início."
    precisa_local = dados.formato in ("PRESENCIAL", "HIBRIDO")
    precisa_link = dados.formato in ("REMOTO", "HIBRIDO")
    local = db.get(LocalDefesa, dados.local_id) if dados.local_id is not None else None
    if precisa_local and local is None:
        campos["local_id"] = "Escolha o local da defesa."
    if precisa_link and not dados.link:
        campos["link"] = "Informe o link da sala virtual."
    elif precisa_link and not dados.link.lower().startswith("https://"):
        campos["link"] = "O link da sala virtual deve começar com https://."
    elif precisa_link and not _tem_endereco(dados.link):
        campos["link"] = "Informe o link completo da sala virtual."
    if campos:
        raise ErroAPI(400, "Confira os campos destacados.", campos=campos)
    return local if precisa_local else None


# =================================================================== RBN09.04 · conflitos de agenda
# (fica entre a conferência da agenda e o agendamento, que usa as duas)


def _horario(h: time) -> str:
    return h.isoformat("minutes")


def conflitos(
    db: Session,
    data: date,
    inicio: time,
    fim: time,
    local_id: int | None,
    pessoas_ids: set[int],
    ignorar_defesa_id: int | None = None,
) -> list[ConflitoOut]:
    """DS-FL04 mensagens 12 e 13: outra defesa no mesmo dia cujo intervalo se sobrepõe a este e que
    usa o mesmo local ou tem alguém desta banca. Intervalos que só se encostam (14h–15h e 15h–15h20)
    não conflitam (CA-03); canceladas não contam (CA-04); a própria defesa fica de fora (CA-05)."""
    consulta = select(Defesa).where(
        Defesa.data == data,
        Defesa.situacao != CANCELADA,
        Defesa.inicio < fim,  # comparação de intervalos completos
        Defesa.fim > inicio,
    )
    if ignorar_defesa_id is not None:
        consulta = consulta.where(Defesa.id != ignorar_defesa_id)
    achados: list[ConflitoOut] = []
    for outra in db.scalars(consulta.order_by(Defesa.inicio, Defesa.id)):
        if local_id is not None and outra.local_id == local_id:
            achados.append(ConflitoOut(tipo="LOCAL", nome=outra.local.nome, data=outra.data,
                                       inicio=outra.inicio, fim=outra.fim))
        for m in sorted(outra.membros, key=lambda m: m.usuario.nome):
            if m.usuario_id in pessoas_ids:
                achados.append(ConflitoOut(tipo="PARTICIPANTE", nome=m.usuario.nome, data=outra.data,
                                           inicio=outra.inicio, fim=outra.fim))
    return achados


def _mensagem_conflito(achados: list[ConflitoOut]) -> str:
    c = achados[0]
    quem = f"O local {c.nome}" if c.tipo == "LOCAL" else c.nome
    return f"Há conflito neste horário: {quem} já está em outra defesa das {_horario(c.inicio)} às {_horario(c.fim)}."


def _exigir_sem_conflito(achados: list[ConflitoOut]) -> None:
    """E4 do DS-FL04: o conflito surgiu ou não foi visto na tela; a confirmação é recusada (409)."""
    if achados:
        raise ErroAPI(409, _mensagem_conflito(achados), conflitos=[c.model_dump(mode="json") for c in achados])


def verificar_conflitos(
    db: Session,
    usuario: Usuario,
    tcc_id: int,
    data: date,
    inicio: time,
    fim: time,
    local_id: int | None,
    pessoas_ids: list[int],
) -> ConflitosOut:
    """GET /defesas/conflitos (DS-FL04 mensagem 11; DS-FL05-B mensagem 4).

    Antes da confirmação a banca só existe na tela, então a tela manda os ids das pessoas já
    cadastradas (pessoa=1&pessoa=2...); o convidado externo novo ainda não tem agenda. Sem pessoas,
    vale a banca da defesa vigente do TCC (remarcação). A defesa vigente do próprio TCC nunca
    conflita com ela mesma (CA-05). Só quem agenda vê a agenda dos outros (RN14)."""
    tcc = obter_para(db, usuario, tcc_id)
    _exigir_responsavel(usuario, tcc)
    if fim <= inicio:
        raise ErroAPI(400, "Confira os campos destacados.", campos={"fim": "O término deve ser depois do início."})
    vigente = defesa_vigente(tcc.id, db)
    ids = set(pessoas_ids) if pessoas_ids else {m.usuario_id for m in vigente.membros} if vigente else set()
    return ConflitosOut(conflitos=conflitos(
        db, data, inicio, fim, local_id, ids, ignorar_defesa_id=vigente.id if vigente else None,
    ))


def agendar(db: Session, usuario: Usuario, tcc_id: int, dados: DefesaCriar, tarefas: BackgroundTasks) -> Defesa:
    """POST /tccs/{id}/defesa (passos 16 a 26): grava defesa, banca, histórico e auditoria juntos e
    enfileira o convite de cada membro, que sai depois da resposta (RBN09.05)."""
    tcc = obter_para(db, usuario, tcc_id)
    _exigir_responsavel(usuario, tcc)  # passo 17
    if defesa_vigente(tcc.id, db) is not None:
        raise ErroAPI(409, "Este TCC já tem uma defesa agendada.")
    resolvidos = _conferir_banca(db, tcc, dados.banca)
    local = _conferir_agenda(db, dados)
    pessoas_ids = {p.id for _, p, _, _ in resolvidos if p is not None}  # externo novo não tem agenda
    _exigir_sem_conflito(conflitos(db, dados.data, dados.inicio, dados.fim, local.id if local else None, pessoas_ids))

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
        acessos.conceder_banca(db, usuario, membro)  # DS-FL04-B passo 8 (RBN01.12)
    db.add(HistoricoDefesa(defesa_id=defesa.id, evento="AGENDAMENTO", usuario_id=usuario.id))  # passo 19
    db.flush()
    db.refresh(defesa)  # carrega a banca recém-gravada para os convites
    for membro in defesa.membros:  # passos 20 e 22 a 26 (RBN09.05 CA-01)
        avisos_defesa.convidar(db, tarefas, defesa, membro)
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


def _descartar_rascunho(db: Session, ator: Usuario, avaliacao: Avaliacao, nome: str) -> None:
    """A avaliação pertence à vaga (avaliacao.membro_id). Na troca, o rascunho de quem sai é descartado
    e o substituto começa em branco (decisão da equipe na SCRUM-77, D15); fica registrado no log."""
    auditoria.registrar(
        db, ator_id=ator.id, acao="descartar_avaliacao", entidade="avaliacao", entidade_id=avaliacao.id,
        campo="status", anterior=f"RASCUNHO de {nome} com {len(avaliacao.criterios)} critério(s)",
    )
    for linha in list(avaliacao.criterios):
        db.delete(linha)
    db.flush()
    db.expire(avaliacao, ["criterios"])  # as linhas já saíram do banco; a lista em memória não vale mais
    db.delete(avaliacao)


def trocar_membro(
    db: Session, usuario: Usuario, defesa_id: int, membro_id: int, dados: PessoaBanca, tarefas: BackgroundTasks
) -> Defesa:
    """PUT /defesas/{id}/banca/{membro}: troca a pessoa de uma vaga e revalida a banca (RN12).
    A pessoa anterior fica no histórico da defesa (BANCA_ALTERADA, CA-06) e no log de auditoria;
    a pessoa nova recebe o convite (RBN09.05).
    Com a avaliação já enviada a troca é recusada (409); um rascunho é descartado (SCRUM-77, D15)."""
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
    avaliacao = db.scalar(select(Avaliacao).where(Avaliacao.membro_id == membro.id))
    if avaliacao is not None and avaliacao.status == ENVIADA:  # RBN10.02: a avaliação enviada não muda mais
        raise ErroAPI(409, "Este membro já enviou a avaliação; ele não pode mais ser trocado.")

    nova = MembroEntrada(papel=membro.papel, usuario_id=dados.usuario_id, externo=dados.externo)
    outros = [m for m in defesa.membros if m.id != membro.id]
    if any(_chave_usuario(o.usuario) == _chave(nova) for o in outros):  # RBN09.02
        raise ErroAPI(422, "Esta pessoa já faz parte da banca.", campo="usuario_id")
    pessoa_vaga, interno, _ = _conferir_vaga(db, tcc, nova)
    if pessoa_vaga is not None:  # RBN09.04: a pessoa nova não pode estar em outra defesa no horário
        _exigir_sem_conflito(conflitos(db, defesa.data, defesa.inicio, defesa.fim, None, {pessoa_vaga.id},
                                       ignorar_defesa_id=defesa.id))
    else:
        pessoa_vaga = _criar_externo(db, nova.externo, usuario)

    anterior = membro.usuario.nome
    if not membro.interno:  # decisão 32-k: quem sai da banca perde o acesso à defesa
        acessos.revogar_banca(db, usuario, defesa, membro.usuario_id)
    if avaliacao is not None:
        _descartar_rascunho(db, usuario, avaliacao, anterior)
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
    db.flush()
    acessos.conceder_banca(db, usuario, membro)  # DS-FL04-B passo 8 para quem entra (RBN01.12)
    avisos_defesa.convidar(db, tarefas, defesa, membro)
    _confirmar(db, "A banca mudou enquanto você editava. Abra a página de novo.")
    db.refresh(defesa)
    return defesa


# =================================================================== RBN09.05 · reenviar o convite


def reenviar_convite(db: Session, usuario: Usuario, defesa_id: int, membro_id: int, tarefas: BackgroundTasks) -> BancaMembro:
    """POST /defesas/{id}/banca/{membro}/convite (CA-03, E5 do DS-FL04): um novo e-mail de convite
    para a mesma vaga, sem refazer a defesa nem a banca."""
    defesa = db.get(Defesa, defesa_id)
    if defesa is None:
        raise ErroAPI(404, "Defesa não encontrada.")
    tcc = obter_para(db, usuario, defesa.tcc_id)  # 404 para quem não vê o TCC (RN07)
    _exigir_responsavel(usuario, tcc)
    if defesa.situacao not in ALTERAVEIS:
        raise ErroAPI(409, "Esta defesa não está mais agendada; não há convite a reenviar.")
    membro = next((m for m in defesa.membros if m.id == membro_id), None)
    if membro is None:
        raise ErroAPI(404, "Membro da banca não encontrado.")
    if any(s.substitui_membro_id == membro.id and s.convocado_em is not None for s in defesa.membros):
        raise ErroAPI(409, "Este titular foi substituído pelo suplente; não há convite a reenviar.")  # RBN09.09
    avisos_defesa.convidar(db, tarefas, defesa, membro)
    auditoria.registrar(
        db, ator_id=usuario.id, acao="reenviar_convite_banca", entidade="banca_membro", entidade_id=membro.id,
        novo=membro.usuario.email,
    )
    db.commit()
    db.refresh(membro)
    return membro


def membro_out(db: Session, membro: BancaMembro) -> MembroOut:
    return _membro_out(db, membro)


# =================================================================== FL05 · remarcar, cancelar, suplente

MOTIVO_MINIMO = 5  # DS-FL05-B mensagem 8: motivo com menos de 5 caracteres é recusado


def realizada(defesa: Defesa) -> bool:
    """A mesma regra da avaliação (SCRUM-77, D6/D21): situação REALIZADA ou término já passado em Manaus."""
    if defesa.situacao == "REALIZADA":
        return True
    return defesa.situacao != CANCELADA and datetime.combine(defesa.data, defesa.fim) <= agora_manaus()


def _defesa_aberta(db: Session, usuario: Usuario, defesa_id: int, pode) -> tuple[Defesa, Tcc]:
    """404 se a defesa não existe ou o TCC não é visível (RN07); 403 sem permissão; 409 se a defesa
    foi cancelada ou já aconteceu (E2 das três fichas)."""
    defesa = db.get(Defesa, defesa_id)
    if defesa is None:
        raise ErroAPI(404, "Defesa não encontrada.")
    tcc = obter_para(db, usuario, defesa.tcc_id)
    pode(usuario, tcc)
    if defesa.situacao == CANCELADA:
        raise ErroAPI(409, "Esta defesa foi cancelada.")
    if realizada(defesa):
        raise ErroAPI(409, "Esta defesa já foi realizada e não pode mais ser alterada.")
    return defesa, tcc


def _exigir_motivo(texto: str, campo: str) -> str:
    texto = (texto or "").strip()
    if len(texto) < MOTIVO_MINIMO:
        raise ErroAPI(422, f"Informe o motivo (pelo menos {MOTIVO_MINIMO} caracteres).", campo=campo)
    return texto


def _retrato(defesa: Defesa) -> dict:
    """Os dados de agenda como estavam, para o histórico (RN14) e o e-mail de remarcação."""
    return {
        "data": defesa.data.isoformat(),
        "inicio": defesa.inicio.isoformat("minutes"),
        "fim": defesa.fim.isoformat("minutes"),
        "formato": defesa.formato,
        "local_id": defesa.local_id,
        "local": defesa.local.nome if defesa.local else None,
        "link": defesa.link,
        "situacao": defesa.situacao,
    }


def _resumo(r: dict) -> str:
    return f"{r['data']} {r['inicio']}-{r['fim']} {r['formato']}" + (f" {r['local']}" if r["local"] else "")


# ------------------------------------------------------------------- SCRUM-65 · RBN09.07 · remarcar


def remarcar(db: Session, usuario: Usuario, defesa_id: int, dados: DefesaRemarcar, tarefas: BackgroundTasks) -> Defesa:
    """POST /defesas/{id}/remarcacao (DS-FL05-B mensagens 10 a 19). Quem agenda (RN14) ou a coordenação.
    O mesmo registro de defesa muda, então a agenda publicada mostra os dados novos (RN09, CA-04)."""
    defesa, _ = _defesa_aberta(db, usuario, defesa_id, _exigir_responsavel)
    motivo = _exigir_motivo(dados.motivo, "motivo")  # CA-02
    local = _conferir_agenda(db, dados)  # RBN09.03 de novo
    link = dados.link if dados.formato != "PRESENCIAL" else None
    anteriores = _retrato(defesa)
    if (dados.data, dados.inicio, dados.fim, dados.formato, local.id if local else None, link) == (
        defesa.data, defesa.inicio, defesa.fim, defesa.formato, defesa.local_id, defesa.link
    ):
        raise ErroAPI(422, "Nada mudou: altere a data, o horário, o formato, o local ou o link.")
    _exigir_sem_conflito(conflitos(  # CA-03 (RBN09.04): a própria defesa não conta
        db, dados.data, dados.inicio, dados.fim, local.id if local else None,
        {m.usuario_id for m in defesa.membros}, ignorar_defesa_id=defesa.id,
    ))

    db.add(HistoricoDefesa(defesa_id=defesa.id, evento="REMARCACAO", motivo=motivo,  # mensagem 11
                           valores_anteriores=anteriores, usuario_id=usuario.id))
    defesa.data, defesa.inicio, defesa.fim = dados.data, dados.inicio, dados.fim  # mensagem 12
    defesa.formato, defesa.local_id, defesa.link = dados.formato, local.id if local else None, link
    defesa.situacao = REMARCADA
    defesa.lembrete_enviado_em = None  # RBN09.06 CA-03: o lembrete sai de novo, com os dados novos
    db.flush()
    db.refresh(defesa)
    auditoria.registrar(  # mensagem 13 · CA-06: anterior, novo e motivo
        db, ator_id=usuario.id, acao="remarcar_defesa", entidade="defesa", entidade_id=defesa.id,
        campo="agenda", anterior=_resumo(anteriores), novo=_resumo(_retrato(defesa)),
    )
    auditoria.registrar(db, ator_id=usuario.id, acao="remarcar_defesa", entidade="defesa",
                        entidade_id=defesa.id, campo="motivo", novo=motivo)
    avisos_defesa.avisar_remarcacao(db, tarefas, defesa, anteriores, motivo)  # mensagens 14 a 19
    db.commit()
    db.refresh(defesa)
    return defesa


# ------------------------------------------------------------------- SCRUM-66 · RBN09.08 · cancelar


def cancelar(db: Session, usuario: Usuario, defesa_id: int, dados: DefesaCancelar, tarefas: BackgroundTasks) -> Defesa:
    """POST /defesas/{id}/cancelamento (DS-FL05-C). O TCC fica como estava (CA-03); a agenda deixa de
    mostrar a apresentação (CA-05) e a avaliação recusa defesa cancelada (CA-04, SCRUM-77)."""
    defesa, _ = _defesa_aberta(db, usuario, defesa_id, _exigir_responsavel)
    justificativa = _exigir_motivo(dados.justificativa, "justificativa")  # CA-02 · E3
    anterior = defesa.situacao
    defesa.situacao = CANCELADA  # mensagem 4
    db.add(HistoricoDefesa(defesa_id=defesa.id, evento="CANCELAMENTO", motivo=justificativa,  # mensagem 5
                           valores_anteriores=_retrato(defesa) | {"situacao": anterior, "publicada": defesa.publicada},
                           usuario_id=usuario.id))
    auditoria.registrar(  # mensagem 6 · CA-06
        db, ator_id=usuario.id, acao="cancelar_defesa", entidade="defesa", entidade_id=defesa.id,
        campo="situacao", anterior=anterior, novo=f"{CANCELADA}: {justificativa}",
    )
    acessos.revogar_banca(db, usuario, defesa)  # decisão 32-k: a defesa cancelada encerra o acesso dos externos
    avisos_defesa.avisar_cancelamento(db, tarefas, defesa, justificativa)  # mensagens 7 a 12
    db.commit()
    db.refresh(defesa)
    return defesa


# ------------------------------------------------------------------- SCRUM-67 · RBN09.09 · suplente


def _exigir_convocador(usuario: Usuario, tcc: Tcc) -> None:
    if not pode_convocar(usuario, tcc):  # E1 · CA-05
        raise ErroAPI(403, "Só a coordenação ou o orientador do TCC convocam o suplente.")


def convocar_suplente(
    db: Session, usuario: Usuario, defesa_id: int, dados: SuplenteConvocar, tarefas: BackgroundTasks
) -> Defesa:
    """POST /defesas/{id}/suplente (DS-FL05-E). O suplente passa a avaliar no lugar do titular (RN20):
    a avaliação (SCRUM-77) lê convocado_em e substitui_membro_id para saber quem avalia."""
    defesa, _ = _defesa_aberta(db, usuario, defesa_id, _exigir_convocador)
    suplente = next((m for m in defesa.membros if m.papel == PAPEL_SUPLENTE), None)
    if suplente is None:  # E3 · CA-04
        raise ErroAPI(409, "Esta banca não tem suplente indicado.")
    if suplente.convocado_em is not None:
        raise ErroAPI(409, "O suplente já foi convocado nesta defesa.")
    titular = next((m for m in defesa.membros if m.id == dados.membro_titular_id), None)
    if titular is None or titular.papel != PAPEL_AVALIADOR:
        raise ErroAPI(422, "Escolha um dos avaliadores titulares da banca.", campo="membro_titular_id")
    motivo = _exigir_motivo(dados.motivo, "motivo")  # E4 · CA-02
    if dados.data is None:  # CA-02: a data é obrigatória
        raise ErroAPI(422, "Informe a data da convocação.", campo="data")
    avaliacao = db.scalar(select(Avaliacao).where(Avaliacao.membro_id == titular.id))
    if avaliacao is not None and avaliacao.status == ENVIADA:  # RBN10.02: a avaliação enviada vale
        raise ErroAPI(409, "Este avaliador já enviou a avaliação; ele não pode mais ser substituído.")
    if avaliacao is not None:  # o rascunho do titular não vale para o suplente (como na troca, D15)
        _descartar_rascunho(db, usuario, avaliacao, titular.usuario.nome)

    suplente.convocado_em = agora()  # mensagem 5
    suplente.substitui_membro_id = titular.id
    suplente.motivo_convocacao = motivo
    db.add(HistoricoDefesa(  # mensagem 6
        defesa_id=defesa.id, evento="SUPLENTE_CONVOCADO", motivo=motivo, usuario_id=usuario.id,
        valores_anteriores={"titular_id": titular.id, "titular": titular.usuario.nome,
                            "suplente_id": suplente.id, "suplente": suplente.usuario.nome,
                            "data": dados.data.isoformat()},
    ))
    auditoria.registrar(  # mensagem 7
        db, ator_id=usuario.id, acao="convocar_suplente", entidade="banca_membro", entidade_id=suplente.id,
        campo="substitui", anterior=titular.usuario.nome,
        novo=f"{suplente.usuario.nome} em {dados.data.isoformat()}: {motivo}",
    )
    db.flush()
    avisos_defesa.avisar_convocacao(db, tarefas, defesa, suplente, titular, motivo)  # mensagens 8 a 12
    db.commit()
    db.refresh(defesa)
    return defesa
