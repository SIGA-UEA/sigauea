"""Acompanhamento do TCC: situação pelo orientador (RBN05.02), histórico (RBN05.04) e tarefas (RBN05.05)."""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import agora
from app.erros import ErroAPI
from app.models import (
    ACEITA,
    EM_ANALISE,
    PAPEL_ORIENTADOR,
    HistoricoSituacao,
    Tcc,
    TarefaTcc,
    Usuario,
)
from app.schemas.tcc import EventoOut, SituacaoAlterar, TarefaCriar, TarefaOut
from app.services import auditoria, tccs
from app.services.turmas import pessoa

DESISTENCIA, APROVADO = "DESISTENCIA", "APROVADO"
TRANSICOES = {(APROVADO, DESISTENCIA), (DESISTENCIA, APROVADO)}  # a análise e a conclusão têm donos próprios
MANAUS = timedelta(hours=-4)


def _campo_invalido(campo: str, mensagem: str) -> ErroAPI:
    return ErroAPI(400, "Confira os campos destacados.", campos={campo: mensagem})


def _hoje():
    return (agora() + MANAUS).date()


def _orientador_do(tcc: Tcc, usuario: Usuario) -> bool:
    return any(
        o.professor_id == usuario.id and o.papel == PAPEL_ORIENTADOR and o.status == ACEITA for o in tcc.orientacoes
    )


def _responsavel_pela_turma(tcc: Tcc, usuario: Usuario) -> bool:
    return tcc.turma.professor_id == usuario.id


# ---------------------------------------------------------------- RBN05.02


def alterar_situacao(db: Session, orientador: Usuario, tcc_id: int, dados: SituacaoAlterar) -> Tcc:
    """Só o orientador do TCC registra a desistência ou a reativa; cada mudança fica no histórico e no log."""
    tcc = db.get(Tcc, tcc_id)
    if tcc is None or not _orientador_do(tcc, orientador):
        raise ErroAPI(403, "Só o orientador do TCC atualiza a situação.")
    motivo = (dados.motivo or "").strip()
    if not motivo:
        mensagem = "Informe o motivo da desistência." if dados.situacao == DESISTENCIA else "Informe o motivo."
        raise _campo_invalido("motivo", mensagem)
    anterior = tcc.situacao
    if (anterior, dados.situacao) not in TRANSICOES:
        raise ErroAPI(409, "Não é possível passar da situação atual para a escolhida.", motivo="transicao_invalida")
    tcc.situacao = dados.situacao
    tcc.desistencia_motivo = motivo if dados.situacao == DESISTENCIA else None
    tcc.atualizado_em = agora()
    db.add(
        HistoricoSituacao(
            tcc_id=tcc.id,
            situacao_anterior=anterior,
            situacao_nova=dados.situacao,
            usuario_id=orientador.id,
            observacao=motivo,
        )
    )
    auditoria.registrar(
        db,
        ator_id=orientador.id,
        acao="atualizar_situacao_tcc",
        entidade="tcc",
        entidade_id=tcc.id,
        campo="situacao",
        anterior=anterior,
        novo=dados.situacao,
    )
    db.commit()
    db.refresh(tcc)
    return tcc


# ---------------------------------------------------------------- RBN05.04


def historico(db: Session, usuario: Usuario, tcc_id: int) -> list[EventoOut]:
    """Submissões, pareceres, vínculos e mudanças de situação em ordem cronológica; só leitura."""
    tcc = tccs.obter_para(db, usuario, tcc_id)
    eventos: list[EventoOut] = []
    for h in tcc.historico:
        if h.situacao_nova == EM_ANALISE:
            descricao = "Cadastro submetido para análise."
            tipo = "SUBMISSAO"
        elif h.situacao_anterior is None:
            descricao, tipo = "Cadastro iniciado como rascunho.", "SITUACAO"
        else:
            descricao, tipo = f"Situação alterada de {h.situacao_anterior} para {h.situacao_nova}.", "SITUACAO"
        eventos.append(
            EventoOut(tipo=tipo, descricao=descricao, detalhe=h.observacao, autor=pessoa(h.usuario), em=h.registrado_em)
        )
    for a in tcc.analises:
        eventos.append(
            EventoOut(
                tipo="PARECER",
                descricao=f"Parecer da coordenação: {a.resultado}.",
                detalhe=a.parecer,
                autor=pessoa(a.coordenador.usuario),
                em=a.decidido_em,
            )
        )
    for o in tcc.orientacoes:
        papel = "orientação" if o.papel == PAPEL_ORIENTADOR else "coorientação"
        solicitante = pessoa(tcc.aluno.usuario) if o.papel == PAPEL_ORIENTADOR else None
        eventos.append(
            EventoOut(
                tipo="VINCULO",
                descricao=f"{papel.capitalize()} solicitada a {o.professor.nome}.",
                detalhe=None,
                autor=solicitante,
                em=o.solicitado_em,
            )
        )
        if o.respondido_em:
            situacao = "aceita" if o.status == ACEITA else "recusada"
            eventos.append(
                EventoOut(
                    tipo="VINCULO",
                    descricao=f"{papel.capitalize()} {situacao} por {o.professor.nome}.",
                    detalhe=o.motivo_recusa,
                    autor=pessoa(o.professor),
                    em=o.respondido_em,
                )
            )
        if o.encerrado_em:
            eventos.append(
                EventoOut(
                    tipo="VINCULO",
                    descricao=f"{papel.capitalize()} de {o.professor.nome} encerrada.",
                    detalhe=o.justificativa_encerramento,
                    autor=None,
                    em=o.encerrado_em,
                )
            )
    return sorted(eventos, key=lambda e: e.em)


# ---------------------------------------------------------------- RBN05.05


def _status(t: TarefaTcc) -> str:
    return "ATRASADA" if t.status == "PENDENTE" and t.prazo < _hoje() else t.status


def tarefa_out(t: TarefaTcc) -> TarefaOut:
    return TarefaOut(
        id=t.id,
        descricao=t.descricao,
        prazo=t.prazo,
        status=_status(t),
        cadastrada_por=pessoa(t.autor),
        criado_em=t.criado_em,
        entregue_em=t.entregue_em,
    )


def criar_tarefa(db: Session, autor: Usuario, tcc_id: int, dados: TarefaCriar) -> TarefaTcc:
    """O orientador ou o professor responsável pela turma cadastra a tarefa de um TCC aprovado."""
    tcc = db.get(Tcc, tcc_id)
    if tcc is None or not (_orientador_do(tcc, autor) or _responsavel_pela_turma(tcc, autor)):
        raise ErroAPI(403, "Só o orientador ou o professor da turma cadastram tarefas.")
    descricao = (dados.descricao or "").strip()
    if not descricao:
        raise _campo_invalido("descricao", "Informe a descrição da tarefa.")
    if dados.prazo < _hoje():
        raise _campo_invalido("prazo", "O prazo não pode ser anterior a hoje.")
    if tcc.situacao != APROVADO:
        raise ErroAPI(409, "Só um TCC aprovado recebe tarefas.", motivo="tcc_nao_aprovado")
    tarefa = TarefaTcc(tcc_id=tcc.id, descricao=descricao, prazo=dados.prazo, cadastrada_por=autor.id)
    db.add(tarefa)
    db.flush()
    auditoria.registrar(
        db,
        ator_id=autor.id,
        acao="criar_tarefa_tcc",
        entidade="tarefa_tcc",
        entidade_id=tarefa.id,
        campo="prazo",
        novo=dados.prazo.isoformat(),
    )
    db.commit()
    db.refresh(tarefa)
    return tarefa


def listar_tarefas(db: Session, usuario: Usuario, tcc_id: int) -> list[TarefaTcc]:
    """Quem consegue ver o TCC vê as suas tarefas, das mais próximas de vencer às mais distantes."""
    tcc = tccs.obter_para(db, usuario, tcc_id)
    consulta = select(TarefaTcc).where(TarefaTcc.tcc_id == tcc.id).order_by(TarefaTcc.prazo, TarefaTcc.id)
    return list(db.scalars(consulta))
