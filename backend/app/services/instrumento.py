"""Instrumento de avaliação ponderado e versionado (RBN10.01, RN19).

Faz o papel do ControladorInstrumento do diagrama de classes (MOD04): consultarInstrumento,
salvarInstrumento e validarPesos. Os comentários "passo N" apontam para a mensagem
correspondente em DS-FL06-G.
"""

from decimal import Decimal

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.erros import ErroAPI
from app.models import (
    COMPETENTE,
    EXEMPLAR,
    FAIXAS_CONCEITO,
    NECESSITA,
    Avaliacao,
    ComponenteAvaliacao,
    CriterioAvaliacao,
    InstrumentoAvaliacao,
    Usuario,
)
from app.schemas.instrumento import (
    ComponenteEntrada,
    ComponenteOut,
    CriterioEntrada,
    CriterioOut,
    FaixaOut,
    InstrumentoConsulta,
    InstrumentoEntrada,
    InstrumentoOut,
    VersaoOut,
)
from app.services import auditoria
from app.services.turmas import pessoa

ROTULOS_CONCEITO = {EXEMPLAR: "Exemplar",
                    COMPETENTE: "Competente", NECESSITA: "Necessita de Trabalho"}
SEM_INSTRUMENTO = "Nenhum instrumento de avaliação cadastrado."


def _faixas() -> list[FaixaOut]:
    return [
        FaixaOut(
            conceito=c, rotulo=ROTULOS_CONCEITO[c], minimo=minimo, maximo=maximo)
        for c, (minimo, maximo) in FAIXAS_CONCEITO.items()
    ]


def _instrumento_out(instrumento: InstrumentoAvaliacao) -> InstrumentoOut:
    return InstrumentoOut(
        id=instrumento.id,
        versao=instrumento.versao,
        vigente=instrumento.vigente,
        criado_em=instrumento.criado_em,
        autor=pessoa(instrumento.autor),
        componentes=[
            ComponenteOut(
                id=c.id,
                nome=c.nome,
                pontos=float(c.pontos),
                ordem=c.ordem,
                criterios=[
                    CriterioOut(
                        id=k.id,
                        nome=k.nome,
                        peso=float(k.peso),
                        texto_exemplar=k.texto_exemplar,
                        texto_competente=k.texto_competente,
                        texto_necessita=k.texto_necessita,
                        ordem=k.ordem,
                    )
                    for k in c.criterios
                ],
            )
            for c in instrumento.componentes
        ],
        conceitos=_faixas(),
    )


def _versao_out(instrumento: InstrumentoAvaliacao) -> VersaoOut:
    return VersaoOut(
        id=instrumento.id,
        versao=instrumento.versao,
        vigente=instrumento.vigente,
        criado_em=instrumento.criado_em,
        autor=pessoa(instrumento.autor),
    )


def obter_vigente(db: Session) -> InstrumentoAvaliacao:
    """Passo 3: a versão vigente (só existe uma)."""
    instrumento = db.scalar(select(InstrumentoAvaliacao).where(
        InstrumentoAvaliacao.vigente.is_(True)))
    if instrumento is None:
        raise ErroAPI(404, SEM_INSTRUMENTO)
    return instrumento


# =================================================================== DS-FL06-G · consultar


def consultar_instrumento(db: Session) -> InstrumentoConsulta:
    """Passos 2 a 4: versão vigente, histórico de versões com data e autor (CA-05) e a estrutura
    (componentes, critérios, pesos e os três conceitos com faixas e textos, CA-01)."""
    vigente = obter_vigente(db)  # passo 3
    versoes = db.scalars(select(InstrumentoAvaliacao).order_by(
        InstrumentoAvaliacao.versao.desc())).all()
    # Passo 4: componentes e critérios vêm pelas relações, já na ordem (ordem do componente e do critério)
    return InstrumentoConsulta(instrumento=_instrumento_out(vigente), versoes=[_versao_out(v) for v in versoes])


# =================================================================== DS-FL06-G · salvar


def validar_pesos(componentes: list[ComponenteAvaliacao], dados: InstrumentoEntrada) -> None:
    """Passo 7: os pesos dos critérios de cada componente fecham os pontos dele (escrita 7,0 e oral 3,0).
    Se não fecham, 422 com os componentes de soma incorreta, e nada é salvo (CA-02, fluxo E1)."""
    por_id = {c.id: c for c in componentes}
    erradas = []
    for entrada in dados.componentes:
        componente = por_id[entrada.id]
        soma = sum((k.peso for k in entrada.criterios), Decimal("0"))
        if soma != Decimal(componente.pontos):
            erradas.append(
                {"id": componente.id, "nome": componente.nome,
                    "pontos": float(componente.pontos), "soma": float(soma)}
            )
    if erradas:
        raise ErroAPI(422, "Os pesos não fecham 7,0 e 3,0.",
                      componentes=erradas)


def existe_avaliacao(db: Session, instrumento_id: int) -> bool:
    """Passo 8: a versão vigente já foi usada em alguma avaliação?

    Conta o rascunho e a enviada: o rascunho já aponta para os critérios desta versão, que o
    passo 11 apagaria (avaliacao_criterio → criterio_avaliacao é RESTRICT).
    """
    return db.scalar(select(exists().where(Avaliacao.instrumento_id == instrumento_id))) is True


def _criar_criterios(db: Session, componente: ComponenteAvaliacao, criterios: list[CriterioEntrada]) -> None:
    for ordem, k in enumerate(criterios, start=1):
        db.add(
            CriterioAvaliacao(
                componente_id=componente.id,
                nome=k.nome,
                peso=k.peso,
                texto_exemplar=k.texto_exemplar,
                texto_competente=k.texto_competente,
                texto_necessita=k.texto_necessita,
                ordem=ordem,
            )
        )


def _criar_nova_versao(
    db: Session, vigente: InstrumentoAvaliacao, autor: Usuario, entrada: dict[int, ComponenteEntrada]
) -> InstrumentoAvaliacao:
    """Passos 9 e 10: nova versão vigente com os mesmos componentes e os critérios recebidos.
    A anterior deixa de ser vigente e fica intacta: as defesas já avaliadas continuam nela (CA-03)."""
    ultima = db.scalar(select(func.max(InstrumentoAvaliacao.versao)))
    vigente.vigente = False
    db.flush()
    nova = InstrumentoAvaliacao(
        versao=ultima + 1, vigente=True, criado_por=autor.id)  # passo 9
    db.add(nova)
    db.flush()
    for antigo in vigente.componentes:
        componente = ComponenteAvaliacao(
            instrumento_id=nova.id, nome=antigo.nome, pontos=antigo.pontos, ordem=antigo.ordem
        )
        db.add(componente)
        db.flush()
        _criar_criterios(
            db, componente, entrada[antigo.id].criterios)  # passo 10
    return nova


def _atualizar(db: Session, vigente: InstrumentoAvaliacao, entrada: dict[int, ComponenteEntrada]) -> None:
    """Passo 11: a versão vigente ainda não foi usada, então os critérios dela são trocados no lugar."""
    for componente in vigente.componentes:
        for criterio in list(componente.criterios):
            db.delete(criterio)
        db.flush()
        _criar_criterios(db, componente, entrada[componente.id].criterios)


def salvar_instrumento(db: Session, autor: Usuario, dados: InstrumentoEntrada) -> InstrumentoOut:
    """Passos 6 a 12: valida os pesos, cria uma versão nova ou atualiza a vigente e registra no log."""
    vigente = obter_vigente(db)
    componentes = list(vigente.componentes)
    if sorted(c.id for c in dados.componentes) != sorted(c.id for c in componentes):
        # Os componentes mudaram de versão desde que a tela foi aberta (outra pessoa salvou antes)
        raise ErroAPI(
            409, "O instrumento foi alterado por outra pessoa. Recarregue a página e tente de novo.")

    validar_pesos(componentes, dados)  # passo 7

    entrada = {c.id: c for c in dados.componentes}
    if existe_avaliacao(db, vigente.id):  # passo 8
        instrumento = _criar_nova_versao(
            db, vigente, autor, entrada)  # passos 9 e 10
    else:
        _atualizar(db, vigente, entrada)  # passo 11
        instrumento = vigente

    auditoria.registrar(  # passo 12 (RNF03)
        db,
        ator_id=autor.id,
        acao="configurar_instrumento",
        entidade="instrumento_avaliacao",
        entidade_id=instrumento.id,
        campo="versao",
        novo=instrumento.versao,
    )
    db.commit()
    db.expire_all()  # recarrega componentes e critérios do banco (a sessão não expira no commit)
    return _instrumento_out(instrumento)
