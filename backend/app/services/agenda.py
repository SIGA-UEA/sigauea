"""ControladorAgenda (S04 · RBN14.01 e RBN14.04, RN08 e RN09): consulta e divulgação das defesas.

A agenda lê a defesa vigente direto da tabela `defesa`, então remarcação, mudança de local ou
link e cancelamento aparecem sem cópia que possa ficar desatualizada (RBN14.04). Publicar e retirar
da agenda seguem o DS-FL05: a defesa continua marcada ao ser retirada.
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import agora
from app.erros import ErroAPI
from app.models import CANCELADA, CONFIRMADA, PAPEL_ORIENTADOR, REMARCADA, Defesa, HistoricoDefesa, Usuario
from app.schemas.agenda import ApresentacaoOut, CondicaoOut, CursoAgenda, DivulgacaoOut
from app.services import auditoria
from app.services.defesas import _orientacao_aceita, pode_agendar
from app.services.tccs import obter_para

VISIVEIS = (CONFIRMADA, REMARCADA)  # cancelada e realizada saem da programação
# RN08: só aparece o que foi publicado na agenda (DS-FL05); a defesa nasce não publicada (DS-FL04 passo 18).


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
    consulta = select(Defesa).where(Defesa.situacao.in_(VISIVEIS), Defesa.publicada.is_(True))
    if periodo == "proximos":
        consulta = consulta.where(Defesa.data >= date.today())
    return [_apresentacao(d) for d in db.scalars(consulta.order_by(Defesa.data, Defesa.inicio, Defesa.id))]


# =================================================================== DS-FL05 · publicar na agenda


def _defesa_visivel(db: Session, usuario: Usuario, defesa_id: int) -> Defesa:
    """A defesa só aparece para quem enxerga o TCC (RN07); os demais recebem 404."""
    defesa = db.get(Defesa, defesa_id)
    if defesa is None:
        raise ErroAPI(404, "Defesa não encontrada.")
    obter_para(db, usuario, defesa.tcc_id)
    return defesa


def _exigir_pode_publicar(db: Session, usuario: Usuario, defesa: Defesa) -> None:
    if not pode_agendar(usuario, defesa.tcc):  # E2: só o responsável (RN14) e a coordenação
        raise ErroAPI(403, "Só o responsável pelo agendamento ou a coordenação publica na agenda.")
    if defesa.situacao == CANCELADA:  # E1
        raise ErroAPI(409, "Esta defesa foi cancelada.")


def condicoes(d: Defesa) -> list[CondicaoOut]:
    """RN09: TCC identificado e data, horário e local ou link confirmados."""
    destino_ok = {
        "PRESENCIAL": d.local_id is not None,
        "REMOTO": bool(d.link),
        "HIBRIDO": d.local_id is not None and bool(d.link),
    }[d.formato]
    return [
        CondicaoOut(descricao="TCC identificado", atendida=bool(d.tcc.titulo.strip())),
        CondicaoOut(descricao="Data e horário confirmados", atendida=d.situacao in VISIVEIS),
        CondicaoOut(descricao="Local ou link confirmado", atendida=destino_ok),
    ]


def _divulgacao(d: Defesa, pode: bool) -> DivulgacaoOut:
    return DivulgacaoOut(
        defesa_id=d.id,
        tcc_id=d.tcc_id,
        situacao=d.situacao,
        publicada=d.publicada,
        pode_publicar=pode and d.situacao != CANCELADA,
        condicoes=condicoes(d),
        previa=None if d.situacao == CANCELADA else _apresentacao(d),
    )


def divulgacao(db: Session, usuario: Usuario, defesa_id: int) -> DivulgacaoOut:
    """GET /defesas/{id}/divulgacao (passos 3 a 5): condições, prévia sem dados pessoais e se está publicada."""
    defesa = _defesa_visivel(db, usuario, defesa_id)
    return _divulgacao(defesa, pode_agendar(usuario, defesa.tcc))


def publicar(db: Session, usuario: Usuario, defesa_id: int) -> DivulgacaoOut:
    """POST /defesas/{id}/publicacao (passos 8 a 11): 422 com as pendências (RN09); grava histórico e auditoria."""
    defesa = _defesa_visivel(db, usuario, defesa_id)
    _exigir_pode_publicar(db, usuario, defesa)
    pendentes = [c.descricao for c in condicoes(defesa) if not c.atendida]
    if pendentes:
        raise ErroAPI(422, "A defesa ainda não pode ser publicada.", pendencias=pendentes)
    if not defesa.publicada:
        defesa.publicada, defesa.publicada_em = True, agora()
        db.add(HistoricoDefesa(defesa_id=defesa.id, evento="PUBLICACAO", usuario_id=usuario.id))  # mensagem 10
        auditoria.registrar(  # mensagem 11
            db, ator_id=usuario.id, acao="publicar_agenda", entidade="defesa", entidade_id=defesa.id,
            campo="publicada", anterior=False, novo=True,
        )
        db.commit()
        db.refresh(defesa)
    return _divulgacao(defesa, True)


def retirar(db: Session, usuario: Usuario, defesa_id: int) -> DivulgacaoOut:
    """POST /defesas/{id}/retirada (passos 14 a 16): tira da agenda; a defesa continua marcada."""
    defesa = _defesa_visivel(db, usuario, defesa_id)
    _exigir_pode_publicar(db, usuario, defesa)
    if not defesa.publicada:
        raise ErroAPI(409, "Esta defesa não está publicada na agenda.")
    defesa.publicada, defesa.publicada_em = False, None
    db.add(HistoricoDefesa(defesa_id=defesa.id, evento="RETIRADA", usuario_id=usuario.id))  # mensagem 16
    db.commit()
    db.refresh(defesa)
    return _divulgacao(defesa, True)
