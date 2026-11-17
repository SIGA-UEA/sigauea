"""Correções exigidas, versão final e conclusão do TCC (RBN11.01 a RBN11.04 · RN11, RN13, RN17, RN24 · DS-FL07).

Faz o papel do ControladorCorrecoes do diagrama de classes (MOD04):
- consultar(tcc): a aba Correções (TEL14), com o prazo, as correções, a versão final e o que falta para concluir;
- registrarCorrecao (DS-FL07-A): um membro da banca que avalia registra a exigência, se o resultado vigente é
  "aprovado com correções"; o aluno recebe e-mail;
- registrarAnuencia (DS-FL07, mensagem 7): o aluno dá anuência às correções; libera a Folha de Aprovação
  (RBN09.15 CA-03);
- marcarAtendida (DS-FL07, mensagem 10): o aluno marca a correção pendente ou devolvida como atendida;
- decidirCorrecao (DS-FL07-B): o professor responsável pela turma aprova, ou devolve com justificativa;
- enviar a versão final (DS-FL07, mensagens 17 a 21): PDF válido de até 20 MB, com SHA-256; depois do prazo fica
  "entregue com atraso" e o professor responsável decide se aceita (DS-FL07-D);
- alterarPrazo (DS-FL07-D, A1): o professor responsável muda o prazo com motivo;
- verificarConclusao (DS-FL07-C): com resultado confirmado e não reprovado, todas as correções aprovadas (se o
  resultado as exige) e a versão final enviada e aceita, o TCC passa a CONCLUIDO, com a data de conclusão.

Quem é o professor responsável (RN24, RN26): o da turma do TCC; no TCC2 é o orientador, no TCC1 o professor da
disciplina. Concluir o TCC não encerra a turma (RBN08.05) nem mexe na situação editorial do artigo (RN10).
"""

from datetime import date

from fastapi import BackgroundTasks, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import config
from app.database import agora
from app.erros import ErroAPI
from app.models import (
    ACEITA,
    APROVADO_COM_CORRECOES,
    CORRECAO_APROVADA,
    CORRECAO_ATENDIDA,
    CORRECAO_DEVOLVIDA,
    CORRECAO_PENDENTE,
    FINALIDADE_FINAL,
    PAPEL_ORIENTADOR,
    REPROVADO_DEFESA,
    TAMANHO_MAXIMO_PDF,
    Correcao,
    Defesa,
    DocumentoTcc,
    HistoricoSituacao,
    ResultadoDefesa,
    Tcc,
    Usuario,
)
from app.schemas.correcoes import CorrecaoOut, CorrecoesOut, PermissoesOut, VersaoFinalOut
from app.services import auditoria, documentos, email
from app.services.avaliacao import membros_que_avaliam
from app.services.defesas import agora_manaus, defesa_vigente
from app.services.tccs import _pode_ver
from app.services.turmas import pessoa

CONCLUIDO = "CONCLUIDO"
TIPO_CORRECAO_EXIGIDA = "CORRECAO_EXIGIDA"
TIPO_CORRECAO_DEVOLVIDA = "CORRECAO_DEVOLVIDA"
TIPO_ENTREGA_ATRASO = "VERSAO_FINAL_ATRASO"
TIPO_TCC_CONCLUIDO = "TCC_CONCLUIDO"
MIN_DESCRICAO = 10  # DS-FL07-A mensagem 5

SEM_VINCULO = "Só quem tem vínculo com o TCC consulta as correções."
SO_O_ALUNO = "Só o aluno autor do TCC faz esta ação."
SO_O_RESPONSAVEL = "Só o professor responsável pela turma do TCC faz esta ação."
SO_A_BANCA = "Só os membros da banca que avaliaram a defesa registram correções."


def _hoje_manaus() -> date:
    """Data de hoje em America/Manaus, pela regra única de services/defesas.py; os testes trocam esta função para
    simular o prazo."""
    return agora_manaus().date()


# =================================================================== contexto


def _obter_tcc(db: Session, usuario: Usuario, tcc_id: int, travar: bool = False) -> Tcc:
    """404 se o TCC não existe; 403 para quem não tem vínculo com ele (RBN11.01 CA-06)."""
    tcc = db.get(Tcc, tcc_id, with_for_update=travar)
    if tcc is None:
        raise ErroAPI(404, "Cadastro de TCC não encontrado.")
    if not _pode_ver(db, usuario, tcc):
        raise ErroAPI(403, SEM_VINCULO)
    return tcc


def _vigente(db: Session, defesa: Defesa | None) -> ResultadoDefesa | None:
    if defesa is None:
        return None
    return db.scalar(
        select(ResultadoDefesa).where(ResultadoDefesa.defesa_id == defesa.id, ResultadoDefesa.vigente.is_(True))
    )


def _resultado_exigido(db: Session, tcc: Tcc) -> tuple[Defesa, ResultadoDefesa]:
    defesa = defesa_vigente(tcc.id, db)
    resultado = _vigente(db, defesa)
    if defesa is None or resultado is None:
        raise ErroAPI(409, "O resultado da defesa ainda não foi confirmado.")
    return defesa, resultado


def _exigir_aberto(tcc: Tcc) -> None:
    if tcc.situacao == CONCLUIDO:
        raise ErroAPI(409, "O TCC já foi concluído.")


def _responsavel(tcc: Tcc, usuario: Usuario) -> bool:
    """RN24: o professor responsável pela turma do TCC (no TCC2, o orientador; no TCC1, o da disciplina)."""
    return tcc.turma.professor_id == usuario.id


def _exigir_responsavel(tcc: Tcc, usuario: Usuario) -> None:
    if not _responsavel(tcc, usuario):
        raise ErroAPI(403, SO_O_RESPONSAVEL)


def _exigir_aluno(tcc: Tcc, usuario: Usuario) -> None:
    if tcc.aluno_id != usuario.id:
        raise ErroAPI(403, SO_O_ALUNO)


def correcoes_da_defesa(db: Session, defesa: Defesa | None) -> list[Correcao]:
    """Todas as correções da defesa, também as registradas antes de uma retificação do resultado."""
    if defesa is None:
        return []
    return list(db.scalars(
        select(Correcao).join(ResultadoDefesa).where(ResultadoDefesa.defesa_id == defesa.id).order_by(Correcao.id)
    ))


def _correcao_do_tcc(db: Session, correcao_id: int, usuario: Usuario) -> tuple[Correcao, Tcc]:
    correcao = db.get(Correcao, correcao_id, with_for_update=True)
    if correcao is None:
        raise ErroAPI(404, "Correção não encontrada.")
    # trava o TCC: duas decisões do mesmo TCC ao mesmo tempo passam uma de cada vez, e a última conclui (DS-FL07-C)
    tcc = _obter_tcc(db, usuario, correcao.resultado.defesa.tcc_id, travar=True)
    return correcao, tcc


# =================================================================== condições de conclusão (DS-FL07-C)


def pendencias(db: Session, tcc: Tcc, defesa: Defesa | None, resultado: ResultadoDefesa | None) -> list[str]:
    """O que ainda falta para concluir o TCC (RBN11.04 CA-02), na ordem do DS-FL07-C. Vazio = pode concluir."""
    if tcc.situacao == CONCLUIDO:
        return []
    if resultado is None:
        return ["Resultado da defesa confirmado pelo orientador."]
    if resultado.resultado == REPROVADO_DEFESA:  # CA-04
        return ["O resultado da defesa é reprovado: o TCC não é concluído como aprovado."]
    faltam = []
    if resultado.resultado == APROVADO_COM_CORRECOES:
        correcoes = correcoes_da_defesa(db, defesa)
        if not correcoes:
            faltam.append("Correções exigidas pela banca (nenhuma registrada ainda).")
        else:
            aprovadas = sum(1 for c in correcoes if c.situacao == CORRECAO_APROVADA)
            if aprovadas < len(correcoes):
                faltam.append(f"Correções aprovadas pelo professor responsável: {aprovadas} de {len(correcoes)}.")
    if resultado.versao_final_id is None:
        faltam.append("Versão final enviada pelo aluno.")
    elif resultado.entregue_com_atraso and resultado.atraso_aceito is None:
        faltam.append("Decisão do professor responsável sobre a entrega com atraso.")
    elif resultado.entregue_com_atraso and resultado.atraso_aceito is False:
        faltam.append("Nova versão final: a entrega com atraso foi recusada pelo professor responsável.")
    return faltam


def _orientador(tcc: Tcc) -> Usuario | None:
    o = next((o for o in tcc.orientacoes if o.papel == PAPEL_ORIENTADOR and o.status == ACEITA
              and o.encerrado_em is None), None)
    return o.professor if o else None


def verificar_conclusao(db: Session, tarefas: BackgroundTasks, tcc: Tcc, ator: Usuario) -> bool:
    """DS-FL07-C: conclui o TCC quando a última condição é satisfeita; senão nada muda (E1). Quem chama faz o
    commit. Devolve se o TCC está concluído."""
    if tcc.situacao == CONCLUIDO:
        return True
    defesa = defesa_vigente(tcc.id, db)
    if pendencias(db, tcc, defesa, _vigente(db, defesa)):
        return False
    anterior = tcc.situacao
    tcc.situacao, tcc.concluido_em, tcc.atualizado_em = CONCLUIDO, agora(), agora()  # mensagem 5
    db.add(HistoricoSituacao(  # mensagem 6
        tcc_id=tcc.id, situacao_anterior=anterior, situacao_nova=CONCLUIDO, usuario_id=ator.id,
        observacao="Conclusão automática: resultado confirmado, correções aprovadas e versão final enviada.",
    ))
    auditoria.registrar(db, ator_id=ator.id, acao="concluir_tcc", entidade="tcc", entidade_id=tcc.id,  # mensagem 7
                        campo="situacao", anterior=anterior, novo=CONCLUIDO)
    destinatarios = [tcc.aluno.usuario] + [o for o in [_orientador(tcc)] if o is not None]
    for pessoa_ in destinatarios:  # mensagem 8
        email.enfileirar(
            db, tarefas, pessoa_, TIPO_TCC_CONCLUIDO, "SIGA UEA: TCC concluído",
            f'Olá, {pessoa_.nome}.\n\nO TCC "{tcc.titulo}", de {tcc.aluno.usuario.nome}, foi concluído: o resultado '
            "da defesa está confirmado, as correções foram aprovadas e a versão final foi enviada.\n\n"
            f"{config.FRONTEND_URL}/tccs/{tcc.id}\n",
            entidade="tcc", entidade_id=tcc.id,
        )
    return True


# =================================================================== consulta (TEL14)


def _correcao_out(c: Correcao) -> CorrecaoOut:
    return CorrecaoOut(
        id=c.id, descricao=c.descricao, avaliador=pessoa(c.avaliador.usuario), papel=c.avaliador.papel,
        situacao=c.situacao, justificativa=c.justificativa, criada_em=c.criada_em, atendida_em=c.atendida_em,
        decidida_por=pessoa(c.decisor) if c.decisor else None, decidida_em=c.decidida_em,
    )


def _versao_final_out(r: ResultadoDefesa) -> VersaoFinalOut | None:
    d = r.versao_final
    if d is None:
        return None
    return VersaoFinalOut(
        id=d.id, versao=d.versao, nome_arquivo=d.nome_arquivo, tamanho_bytes=d.tamanho_bytes, sha256=d.sha256,
        enviado_em=d.enviado_em, entregue_com_atraso=bool(r.entregue_com_atraso), atraso_aceito=r.atraso_aceito,
    )


def _membro_que_avalia(defesa: Defesa | None, usuario: Usuario):
    if defesa is None:
        return None
    return next((m for m in membros_que_avaliam(defesa) if m.usuario_id == usuario.id), None)


def consultar(db: Session, usuario: Usuario, tcc_id: int) -> CorrecoesOut:
    """GET /tccs/{idTcc}/correcoes (DS-FL07, mensagens 3 a 5)."""
    tcc = _obter_tcc(db, usuario, tcc_id)
    defesa = defesa_vigente(tcc.id, db)
    resultado = _vigente(db, defesa)
    aberto = tcc.situacao != CONCLUIDO
    aluno = tcc.aluno_id == usuario.id
    com_correcoes = resultado is not None and resultado.resultado == APROVADO_COM_CORRECOES
    aprovado = resultado is not None and resultado.resultado != REPROVADO_DEFESA
    responsavel = _responsavel(tcc, usuario)
    return CorrecoesOut(
        tcc_id=tcc.id,
        defesa_id=defesa.id if defesa else None,
        resultado=resultado.resultado if resultado else None,
        situacao_tcc=tcc.situacao,
        concluido_em=tcc.concluido_em,
        prazo=resultado.prazo_versao_final if resultado else None,
        prazo_motivo=resultado.prazo_motivo if resultado else None,
        anuencia_em=resultado.anuencia_em if resultado else None,
        professor_responsavel=pessoa(tcc.turma.professor.usuario),
        correcoes=[_correcao_out(c) for c in correcoes_da_defesa(db, defesa)],
        versao_final=_versao_final_out(resultado) if resultado else None,
        pendencias=pendencias(db, tcc, defesa, resultado),
        permissoes=PermissoesOut(
            registrar=aberto and com_correcoes and _membro_que_avalia(defesa, usuario) is not None,
            marcar_atendida=aberto and aluno and com_correcoes,
            enviar_versao_final=aberto and aluno and aprovado,
            dar_anuencia=aluno and com_correcoes and resultado.anuencia_em is None,
            decidir=aberto and responsavel and resultado is not None,
            alterar_prazo=aberto and responsavel and aprovado,
        ),
    )


# =================================================================== RBN11.01 · registrar correção e prazo


def registrar_correcao(db: Session, tarefas: BackgroundTasks, usuario: Usuario, tcc_id: int, descricao: str
                       ) -> CorrecoesOut:
    """POST /tccs/{idTcc}/correcoes (DS-FL07-A, mensagens 6 a 14)."""
    tcc = _obter_tcc(db, usuario, tcc_id, travar=True)
    _exigir_aberto(tcc)
    defesa, resultado = _resultado_exigido(db, tcc)
    if resultado.resultado != APROVADO_COM_CORRECOES:  # CA-02: sem lista quando aprovado ou reprovado
        raise ErroAPI(409, "O resultado vigente da defesa não exige correções.")
    membro = _membro_que_avalia(defesa, usuario)  # mensagem 7 (E1)
    if membro is None:
        raise ErroAPI(403, SO_A_BANCA)
    if len(descricao) < MIN_DESCRICAO:
        raise ErroAPI(422, f"Descreva a correção com ao menos {MIN_DESCRICAO} caracteres.", campo="descricao")
    correcao = Correcao(resultado_id=resultado.id, descricao=descricao, avaliador_id=membro.id,
                        situacao=CORRECAO_PENDENTE)  # mensagem 8
    db.add(correcao)
    db.flush()
    auditoria.registrar(db, ator_id=usuario.id, acao="registrar_correcao", entidade="correcao",  # mensagem 9
                        entidade_id=correcao.id, campo="descricao", novo=descricao)
    aluno = tcc.aluno.usuario
    prazo = resultado.prazo_versao_final
    ate = f"\nPrazo da versão final: {prazo.strftime('%d/%m/%Y')}." if prazo else ""
    email.enfileirar(  # mensagens 10 a 14 (E2: a falha fica registrada e não desfaz a correção)
        db, tarefas, aluno, TIPO_CORRECAO_EXIGIDA, "SIGA UEA: nova correção exigida pela banca",
        f'Olá, {aluno.nome}.\n\n{usuario.nome} registrou uma correção no TCC "{tcc.titulo}":\n\n{descricao}\n{ate}'
        f"\n\nVeja as correções na aba Correções do TCC:\n{config.FRONTEND_URL}/tccs/{tcc.id}\n",
        entidade="tcc", entidade_id=tcc.id,
    )
    db.commit()
    return consultar(db, usuario, tcc_id)


def alterar_prazo(db: Session, usuario: Usuario, tcc_id: int, prazo: date, motivo: str) -> CorrecoesOut:
    """POST /tccs/{idTcc}/correcoes/prazo (DS-FL07-D, A1 · RBN11.01 CA-05): o prazo vale para este TCC."""
    tcc = _obter_tcc(db, usuario, tcc_id, travar=True)
    _exigir_responsavel(tcc, usuario)
    _exigir_aberto(tcc)
    _, resultado = _resultado_exigido(db, tcc)
    if not motivo:  # E4
        raise ErroAPI(422, "Informe o motivo da alteração do prazo.", campo="motivo")
    if prazo < _hoje_manaus():  # o atraso é decidido no envio; um prazo já passado não faz sentido
        raise ErroAPI(422, "O novo prazo não pode ser anterior a hoje.", campo="prazo")
    anterior = resultado.prazo_versao_final
    resultado.prazo_versao_final, resultado.prazo_motivo = prazo, motivo
    auditoria.registrar(  # mensagem 9: anterior, novo e motivo
        db, ator_id=usuario.id, acao="alterar_prazo_versao_final", entidade="resultado_defesa",
        entidade_id=resultado.id, campo="prazo_versao_final",
        anterior=anterior.isoformat() if anterior else None, novo=f"{prazo.isoformat()}; motivo: {motivo}",
    )
    db.commit()
    return consultar(db, usuario, tcc_id)


# =================================================================== RBN11.02 · anuência, atendida e versão final


def registrar_anuencia(db: Session, usuario: Usuario, tcc_id: int) -> CorrecoesOut:
    """POST /tccs/{idTcc}/correcoes/anuencia (DS-FL07, mensagens 6 a 8 · RBN09.15 CA-03)."""
    tcc = _obter_tcc(db, usuario, tcc_id, travar=True)
    _exigir_aluno(tcc, usuario)
    _, resultado = _resultado_exigido(db, tcc)
    if resultado.resultado != APROVADO_COM_CORRECOES:
        raise ErroAPI(409, "A anuência só é pedida quando o resultado é aprovado com correções.")
    if resultado.anuencia_em is not None:
        raise ErroAPI(409, "A anuência às correções já foi registrada.")
    resultado.anuencia_em = agora()
    auditoria.registrar(db, ator_id=usuario.id, acao="registrar_anuencia", entidade="resultado_defesa",
                        entidade_id=resultado.id, campo="anuencia_em", novo=resultado.anuencia_em.isoformat())
    db.commit()
    return consultar(db, usuario, tcc_id)


def marcar_atendida(db: Session, usuario: Usuario, correcao_id: int) -> CorrecoesOut:
    """POST /correcoes/{idCorrecao}/atendida (DS-FL07, mensagens 10 e 11 · RBN11.02 CA-01, CA-05, CA-06)."""
    correcao, tcc = _correcao_do_tcc(db, correcao_id, usuario)
    _exigir_aluno(tcc, usuario)  # E2
    _exigir_aberto(tcc)
    if correcao.situacao not in (CORRECAO_PENDENTE, CORRECAO_DEVOLVIDA):
        raise ErroAPI(409, "Só uma correção pendente ou devolvida pode ser marcada como atendida.")
    anterior = correcao.situacao
    correcao.situacao, correcao.atendida_em = CORRECAO_ATENDIDA, agora()
    auditoria.registrar(db, ator_id=usuario.id, acao="marcar_correcao_atendida", entidade="correcao",
                        entidade_id=correcao.id, campo="situacao", anterior=anterior, novo=CORRECAO_ATENDIDA)
    db.commit()
    return consultar(db, usuario, tcc.id)


def _validar_pdf(conteudo: bytes) -> None:
    """RN11, RBN11.02 CA-04: vazio, acima de 20 MB ou sem o cabeçalho de PDF é recusado; nada muda."""
    if not conteudo:
        raise ErroAPI(422, "O arquivo está vazio.", campo="arquivo")
    if len(conteudo) > TAMANHO_MAXIMO_PDF:
        raise ErroAPI(422, "O arquivo passa de 20 MB.", campo="arquivo")
    if not conteudo.startswith(b"%PDF-"):
        raise ErroAPI(422, "O arquivo não é um PDF válido.", campo="arquivo")


def enviar_versao_final(
    db: Session, tarefas: BackgroundTasks, usuario: Usuario, tcc_id: int, arquivo: UploadFile
) -> CorrecoesOut:
    """POST /tccs/{idTcc}/correcoes/versao-final (DS-FL07, mensagens 14 a 21 · RBN11.02).

    Grava o PDF como nova versão (finalidade FINAL) sem apagar as anteriores (CA-02), marca a entrega com atraso
    depois do prazo (CA-03) e confere se o TCC pode ser concluído (DS-FL07-C)."""
    tcc = _obter_tcc(db, usuario, tcc_id, travar=True)
    _exigir_aluno(tcc, usuario)  # E2 / CA-06
    _exigir_aberto(tcc)
    _, resultado = _resultado_exigido(db, tcc)
    if resultado.resultado == REPROVADO_DEFESA:
        raise ErroAPI(409, "O resultado da defesa é reprovado: não há versão final a enviar.")
    conteudo = arquivo.file.read(TAMANHO_MAXIMO_PDF + 1)
    _validar_pdf(conteudo)  # E1: a versão vigente é mantida

    versao = (db.scalar(select(func.max(DocumentoTcc.versao)).where(DocumentoTcc.tcc_id == tcc.id)) or 0) + 1
    caminho = f"tccs/{tcc.id}/v{versao}-final.pdf"
    sha256 = documentos.gravar(caminho, conteudo)
    try:
        documento = DocumentoTcc(  # mensagem 18
            tcc_id=tcc.id, versao=versao, finalidade=FINALIDADE_FINAL,
            nome_arquivo=(arquivo.filename or "versao-final.pdf")[:255], tamanho_bytes=len(conteudo),
            sha256=sha256, caminho=caminho, enviado_por=usuario.id,
        )
        db.add(documento)
        db.flush()
        prazo = resultado.prazo_versao_final
        atrasada = prazo is not None and _hoje_manaus() > prazo  # mensagem 19 (CA-03)
        resultado.versao_final_id = documento.id
        resultado.entregue_com_atraso = atrasada
        resultado.atraso_aceito = resultado.atraso_decidido_por = resultado.atraso_decidido_em = None
        auditoria.registrar(  # mensagem 20
            db, ator_id=usuario.id, acao="enviar_versao_final", entidade="documento_tcc", entidade_id=documento.id,
            campo="versao", novo=f"v{versao} FINAL; sha256 {sha256}" + ("; entregue com atraso" if atrasada else ""),
        )
        if atrasada:  # CA-03: o professor responsável é avisado para decidir
            professor = tcc.turma.professor.usuario
            email.enfileirar(
                db, tarefas, professor, TIPO_ENTREGA_ATRASO, "SIGA UEA: versão final entregue com atraso",
                f'Olá, {professor.nome}.\n\n{tcc.aluno.usuario.nome} enviou a versão final do TCC "{tcc.titulo}" '
                f"depois do prazo ({prazo.strftime('%d/%m/%Y')}). Decida se aceita a entrega na aba Correções:\n"
                f"{config.FRONTEND_URL}/tccs/{tcc.id}\n",
                entidade="tcc", entidade_id=tcc.id,
            )
        verificar_conclusao(db, tarefas, tcc, usuario)  # mensagem 21
        db.commit()
    except Exception:
        db.rollback()
        documentos.apagar(caminho)  # o arquivo sem registro não fica no disco
        raise
    return consultar(db, usuario, tcc_id)


def arquivo_versao_final(db: Session, usuario: Usuario, tcc_id: int) -> tuple[str, bytes]:
    """GET /tccs/{idTcc}/correcoes/versao-final: o PDF vigente, conferido pelo SHA-256 (RNF06)."""
    tcc = _obter_tcc(db, usuario, tcc_id)
    resultado = _vigente(db, defesa_vigente(tcc.id, db))
    if resultado is None or resultado.versao_final is None:
        raise ErroAPI(404, "A versão final ainda não foi enviada.")
    d = resultado.versao_final
    return d.nome_arquivo, documentos.ler(d.caminho, d.sha256)


# =================================================================== RBN11.03 · decidir correção e atraso


def decidir_correcao(
    db: Session, tarefas: BackgroundTasks, usuario: Usuario, correcao_id: int, decisao: str, justificativa: str
) -> CorrecoesOut:
    """POST /correcoes/{idCorrecao}/decisao (DS-FL07-B, mensagens 5 a 16)."""
    correcao, tcc = _correcao_do_tcc(db, correcao_id, usuario)
    _exigir_responsavel(tcc, usuario)  # E1 / CA-04
    _exigir_aberto(tcc)
    if correcao.situacao != CORRECAO_ATENDIDA:  # E2 (mensagem 9)
        raise ErroAPI(409, "Só uma correção marcada como atendida pelo aluno pode ser aprovada ou devolvida.")
    devolver = decisao == "DEVOLVER"
    if devolver and not justificativa:  # E3 / CA-03
        raise ErroAPI(422, "Escreva o que falta corrigir para devolver a correção.", campo="justificativa")
    nova = CORRECAO_DEVOLVIDA if devolver else CORRECAO_APROVADA
    correcao.situacao, correcao.decidida_por, correcao.decidida_em = nova, usuario.id, agora()  # mensagem 10
    correcao.justificativa = justificativa if devolver else None
    auditoria.registrar(db, ator_id=usuario.id, acao="decidir_correcao", entidade="correcao",  # mensagem 11
                        entidade_id=correcao.id, campo="situacao", anterior=CORRECAO_ATENDIDA,
                        novo=f"{nova}; {justificativa}" if devolver else nova)
    if devolver:  # mensagens 12 a 16
        aluno = tcc.aluno.usuario
        email.enfileirar(
            db, tarefas, aluno, TIPO_CORRECAO_DEVOLVIDA, "SIGA UEA: correção devolvida",
            f'Olá, {aluno.nome}.\n\n{usuario.nome} devolveu uma correção do TCC "{tcc.titulo}".\n\n'
            f"Correção: {correcao.descricao}\nO que falta: {justificativa}\n\n"
            f"Ajuste o trabalho, envie a versão final de novo e marque a correção como atendida:\n"
            f"{config.FRONTEND_URL}/tccs/{tcc.id}\n",
            entidade="tcc", entidade_id=tcc.id,
        )
    else:  # CA-06: com a última aprovada, a conclusão automática é avaliada
        verificar_conclusao(db, tarefas, tcc, usuario)
    db.commit()
    return consultar(db, usuario, tcc.id)


def decidir_atraso(db: Session, tarefas: BackgroundTasks, usuario: Usuario, tcc_id: int, aceita: bool
                   ) -> CorrecoesOut:
    """POST /tccs/{idTcc}/correcoes/atraso (DS-FL07-D, mensagens 2 a 5 · RBN11.03 CA-05)."""
    tcc = _obter_tcc(db, usuario, tcc_id, travar=True)
    _exigir_responsavel(tcc, usuario)
    _exigir_aberto(tcc)
    _, resultado = _resultado_exigido(db, tcc)
    if not resultado.entregue_com_atraso or resultado.atraso_aceito is not None:  # E3
        raise ErroAPI(409, "Não há entrega com atraso a decidir.")
    resultado.atraso_aceito, resultado.atraso_decidido_por, resultado.atraso_decidido_em = aceita, usuario.id, agora()
    auditoria.registrar(db, ator_id=usuario.id, acao="decidir_atraso", entidade="resultado_defesa",
                        entidade_id=resultado.id, campo="atraso_aceito", novo="aceita" if aceita else "recusada")
    if aceita:
        verificar_conclusao(db, tarefas, tcc, usuario)
    db.commit()
    return consultar(db, usuario, tcc_id)


# =================================================================== integração com o resultado (DS-FL06)


def copiar_para_retificacao(atual: ResultadoDefesa, nova: ResultadoDefesa) -> None:
    """A retificação grava uma nova versão do resultado; o prazo, a anuência do aluno, a versão final e a decisão
    sobre o atraso continuam valendo (as correções ficam ligadas à defesa)."""
    for campo in ("prazo_versao_final", "prazo_motivo", "anuencia_em", "versao_final_id", "entregue_com_atraso",
                  "atraso_aceito", "atraso_decidido_por", "atraso_decidido_em"):
        setattr(nova, campo, getattr(atual, campo))
