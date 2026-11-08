"""Avaliação da defesa pelos membros da banca (Sprint S04 · RBN10.02 a RBN10.05, RN13, RN19, RN20).

Faz o papel do ControladorAvaliacaoDefesa do diagrama de classes (MOD04). Os comentários "passo N"
apontam para a mensagem correspondente em DS-FL06-A (Avaliador lança a avaliação).

Decisões da equipe registradas em claude/Divergencias_e_decisoes_RAN10.md (projeto):
- Avaliam o orientador, os dois avaliadores e o suplente convocado, no lugar do titular; o
  coorientador não avalia (D2).
- O rascunho abre desde o agendamento da defesa (não cancelada); o envio só depois da defesa
  realizada: situação REALIZADA ou horário de término passado, no horário de Manaus (D6, D21).
- A versão do instrumento fica fixada na primeira avaliação gravada da defesa (RN19, D13).
- Nota ponderada = nota × peso ÷ 10, gravada com 2 casas; nota total = soma dos valores exatos,
  arredondada só no final para 1 casa, como na planilha de avaliação (D9).
- Parecer obrigatório no envio, com pelo menos 20 caracteres; opcional no rascunho (D10).
"""

from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import agora
from app.erros import ErroAPI
from app.models import (
    CANCELADA,
    ENVIADA,
    FAIXAS_CONCEITO,
    PAPEL_AVALIADOR,
    PAPEL_ORIENTADOR,
    PAPEL_SUPLENTE,
    RASCUNHO,
    Avaliacao,
    AvaliacaoCriterio,
    BancaMembro,
    CriterioAvaliacao,
    Defesa,
    InstrumentoAvaliacao,
    Usuario,
)
from app.schemas.avaliacao import (
    AvaliacaoConsulta,
    AvaliacaoEntrada,
    CriterioAvaliado,
    CriterioAvaliadoOut,
    EnviosOut,
    MinhaAvaliacaoOut,
)
from app.services import auditoria
from app.services.instrumento import ROTULOS_CONCEITO, instrumento_out, obter_vigente

REALIZADA = "REALIZADA"
FUSO_MANAUS = timedelta(hours=-4)  # America/Manaus não tem horário de verão (mesma regra da SCRUM-68)
PARECER_MINIMO = 20
CENTESIMO, DECIMO = Decimal("0.01"), Decimal("0.1")

NAO_AVALIA = "Você não avalia esta defesa."
INSTRUMENTO_MUDOU = "O instrumento de avaliação mudou desde que a página foi aberta. Recarregue a página."


# =================================================================== passos 4 e 5 · defesa e papel


def _agora_manaus() -> datetime:
    return agora() + FUSO_MANAUS


def defesa_realizada(defesa: Defesa) -> bool:
    """Passo 4: situação REALIZADA ou horário de término já passado (Manaus). Só libera o envio."""
    if defesa.situacao == REALIZADA:
        return True
    return defesa.situacao != CANCELADA and datetime.combine(defesa.data, defesa.fim) <= _agora_manaus()


def membros_que_avaliam(defesa: Defesa) -> list[BancaMembro]:
    """Avaliadores esperados (RN13, RN20): orientador e os dois avaliadores; o suplente convocado entra
    no lugar do titular que ele substitui (RBN10.05, CA-05). Coorientador e suplente não convocado, não."""
    convocados = [m for m in defesa.membros if m.papel == PAPEL_SUPLENTE and m.convocado_em is not None]
    substituidos = {m.substitui_membro_id for m in convocados}
    titulares = [
        m for m in defesa.membros
        if m.papel in (PAPEL_ORIENTADOR, PAPEL_AVALIADOR) and m.id not in substituidos
    ]
    return titulares + convocados


def _obter_defesa(db: Session, defesa_id: int) -> Defesa:
    defesa = db.get(Defesa, defesa_id)
    if defesa is None:
        raise ErroAPI(404, "Defesa não encontrada.")
    return defesa


def verificar_papel(defesa: Defesa, usuario: Usuario) -> BancaMembro:
    """Passo 5: quem pede avalia esta defesa? Se não, 403 (fluxos E2 e E6, CA-04)."""
    membro = next((m for m in membros_que_avaliam(defesa) if m.usuario_id == usuario.id), None)
    if membro is None:
        raise ErroAPI(403, NAO_AVALIA)
    return membro


def _abrir(db: Session, usuario: Usuario, defesa_id: int) -> tuple[Defesa, BancaMembro]:
    """Passos 4 e 5 juntos: a defesa existe, quem pede avalia e ela não foi cancelada."""
    defesa = _obter_defesa(db, defesa_id)
    membro = verificar_papel(defesa, usuario)
    if defesa.situacao == CANCELADA:
        raise ErroAPI(409, "Esta defesa foi cancelada.")
    return defesa, membro


# =================================================================== passos 6 e 7 · instrumento e avaliação


def instrumento_da_defesa(db: Session, defesa: Defesa) -> InstrumentoAvaliacao:
    """Passo 6 (RN19): a versão fixada pela primeira avaliação gravada da defesa; sem nenhuma, a vigente."""
    fixada = db.scalar(select(Avaliacao).where(Avaliacao.defesa_id == defesa.id).limit(1))
    return fixada.instrumento if fixada else obter_vigente(db)


def _minha(db: Session, defesa: Defesa, membro: BancaMembro) -> Avaliacao | None:
    """Passo 7: a avaliação deste membro, em rascunho ou enviada (CA-02: só a própria)."""
    return db.scalar(select(Avaliacao).where(Avaliacao.defesa_id == defesa.id, Avaliacao.membro_id == membro.id))


def pendentes(db: Session, defesa: Defesa) -> list[BancaMembro]:
    """RBN10.05 (CA-03): avaliadores esperados que ainda não enviaram. A confirmação do resultado
    (SCRUM-70, RBN09.12) usa esta lista para ficar bloqueada enquanto ela não estiver vazia."""
    enviadas = set(
        db.scalars(
            select(Avaliacao.membro_id).where(Avaliacao.defesa_id == defesa.id, Avaliacao.status == ENVIADA)
        )
    )
    return [m for m in membros_que_avaliam(defesa) if m.id not in enviadas]


def _criterios(instrumento: InstrumentoAvaliacao) -> list[CriterioAvaliacao]:
    return [k for c in instrumento.componentes for k in c.criterios]


# =================================================================== cálculo (RBN10.04)


def ponderada_exata(nota: Decimal, peso: Decimal) -> Decimal:
    """Nota ponderada sem arredondar: nota × peso ÷ 10 (planilha de avaliação, coluna I)."""
    return Decimal(nota) * Decimal(peso) / 10


def nota_total(itens: list[tuple[Decimal, Decimal]]) -> Decimal:
    """Soma das ponderadas exatas (nota, peso), arredondada só no final para 1 casa (D9)."""
    return sum((ponderada_exata(n, p) for n, p in itens), Decimal("0")).quantize(DECIMO, ROUND_HALF_UP)


def _faixa(conceito: str) -> str:
    minimo, maximo = FAIXAS_CONCEITO[conceito]
    return f"{minimo:.1f} a {maximo:.1f}".replace(".", ",")


def _conferir(instrumento: InstrumentoAvaliacao, dados: AvaliacaoEntrada) -> dict[int, CriterioAvaliado]:
    """Passo 9 no servidor (RBN10.03, CA-05): cada critério é desta versão e a nota está na faixa do conceito.
    Um critério de outra versão quer dizer que a tela ficou desatualizada (409); nota fora da faixa ou critério
    repetido dá 422 com os critérios destacados (fluxo E4)."""
    por_id = {k.id: k for k in _criterios(instrumento)}
    recebidos: dict[int, CriterioAvaliado] = {}
    erros = []
    for item in dados.criterios:
        criterio = por_id.get(item.criterio_id)
        if criterio is None:
            raise ErroAPI(409, INSTRUMENTO_MUDOU)
        minimo, maximo = FAIXAS_CONCEITO[item.conceito]
        if item.criterio_id in recebidos:
            erros.append({"id": criterio.id, "nome": criterio.nome, "motivo": "Critério repetido."})
        elif not Decimal(str(minimo)) <= item.nota <= Decimal(str(maximo)):
            erros.append({
                "id": criterio.id,
                "nome": criterio.nome,
                "motivo": f"A nota de {ROTULOS_CONCEITO[item.conceito]} vai de {_faixa(item.conceito)}.",
            })
        recebidos[item.criterio_id] = item
    if erros:
        raise ErroAPI(422, "Confira os critérios destacados.", criterios=erros)
    return recebidos


# =================================================================== saída


def _br(valor: Decimal) -> str:
    return f"{valor:.1f}".replace(".", ",")


def _minha_out(avaliacao: Avaliacao) -> MinhaAvaliacaoOut:
    criterios = _criterios(avaliacao.instrumento)
    preenchidos = {c.criterio_id for c in avaliacao.criterios}
    faltam = [k.id for k in criterios if k.id not in preenchidos]
    total = avaliacao.nota_total
    if total is None and not faltam:  # rascunho completo: a total já pode ser mostrada (RBN10.04, CA-02)
        pesos = {k.id: k.peso for k in criterios}
        total = nota_total([(c.nota, pesos[c.criterio_id]) for c in avaliacao.criterios])
    return MinhaAvaliacaoOut(
        id=avaliacao.id,
        status=avaliacao.status,
        parecer=avaliacao.parecer,
        criterios=[
            CriterioAvaliadoOut(
                criterio_id=c.criterio_id,
                conceito=c.conceito,
                nota=float(c.nota),
                nota_ponderada=float(c.nota_ponderada),
            )
            for c in avaliacao.criterios
        ],
        pendentes=faltam,
        nota_total=float(total) if total is not None else None,
        enviada_em=avaliacao.enviada_em,
    )


def consultar(db: Session, usuario: Usuario, defesa_id: int) -> AvaliacaoConsulta:
    """GET /defesas/{id}/avaliacao (passos 3 a 7): {instrumento, minha avaliação, envios}.
    A tela decide o que mostrar: envio ainda não liberado (E1), avaliação enviada (E3) ou aberta."""
    defesa, membro = _abrir(db, usuario, defesa_id)  # passos 4 e 5
    minha = _minha(db, defesa, membro)  # passo 7
    instrumento = minha.instrumento if minha else instrumento_da_defesa(db, defesa)  # passo 6
    esperados = membros_que_avaliam(defesa)
    return AvaliacaoConsulta(
        defesa_id=defesa.id,
        envio_liberado=defesa_realizada(defesa),
        instrumento=instrumento_out(instrumento),
        minha_avaliacao=_minha_out(minha) if minha else None,
        envios=EnviosOut(enviadas=len(esperados) - len(pendentes(db, defesa)), esperadas=len(esperados)),
    )


# =================================================================== passos 12 a 19 · gravar


def _para_gravar(db: Session, usuario: Usuario, defesa_id: int) -> tuple[Defesa, BancaMembro, Avaliacao | None]:
    defesa, membro = _abrir(db, usuario, defesa_id)
    minha = _minha(db, defesa, membro)
    if minha is not None and minha.status == ENVIADA:  # fluxo E5 (também no PUT, D20)
        raise ErroAPI(409, "Esta avaliação já foi enviada e não pode mais ser alterada.")
    return defesa, membro, minha


def _iniciar(db: Session, defesa: Defesa, membro: BancaMembro) -> Avaliacao:
    """Passo 13: a primeira gravação cria a avaliação e fixa nela a versão do instrumento da defesa (RN19)."""
    avaliacao = Avaliacao(
        defesa_id=defesa.id,
        membro_id=membro.id,
        instrumento_id=instrumento_da_defesa(db, defesa).id,
        status=RASCUNHO,
    )
    db.add(avaliacao)
    try:
        db.flush()
    except IntegrityError:  # a mesma pessoa gravou em outra aba ao mesmo tempo (uq_avaliacao_defesa_membro)
        db.rollback()
        raise ErroAPI(409, "Sua avaliação foi alterada em outra janela. Recarregue a página.") from None
    return avaliacao


def _texto(criterio: CriterioAvaliacao, conceito: str, nota: Decimal) -> str:
    return f"{criterio.nome}: {ROTULOS_CONCEITO[conceito]} {_br(nota)}"


def _gravar_criterios(
    db: Session, usuario: Usuario, avaliacao: Avaliacao, recebidos: dict[int, CriterioAvaliado]
) -> None:
    """Passos 14 e 18: grava conceito, nota e ponderada (2 casas) de cada critério recebido; os que
    saíram da tela são apagados. Cada mudança vai para o log com o valor anterior e o novo (CA-06)."""
    por_id = {k.id: k for k in _criterios(avaliacao.instrumento)}
    atuais = {c.criterio_id: c for c in avaliacao.criterios}

    def registrar(criterio_id: int, anterior: str | None, novo: str | None) -> None:
        auditoria.registrar(
            db, ator_id=usuario.id, acao="salvar_avaliacao", entidade="avaliacao", entidade_id=avaliacao.id,
            campo=f"criterio_{criterio_id}", anterior=anterior, novo=novo,
        )

    for criterio_id, linha in atuais.items():
        if criterio_id not in recebidos:
            registrar(criterio_id, _texto(por_id[criterio_id], linha.conceito, linha.nota), None)
            db.delete(linha)
    for criterio_id, item in recebidos.items():
        criterio = por_id[criterio_id]
        ponderada = ponderada_exata(item.nota, criterio.peso).quantize(CENTESIMO, ROUND_HALF_UP)
        linha = atuais.get(criterio_id)
        if linha is None:
            db.add(AvaliacaoCriterio(
                avaliacao_id=avaliacao.id, criterio_id=criterio_id,
                conceito=item.conceito, nota=item.nota, nota_ponderada=ponderada,
            ))
            registrar(criterio_id, None, _texto(criterio, item.conceito, item.nota))
        elif (linha.conceito, linha.nota) != (item.conceito, item.nota):
            registrar(
                criterio_id,
                _texto(criterio, linha.conceito, linha.nota),
                _texto(criterio, item.conceito, item.nota),
            )
            linha.conceito, linha.nota, linha.nota_ponderada = item.conceito, item.nota, ponderada


def _gravar_parecer(db: Session, usuario: Usuario, avaliacao: Avaliacao, parecer: str | None) -> None:
    parecer = parecer or None
    if parecer != avaliacao.parecer:
        auditoria.registrar(
            db, ator_id=usuario.id, acao="salvar_avaliacao", entidade="avaliacao", entidade_id=avaliacao.id,
            campo="parecer", anterior=avaliacao.parecer, novo=parecer,
        )
        avaliacao.parecer = parecer


def _concluir(db: Session, avaliacao: Avaliacao) -> MinhaAvaliacaoOut:
    db.commit()
    db.refresh(avaliacao)
    db.expire(avaliacao, ["criterios"])  # recarrega as linhas de critério gravadas agora
    return _minha_out(avaliacao)


def salvar_rascunho(db: Session, usuario: Usuario, defesa_id: int, dados: AvaliacaoEntrada) -> MinhaAvaliacaoOut:
    """PUT /defesas/{id}/avaliacao (passos 12 a 14): grava o que já foi preenchido, sem exigir todos os
    critérios nem o parecer (CA-03). Só critérios completos e na faixa; o envio fica para o POST."""
    defesa, membro, avaliacao = _para_gravar(db, usuario, defesa_id)
    instrumento = avaliacao.instrumento if avaliacao else instrumento_da_defesa(db, defesa)
    recebidos = _conferir(instrumento, dados)
    if avaliacao is None:
        avaliacao = _iniciar(db, defesa, membro)  # passo 13
    _gravar_criterios(db, usuario, avaliacao, recebidos)  # passo 14
    _gravar_parecer(db, usuario, avaliacao, dados.parecer)
    return _concluir(db, avaliacao)


def enviar(db: Session, usuario: Usuario, defesa_id: int, dados: AvaliacaoEntrada) -> MinhaAvaliacaoOut:
    """POST /defesas/{id}/avaliacao/envio (passos 17 a 19). Bloqueia o envio incompleto (RBN10.05, CA-01 e
    CA-06), recalcula ponderadas e total no servidor (RBN10.04, CA-05) e torna a avaliação não editável."""
    defesa, membro, avaliacao = _para_gravar(db, usuario, defesa_id)
    if not defesa_realizada(defesa):  # D21: antes da defesa só rascunho
        raise ErroAPI(409, "A defesa ainda não foi realizada. Salve o rascunho e envie depois da defesa.")
    instrumento = avaliacao.instrumento if avaliacao else instrumento_da_defesa(db, defesa)
    recebidos = _conferir(instrumento, dados)
    faltam = [
        {"id": k.id, "nome": k.nome, "motivo": "Escolha o conceito e informe a nota."}
        for k in _criterios(instrumento) if k.id not in recebidos
    ]
    if faltam:  # fluxo E4 (RBN10.05, CA-01): os critérios faltantes vão destacados
        raise ErroAPI(422, "Confira os critérios destacados.", criterios=faltam)
    if len(dados.parecer or "") < PARECER_MINIMO:  # passo 10
        raise ErroAPI(422, f"O parecer precisa de pelo menos {PARECER_MINIMO} caracteres.", campo="parecer")

    if avaliacao is None:
        avaliacao = _iniciar(db, defesa, membro)
    _gravar_criterios(db, usuario, avaliacao, recebidos)  # passo 18
    _gravar_parecer(db, usuario, avaliacao, dados.parecer)
    pesos = {k.id: k.peso for k in _criterios(instrumento)}
    avaliacao.nota_total = nota_total([(i.nota, pesos[i.criterio_id]) for i in recebidos.values()])  # passo 19
    avaliacao.status = ENVIADA
    avaliacao.enviada_em = agora()
    auditoria.registrar(  # CA-06 (RNF03)
        db, ator_id=usuario.id, acao="enviar_avaliacao", entidade="avaliacao", entidade_id=avaliacao.id,
        campo="status", anterior=RASCUNHO, novo=f"{ENVIADA} · nota {_br(avaliacao.nota_total)}",
    )
    return _concluir(db, avaliacao)
