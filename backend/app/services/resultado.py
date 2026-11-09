"""Resultado da defesa: consulta e consolidação da nota final (RBN09.11, RN07, RN13, RN21).

Faz o papel de consultarResultado(defesa) do ControladorAvaliacaoDefesa (diagrama de classes, MOD04), na
parte que o DS-FL06 executa antes da confirmação: GET /defesas/{idDefesa}/resultado confere quem já enviou a
avaliação e, com todas enviadas, chama a CalculadoraNotaFinal (DS-FL06-B). A confirmação do resultado
(registrarResultado, POST da mesma rota) e o ramo "[resultado já confirmado]" chegam com o SCRUM-70.

Quem pode: o orientador do TCC, o ator do DS-FL06 (RBN09.12). Quem vê o TCC sem ser o orientador recebe
403 (o avaliador vê só a própria avaliação, RBN10.02 CA-02); quem nem vê o TCC recebe 404 (RN07).
"""

from sqlalchemy.orm import Session

from app.erros import ErroAPI
from app.models import ACEITA, CANCELADA, PAPEL_ORIENTADOR, Defesa, Tcc, Usuario
from app.schemas.resultado import (
    MembroPendenteOut,
    NotaDoMembroOut,
    NotaFinalOut,
    RegraExcecaoOut,
    ResultadoConsulta,
)
from app.services import avaliacao, nota_final
from app.services.tccs import obter_para
from app.services.turmas import pessoa

SO_O_ORIENTADOR = "Só o orientador do TCC consolida o resultado da defesa."


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


def consultar_resultado(db: Session, usuario: Usuario, defesa_id: int) -> ResultadoConsulta:
    """GET /defesas/{idDefesa}/resultado (DS-FL06, mensagens 3 a 9)."""
    defesa = _defesa_do_orientador(db, usuario, defesa_id)
    faltam = avaliacao.pendentes(db, defesa)  # "quem já enviou" (RBN10.05)
    if faltam:  # [falta avaliação]: o cálculo não é liberado e as pendências são indicadas (CA-05)
        return ResultadoConsulta(
            defesa_id=defesa.id,
            pendentes=[MembroPendenteOut(membro_id=m.id, papel=m.papel, pessoa=pessoa(m.usuario)) for m in faltam],
            consolidacao=None,
        )
    # [todas enviadas]: DS-FL06-B
    return ResultadoConsulta(defesa_id=defesa.id, pendentes=[],
                             consolidacao=_consolidacao_out(nota_final.calcular_nota_final(db, defesa)))
