"""Quem consulta o resultado e os documentos da defesa (RN07 · RBN09.13 e RBN09.16, E2 dos dois cards).

Só quem tem vínculo com o TCC (o aluno autor, o orientador e os membros da banca, inclusive externos) e a
coordenação do núcleo do curso do TCC consultam o resultado e os documentos, também pela URL do PDF. Qualquer
outro usuário recebe 403, sem nenhum dado (CA-03 do RBN09.13 e do RBN09.16).
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.erros import ErroAPI
from app.models import ACEITA, PAPEL_ORIENTADOR, PERFIL_COORDENADOR, BancaMembro, Defesa, Tcc, Usuario

SEM_VINCULO = "Só quem tem vínculo com o TCC e a coordenação do núcleo consultam o resultado e os documentos."


@dataclass(frozen=True)
class Vinculo:
    """O papel de quem consulta, do mais amplo ao mais restrito."""

    orientador: bool
    coordenacao: bool
    aluno: bool
    membro: BancaMembro | None  # membro da banca (o orientador também é membro)

    @property
    def gestao(self) -> bool:
        """Gera a ata e a folha e emite certificados: coordenação ou orientador (RBN09.14 e E3 do RBN09.17)."""
        return self.orientador or self.coordenacao


def orientador_do_tcc(tcc: Tcc, usuario: Usuario) -> bool:
    return any(
        o.papel == PAPEL_ORIENTADOR and o.status == ACEITA and o.encerrado_em is None and o.professor_id == usuario.id
        for o in tcc.orientacoes
    )


def _coordenacao_do_nucleo(tcc: Tcc, usuario: Usuario) -> bool:
    if PERFIL_COORDENADOR not in usuario.perfis or usuario.docente is None:
        return False
    return tcc.aluno.curso.nucleo_id == usuario.docente.nucleo_id


def vinculo(db: Session, usuario: Usuario, defesa_id: int) -> tuple[Defesa, Vinculo]:
    """A defesa e o vínculo de quem consulta; 404 se a defesa não existe e 403 sem vínculo (E2)."""
    defesa = db.get(Defesa, defesa_id)
    if defesa is None:
        raise ErroAPI(404, "Defesa não encontrada.")
    tcc = defesa.tcc
    v = Vinculo(
        orientador=orientador_do_tcc(tcc, usuario),
        coordenacao=_coordenacao_do_nucleo(tcc, usuario),
        aluno=tcc.aluno_id == usuario.id,
        membro=next((m for m in defesa.membros if m.usuario_id == usuario.id), None),
    )
    if not (v.orientador or v.coordenacao or v.aluno or v.membro is not None):
        raise ErroAPI(403, SEM_VINCULO)
    return defesa, v
