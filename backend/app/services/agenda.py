"""Agenda de apresentações das defesas (S04 · RBN14.01 e RBN14.04, RN08).

A agenda lê a defesa vigente direto da tabela `defesa`, então remarcação, mudança de local ou
link e cancelamento aparecem sem cópia que possa ficar desatualizada (RBN14.04).
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CONFIRMADA, PAPEL_ORIENTADOR, REMARCADA, Defesa
from app.schemas.agenda import ApresentacaoOut, CursoAgenda
from app.services.defesas import _orientacao_aceita

VISIVEIS = (CONFIRMADA, REMARCADA)  # cancelada e realizada saem da programação


def _apresentacao(d: Defesa) -> ApresentacaoOut:
    tcc = d.tcc
    orientador = _orientacao_aceita(tcc, PAPEL_ORIENTADOR)
    curso = tcc.aluno.curso
    return ApresentacaoOut(
        id=d.id,
        titulo=tcc.titulo,
        autor=tcc.aluno.usuario.nome,
        orientador=orientador.professor.nome if orientador else None,
        curso=CursoAgenda(sigla=curso.sigla, nome=curso.nome),
        formato=d.formato,
        data=d.data,
        inicio=d.inicio,
        fim=d.fim,
        local=d.local.nome if d.local else None,
        link=d.link if d.divulgar_link else None,
        remarcada=d.situacao == REMARCADA,
    )


def listar(db: Session, periodo: str = "proximos") -> list[ApresentacaoOut]:
    """RBN14.01 CA-01: ordem crescente de data e horário. "proximos" (DS-FL05-A passo 2) começa hoje."""
    consulta = select(Defesa).where(Defesa.situacao.in_(VISIVEIS))
    if periodo == "proximos":
        consulta = consulta.where(Defesa.data >= date.today())
    return [_apresentacao(d) for d in db.scalars(consulta.order_by(Defesa.data, Defesa.inicio, Defesa.id))]
