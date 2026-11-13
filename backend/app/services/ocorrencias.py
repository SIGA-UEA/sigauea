"""Ocorrências da defesa, lista de ouvintes e declaração de horas (RBN09.10, RN07, RN15, RN23).

Faz o papel do ControladorOcorrencias do diagrama de classes (MOD04): consultarOcorrencias,
registrarOcorrencia, corrigirOcorrencia, registrarOuvinte, registrarOuvintesEmLote, corrigirOuvinte,
removerOuvinte e emitirDeclaracao. Os comentários "msg N" apontam para a mensagem do DS-FL09,
DS-FL09-A ou DS-FL09-B. A presença da banca (registrarPresencaBanca) não tem diagrama: entrou por decisão da
equipe em 11/11/2026, para o certificado de participação sair só para quem esteve na sessão (RBN09.17).

Quem pode (CA-05 e CA-06): a coordenação e o orientador do TCC. Os demais que veem o TCC recebem 403;
quem nem vê o TCC recebe 404 (RN07). A lista de ouvintes nunca sai daqui para a agenda pública (RN08).

Quando libera (E1): a defesa já começou (data e início no horário de Manaus) ou está REALIZADA, como
pede o CA-01 ("defesa realizada ou em andamento"). A declaração só sai depois do fim da defesa (RN15).
"""

import re
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import agora
from app.erros import ErroAPI
from app.models import (
    ACEITA,
    CANCELADA,
    DOC_CERTIFICADO,
    DOC_DECLARACAO,
    PAPEL_ORIENTADOR,
    PAPEL_SUPLENTE,
    PERFIL_COORDENADOR,
    BancaMembro,
    Defesa,
    DocumentoOficial,
    OcorrenciaDefesa,
    OuvinteDefesa,
    Tcc,
    Usuario,
)
from app.schemas.ocorrencia import (
    DeclaracaoOut,
    MembroPresencaOut,
    PresencaBancaEntrada,
    LinhaComProblema,
    LoteEntrada,
    LoteOut,
    OcorrenciaOut,
    OuvinteEntrada,
    OuvinteOut,
    PresencaOut,
)
from app.services import auditoria, documentos
from app.services.tccs import obter_para
from app.services.turmas import pessoa

REALIZADA = "REALIZADA"
# Matrícula do ouvinte: a mesma regra do cadastro de aluno (6 a 20 dígitos). O DS-FL09 e o protótipo
# da TEL19 falam em 7 dígitos, que o próprio protótipo marca como suposição; as matrículas da UEA
# no sistema têm 10 dígitos. Decisão registrada no PR do SCRUM-68.
MATRICULA = re.compile(r"^\d{6,20}$")
SEPARADOR_LOTE = re.compile(r"[;,\t]")
MSG_MATRICULA = "A matrícula deve ter só números (de 6 a 20 dígitos)."
MSG_NOME = "Informe o nome completo (nome e sobrenome), como deve sair na declaração."
MSG_REPETIDA = "Esta matrícula já está na lista."


# =================================================================== RN07 · defesa, vínculo e etapa


def _agora_manaus() -> datetime:
    return agora() + documentos.FUSO_MANAUS


def liberada(defesa: Defesa) -> bool:
    """E1: defesa realizada ou já iniciada (CA-01)."""
    if defesa.situacao == REALIZADA:
        return True
    return defesa.situacao != CANCELADA and datetime.combine(defesa.data, defesa.inicio) <= _agora_manaus()


def pode_emitir(defesa: Defesa) -> bool:
    """RN15: a declaração só sai para a defesa realizada (situação REALIZADA ou horário de término passado)."""
    if defesa.situacao == REALIZADA:
        return True
    return defesa.situacao != CANCELADA and datetime.combine(defesa.data, defesa.fim) <= _agora_manaus()


def _orientador_do_tcc(tcc: Tcc, usuario: Usuario) -> bool:
    return any(
        o.papel == PAPEL_ORIENTADOR and o.status == ACEITA and o.encerrado_em is None and o.professor_id == usuario.id
        for o in tcc.orientacoes
    )


def _defesa(db: Session, usuario: Usuario, defesa_id: int) -> Defesa:
    """Msg 3 do DS-FL09: situação e vínculo (RN07). 404 sem acesso ao TCC; 403 sem vínculo (CA-05)."""
    defesa = db.get(Defesa, defesa_id)
    if defesa is None:
        raise ErroAPI(404, "Defesa não encontrada.")
    tcc = obter_para(db, usuario, defesa.tcc_id)
    if PERFIL_COORDENADOR not in usuario.perfis and not _orientador_do_tcc(tcc, usuario):
        raise ErroAPI(403, "Só a coordenação e o orientador do TCC registram ocorrências e ouvintes da defesa.")
    return defesa


def _para_gravar(db: Session, usuario: Usuario, defesa_id: int) -> Defesa:
    """E2 do DS-FL09: sem vínculo (403) ou defesa cancelada (409); E1: defesa que ainda não começou (409)."""
    defesa = _defesa(db, usuario, defesa_id)
    if defesa.situacao == CANCELADA:
        raise ErroAPI(409, "Esta defesa foi cancelada.")
    if not liberada(defesa):
        raise ErroAPI(409, "Etapa ainda não liberada: a defesa ainda não começou.")
    return defesa


# =================================================================== saída


def _ocorrencia_out(o: OcorrenciaDefesa) -> OcorrenciaOut:
    return OcorrenciaOut(id=o.id, texto=o.texto, autor=pessoa(o.autor), criado_em=o.criado_em,
                         alterada_em=o.alterada_em)


def _declaracao(db: Session, ouvinte_id: int) -> DocumentoOficial | None:
    return db.scalar(
        select(DocumentoOficial).where(
            DocumentoOficial.tipo == DOC_DECLARACAO,
            DocumentoOficial.ouvinte_id == ouvinte_id,
            DocumentoOficial.vigente.is_(True),
        )
    )


def _declaracao_out(d: DocumentoOficial | None) -> DeclaracaoOut | None:
    if d is None:
        return None
    return DeclaracaoOut(id=d.id, ouvinte_id=d.ouvinte_id, versao=d.versao, gerado_em=d.gerado_em)


def matricula_valida(matricula: str | None) -> bool:
    return bool(matricula) and MATRICULA.fullmatch(matricula) is not None


def _ouvinte_out(db: Session, o: OuvinteDefesa) -> OuvinteOut:
    return OuvinteOut(id=o.id, nome=o.nome, matricula=o.matricula, pronto=matricula_valida(o.matricula),
                      declaracao=_declaracao_out(_declaracao(db, o.id)))


def _ouvintes(db: Session, defesa_id: int) -> list[OuvinteDefesa]:
    return list(db.scalars(select(OuvinteDefesa).where(OuvinteDefesa.defesa_id == defesa_id)
                           .order_by(OuvinteDefesa.id)))


# =================================================================== DS-FL09 · consultar


def consultar_ocorrencias(db: Session, usuario: Usuario, defesa_id: int) -> PresencaOut:
    """GET /defesas/{id}/ocorrencias (msgs 2 a 6)."""
    defesa = _defesa(db, usuario, defesa_id)
    ocorrencias = db.scalars(select(OcorrenciaDefesa).where(OcorrenciaDefesa.defesa_id == defesa.id)
                             .order_by(OcorrenciaDefesa.id))  # msg 4
    ouvintes = [_ouvinte_out(db, o) for o in _ouvintes(db, defesa.id)]  # msg 5
    return PresencaOut(
        defesa_id=defesa.id,
        situacao=defesa.situacao,
        liberada=liberada(defesa),
        pode_emitir=pode_emitir(defesa),
        ocorrencias=[_ocorrencia_out(o) for o in ocorrencias],
        ouvintes=ouvintes,
        prontos=sum(1 for o in ouvintes if o.pronto),
        banca=[_presenca_out(m) for m in participantes(defesa)],
    )


# =================================================================== presença da banca (RBN09.17)


def participantes(defesa: Defesa) -> list[BancaMembro]:
    """Membros que participam da sessão: todos, menos o suplente não convocado e o titular que o suplente
    convocado substituiu (RN20)."""
    substituidos = {m.substitui_membro_id for m in defesa.membros if m.convocado_em is not None}
    return [m for m in defesa.membros
            if m.id not in substituidos and (m.papel != PAPEL_SUPLENTE or m.convocado_em is not None)]


def _presenca_out(m: BancaMembro) -> MembroPresencaOut:
    return MembroPresencaOut(membro_id=m.id, papel=m.papel, pessoa=pessoa(m.usuario), presente=m.presente)


def registrar_presenca_banca(
    db: Session, usuario: Usuario, defesa_id: int, membro_id: int, dados: PresencaBancaEntrada
) -> MembroPresencaOut:
    """PUT /defesas/{id}/banca/{membroId}/presenca: marca o membro presente ou ausente na sessão, com as mesmas
    regras das ocorrências (coordenação ou orientador; defesa iniciada e não cancelada)."""
    defesa = _para_gravar(db, usuario, defesa_id)
    membro = next((m for m in participantes(defesa) if m.id == membro_id), None)
    if membro is None:
        raise ErroAPI(404, "Membro da banca não encontrado nesta defesa.")
    anterior = membro.presente
    if anterior != dados.presente and db.scalar(select(DocumentoOficial.id).where(
            DocumentoOficial.tipo == DOC_CERTIFICADO, DocumentoOficial.membro_id == membro.id,
            DocumentoOficial.vigente.is_(True))) is not None:
        raise ErroAPI(409, "O certificado deste membro já foi emitido; a presença não pode mais ser alterada.")
    membro.presente = dados.presente
    auditoria.registrar(db, ator_id=usuario.id, acao="registrar_presenca_banca", entidade="banca_membro",
                        entidade_id=membro.id, campo="presente",
                        anterior=None if anterior is None else ("presente" if anterior else "ausente"),
                        novo="presente" if dados.presente else "ausente")
    db.commit()
    return _presenca_out(membro)


# =================================================================== DS-FL09 e DS-FL09-A · ocorrências


def registrar_ocorrencia(db: Session, usuario: Usuario, defesa_id: int, texto: str) -> OcorrenciaOut:
    """POST /defesas/{id}/ocorrencias (msgs 9 a 11): texto, quem e quando (CA-01)."""
    defesa = _para_gravar(db, usuario, defesa_id)
    ocorrencia = OcorrenciaDefesa(defesa_id=defesa.id, texto=texto, autor_id=usuario.id)
    db.add(ocorrencia)
    db.flush()
    auditoria.registrar(db, ator_id=usuario.id, acao="registrar_ocorrencia", entidade="ocorrencia_defesa",
                        entidade_id=ocorrencia.id, novo=texto)
    db.commit()
    db.refresh(ocorrencia)
    return _ocorrencia_out(ocorrencia)


def corrigir_ocorrencia(db: Session, usuario: Usuario, defesa_id: int, ocorrencia_id: int, texto: str) -> OcorrenciaOut:
    """PUT /defesas/{id}/ocorrencias/{id} (DS-FL09-A msgs 2 a 4): texto novo e alterada_em; o anterior fica no log."""
    defesa = _para_gravar(db, usuario, defesa_id)
    ocorrencia = db.get(OcorrenciaDefesa, ocorrencia_id)
    if ocorrencia is None or ocorrencia.defesa_id != defesa.id:
        raise ErroAPI(404, "Ocorrência não encontrada.")
    anterior = ocorrencia.texto
    ocorrencia.texto = texto
    ocorrencia.alterada_em = agora()
    auditoria.registrar(db, ator_id=usuario.id, acao="corrigir_ocorrencia", entidade="ocorrencia_defesa",
                        entidade_id=ocorrencia.id, campo="texto", anterior=anterior, novo=texto)
    db.commit()
    db.refresh(ocorrencia)
    return _ocorrencia_out(ocorrencia)


# =================================================================== DS-FL09 e DS-FL09-A · ouvintes


def _descricao(nome: str, matricula: str | None) -> str:
    """Como o ouvinte aparece no log de auditoria."""
    return f"{nome} ({matricula})" if matricula else f"{nome} (sem matrícula)"


def _conferir_ouvinte(db: Session, defesa_id: int, nome: str, matricula: str | None, exceto: int | None = None,
                      ja_na_lista: set[str] | None = None, exigir_matricula: bool = False) -> tuple[str, str | None]:
    """Nome completo, como sai na declaração (DS-FL09 pede 3 letras ou mais; aqui também nome e sobrenome).

    A matrícula é opcional, como no dicionário de dados ("se for aluno da UEA"): o visitante de fora entra na
    lista sem ela e só fica sem declaração (FL09, E5). Quando informada, precisa ser válida e não repetir na
    defesa (E1 do DS-FL09, CA-04)."""
    nome, matricula = " ".join(nome.split()), (matricula or "").strip() or None
    partes = [p for p in nome.split() if sum(c.isalpha() for c in p) >= 2]
    if len(partes) < 2 or sum(c.isalpha() for c in nome) < 3 or len(nome) > 150:
        raise ErroAPI(422, MSG_NOME, campo="nome")
    if matricula is None:
        if exigir_matricula:
            raise ErroAPI(422, MSG_MATRICULA, campo="matricula")
        return nome, None
    if not matricula_valida(matricula):
        raise ErroAPI(422, MSG_MATRICULA, campo="matricula")
    repetida = db.scalar(select(OuvinteDefesa.id).where(
        OuvinteDefesa.defesa_id == defesa_id, OuvinteDefesa.matricula == matricula,
        OuvinteDefesa.id != (exceto or 0)))
    if repetida is not None or (ja_na_lista is not None and matricula in ja_na_lista):
        raise ErroAPI(422, MSG_REPETIDA, campo="matricula")
    return nome, matricula


def _gravar(db: Session) -> None:
    """Confirma; se a restrição única barrar um pedido simultâneo, é a mesma matrícula repetida (CA-04)."""
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ErroAPI(422, MSG_REPETIDA, campo="matricula") from None


def _incluir(db: Session, usuario: Usuario, defesa: Defesa, nome: str, matricula: str | None) -> OuvinteDefesa:
    """Adiciona o ouvinte e registra no log (RNF03). Quem chama confirma a transação."""
    ouvinte = OuvinteDefesa(defesa_id=defesa.id, nome=nome, matricula=matricula)
    db.add(ouvinte)
    db.flush()
    auditoria.registrar(db, ator_id=usuario.id, acao="registrar_ouvinte", entidade="ouvinte_defesa",
                        entidade_id=ouvinte.id, novo=_descricao(nome, matricula))
    return ouvinte


def registrar_ouvinte(db: Session, usuario: Usuario, defesa_id: int, dados: OuvinteEntrada) -> OuvinteOut:
    """POST /defesas/{id}/ouvintes (msgs 13 a 15)."""
    defesa = _para_gravar(db, usuario, defesa_id)
    nome, matricula = _conferir_ouvinte(db, defesa.id, dados.nome, dados.matricula)
    try:
        ouvinte = _incluir(db, usuario, defesa, nome, matricula)
    except IntegrityError:  # outra pessoa gravou a mesma matrícula entre a conferência e a gravação
        db.rollback()
        raise ErroAPI(422, MSG_REPETIDA, campo="matricula") from None
    _gravar(db)
    db.refresh(ouvinte)
    return _ouvinte_out(db, ouvinte)


def registrar_ouvintes_em_lote(db: Session, usuario: Usuario, defesa_id: int, dados: LoteEntrada) -> LoteOut:
    """POST /defesas/{id}/ouvintes/lote (msgs 16 a 18): grava as linhas válidas e devolve as que não entraram.

    Cada linha é "nome; matrícula" ou só o nome (visitante sem matrícula). Cada ouvinte é gravado no seu próprio
    ponto de salvamento: se outra pessoa gravar a mesma matrícula ao mesmo tempo, só aquela linha volta como
    problema, e as demais continuam."""
    defesa = _para_gravar(db, usuario, defesa_id)
    validas, problemas, vistas = [], [], set()
    for numero, linha in enumerate(dados.linhas, start=1):
        if not linha.strip():
            continue
        partes = [p.strip() for p in SEPARADOR_LOTE.split(linha)]
        if len(partes) > 2:
            problemas.append(LinhaComProblema(linha=numero, texto=linha.strip(),
                                              motivo='Use "nome; matrícula" ou só o nome.'))
            continue
        try:
            nome, matricula = _conferir_ouvinte(db, defesa.id, partes[0], partes[1] if len(partes) == 2 else None,
                                                ja_na_lista=vistas)
        except ErroAPI as erro:
            problemas.append(LinhaComProblema(linha=numero, texto=linha.strip(), motivo=erro.corpo["detail"]))
            continue
        if matricula:
            vistas.add(matricula)
        validas.append((numero, linha.strip(), nome, matricula))

    novos = []
    for numero, texto, nome, matricula in validas:
        ponto = db.begin_nested()
        try:
            novos.append(_incluir(db, usuario, defesa, nome, matricula))
            ponto.commit()
        except IntegrityError:
            ponto.rollback()
            problemas.append(LinhaComProblema(linha=numero, texto=texto, motivo=MSG_REPETIDA))
    db.commit()
    problemas.sort(key=lambda p: p.linha)
    return LoteOut(adicionados=[_ouvinte_out(db, o) for o in novos], linhas_com_problema=problemas)


def _ouvinte(db: Session, defesa: Defesa, ouvinte_id: int) -> OuvinteDefesa:
    ouvinte = db.get(OuvinteDefesa, ouvinte_id)
    if ouvinte is None or ouvinte.defesa_id != defesa.id:
        raise ErroAPI(404, "Ouvinte não encontrado.")
    return ouvinte


def corrigir_ouvinte(db: Session, usuario: Usuario, defesa_id: int, ouvinte_id: int, matricula: str) -> OuvinteOut:
    """PUT /defesas/{id}/ouvintes/{id} (DS-FL09-A msgs 6 a 9): corrige ou informa a matrícula e registra no log."""
    defesa = _para_gravar(db, usuario, defesa_id)
    ouvinte = _ouvinte(db, defesa, ouvinte_id)
    if _declaracao(db, ouvinte.id) is not None:
        raise ErroAPI(409, "A declaração deste ouvinte já foi emitida com esta matrícula.")
    _, matricula = _conferir_ouvinte(db, defesa.id, ouvinte.nome, matricula, exceto=ouvinte.id,
                                     exigir_matricula=True)
    anterior = ouvinte.matricula
    ouvinte.matricula = matricula
    auditoria.registrar(db, ator_id=usuario.id, acao="corrigir_ouvinte", entidade="ouvinte_defesa",
                        entidade_id=ouvinte.id, campo="matricula", anterior=anterior, novo=matricula)
    _gravar(db)
    db.refresh(ouvinte)
    return _ouvinte_out(db, ouvinte)


def remover_ouvinte(db: Session, usuario: Usuario, defesa_id: int, ouvinte_id: int) -> OuvinteOut:
    """DELETE /defesas/{id}/ouvintes/{id} (DS-FL09-A msgs 11 e 12). Devolve o removido, para o "Desfazer".
    O registro sai da lista, mas fica no log quem removeu, quando e quem era (RNF03)."""
    defesa = _para_gravar(db, usuario, defesa_id)
    ouvinte = _ouvinte(db, defesa, ouvinte_id)
    if _declaracao(db, ouvinte.id) is not None:
        raise ErroAPI(409, "Este ouvinte já recebeu a declaração e não pode sair da lista.")
    removido = _ouvinte_out(db, ouvinte)
    auditoria.registrar(db, ator_id=usuario.id, acao="remover_ouvinte", entidade="ouvinte_defesa",
                        entidade_id=ouvinte.id, anterior=_descricao(ouvinte.nome, ouvinte.matricula))
    db.delete(ouvinte)
    db.commit()
    return removido


# =================================================================== DS-FL09-B · declaração de horas

MSG_JA_EMITIDA = "A declaração deste ouvinte já foi emitida."


def emitir_declaracao(db: Session, usuario: Usuario, defesa_id: int, ouvinte_id: int) -> DeclaracaoOut:
    """POST /defesas/{id}/declaracoes (msgs 2 a 5): gera o PDF e grava o DocumentoOficial DECLARACAO_HORAS.

    Dois cliques ao mesmo tempo: o índice único parcial uq_documento_oficial_declaracao_vigente deixa passar só
    uma declaração vigente por ouvinte; a outra recebe 409 e o PDF dela é apagado."""
    defesa = _defesa(db, usuario, defesa_id)
    if defesa.situacao == CANCELADA:
        raise ErroAPI(409, "Esta defesa foi cancelada.")
    if not pode_emitir(defesa):  # msg 3 · E4
        raise ErroAPI(409, "A declaração só pode ser emitida depois que a defesa for realizada (RN15).")
    ouvinte = _ouvinte(db, defesa, ouvinte_id)
    if not matricula_valida(ouvinte.matricula):  # msg 4 · E5
        raise ErroAPI(422, "Informe a matrícula completa do ouvinte para emitir a declaração.", campo="matricula")
    if _declaracao(db, ouvinte.id) is not None:
        raise ErroAPI(409, MSG_JA_EMITIDA)

    documento = DocumentoOficial(defesa_id=defesa.id, tipo=DOC_DECLARACAO, versao=1, vigente=True,
                                 sha256="0" * 64, caminho="", ouvinte_id=ouvinte.id)
    db.add(documento)
    try:
        db.flush()  # o número da declaração vai impresso no PDF
    except IntegrityError:
        db.rollback()
        raise ErroAPI(409, MSG_JA_EMITIDA) from None
    documento.caminho = f"declaracoes/defesa-{defesa.id}/declaracao-{documento.id}-v{documento.versao}.pdf"
    conteudo = documentos.declaracao_horas(numero=documento.id, ouvinte=ouvinte, defesa=defesa,
                                           tcc=defesa.tcc, gerado_em=documento.gerado_em or agora())
    documento.sha256 = documentos.gravar(documento.caminho, conteudo)
    auditoria.registrar(db, ator_id=usuario.id, acao="emitir_declaracao", entidade="documento_oficial",
                        entidade_id=documento.id, campo="ouvinte",
                        novo=f"{_descricao(ouvinte.nome, ouvinte.matricula)} · versão {documento.versao} · "
                             f"sha256 {documento.sha256}")
    caminho = documento.caminho
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        documentos.apagar(caminho)
        raise ErroAPI(409, MSG_JA_EMITIDA) from None
    except Exception:
        db.rollback()
        documentos.apagar(caminho)
        raise
    db.refresh(documento)
    return _declaracao_out(documento)


def arquivo_da_declaracao(db: Session, usuario: Usuario, defesa_id: int, declaracao_id: int) -> bytes:
    """O PDF emitido, conferido pelo SHA-256 (RNF06). Mesmo acesso das demais rotas (CA-06)."""
    defesa = _defesa(db, usuario, defesa_id)
    documento = db.get(DocumentoOficial, declaracao_id)
    if documento is None or documento.defesa_id != defesa.id or documento.tipo != DOC_DECLARACAO:
        raise ErroAPI(404, "Declaração não encontrada.")
    return documentos.ler(documento.caminho, documento.sha256)
