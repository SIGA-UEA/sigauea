"""Resultado da defesa: consolidação, confirmação e retificação (RBN09.11, RBN09.12 · RN07, RN13, RN21).

Faz o papel de consultarResultado(defesa), registrarResultado(defesa, resultado) e
retificarResultado(defesa, resultado, motivo) do ControladorAvaliacaoDefesa (diagrama de classes, MOD04):
- GET /defesas/{id}/resultado (DS-FL06, mensagens 3 a 9): com resultado vigente, devolve o resultado e as
  retificações (A2); senão confere quem já enviou a avaliação e, com todas enviadas, chama a
  CalculadoraNotaFinal (DS-FL06-B);
- POST /defesas/{id}/resultado (DS-FL06, mensagens 7 a 15): recalcula a nota final, grava a versão 1 do
  ResultadoDefesa, registra no log e avisa o aluno e a banca por e-mail;
- POST /defesas/{id}/resultado/retificacao (DS-FL06-D): grava uma nova versão, a anterior deixa de ser
  vigente (de, para, quem, quando, motivo), registra no log e avisa o aluno e a banca.

Quem pode: só o orientador do TCC, o ator do DS-FL06 (RBN09.12, CA-05). Quem vê o TCC sem ser o orientador
recebe 403 (o avaliador vê só a própria avaliação, RBN10.02 CA-02); quem nem vê o TCC recebe 404 (RN07).

Efeitos da confirmação (CA-04): a ata é gerada a partir do resultado confirmado em "Ata e certificados"
(RBN09.14) e, em "aprovado com correções", a lista de correções é registrada a partir dele (RBN11.01). A ata
gerada antes de uma retificação fica desatualizada: o resultado vigente é mais novo que ela (RN15).
"""

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import agora
from app.erros import ErroAPI
from app.models import ACEITA, CANCELADA, PAPEL_ORIENTADOR, Defesa, ResultadoDefesa, Tcc, Usuario
from app.schemas.resultado import (
    ConfirmacaoEntrada,
    MembroPendenteOut,
    NotaDoMembroOut,
    NotaFinalOut,
    RegraExcecaoOut,
    ResultadoConsulta,
    ResultadoOut,
    RetificacaoEntrada,
    RetificacaoOut,
)
from app.services import acessos, auditoria, avaliacao, avisos_defesa, nota_final
from app.services.tccs import obter_para
from app.services.turmas import pessoa

SO_O_ORIENTADOR = "Só o orientador do TCC consolida o resultado da defesa."
JA_CONFIRMADO = "O resultado desta defesa já foi confirmado. Para alterá-lo, registre uma retificação."


def _orientador_do_tcc(tcc: Tcc, usuario: Usuario) -> bool:
    return any(
        o.papel == PAPEL_ORIENTADOR and o.status == ACEITA and o.encerrado_em is None and o.professor_id == usuario.id
        for o in tcc.orientacoes
    )


def _defesa_do_orientador(db: Session, usuario: Usuario, defesa_id: int) -> Defesa:
    defesa = db.get(Defesa, defesa_id)
    if defesa is None:
        raise ErroAPI(404, "Defesa não encontrada.")
    tcc = obter_para(db, usuario, defesa.tcc_id)  # 404 para quem não vê o TCC (RN07)
    if not _orientador_do_tcc(tcc, usuario):
        raise ErroAPI(403, SO_O_ORIENTADOR)
    if defesa.situacao == CANCELADA:
        raise ErroAPI(409, "Esta defesa foi cancelada.")
    return defesa


def _versoes(db: Session, defesa: Defesa) -> list[ResultadoDefesa]:
    return list(db.scalars(
        select(ResultadoDefesa).where(ResultadoDefesa.defesa_id == defesa.id).order_by(ResultadoDefesa.versao)
    ))


def vigente(db: Session, defesa: Defesa) -> ResultadoDefesa | None:
    """O resultado confirmado que vale para a defesa (ata, folha e correções partem dele)."""
    return db.scalar(
        select(ResultadoDefesa).where(ResultadoDefesa.defesa_id == defesa.id, ResultadoDefesa.vigente.is_(True))
    )


def _resultado_out(versoes: list[ResultadoDefesa]) -> ResultadoOut:
    atual, primeira = versoes[-1], versoes[0]
    return ResultadoOut(
        versao=atual.versao,
        resultado=atual.resultado,
        parecer=atual.parecer,
        media=float(atual.media),
        nota_final=float(atual.nota_final),
        regra_qualis=atual.regra_qualis,
        confirmado_por=pessoa(primeira.autor),
        confirmado_em=primeira.confirmado_em,
        retificacoes=[
            RetificacaoOut(de=antes.resultado, para=depois.resultado, motivo=depois.motivo_retificacao or "",
                           por=pessoa(depois.autor), em=depois.confirmado_em)
            for antes, depois in zip(versoes, versoes[1:])
        ],
    )


def _consolidacao_out(calculo: nota_final.NotaFinal) -> NotaFinalOut:
    return NotaFinalOut(
        notas=[
            NotaDoMembroOut(membro_id=n.membro.id, papel=n.membro.papel, pessoa=pessoa(n.membro.usuario),
                            nota=float(n.nota))
            for n in calculo.notas
        ],
        media=float(calculo.media),
        regra=RegraExcecaoOut(
            aplicada=calculo.regra.aplicada,
            porque=calculo.regra.porque,
            modalidade=calculo.regra.modalidade,
            situacao_editorial=calculo.regra.situacao_editorial,
            qualis=calculo.regra.qualis,
        ),
        nota_final=float(calculo.nota_final),
    )


def _pendentes_out(faltam) -> list[MembroPendenteOut]:
    return [MembroPendenteOut(membro_id=m.id, papel=m.papel, pessoa=pessoa(m.usuario)) for m in faltam]


def consultar_resultado(db: Session, usuario: Usuario, defesa_id: int) -> ResultadoConsulta:
    """GET /defesas/{idDefesa}/resultado (DS-FL06, mensagens 3 a 9)."""
    defesa = _defesa_do_orientador(db, usuario, defesa_id)
    versoes = _versoes(db, defesa)
    if versoes:  # [resultado já confirmado (RN13)]: o resultado, "Retificar resultado" e "Ata e certificados"
        return ResultadoConsulta(defesa_id=defesa.id, pendentes=[], consolidacao=None,
                                 resultado=_resultado_out(versoes))
    faltam = avaliacao.pendentes(db, defesa)  # "quem já enviou" (RBN10.05)
    if faltam:  # [falta avaliação]: o cálculo não é liberado e as pendências são indicadas (CA-05 do RBN09.11)
        return ResultadoConsulta(defesa_id=defesa.id, pendentes=_pendentes_out(faltam), consolidacao=None)
    # [todas enviadas]: DS-FL06-B
    return ResultadoConsulta(defesa_id=defesa.id, pendentes=[],
                             consolidacao=_consolidacao_out(nota_final.calcular_nota_final(db, defesa)))


def _gravar(db: Session) -> None:
    """Duas confirmações (ou retificações) ao mesmo tempo: o índice de resultado vigente e a versão única
    deixam passar só a primeira; a outra recebe 409, como no E2 do DS-FL06."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ErroAPI(409, JA_CONFIRMADO) from None


def confirmar_resultado(
    db: Session, usuario: Usuario, defesa_id: int, dados: ConfirmacaoEntrada, tarefas: BackgroundTasks
) -> ResultadoConsulta:
    """POST /defesas/{idDefesa}/resultado {resultado, parecer} (DS-FL06, mensagens 7 a 15)."""
    defesa = _defesa_do_orientador(db, usuario, defesa_id)  # E1: não é o orientador → 403 (CA-05)
    if vigente(db, defesa) is not None:  # E2: já confirmado → 409 (RN13, CA-06)
        raise ErroAPI(409, JA_CONFIRMADO)
    faltam = avaliacao.pendentes(db, defesa)
    if faltam:  # CA-03: impedido, com as pendências listadas (RBN10.05)
        nomes = ", ".join(m.usuario.nome for m in faltam)
        raise ErroAPI(409, f"Aguardando avaliações. Faltam: {nomes}.",
                      pendentes=[p.model_dump(mode="json") for p in _pendentes_out(faltam)])
    parecer = dados.parecer.strip()
    if not parecer:
        raise ErroAPI(422, "Escreva o parecer da banca antes de confirmar.", campo="parecer")

    calculo = nota_final.calcular_nota_final(db, defesa)  # "recalcular a nota final"
    registro = ResultadoDefesa(
        defesa_id=defesa.id, versao=1, vigente=True, media=calculo.media, nota_final=calculo.nota_final,
        regra_qualis=calculo.regra.aplicada, resultado=dados.resultado, parecer=parecer,
        confirmado_por=usuario.id, confirmado_em=agora(),
    )
    db.add(registro)
    try:
        db.flush()
    except IntegrityError:  # outra confirmação gravou entre a conferência e esta gravação
        db.rollback()
        raise ErroAPI(409, JA_CONFIRMADO) from None
    auditoria.registrar(db, ator_id=usuario.id, acao="confirmar_resultado", entidade="resultado_defesa",
                        entidade_id=registro.id, campo="resultado",
                        novo=f"{dados.resultado}; nota final {calculo.nota_final}")
    acessos.definir_prazo_banca(db, defesa, registro.confirmado_em)  # RBN01.12: o externo tem mais 7 dias (32-d)
    # E3: o aviso entra na fila na mesma transação e sai depois da resposta; a falha de envio não desfaz nada
    avisos_defesa.avisar_resultado(db, tarefas, defesa, registro)
    _gravar(db)
    return consultar_resultado(db, usuario, defesa_id)


def retificar_resultado(
    db: Session, usuario: Usuario, defesa_id: int, dados: RetificacaoEntrada, tarefas: BackgroundTasks
) -> ResultadoConsulta:
    """POST /defesas/{idDefesa}/resultado/retificacao {resultado, motivo} (DS-FL06-D)."""
    defesa = _defesa_do_orientador(db, usuario, defesa_id)  # E4: não é o orientador → 403
    atual = vigente(db, defesa)
    if atual is None:
        raise ErroAPI(409, "O resultado desta defesa ainda não foi confirmado.")
    motivo = dados.motivo.strip()
    if not motivo:  # E5 (RN13)
        raise ErroAPI(422, "Informe o motivo da retificação.", campo="motivo")
    if dados.resultado == atual.resultado:  # a tela avisa antes; a API também não grava versão sem mudança
        raise ErroAPI(422, "O novo resultado é igual ao vigente: nada mudou.", campo="resultado")

    anterior = atual.resultado
    atual.vigente = False
    nova = ResultadoDefesa(
        defesa_id=defesa.id, versao=atual.versao + 1, vigente=True, media=atual.media, nota_final=atual.nota_final,
        regra_qualis=atual.regra_qualis, resultado=dados.resultado, parecer=atual.parecer,
        confirmado_por=usuario.id, confirmado_em=agora(), motivo_retificacao=motivo,
    )
    try:
        db.flush()  # a versão anterior deixa de ser vigente antes da nova entrar (índice de resultado vigente)
        db.add(nova)
        db.flush()
    except IntegrityError:  # outra retificação gravou a mesma versão ao mesmo tempo
        db.rollback()
        raise ErroAPI(409, "Outra retificação acabou de ser registrada. Confira o resultado vigente.") from None
    auditoria.registrar(db, ator_id=usuario.id, acao="retificar_resultado", entidade="resultado_defesa",
                        entidade_id=nova.id, campo="resultado", anterior=anterior,
                        novo=f"{dados.resultado}; motivo: {motivo}")
    avisos_defesa.avisar_retificacao(db, tarefas, defesa, anterior, nova)  # E6: idem
    _gravar(db)
    return consultar_resultado(db, usuario, defesa_id)
