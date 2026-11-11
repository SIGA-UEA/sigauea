"""Documentos da defesa: ata, Folha de Aprovação e certificados de participação (RBN09.14 a RBN09.17 ·
RN07, RN13, RN15, RN17, RN20 · DS-FL06-C, DS-FL06-E e DS-FL06-F, TEL13).

Faz o papel do ControladorDocumentosDefesa do diagrama de classes (MOD04): listarDocumentos(defesa),
gerarAta(defesa), gerarFolha(defesa), emitirCertificados(defesa, membros) e baixar(documento).

Regras gerais:
- quem gera a ata e a folha e emite certificados: a coordenação ou o orientador do TCC (E3 do RBN09.17);
- quem consulta e baixa: quem tem vínculo com o TCC e a coordenação do núcleo (E2 do RBN09.13 e do RBN09.16).
  A folha só chega ao aluno depois de liberada (RBN09.15 CA-03) e o certificado só ao próprio membro;
- cada geração é uma nova versão: a anterior fica "substituída" e a nova "vigente" (RN15); o índice único
  parcial uq_documento_oficial_ata_folha_vigente barra duas vigentes com dois cliques ao mesmo tempo;
- o PDF é gravado com SHA-256 e conferido na leitura (RNF06); cada download fica no log com a versão
  (RBN09.16 CA-05);
- falha ao gerar não muda nada: a transação é desfeita e o arquivo apagado (E2 do DS-FL06-C).
"""

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import agora
from app.erros import ErroAPI
from app.models import (
    APROVADO_COM_CORRECOES,
    CANCELADA,
    DOC_ATA,
    DOC_CERTIFICADO,
    DOC_FOLHA,
    REPROVADO_DEFESA,
    BancaMembro,
    Defesa,
    DocumentoOficial,
    NotificacaoEmail,
    ResultadoDefesa,
    Usuario,
)
from app.schemas.documento import (
    CertificadoOut,
    CertificadosEntrada,
    DocumentoDefesaOut,
    DocumentosOut,
    VersaoDocumentoOut,
)
from app.services import auditoria, documentos, email, nota_final
from app.services.acesso_defesa import Vinculo, vinculo
from app.services.ocorrencias import participantes, pode_emitir
from app.services.turmas import pessoa

TIPO_EMAIL_CERTIFICADO = "CERTIFICADO"
SO_GESTAO = "Só a coordenação e o orientador do TCC geram os documentos da defesa."
NAO_CONFIRMADO = "Indisponível por enquanto: o resultado da defesa ainda não foi confirmado."
NOMES = {DOC_ATA: "ata", DOC_FOLHA: "folha de aprovação", DOC_CERTIFICADO: "certificado"}


# =================================================================== consultas


def _resultados(db: Session, defesa: Defesa) -> list[ResultadoDefesa]:
    return list(db.scalars(select(ResultadoDefesa).where(ResultadoDefesa.defesa_id == defesa.id)
                           .order_by(ResultadoDefesa.versao)))


def _versoes(db: Session, defesa: Defesa, tipo: str) -> list[DocumentoOficial]:
    return list(db.scalars(select(DocumentoOficial).where(DocumentoOficial.defesa_id == defesa.id,
                                                          DocumentoOficial.tipo == tipo)
                           .order_by(DocumentoOficial.versao.desc())))


def _versao_out(d: DocumentoOficial) -> VersaoDocumentoOut:
    return VersaoDocumentoOut(id=d.id, versao=d.versao, vigente=d.vigente, gerado_em=d.gerado_em,
                              substituido_em=d.substituido_em)


def _folha_aplica(defesa: Defesa) -> bool:
    """RBN09.15: exclusiva para TCC2 e para a modalidade artigo."""
    return defesa.tcc.etapa == "TCC2" or defesa.tcc.modalidade == "ARTIGO"


def folha_liberada(resultado: ResultadoDefesa | None) -> bool:
    """CA-03 do RBN09.15: aprovado, ou aprovado com correções depois da anuência do aluno."""
    if resultado is None or resultado.resultado == REPROVADO_DEFESA:
        return False
    return resultado.resultado != APROVADO_COM_CORRECOES or resultado.anuencia_em is not None


def _faltas(defesa: Defesa) -> list[str]:
    """Dados obrigatórios da ata e da folha (CA-03 do RBN09.14, CA-04 do RBN09.15): local da sessão e a banca
    completa (orientador e dois avaliadores ou o suplente convocado), com a presença registrada."""
    faltas: list[str] = []
    if defesa.local is None and not defesa.link:
        faltas.append("Local da defesa.")
    membros = participantes(defesa)
    if not any(m.papel == "ORIENTADOR" for m in membros):
        faltas.append("Orientador na banca.")
    avaliadores = [m for m in membros if m.papel == "AVALIADOR" or (m.papel == "SUPLENTE" and m.convocado_em)]
    substituidos = {m.substitui_membro_id for m in membros if m.substitui_membro_id}
    if len([m for m in avaliadores if m.id not in substituidos]) < 2:
        faltas.append("Dois avaliadores na banca.")
    for m in membros:
        if m.presente is None:
            faltas.append(f"Presença de {m.usuario.nome} (Presença e ocorrências).")
    return faltas


def _secao(db: Session, defesa: Defesa, tipo: str, resultado: ResultadoDefesa | None, aplica: bool,
           visivel: bool) -> DocumentoDefesaOut:
    versoes = _versoes(db, defesa, tipo) if visivel else []
    faltas = _faltas(defesa) if resultado is not None and aplica else []
    motivo = None
    if not aplica:
        motivo = "Não se aplica: a Folha de Aprovação é só para TCC2 ou para a modalidade artigo."
    elif defesa.situacao == CANCELADA:
        motivo = "Esta defesa foi cancelada."
    elif resultado is None:
        motivo = NAO_CONFIRMADO
    elif tipo == DOC_FOLHA and resultado.resultado == REPROVADO_DEFESA:
        motivo = "Não se aplica: o resultado foi reprovado."
    elif tipo == DOC_FOLHA and not folha_liberada(resultado):
        motivo = "Liberada depois que o aluno der a anuência às correções exigidas."
    elif faltas:
        motivo = "Faltam dados obrigatórios para gerar o documento."
    vigente = next((v for v in versoes if v.vigente), None)
    desatualizada = bool(vigente and resultado and resultado.confirmado_em > vigente.gerado_em)
    return DocumentoDefesaOut(aplica=aplica, disponivel=motivo is None, motivo=motivo, faltas=faltas,
                              desatualizada=desatualizada, versoes=[_versao_out(v) for v in versoes])


def _envio(db: Session, certificado: DocumentoOficial | None) -> str:
    if certificado is None:
        return "NAO_ENVIADO"
    ultimo = db.scalar(select(NotificacaoEmail).where(
        NotificacaoEmail.tipo == TIPO_EMAIL_CERTIFICADO, NotificacaoEmail.entidade == "documento_oficial",
        NotificacaoEmail.entidade_id == certificado.id).order_by(NotificacaoEmail.id.desc()).limit(1))
    if ultimo is None:
        return "NAO_ENVIADO"
    return {"pendente": "PENDENTE", "enviado": "ENVIADO", "falha": "FALHA"}.get(ultimo.status, "PENDENTE")


def _certificado(db: Session, membro: BancaMembro) -> DocumentoOficial | None:
    return db.scalar(select(DocumentoOficial).where(DocumentoOficial.tipo == DOC_CERTIFICADO,
                                                    DocumentoOficial.membro_id == membro.id,
                                                    DocumentoOficial.vigente.is_(True)))


def _motivo_certificado(defesa: Defesa, membro: BancaMembro) -> str | None:
    if defesa.situacao == CANCELADA:
        return "Defesa cancelada."
    if not pode_emitir(defesa):
        return "A defesa ainda não foi realizada."
    if membro.presente is None:
        return "Presença não registrada."
    if not membro.presente:
        return "Ausente na defesa."
    return None


def _certificados_out(db: Session, defesa: Defesa) -> list[CertificadoOut]:
    linhas = []
    for m in participantes(defesa):  # o suplente não convocado fica de fora (CA-04)
        cert = _certificado(db, m)
        motivo = _motivo_certificado(defesa, m)
        linhas.append(CertificadoOut(
            membro_id=m.id, papel=m.papel, pessoa=pessoa(m.usuario), presente=m.presente,
            pode_emitir=motivo is None and cert is None, motivo=motivo, certificado_id=cert.id if cert else None,
            emitido_em=cert.gerado_em if cert else None, envio=_envio(db, cert)))
    return linhas


def _documentos_out(db: Session, defesa: Defesa, v: Vinculo) -> DocumentosOut:
    resultados = _resultados(db, defesa)
    vigente = next((r for r in resultados if r.vigente), None)
    ve_folha = v.gestao or (v.aluno and folha_liberada(vigente))
    meus = []
    if v.membro is not None:
        cert = _certificado(db, v.membro)
        meus = [_versao_out(cert)] if cert else []
    return DocumentosOut(
        defesa_id=defesa.id,
        pode_gerar=v.gestao,
        resultado_confirmado=vigente is not None,
        ata=_secao(db, defesa, DOC_ATA, vigente, True, True),
        folha=_secao(db, defesa, DOC_FOLHA, vigente, _folha_aplica(defesa), ve_folha),
        certificados=_certificados_out(db, defesa) if v.gestao else [],
        meus_certificados=meus,
    )


def listar_documentos(db: Session, usuario: Usuario, defesa_id: int) -> DocumentosOut:
    """GET /defesas/{idDefesa}/documentos (DS-FL06-C mensagens 2 a 4; DS-FL06-E mensagens 4 a 6)."""
    defesa, v = vinculo(db, usuario, defesa_id)
    return _documentos_out(db, defesa, v)


# =================================================================== geração (DS-FL06-C)


def _gestao(db: Session, usuario: Usuario, defesa_id: int) -> tuple[Defesa, Vinculo]:
    defesa, v = vinculo(db, usuario, defesa_id)
    if not v.gestao:
        raise ErroAPI(403, SO_GESTAO)
    if defesa.situacao == CANCELADA:
        raise ErroAPI(409, "Esta defesa foi cancelada.")
    return defesa, v


def _gravar_documento(db: Session, usuario: Usuario, defesa: Defesa, tipo: str, montar, membro_id=None):
    """Nova versão vigente do documento; a anterior fica substituída (RN15). `montar(numero, versao, gerado_em)`
    devolve os bytes do PDF. Falha ao gerar não muda nada (E2)."""
    anterior = next((d for d in _versoes(db, defesa, tipo) if d.vigente and d.membro_id == membro_id), None)
    versao = max((d.versao for d in _versoes(db, defesa, tipo) if d.membro_id == membro_id), default=0) + 1
    gerado_em = agora()
    if anterior is not None:
        anterior.vigente = False
        anterior.substituido_em = gerado_em
    documento = DocumentoOficial(defesa_id=defesa.id, tipo=tipo, versao=versao, vigente=True, sha256="0" * 64,
                                 caminho="", membro_id=membro_id, gerado_em=gerado_em)
    caminho = None
    try:
        db.flush()  # a anterior deixa de ser vigente antes da nova (índice de vigente)
        db.add(documento)
        db.flush()  # o número do documento vai impresso no PDF
        caminho = f"defesas/defesa-{defesa.id}/{tipo.lower()}-{documento.id}-v{versao}.pdf"
        documento.caminho = caminho
        documento.sha256 = documentos.gravar(caminho, montar(documento.id, versao, gerado_em))
        auditoria.registrar(db, ator_id=usuario.id, acao=f"gerar_{tipo.lower()}", entidade="documento_oficial",
                            entidade_id=documento.id, campo="versao", anterior=anterior.versao if anterior else None,
                            novo=f"versão {versao} · sha256 {documento.sha256}")
        db.commit()
    except IntegrityError:  # outro clique gerou a mesma versão ao mesmo tempo
        db.rollback()
        if caminho:
            documentos.apagar(caminho)
        raise ErroAPI(409, f"Outra {NOMES[tipo]} acabou de ser gerada. Confira a versão vigente.") from None
    except ErroAPI:
        db.rollback()
        raise
    except Exception:  # E2: "Não foi possível gerar o documento"; nada muda
        db.rollback()
        if caminho:
            documentos.apagar(caminho)
        raise ErroAPI(500, "Não foi possível gerar o documento. Nada foi alterado; tente de novo.") from None
    db.refresh(documento)
    return documento


def _exigir_dados(defesa: Defesa, resultado: ResultadoDefesa | None) -> ResultadoDefesa:
    if resultado is None:  # E1 do DS-FL06-C (RBN09.14 CA-04)
        raise ErroAPI(409, NAO_CONFIRMADO)
    faltas = _faltas(defesa)
    if faltas:  # CA-03 do RBN09.14 e CA-04 do RBN09.15: não emite e diz o que falta
        raise ErroAPI(409, "Faltam dados obrigatórios para gerar o documento.", faltas=faltas)
    return resultado


def gerar_ata(db: Session, usuario: Usuario, defesa_id: int) -> DocumentosOut:
    """POST /defesas/{idDefesa}/documentos/ata (DS-FL06-C mensagens 5 a 11)."""
    defesa, v = _gestao(db, usuario, defesa_id)
    resultados = _resultados(db, defesa)
    resultado = _exigir_dados(defesa, next((r for r in resultados if r.vigente), None))
    calculo = nota_final.calcular_nota_final(db, defesa)
    conteudo = documentos.montar_ata(
        defesa=defesa, tcc=defesa.tcc, membros=participantes(defesa),
        notas=[(n.membro, n.nota) for n in calculo.notas], resultado=resultado,
        retificacoes=list(zip(resultados, resultados[1:])))
    _gravar_documento(db, usuario, defesa, DOC_ATA,
                      lambda numero, versao, em: documentos.ata_defesa(conteudo, numero=numero, versao=versao,
                                                                       gerado_em=em))
    return _documentos_out(db, defesa, v)


def gerar_folha(db: Session, usuario: Usuario, defesa_id: int) -> DocumentosOut:
    """POST /defesas/{idDefesa}/documentos/folha (DS-FL06-C mensagens 12 a 15)."""
    defesa, v = _gestao(db, usuario, defesa_id)
    if not _folha_aplica(defesa):  # CA-02: TCC1 em monografia não tem folha
        raise ErroAPI(409, "Não se aplica: a Folha de Aprovação é só para TCC2 ou para a modalidade artigo.")
    resultado = next((r for r in _resultados(db, defesa) if r.vigente), None)
    if resultado is not None and resultado.resultado == REPROVADO_DEFESA:  # E3
        raise ErroAPI(409, "Não se aplica: o resultado foi reprovado.")
    if resultado is not None and not folha_liberada(resultado):  # E3: anuência pendente (CA-03)
        raise ErroAPI(409, "A folha só pode ser gerada depois que o aluno der a anuência às correções exigidas.")
    resultado = _exigir_dados(defesa, resultado)
    conteudo = documentos.montar_folha(defesa=defesa, tcc=defesa.tcc, membros=participantes(defesa),
                                       resultado=resultado)
    _gravar_documento(db, usuario, defesa, DOC_FOLHA,
                      lambda numero, versao, em: documentos.folha_aprovacao(conteudo, numero=numero, versao=versao,
                                                                            gerado_em=em))
    return _documentos_out(db, defesa, v)


# =================================================================== certificados (DS-FL06-F)


def _texto_certificado(defesa: Defesa, membro: BancaMembro) -> tuple[str, str]:
    corpo = (
        f"Olá, {membro.usuario.nome}.\n\n"
        "Segue em anexo o seu certificado de participação na banca examinadora da defesa de TCC abaixo.\n\n"
        f"Trabalho: {defesa.tcc.titulo}\nAutor(a): {defesa.tcc.aluno.usuario.nome}\n"
        f"Defesa em {defesa.data.strftime('%d/%m/%Y')}\n\nSIGA UEA - Núcleo de Computação (NUCOMP) da EST/UEA"
    )
    return "Certificado de participação em banca de defesa de TCC", corpo


def _enviar_certificado(db: Session, tarefas: BackgroundTasks, defesa: Defesa, membro: BancaMembro,
                        certificado: DocumentoOficial) -> None:
    """Envia o PDF anexado ao e-mail do participante; o envio fica registrado com data e situação (CA-02)."""
    arquivo = documentos.ler(certificado.caminho, certificado.sha256)
    assunto, corpo = _texto_certificado(defesa, membro)
    email.enfileirar(db, tarefas, membro.usuario, TIPO_EMAIL_CERTIFICADO, assunto, corpo,
                     entidade="documento_oficial", entidade_id=certificado.id,
                     anexo=(f"certificado-participacao-{certificado.id}.pdf", arquivo))


def emitir_certificados(
    db: Session, usuario: Usuario, defesa_id: int, dados: CertificadosEntrada, tarefas: BackgroundTasks
) -> DocumentosOut:
    """POST /defesas/{idDefesa}/documentos/certificados {idsMembro[]} (DS-FL06-F)."""
    defesa, v = _gestao(db, usuario, defesa_id)  # E3 (CA-06): 403; cancelada: 409 (CA-03)
    if not pode_emitir(defesa):  # E1: defesa não realizada (RN15)
        raise ErroAPI(409, "Os certificados só podem ser emitidos depois que a defesa for realizada (RN15).")
    por_id = {m.id: m for m in participantes(defesa)}  # o suplente não convocado fica de fora (CA-04)
    escolhidos = []
    for membro_id in dict.fromkeys(dados.ids_membro):
        membro = por_id.get(membro_id)
        if membro is None:
            raise ErroAPI(404, "Membro da banca não encontrado nesta defesa.")
        motivo = _motivo_certificado(defesa, membro)
        if motivo is not None:  # CA-03: ausente (ou sem presença registrada) não recebe certificado
            raise ErroAPI(409, f"{membro.usuario.nome} não recebe certificado: {motivo[0].lower()}{motivo[1:]}",
                          membro_id=membro.id)
        if _certificado(db, membro) is None:  # CA-05: emitir de novo não duplica
            escolhidos.append(membro)
    for membro in escolhidos:
        conteudo = documentos.montar_certificado(defesa=defesa, tcc=defesa.tcc, membro=membro)
        cert = _gravar_documento(
            db, usuario, defesa, DOC_CERTIFICADO,
            lambda numero, versao, em: documentos.certificado_participacao(conteudo, numero=numero, gerado_em=em),
            membro_id=membro.id)
        _enviar_certificado(db, tarefas, defesa, membro, cert)
        db.commit()
    return _documentos_out(db, defesa, v)


def reenviar_certificado(
    db: Session, usuario: Usuario, documento_id: int, tarefas: BackgroundTasks
) -> DocumentosOut:
    """POST /documentos/{id}/reenvio: manda de novo o mesmo certificado, sem gerar outro (CA-05, E2)."""
    documento = db.get(DocumentoOficial, documento_id)
    if documento is None or documento.tipo != DOC_CERTIFICADO or not documento.vigente:
        raise ErroAPI(404, "Certificado não encontrado.")
    defesa, v = _gestao(db, usuario, documento.defesa_id)
    membro = db.get(BancaMembro, documento.membro_id)
    _enviar_certificado(db, tarefas, defesa, membro, documento)
    auditoria.registrar(db, ator_id=usuario.id, acao="reenviar_certificado", entidade="documento_oficial",
                        entidade_id=documento.id, campo="destinatario", novo=membro.usuario.nome)
    db.commit()
    return _documentos_out(db, defesa, v)


# =================================================================== download (DS-FL06-E)


def baixar(db: Session, usuario: Usuario, documento_id: int) -> tuple[DocumentoOficial, bytes]:
    """GET /documentos/{idDocumento}/arquivo (DS-FL06-E mensagens 7 e 8). Mesmo acesso da tela, também pela URL
    direta (CA-03 do RBN09.16); o arquivo é conferido pelo SHA-256 (CA-04) e o download vai para o log (CA-05)."""
    documento = db.get(DocumentoOficial, documento_id)
    if documento is None:
        raise ErroAPI(404, "Documento não encontrado.")
    defesa, v = vinculo(db, usuario, documento.defesa_id)  # sem vínculo: 403
    if documento.tipo == DOC_FOLHA and not v.gestao:
        vigente = next((r for r in _resultados(db, defesa) if r.vigente), None)
        if not (v.aluno and folha_liberada(vigente)):  # CA-03 do RBN09.15
            raise ErroAPI(403, "A Folha de Aprovação ainda não foi liberada para você.")
    elif documento.tipo == DOC_CERTIFICADO and not v.gestao:
        if v.membro is None or v.membro.id != documento.membro_id:
            raise ErroAPI(403, "Este certificado é de outro participante.")
    elif documento.tipo not in (DOC_ATA, DOC_FOLHA, DOC_CERTIFICADO) and not v.gestao:
        raise ErroAPI(403, "Documento disponível só para a coordenação e o orientador.")
    conteudo = documentos.ler(documento.caminho, documento.sha256)
    auditoria.registrar(db, ator_id=usuario.id, acao="baixar_documento", entidade="documento_oficial",
                        entidade_id=documento.id, campo=documento.tipo,
                        novo=f"versão {documento.versao}{' (vigente)' if documento.vigente else ' (substituída)'}")
    db.commit()
    return documento, conteudo
