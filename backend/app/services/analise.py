"""Análise do cadastro de TCC pela coordenação (RAN04: RBN04.01 a RBN04.05).

Cada função segue um diagrama de sequência; os comentários "passo N" apontam para a
mensagem correspondente em DS-FL02-A (abrir a fila e examinar um cadastro) e DS-FL02
(aprovar, devolver ou reprovar).
"""

from fastapi import BackgroundTasks
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.database import agora
from app.erros import ErroAPI
from app.models import (
    EM_ANALISE,
    PAPEL_ORIENTADOR,
    ACEITA,
    RESULTADOS_ANALISE,
    Aluno,
    AnaliseCadastro,
    Curso,
    HistoricoSituacao,
    PeriodoLetivo,
    Tcc,
    Usuario,
)
from app.schemas.tcc import CadastroOut, CadastroResumo, DecisaoEntrada, DecisaoOut
from app.schemas.usuario import CursoOut
from app.services import auditoria, email
from app.services.tccs import _reenviar_falhas, _vinculo, decisao_out, mensagem_resultado, para_saida
from app.services.turmas import pessoa

SITUACOES_ANALISE = (EM_ANALISE, *RESULTADOS_ANALISE)  # RN10: pendente, aprovado, devolvido, reprovado
NAO_ENCONTRADO = "Cadastro de TCC não encontrado."
MINIMO_PARECER = 10  # devolver e reprovar: o mesmo mínimo que a TEL07 confere (DS-FL02 passo 2)


def _nucleo(coordenador: Usuario) -> int:
    """RN07: a coordenação acessa todos os cursos do seu núcleo, e só eles."""
    if coordenador.docente is None:
        raise ErroAPI(403, "Seu perfil não tem permissão para esta ação.")
    return coordenador.docente.nucleo_id


def _situacoes(texto: str | None) -> tuple[str, ...]:
    if not texto:
        return SITUACOES_ANALISE
    pedidas = tuple(s.strip().upper() for s in texto.split(",") if s.strip())
    invalidas = [s for s in pedidas if s not in SITUACOES_ANALISE]
    if invalidas or not pedidas:
        raise ErroAPI(400, "Confira os campos destacados.", campos={"situacao": "Situação inválida."})
    return pedidas


def _resumo(tcc: Tcc) -> CadastroResumo:
    hoje = agora().date()
    return CadastroResumo(
        id=tcc.id,
        protocolo=tcc.protocolo,
        titulo=tcc.titulo,
        aluno=pessoa(tcc.aluno.usuario),
        matricula=tcc.aluno.matricula,
        curso=CursoOut.model_validate(tcc.aluno.curso),
        etapa=tcc.etapa,
        modalidade=tcc.modalidade,
        periodo=tcc.periodo.codigo,
        situacao=tcc.situacao,
        submetido_em=tcc.submetido_em,
        dias_aguardando=(hoje - tcc.submetido_em.date()).days if tcc.submetido_em else 0,
        decisao=decisao_out(tcc.analises[-1] if tcc.analises else None),
    )


# =================================================================== DS-FL02-A · fila e consulta


def listar(
    db: Session, coordenador: Usuario, situacao: str | None, curso: int | None, periodo: str | None
) -> list[CadastroResumo]:
    """Passos 2, 5 e 14: cadastros do núcleo, filtrados por situação, curso e período (RBN04.01)."""
    consulta = (
        select(Tcc)
        .join(Aluno, Aluno.usuario_id == Tcc.aluno_id)
        .join(Curso, Curso.id == Aluno.curso_id)
        .join(PeriodoLetivo, PeriodoLetivo.id == Tcc.periodo_id)
        .where(
            Curso.nucleo_id == _nucleo(coordenador),
            Tcc.protocolo.is_not(None),  # rascunho nunca enviado não chega à coordenação
            Tcc.situacao.in_(_situacoes(situacao)),
        )
    )
    if curso:
        consulta = consulta.where(Curso.id == curso)
    if periodo:
        consulta = consulta.where(PeriodoLetivo.codigo == periodo.strip())
    tccs = list(db.scalars(consulta))

    # Passo 3: a fila vem do mais antigo para o mais recente; os já analisados, da decisão mais nova para a mais antiga.
    def ordem(t: Tcc):
        if t.situacao == EM_ANALISE:
            return (0, t.submetido_em.timestamp(), t.id)
        ultima = t.analises[-1].decidido_em.timestamp() if t.analises else 0
        return (1, -ultima, t.id)

    return [_resumo(t) for t in sorted(tccs, key=ordem)]


def _obter_no_nucleo(db: Session, coordenador: Usuario, tcc_id: int, travar: bool = False) -> Tcc:
    """Passo 8 (DS-FL02-A) e passo 5 (DS-FL02): fora do núcleo ou nunca enviado não é retornado (RN07)."""
    nucleo = _nucleo(coordenador)
    tcc = db.get(Tcc, tcc_id, with_for_update=travar)
    if tcc is None or tcc.protocolo is None or tcc.aluno.curso.nucleo_id != nucleo:
        raise ErroAPI(404, NAO_ENCONTRADO)
    return tcc


def obter(db: Session, coordenador: Usuario, tcc_id: int) -> CadastroOut:
    """Passos 7 a 10: dados, PDF preliminar vigente (ou vazio) e a última decisão."""
    tcc = _obter_no_nucleo(db, coordenador, tcc_id)
    return CadastroOut(
        tcc=para_saida(tcc),
        documento=None,  # passo 9: o envio do PDF (DocumentoTCC) ainda não existe; vem com o SCRUM-55
        decisao=decisao_out(tcc.analises[-1] if tcc.analises else None),  # passo 10
    )


def documento(db: Session, coordenador: Usuario, tcc_id: int) -> None:
    """Passo 12: o arquivo PDF. Enquanto o aluno não enviar o PDF, não há o que abrir."""
    _obter_no_nucleo(db, coordenador, tcc_id)
    raise ErroAPI(404, "Nenhum PDF enviado.")


# =================================================================== DS-FL02 · decisão


def decidir(
    db: Session, tarefas: BackgroundTasks, coordenador: Usuario, tcc_id: int, dados: DecisaoEntrada
) -> DecisaoOut:
    """Aprovar, devolver ou reprovar (RBN04.02 a RBN04.04). O 403 sem perfil Coordenação vem da rota (RN06)."""
    tcc = _obter_no_nucleo(db, coordenador, tcc_id, travar=True)  # passo 5, com trava da linha
    if tcc.situacao != EM_ANALISE:  # passo 6 (E2): outra pessoa já decidiu, ou não está em análise
        raise _ja_decidido(tcc)
    if dados.resultado != "APROVADO" and len(dados.parecer) < MINIMO_PARECER:  # E1: devolver e reprovar exigem parecer
        campo = (
            "Explique o que o aluno precisa corrigir (mínimo de 10 caracteres)."
            if dados.resultado == "DEVOLVIDO"
            else "Justifique a reprovação (mínimo de 10 caracteres)."
        )
        raise ErroAPI(422, "Informe o parecer.", campos={"parecer": campo})

    # Passo 8: só muda se ainda estiver em análise. Com duas decisões ao mesmo tempo, só a primeira passa (CA-05),
    # mesmo no banco que não trava a linha.
    mudou = db.execute(
        update(Tcc)
        .where(Tcc.id == tcc.id, Tcc.situacao == EM_ANALISE)
        .values(situacao=dados.resultado, atualizado_em=agora())  # protocolo mantido
        .execution_options(synchronize_session=False)
    ).rowcount
    if not mudou:
        db.rollback()
        raise _ja_decidido(db.get(Tcc, tcc_id))
    analise = AnaliseCadastro(  # passo 7
        tcc_id=tcc.id,
        coordenador_id=coordenador.id,
        resultado=dados.resultado,
        parecer=dados.parecer,
        decidido_em=agora(),
    )
    db.add(analise)
    db.add(  # passo 9
        HistoricoSituacao(
            tcc_id=tcc.id,
            situacao_anterior=EM_ANALISE,
            situacao_nova=dados.resultado,
            usuario_id=coordenador.id,
            observacao=dados.parecer or None,
        )
    )
    auditoria.registrar(  # passo 10 (RNF03)
        db,
        ator_id=coordenador.id,
        acao="decidir_cadastro",
        entidade="tcc",
        entidade_id=tcc.id,
        campo="situacao",
        anterior=EM_ANALISE,
        novo=dados.resultado,
    )
    db.flush()
    db.refresh(tcc)

    # Passos 11 e 12: aviso ao aluno e ao orientador, enviado depois da resposta (passos 13 a 16)
    _reenviar_falhas(db, tarefas, tcc)
    orientador = _vinculo(tcc, PAPEL_ORIENTADOR)
    destinatarios = [tcc.aluno.usuario]
    if orientador and orientador.status == ACEITA:
        destinatarios.append(orientador.professor)
    for pessoa_avisada in destinatarios:
        email.enfileirar(
            db,
            tarefas,
            pessoa_avisada,
            "RESULTADO_ANALISE",
            *mensagem_resultado(pessoa_avisada, tcc, analise),
            entidade="tcc",
            entidade_id=tcc.id,
        )
    db.commit()
    db.refresh(analise)
    return decisao_out(analise)


def _ja_decidido(tcc: Tcc) -> ErroAPI:
    """409 com a situação atual e a decisão registrada, para a tela mostrar e atualizar a fila."""
    ultima = tcc.analises[-1] if tcc.analises else None
    return ErroAPI(
        409,
        "Este cadastro não está mais aguardando análise. Veja a decisão registrada.",
        motivo="ja_decidido",
        situacao=tcc.situacao,
        decisao=decisao_out(ultima).model_dump(mode="json") if ultima else None,
    )
