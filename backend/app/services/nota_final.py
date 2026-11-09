"""Nota final da defesa (RBN09.11, RN13, RN21).

Faz o papel da CalculadoraNotaFinal do diagrama de classes (MOD04): calcularNotaFinal(defesa),
calcularMedia(notas) e recalcularNotaFinal(defesa). Segue o DS-FL06-B (Consolidar a nota final): os
comentários "msg N" apontam para a mensagem do diagrama.

- Nota final = média das notas totais enviadas pelos dois avaliadores e pelo orientador (RN21); o suplente
  convocado entra no lugar do titular que substitui (RN20, mesma regra da avaliação).
- Exceção editorial (RN21): artigo ACEITO ou PUBLICADO em veículo Qualis A ou B → nota final = maior valor
  entre 6,00 e a média. Nos demais casos (artigo em outra situação, sem Qualis A/B ou monografia), a média.
- Precisão (CA-06): duas casas, arredondamento comercial (meio para cima), as mesmas em tela, ata e
  relatórios. A ficha (CT-09.11-04 = 8,33) e o DS-FL06-B ("6,00") pedem duas casas; o SQL físico guarda
  resultado_defesa.media e nota_final com uma (NUMERIC(3,1)). Ver o PR do SCRUM-69.
- O cálculo só é liberado quando todas as avaliações esperadas foram enviadas (RBN10.05, CA-05).
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ENVIADA, Avaliacao, BancaMembro, Defesa
from app.services.avaliacao import membros_que_avaliam

CENTESIMO = Decimal("0.01")
PISO_EXCECAO = Decimal("6.00")  # RN21
MODALIDADE_ARTIGO = "ARTIGO"
SITUACOES_DA_EXCECAO = ("ACEITO", "PUBLICADO")
# Qualis A ou B (RN21): os estratos A1 a A4 e B1 a B4. Lista fechada: "BX" ou "B5" (estrato que não existe)
# não aplicam a exceção, mesmo começando com A ou B.
ESTRATOS_DA_EXCECAO = ("A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4")
NOME_SITUACAO = {"SUBMETIDO": "submetido", "EM_REVISAO": "em revisão", "ACEITO": "aceito", "RECUSADO": "recusado",
                 "PUBLICADO": "publicado"}


@dataclass
class NotaDoMembro:
    membro: BancaMembro
    nota: Decimal


@dataclass
class RegraExcecao:
    aplicada: bool
    porque: str
    modalidade: str
    situacao_editorial: str | None
    qualis: str | None


@dataclass
class NotaFinal:
    notas: list[NotaDoMembro]
    media: Decimal
    regra: RegraExcecao
    nota_final: Decimal


def _br(valor: Decimal) -> str:
    return f"{valor:.2f}".replace(".", ",")


def calcular_media(notas: list[Decimal]) -> Decimal:
    """calcularMedia(notas): média simples, com duas casas (CA-01, CA-06)."""
    if not notas:
        raise ValueError("Sem notas para calcular a média.")
    return (sum(notas, Decimal("0")) / len(notas)).quantize(CENTESIMO, ROUND_HALF_UP)


def regra_excecao(defesa: Defesa) -> RegraExcecao:
    """Msgs 5 a 9 do DS-FL06-B: modalidade do TCC e, se ARTIGO, situação editorial atual e Qualis."""
    tcc = defesa.tcc
    if tcc.modalidade != MODALIDADE_ARTIGO:  # [MONOGRAFIA]
        return RegraExcecao(False, "Não se aplica: a modalidade é monografia.", tcc.modalidade, None, None)
    publicacao = tcc.publicacoes[-1] if tcc.publicacoes else None  # a situação atual é a do registro mais recente
    situacao = publicacao.situacao_atual if publicacao else None
    qualis = (publicacao.qualis or "").strip().upper() if publicacao else ""
    if situacao in SITUACOES_DA_EXCECAO and qualis in ESTRATOS_DA_EXCECAO:
        return RegraExcecao(
            True,
            f"Artigo {NOME_SITUACAO[situacao]} em veículo Qualis {qualis}: a nota final é o maior valor entre "
            f"{_br(PISO_EXCECAO)} e a média.",
            tcc.modalidade, situacao, qualis,
        )
    return RegraExcecao(False, "Não aplicada: o artigo não está aceito ou publicado em veículo Qualis A ou B.",
                        tcc.modalidade, situacao, qualis or None)


def notas_enviadas(db: Session, defesa: Defesa) -> list[NotaDoMembro]:
    """Msgs 2 e 3: as notas totais das avaliações enviadas pelos membros que avaliam esta defesa."""
    esperados = {m.id: m for m in membros_que_avaliam(defesa)}
    avaliacoes = db.scalars(select(Avaliacao).where(Avaliacao.defesa_id == defesa.id, Avaliacao.status == ENVIADA))
    por_membro = {a.membro_id: a for a in avaliacoes if a.membro_id in esperados}
    return [NotaDoMembro(esperados[i], Decimal(por_membro[i].nota_total)) for i in esperados if i in por_membro]


def calcular_nota_final(db: Session, defesa: Defesa) -> NotaFinal:
    """calcularNotaFinal(idDefesa): DS-FL06-B inteiro. Quem chama garante que não há avaliação pendente."""
    notas = notas_enviadas(db, defesa)
    media = calcular_media([n.nota for n in notas])  # msg 4
    regra = regra_excecao(defesa)
    nota_final = max(PISO_EXCECAO, media) if regra.aplicada else media
    return NotaFinal(notas=notas, media=media, regra=regra, nota_final=nota_final)


def recalcular_nota_final(db: Session, defesa: Defesa) -> NotaFinal:
    """recalcularNotaFinal(defesa): usada na confirmação do resultado (DS-FL06, SCRUM-70) para gravar o valor
    calculado no servidor no momento da confirmação, e não o que a tela mostrou antes."""
    return calcular_nota_final(db, defesa)
