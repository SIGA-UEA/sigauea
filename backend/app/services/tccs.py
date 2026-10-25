"""Cadastro e submissão do TCC (RAN03) e vínculos de orientação (RAN06).

Cada função segue um diagrama de sequência; os comentários "DS-FL01 passo N"
apontam para a mensagem correspondente no diagrama do Documento de Sequência.
"""

from datetime import date

from fastapi import BackgroundTasks
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import config
from app.database import agora
from app.erros import ErroAPI
from app.models import (
    ACEITA,
    DEVOLVIDO,
    EM_ANALISE,
    MATRICULADO,
    PAPEL_COORIENTADOR,
    PAPEL_ORIENTADOR,
    PENDENTE,
    PERFIL_COORDENADOR,
    PERFIL_ORIENTADOR,
    PERFIL_PROFESSOR,
    RASCUNHO,
    RECUSADA,
    AreaInteresse,
    Docente,
    HistoricoPublicacao,
    HistoricoSituacao,
    MatriculaTurma,
    NotificacaoEmail,
    Orientacao,
    PeriodoLetivo,
    PublicacaoArtigo,
    Tcc,
    TccPalavraChave,
    Turma,
    Usuario,
    UsuarioPerfil,
    Perfil,
)
from app.schemas.tcc import (
    ArtigoOut,
    FormularioOut,
    HistoricoOut,
    IndicarOrientador,
    RespostaOrientacao,
    SolicitacaoOut,
    SubmissaoOut,
    TccOut,
    TccSalvar,
    VinculoOut,
)
from app.schemas.usuario import AreaOut, CursoOut
from app.services import auditoria, email
from app.services.turmas import pessoa, turma_resumo

EDITAVEIS = (RASCUNHO, DEVOLVIDO)  # DS-FL01-B: PUT só nessas situações
VIGENTES = (PENDENTE, ACEITA)  # vínculo que ainda vale


# =================================================================== saída


def _vinculo(tcc: Tcc, papel: str) -> Orientacao | None:
    """O vínculo atual de um papel: o pendente/aceito, ou o último recusado (para mostrar o motivo)."""
    do_papel = [o for o in tcc.orientacoes if o.papel == papel and o.encerrado_em is None]
    for o in reversed(do_papel):
        if o.status in VIGENTES:
            return o
    return do_papel[-1] if do_papel and do_papel[-1].status == RECUSADA else None


def _vinculo_out(o: Orientacao | None) -> VinculoOut | None:
    if o is None:
        return None
    return VinculoOut(
        id=o.id,
        professor=pessoa(o.professor),
        papel=o.papel,
        status=o.status,
        solicitado_em=o.solicitado_em,
        respondido_em=o.respondido_em,
        motivo_recusa=o.motivo_recusa,
    )


def pendencias(tcc: Tcc) -> list[str]:
    """O que impede a submissão (DS-FL01 passo 6 e RBN03.03)."""
    faltam = []
    if not tcc.titulo.strip():
        faltam.append("Informe o título.")
    if not tcc.resumo.strip():
        faltam.append("Escreva o resumo.")
    if not tcc.palavras:
        faltam.append("Informe ao menos uma palavra-chave.")
    orientador = _vinculo(tcc, PAPEL_ORIENTADOR)
    if orientador is None or orientador.status == RECUSADA:
        faltam.append("Indique o orientador.")
    elif orientador.status == PENDENTE:
        faltam.append("Aguarde o orientador aceitar a orientação.")
    return faltam


def para_saida(tcc: Tcc) -> TccOut:
    pub = tcc.publicacoes[-1] if tcc.publicacoes else None
    return TccOut(
        id=tcc.id,
        protocolo=tcc.protocolo,
        situacao=tcc.situacao,
        etapa=tcc.etapa,
        modalidade=tcc.modalidade,
        titulo=tcc.titulo,
        subtitulo=tcc.subtitulo,
        resumo=tcc.resumo,
        palavras_chave=[p.palavra for p in tcc.palavras],
        area=AreaOut.model_validate(tcc.area),
        turma=turma_resumo(tcc.turma),
        aluno=pessoa(tcc.aluno.usuario),
        matricula=tcc.aluno.matricula,
        curso=CursoOut.model_validate(tcc.aluno.curso),
        orientador=_vinculo_out(_vinculo(tcc, PAPEL_ORIENTADOR)),
        coorientador=_vinculo_out(_vinculo(tcc, PAPEL_COORIENTADOR)),
        artigo=(
            ArtigoOut(
                tipo_veiculo=pub.tipo_veiculo,
                veiculo=pub.veiculo,
                situacao=pub.situacao_atual,
                doi=pub.doi,
                qualis=pub.qualis,
            )
            if pub and tcc.modalidade == "ARTIGO"
            else None
        ),
        submetido_em=tcc.submetido_em,
        criado_em=tcc.criado_em,
        atualizado_em=tcc.atualizado_em,
        pendencias=pendencias(tcc) if tcc.situacao in EDITAVEIS else [],
        historico=[
            HistoricoOut(
                situacao_anterior=h.situacao_anterior,
                situacao_nova=h.situacao_nova,
                usuario=pessoa(h.usuario),
                registrado_em=h.registrado_em,
            )
            for h in tcc.historico
        ],
    )


# =================================================================== consultas de apoio


def matricula_vigente(db: Session, aluno_id: int) -> MatriculaTurma | None:
    """DS-FL01 obterSituacao(idAluno): a matrícula do período em curso (ou do mais recente)."""
    hoje = date.today()
    matriculas = list(
        db.scalars(
            select(MatriculaTurma)
            .join(Turma)
            .join(PeriodoLetivo)
            .where(MatriculaTurma.aluno_id == aluno_id)
            .order_by(PeriodoLetivo.inicio.desc(), MatriculaTurma.id.desc())
        )
    )
    for m in matriculas:
        if m.turma.periodo.inicio <= hoje <= m.turma.periodo.fim:
            return m
    return matriculas[0] if matriculas else None


def _exigir_matriculado(db: Session, aluno_id: int) -> MatriculaTurma:
    m = matricula_vigente(db, aluno_id)
    if m is None or m.situacao != MATRICULADO:
        # RN05: só quem está numa turma com situação "Matriculado" cadastra e submete.
        raise ErroAPI(
            403,
            "Você precisa estar matriculado em uma turma de TCC. Procure a coordenação.",
            motivo="sem_matricula",
        )
    return m


def _docentes_com(db: Session, perfis: tuple[str, ...]) -> list[Usuario]:
    return list(
        db.scalars(
            select(Usuario)
            .join(Docente)
            .join(UsuarioPerfil, UsuarioPerfil.usuario_id == Usuario.id)
            .join(Perfil)
            .where(Perfil.codigo.in_(perfis), Usuario.ativo.is_(True))
            .distinct()
            .order_by(Usuario.nome)
        )
    )


def orientadores_elegiveis(db: Session) -> list[Usuario]:
    """DS-FL01-A passo 10: docentes ativos com perfil de orientador."""
    return _docentes_com(db, (PERFIL_ORIENTADOR,))


def coorientadores_elegiveis(db: Session) -> list[Usuario]:
    return _docentes_com(db, (PERFIL_ORIENTADOR, PERFIL_PROFESSOR))


def _verificar_elegibilidade(db: Session, orientador_id: int | None, coorientador_id: int | None) -> None:
    """DS-FL01-B passo 13 (E2): orientador e coorientador elegíveis e diferentes (RBN06.02)."""
    erros = {}
    if orientador_id and orientador_id not in {u.id for u in orientadores_elegiveis(db)}:
        erros["orientador_id"] = "Escolha um docente ativo com perfil de orientador."
    if coorientador_id:
        if coorientador_id == orientador_id:
            erros["coorientador_id"] = "O coorientador não pode ser o próprio orientador."
        elif coorientador_id not in {u.id for u in coorientadores_elegiveis(db)}:
            erros["coorientador_id"] = "Escolha um docente ativo como coorientador."
    if erros:
        raise ErroAPI(422, "Orientador ou coorientador não elegível.", campos=erros)


# =================================================================== DS-FL01-A · abrir formulário


def formulario(db: Session, aluno: Usuario) -> FormularioOut:
    m = _exigir_matriculado(db, aluno.id)  # passo 7 + 403
    tcc = db.scalar(
        select(Tcc).where(Tcc.aluno_id == aluno.id, Tcc.periodo_id == m.turma.periodo_id)
    )  # passo 8
    origem = None
    if tcc is None and m.turma.disciplina == "TCC2":  # passo 9 (A4, RBN08.04)
        tcc1 = db.scalar(
            select(Tcc).where(Tcc.aluno_id == aluno.id, Tcc.etapa == "TCC1").order_by(Tcc.id.desc())
        )
        if tcc1:
            o = _vinculo(tcc1, PAPEL_ORIENTADOR)
            origem = {
                "tcc_origem_id": tcc1.id,
                "titulo": tcc1.titulo,
                "area_id": tcc1.area_id,
                "modalidade": tcc1.modalidade,
                "orientador_id": o.professor_id if o and o.status == ACEITA else None,
            }
    return FormularioOut(
        turma=turma_resumo(m.turma),
        situacao_matricula=m.situacao,
        tcc=para_saida(tcc) if tcc else None,
        origem=origem,
        orientadores=[pessoa(u) for u in orientadores_elegiveis(db)],  # passo 10
        coorientadores=[pessoa(u) for u in coorientadores_elegiveis(db)],
        areas=[
            AreaOut.model_validate(a) for a in db.scalars(select(AreaInteresse).order_by(AreaInteresse.nome))
        ],
    )


# =================================================================== DS-FL01-B · salvar rascunho


def _area(db: Session, area_id: int) -> AreaInteresse:
    area = db.get(AreaInteresse, area_id)
    if area is None:
        raise ErroAPI(400, "Confira os campos destacados.", campos={"area_id": "Área inválida."})
    return area


def _obter_do_aluno(db: Session, tcc_id: int, aluno: Usuario, travar: bool = False) -> Tcc:
    """DS-FL01 passo 4 e DS-FL01-B passo 12: inexistente ou de outro aluno (RN07)."""
    tcc = db.get(Tcc, tcc_id, with_for_update=travar)
    if tcc is None or tcc.aluno_id != aluno.id:
        raise ErroAPI(404, "Cadastro de TCC não encontrado.")
    return tcc


def _salvar_artigo(db: Session, tcc: Tcc, dados: TccSalvar, ator: Usuario) -> None:
    """DS-FL01-B passo 9: situação editorial, tipo de veículo, local e DOI (RBN03.02)."""
    if tcc.modalidade != "ARTIGO" or dados.artigo is None:
        return
    a = dados.artigo
    if a.situacao == "PUBLICADO" and not a.doi:
        raise ErroAPI(
            400, "Confira os campos destacados.", campos={"doi": "Informe o DOI do artigo publicado."}
        )
    pub = tcc.publicacoes[-1] if tcc.publicacoes else None
    if pub is None:
        pub = PublicacaoArtigo(
            tcc_id=tcc.id,
            tipo_veiculo=a.tipo_veiculo,
            veiculo=a.veiculo,
            doi=a.doi or None,
            qualis=a.qualis or None,
            situacao_atual=a.situacao,
        )
        db.add(pub)
        db.flush()
        tcc.publicacoes.append(pub)
        db.add(
            HistoricoPublicacao(
                publicacao_id=pub.id, situacao=a.situacao, data=date.today(), usuario_id=ator.id
            )
        )
        return
    if pub.situacao_atual != a.situacao:
        db.add(
            HistoricoPublicacao(
                publicacao_id=pub.id, situacao=a.situacao, data=date.today(), usuario_id=ator.id
            )
        )
    pub.tipo_veiculo, pub.veiculo, pub.situacao_atual = a.tipo_veiculo, a.veiculo, a.situacao
    pub.doi, pub.qualis = a.doi or None, a.qualis or None


def _aviso_vinculo(db: Session, tarefas: BackgroundTasks, o: Orientacao, tcc: Tcc) -> None:
    """RBN03.06, DS-FL01-B passo 18 e DS-FL03-B passo 12: o professor indicado recebe e-mail."""
    papel = "orientador(a)" if o.papel == PAPEL_ORIENTADOR else "coorientador(a)"
    email.enfileirar(
        db,
        tarefas,
        o.professor,
        "VINCULO_ORIENTACAO",
        "SIGA UEA: pedido de orientação de TCC",
        f"Olá, {o.professor.nome}.\n\n{tcc.aluno.usuario.nome} (matrícula {tcc.aluno.matricula}) indicou você "
        f'como {papel} do TCC "{tcc.titulo}".\n\nPara aceitar ou recusar, entre no sistema:\n'
        f"{config.FRONTEND_URL}/orientacoes\n",
        entidade="tcc",
        entidade_id=tcc.id,
    )


def _registrar_vinculo(db, tarefas, tcc: Tcc, professor_id: int, papel: str, ator: Usuario) -> Orientacao:
    """DS-FL01-B passo 16 e DS-FL03-B passo 10: vínculo PENDENTE com data (RN16)."""
    o = Orientacao(tcc=tcc, professor_id=professor_id, papel=papel, status=PENDENTE)
    db.add(o)
    db.flush()
    auditoria.registrar(
        db,
        ator_id=ator.id,
        acao="indicar_orientacao",
        entidade="tcc",
        entidade_id=tcc.id,
        campo=papel.lower(),
        novo=o.professor.nome,
    )
    _aviso_vinculo(db, tarefas, o, tcc)
    return o


def _salvar_vinculo(db, tarefas, tcc: Tcc, papel: str, professor_id: int | None, ator: Usuario) -> None:
    """DS-FL01-B passos 15 e 16: troca o pendente; aceito só a coordenação substitui (FL03-C)."""
    atual = _vinculo(tcc, papel)
    if atual and atual.status in VIGENTES and atual.professor_id == professor_id:
        return
    if atual and atual.status == ACEITA:
        nome = "orientador" if papel == PAPEL_ORIENTADOR else "coorientador"
        raise ErroAPI(
            409, f"O {nome} já aceitou. A troca agora é feita pela coordenação.", campo=f"{nome}_id"
        )
    if atual and atual.status == PENDENTE:
        atual.status, atual.encerrado_em = "SUBSTITUIDA", agora()
        atual.justificativa_encerramento = "O aluno indicou outra pessoa antes da resposta."
    if professor_id:
        _registrar_vinculo(db, tarefas, tcc, professor_id, papel, ator)


def _palavras(tcc: Tcc, palavras: list[str]) -> None:
    tcc.palavras = [TccPalavraChave(ordem=i + 1, palavra=p) for i, p in enumerate(palavras)]


def criar(db: Session, tarefas: BackgroundTasks, aluno: Usuario, dados: TccSalvar) -> Tcc:
    m = _exigir_matriculado(db, aluno.id)  # passo 4 (RN05)
    turma = m.turma
    if db.scalar(select(Tcc.id).where(Tcc.aluno_id == aluno.id, Tcc.periodo_id == turma.periodo_id)):
        # alt "POST e já existe cadastro no período" (RN04)
        raise ErroAPI(409, "Você já tem um cadastro de TCC neste período letivo.", motivo="duplicado")
    _verificar_elegibilidade(db, dados.orientador_id, dados.coorientador_id)  # passo 13
    _area(db, dados.area_id)  # passo 5
    tcc = Tcc(  # passo 6: RASCUNHO, sem protocolo
        aluno_id=aluno.id,
        turma_id=turma.id,
        periodo_id=turma.periodo_id,
        etapa=turma.disciplina,
        modalidade=dados.modalidade,
        titulo=dados.titulo,
        subtitulo=dados.subtitulo or None,
        resumo=dados.resumo,
        area_id=dados.area_id,
        situacao=RASCUNHO,
    )
    db.add(tcc)
    try:
        db.flush()
    except IntegrityError:  # dois "salvar" ao mesmo tempo: o índice único barra o segundo
        db.rollback()
        raise ErroAPI(
            409, "Você já tem um cadastro de TCC neste período letivo.", motivo="duplicado"
        ) from None
    _palavras(tcc, dados.palavras_chave)
    db.add(
        HistoricoSituacao(tcc_id=tcc.id, situacao_anterior=None, situacao_nova=RASCUNHO, usuario_id=aluno.id)
    )
    auditoria.registrar(
        db,
        ator_id=aluno.id,
        acao="criar_tcc",
        entidade="tcc",
        entidade_id=tcc.id,
        campo="titulo",
        novo=tcc.titulo,
    )
    db.flush()
    db.refresh(tcc)
    _salvar_artigo(db, tcc, dados, aluno)  # passo 9
    _salvar_vinculo(db, tarefas, tcc, PAPEL_ORIENTADOR, dados.orientador_id, aluno)  # passos 15 e 16
    _salvar_vinculo(db, tarefas, tcc, PAPEL_COORIENTADOR, dados.coorientador_id, aluno)
    db.commit()
    db.refresh(tcc)
    return tcc


def atualizar(db: Session, tarefas: BackgroundTasks, aluno: Usuario, tcc_id: int, dados: TccSalvar) -> Tcc:
    _exigir_matriculado(db, aluno.id)  # passo 4 (RN05)
    tcc = _obter_do_aluno(db, tcc_id, aluno)  # passo 12 (RN07)
    if tcc.situacao not in EDITAVEIS:
        raise ErroAPI(409, "O cadastro não pode ser editado nesta situação.", motivo="nao_editavel")
    _verificar_elegibilidade(db, dados.orientador_id, dados.coorientador_id)  # passo 13
    _area(db, dados.area_id)  # passo 5
    # passos 6 e 14: atualizar mantém protocolo e parecer (RBN03.05); cada campo alterado vai para o log
    novos = {
        "titulo": dados.titulo,
        "subtitulo": dados.subtitulo or None,
        "resumo": dados.resumo,
        "area_id": dados.area_id,
        "modalidade": dados.modalidade,
    }
    for campo, valor in novos.items():
        if getattr(tcc, campo) != valor:
            auditoria.registrar(
                db,
                ator_id=aluno.id,
                acao="editar_tcc",
                entidade="tcc",
                entidade_id=tcc.id,
                campo=campo,
                anterior=getattr(tcc, campo),
                novo=valor,
            )
            setattr(tcc, campo, valor)
    antes = [p.palavra for p in tcc.palavras]
    if antes != dados.palavras_chave:
        auditoria.registrar(
            db,
            ator_id=aluno.id,
            acao="editar_tcc",
            entidade="tcc",
            entidade_id=tcc.id,
            campo="palavras_chave",
            anterior=", ".join(antes),
            novo=", ".join(dados.palavras_chave),
        )
        tcc.palavras.clear()
        db.flush()
        _palavras(tcc, dados.palavras_chave)
    tcc.atualizado_em = agora()
    _salvar_artigo(db, tcc, dados, aluno)  # passo 9
    _salvar_vinculo(db, tarefas, tcc, PAPEL_ORIENTADOR, dados.orientador_id, aluno)  # passos 15 e 16
    _salvar_vinculo(db, tarefas, tcc, PAPEL_COORIENTADOR, dados.coorientador_id, aluno)
    db.commit()
    db.refresh(tcc)
    return tcc


# =================================================================== DS-FL01 · submeter


def gerar_protocolo(tcc: Tcc) -> str:
    """DS-FL01 passo 8: único por construção (ano do período + número do cadastro)."""
    return f"TCC-{tcc.periodo.codigo[:4]}-{tcc.id:05d}"


def submeter(db: Session, tarefas: BackgroundTasks, aluno: Usuario, tcc_id: int) -> SubmissaoOut:
    # passo 4, com trava de linha: dois cliques ao mesmo tempo não geram dois protocolos (RNF06)
    tcc = _obter_do_aluno(db, tcc_id, aluno, travar=True)
    if tcc.situacao == EM_ANALISE:  # repetição da solicitação: devolve o protocolo, nada é criado
        db.commit()
        return SubmissaoOut(
            protocolo=tcc.protocolo, situacao=tcc.situacao, aviso_pendente=False, tcc=para_saida(tcc)
        )
    if tcc.situacao not in EDITAVEIS:
        raise ErroAPI(409, "O TCC não pode ser submetido nesta situação.", motivo="nao_editavel")
    _exigir_matriculado(db, aluno.id)  # passo 5 (RN05)
    faltam = pendencias(tcc)  # passo 6 (E1) e RBN03.03
    if faltam:
        raise ErroAPI(422, "Ainda falta completar o cadastro.", campos_pendentes=faltam)
    anterior = tcc.situacao
    primeira = tcc.protocolo is None
    tcc.situacao = EM_ANALISE  # passo 7
    tcc.submetido_em = agora()
    tcc.atualizado_em = agora()
    if primeira:
        tcc.protocolo = gerar_protocolo(tcc)  # passos 8 e 9 (RBN03.04)
    db.add(
        HistoricoSituacao(
            tcc_id=tcc.id,
            situacao_anterior=anterior,
            situacao_nova=EM_ANALISE,
            usuario_id=aluno.id,
            observacao="Primeira submissão." if primeira else "Reenvio após devolução.",
        )
    )  # passo 10
    auditoria.registrar(
        db,
        ator_id=aluno.id,
        acao="submeter_tcc",
        entidade="tcc",
        entidade_id=tcc.id,
        campo="situacao",
        anterior=anterior,
        novo=EM_ANALISE,
    )
    if primeira:
        auditoria.registrar(
            db,
            ator_id=aluno.id,
            acao="gerar_protocolo",
            entidade="tcc",
            entidade_id=tcc.id,
            campo="protocolo",
            novo=tcc.protocolo,
        )
    # passos 12 e 13: aviso ao orientador, fora da requisição (RNF01 exclui o envio do tempo medido)
    orientador = _vinculo(tcc, PAPEL_ORIENTADOR)
    email.enfileirar(
        db,
        tarefas,
        orientador.professor,
        "CADASTRO_SUBMETIDO",
        f"SIGA UEA: cadastro de TCC submetido ({tcc.protocolo})",
        f'Olá, {orientador.professor.nome}.\n\n{aluno.nome} submeteu o cadastro do TCC "{tcc.titulo}", '
        f"que você orienta. Protocolo: {tcc.protocolo}.\nA coordenação vai analisar o cadastro.\n\n"
        f"{config.FRONTEND_URL}/tccs/{tcc.id}\n",
        entidade="tcc",
        entidade_id=tcc.id,
    )
    db.commit()
    db.refresh(tcc)
    return SubmissaoOut(
        protocolo=tcc.protocolo, situacao=tcc.situacao, aviso_pendente=True, tcc=para_saida(tcc)
    )


# =================================================================== consulta (RN07)


def _pode_ver(db: Session, usuario: Usuario, tcc: Tcc) -> bool:
    if tcc.aluno_id == usuario.id or PERFIL_COORDENADOR in usuario.perfis:
        return True
    if any(o.professor_id == usuario.id for o in tcc.orientacoes):
        return True
    return tcc.turma.professor_id == usuario.id  # professor responsável pela turma (RN24)


def obter_para(db: Session, usuario: Usuario, tcc_id: int) -> Tcc:
    tcc = db.get(Tcc, tcc_id)
    if tcc is None or not _pode_ver(db, usuario, tcc):
        raise ErroAPI(404, "Cadastro de TCC não encontrado.")
    return tcc


def listar_para(db: Session, usuario: Usuario) -> list[Tcc]:
    """RBN05.01: aluno vê os seus; orientador, os que orienta; professor, os da turma; coordenação, todos."""
    consulta = select(Tcc).order_by(Tcc.atualizado_em.desc())
    if PERFIL_COORDENADOR not in usuario.perfis:
        consulta = (
            consulta.outerjoin(Orientacao, Orientacao.tcc_id == Tcc.id)
            .join(Turma, Turma.id == Tcc.turma_id)
            .where(
                or_(
                    Tcc.aluno_id == usuario.id,
                    Orientacao.professor_id == usuario.id,
                    Turma.professor_id == usuario.id,
                )
            )
            .distinct()
        )
    return list(db.scalars(consulta))


# =================================================================== DS-FL03 · orientação


def indicar(
    db: Session, tarefas: BackgroundTasks, aluno: Usuario, tcc_id: int, dados: IndicarOrientador
) -> Orientacao:
    """Indicar novo orientador (após recusa) ou o coorientador pela rota própria.

    Nenhuma tela usa esta rota: a tela de cadastro indica pelo PUT /tccs/{id} (nota no DS-FL03-B).
    """
    tcc = _obter_do_aluno(db, tcc_id, aluno)
    if tcc.situacao not in EDITAVEIS:
        raise ErroAPI(409, "O cadastro não pode ser editado nesta situação.", motivo="nao_editavel")
    outro = _vinculo(tcc, PAPEL_COORIENTADOR if dados.papel == PAPEL_ORIENTADOR else PAPEL_ORIENTADOR)
    outro_id = outro.professor_id if outro and outro.status in VIGENTES else None
    if dados.papel == PAPEL_ORIENTADOR:
        _verificar_elegibilidade(db, dados.professor_id, outro_id)  # DS-FL03-B passo 9 (E1)
    else:
        _verificar_elegibilidade(db, outro_id, dados.professor_id)
    atual = _vinculo(tcc, dados.papel)
    if atual and atual.status in VIGENTES:
        raise ErroAPI(
            409, "Já existe um vínculo pendente ou aceito para este papel.", motivo="vinculo_vigente"
        )
    o = _registrar_vinculo(db, tarefas, tcc, dados.professor_id, dados.papel, aluno)  # DS-FL03-B passos 10 a 13
    db.commit()
    return o


def listar_solicitacoes(db: Session, professor: Usuario, status: str | None) -> list[Orientacao]:
    """DS-FL03-A passo 4: vínculos do orientador, filtrados pelo status."""
    consulta = select(Orientacao).where(
        Orientacao.professor_id == professor.id, Orientacao.encerrado_em.is_(None)
    )
    if status:
        consulta = consulta.where(Orientacao.status == status)
    return list(db.scalars(consulta.order_by(Orientacao.solicitado_em.desc())))


def obter_solicitacao(db: Session, professor: Usuario, orientacao_id: int) -> Orientacao:
    o = db.get(Orientacao, orientacao_id)
    if o is None or o.professor_id != professor.id:  # RN07
        raise ErroAPI(404, "Solicitação de orientação não encontrada.")
    return o


def solicitacao_out(o: Orientacao) -> SolicitacaoOut:
    return SolicitacaoOut(
        id=o.id,
        papel=o.papel,
        status=o.status,
        solicitado_em=o.solicitado_em,
        respondido_em=o.respondido_em,
        motivo_recusa=o.motivo_recusa,
        tcc=para_saida(o.tcc),
    )


def responder(
    db: Session, tarefas: BackgroundTasks, professor: Usuario, orientacao_id: int, dados: RespostaOrientacao
) -> Orientacao:
    """DS-FL03: o orientador aceita ou recusa (RBN06.03)."""
    o = obter_solicitacao(db, professor, orientacao_id)  # passo 7
    if o.status != PENDENTE or o.encerrado_em is not None:
        raise ErroAPI(409, "Esta solicitação já foi respondida.", motivo="respondida")
    if dados.decisao == "RECUSAR" and not (dados.motivo or "").strip():
        raise ErroAPI(400, "Confira os campos destacados.", campos={"motivo": "Informe o motivo da recusa."})
    o.status = ACEITA if dados.decisao == "ACEITAR" else RECUSADA  # passo 8
    o.respondido_em = agora()
    o.motivo_recusa = dados.motivo if o.status == RECUSADA else None
    auditoria.registrar(
        db,
        ator_id=professor.id,
        acao="responder_orientacao",
        entidade="tcc",
        entidade_id=o.tcc_id,
        campo=o.papel.lower(),
        anterior=PENDENTE,
        novo=o.status,
    )
    aluno = o.tcc.aluno.usuario  # passo 10
    if o.status == ACEITA:
        assunto, texto = "SIGA UEA: orientação aceita", f"{professor.nome} aceitou orientar o seu TCC."
    else:
        assunto = "SIGA UEA: orientação recusada"
        texto = (
            f"{professor.nome} recusou o pedido de orientação. Motivo: {o.motivo_recusa}\n"
            "Indique outro orientador para poder submeter o cadastro."
        )
    email.enfileirar(  # passos 11 a 13
        db,
        tarefas,
        aluno,
        "ORIENTACAO_" + ("ACEITA" if o.status == ACEITA else "RECUSADA"),
        assunto,
        f"Olá, {aluno.nome}.\n\n{texto}\n\n{config.FRONTEND_URL}/tccs/{o.tcc_id}\n",
        entidade="tcc",
        entidade_id=o.tcc_id,
    )
    db.commit()
    return o


def avisos_pendentes(db: Session, tcc: Tcc) -> int:
    """Quantos e-mails sobre este TCC falharam e aguardam reenvio (RBN03.06)."""
    return len(
        list(
            db.scalars(
                select(NotificacaoEmail.id).where(
                    NotificacaoEmail.entidade == "tcc",
                    NotificacaoEmail.entidade_id == tcc.id,
                    NotificacaoEmail.status == "falha",
                )
            )
        )
    )
