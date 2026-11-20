"""Publicação do artigo: situação editorial, histórico e aviso por e-mail (RBN12.01 a RBN12.03 · RN03, RN07 ·
DS-FL08, DS-FL08-A e DS-FL08-B, TEL15).

Faz o papel do ControladorPublicacao do diagrama de classes (MOD05): obterDoTcc, registrar e listar o histórico; e,
no DS-FL08-A, o notificarSituacao do ControladorNotificacao.

Modelo (físico): cada PublicacaoArtigo é uma submissão a um veículo, e o TCC pode ter várias; o HistoricoPublicacao
guarda cada mudança de situação de uma submissão, com data e responsável. Registrar no mesmo veículo atualiza a
situação da submissão; registrar em outro veículo cria uma submissão nova, e a anterior continua no histórico
(CA-02 do RBN12.02). Nada do histórico é editado (CA-04).

Quem pode: registrar, o aluno autor e o orientador do TCC (CA-06 do RBN12.01); consultar, quem vê o TCC. Sem
vínculo, 403; TCC que não é artigo, 409 (E1). A situação editorial não muda o cadastro nem a defesa (CA-04 do
RBN12.01); só a nota final pode mudar pela regra do Qualis (DS-FL06-B), calculada na confirmação do resultado.
"""

import re
from datetime import date

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app import config
from app.erros import ErroAPI
from app.models import ACEITA, PAPEL_ORIENTADOR, HistoricoPublicacao, PublicacaoArtigo, Tcc, Usuario
from app.schemas.publicacao import PublicacaoOut, RegistroEntrada, RegistroOut, SituacaoAtualOut
from app.services import auditoria, email
from app.services.nota_final import ESTRATOS_DA_EXCECAO
from app.services.tccs import obter_para
from app.services.turmas import pessoa

SITUACOES = ("SUBMETIDO", "EM_REVISAO", "ACEITO", "RECUSADO", "PUBLICADO")
NOME_SITUACAO = {"SUBMETIDO": "Submetido", "EM_REVISAO": "Em revisão", "ACEITO": "Aceito", "RECUSADO": "Recusado",
                 "PUBLICADO": "Publicado"}
ESTRATOS = ESTRATOS_DA_EXCECAO + ("C",)
TIPO_EMAIL = "SITUACAO_ARTIGO"
SEM_VINCULO = "Só quem tem vínculo com o TCC consulta a publicação do artigo."


# =================================================================== acesso


def _tcc(db: Session, usuario: Usuario, tcc_id: int) -> Tcc:
    """O TCC, se o usuário o vê; sem vínculo, 403 (E1), sem dizer se o TCC existe para quem não o vê."""
    try:
        return obter_para(db, usuario, tcc_id)
    except ErroAPI:
        raise ErroAPI(403, SEM_VINCULO) from None


def _orientador(tcc: Tcc) -> Usuario | None:
    return next((o.professor for o in tcc.orientacoes
                 if o.papel == PAPEL_ORIENTADOR and o.status == ACEITA and o.encerrado_em is None), None)


def _pode_registrar(tcc: Tcc, usuario: Usuario) -> bool:
    orientador = _orientador(tcc)
    return tcc.aluno_id == usuario.id or (orientador is not None and orientador.id == usuario.id)


# =================================================================== saída


def _atual(tcc: Tcc) -> PublicacaoArtigo | None:
    """A situação atual é a da submissão mais recente (a mesma regra da nota final, DS-FL06-B)."""
    return tcc.publicacoes[-1] if tcc.publicacoes else None


def _historico(tcc: Tcc) -> list[RegistroOut]:
    linhas = []
    for pub in tcc.publicacoes:
        for h in pub.historico:
            linhas.append(RegistroOut(
                id=h.id, situacao=h.situacao, data=h.data, responsavel=pessoa(h.usuario) if h.usuario else None,
                registrado_em=h.registrado_em, veiculo=pub.veiculo, tipo_veiculo=pub.tipo_veiculo, qualis=pub.qualis,
                link=pub.doi))
    return sorted(linhas, key=lambda r: (r.data, r.registrado_em, r.id), reverse=True)


def _saida(tcc: Tcc, usuario: Usuario) -> PublicacaoOut:
    atual = _atual(tcc)
    return PublicacaoOut(
        tcc_id=tcc.id,
        pode_registrar=_pode_registrar(tcc, usuario),
        atual=SituacaoAtualOut(veiculo=atual.veiculo, tipo_veiculo=atual.tipo_veiculo, qualis=atual.qualis,
                               link=atual.doi, situacao=atual.situacao_atual) if atual else None,
        historico=_historico(tcc),
    )


def consultar(db: Session, usuario: Usuario, tcc_id: int) -> PublicacaoOut:
    """GET /tccs/{idTcc}/publicacao (DS-FL08 mensagens 3 a 5) e /publicacoes/historico (DS-FL08-B)."""
    tcc = _tcc(db, usuario, tcc_id)
    if tcc.modalidade != "ARTIGO":
        raise ErroAPI(409, "Este TCC não é da modalidade artigo.")
    return _saida(tcc, usuario)


# =================================================================== RBN12.01 · registrar


def _validar(dados: RegistroEntrada, atual: PublicacaoArtigo | None) -> dict:
    """DS-FL08 mensagem 7 e E2: campo inválido ou situação fora do vocabulário marcam o campo (422)."""
    campos: dict[str, str] = {}
    veiculo = dados.veiculo.strip()
    if len(veiculo) < 2:
        campos["veiculo"] = "Informe o veículo (revista ou evento)."
    elif len(veiculo) > 200:
        campos["veiculo"] = "Use até 200 caracteres."
    if dados.situacao not in SITUACOES:
        campos["situacao"] = "Escolha a situação editorial."
    if dados.data is None:
        campos["data"] = "Informe a data da alteração."
    elif dados.data > date.today():
        campos["data"] = "A data não pode ser futura."
    qualis = (dados.qualis or "").strip().upper() or None
    if qualis is not None and qualis not in ESTRATOS:
        campos["qualis"] = "Use um estrato de A1 a A4, de B1 a B4 ou C."
    link = (dados.link or "").strip() or None
    if link is not None and not re.match(r"^https://\S+$", link) and not re.match(r"^10\.\d{4,9}/\S+$", link):
        campos["link"] = "Use um endereço que comece com https:// ou um DOI (10.xxxx/...)."
    mesmo = atual is not None and atual.veiculo.strip().lower() == veiculo.lower()
    tipo = dados.tipo_veiculo or (atual.tipo_veiculo if mesmo else None)
    if tipo is None and "veiculo" not in campos:
        campos["tipo_veiculo"] = "Informe se é periódico ou congresso."
    if dados.situacao == "PUBLICADO" and not (link or (atual.doi if mesmo else None)):
        campos["link"] = "Para publicado, informe o DOI ou o endereço da publicação."
    if campos:
        raise ErroAPI(422, "Confira os campos destacados.", campos=campos)
    return {"veiculo": veiculo, "tipo": tipo, "qualis": qualis, "link": link, "mesmo": mesmo}


def registrar(db: Session, usuario: Usuario, tcc_id: int, dados: RegistroEntrada,
              tarefas: BackgroundTasks) -> PublicacaoOut:
    """POST /tccs/{idTcc}/publicacao (DS-FL08 mensagens 8 a 12)."""
    tcc = _tcc(db, usuario, tcc_id)
    if not _pode_registrar(tcc, usuario):  # E1: só o aluno autor e o orientador
        raise ErroAPI(403, "Só o aluno autor e o orientador registram a publicação do artigo.")
    if tcc.modalidade != "ARTIGO":  # E1: 409
        raise ErroAPI(409, "Este TCC não é da modalidade artigo.")
    atual = _atual(tcc)
    v = _validar(dados, atual)
    situacao_antes = atual.situacao_atual if atual else None

    if v["mesmo"]:  # atualizar(idPublicacao, situação, veículo, qualis)
        pub = atual
        pub.situacao_atual = dados.situacao
        pub.qualis = v["qualis"] if v["qualis"] is not None else pub.qualis
        pub.doi = v["link"] if v["link"] is not None else pub.doi
        pub.tipo_veiculo = v["tipo"]
    else:  # outra submissão: a anterior continua no histórico (CA-02 do RBN12.02)
        pub = PublicacaoArtigo(tcc_id=tcc.id, tipo_veiculo=v["tipo"], veiculo=v["veiculo"], qualis=v["qualis"],
                               doi=v["link"], situacao_atual=dados.situacao)
        db.add(pub)
        db.flush()
        tcc.publicacoes.append(pub)
    registro = HistoricoPublicacao(publicacao_id=pub.id, situacao=dados.situacao, data=dados.data,
                                   usuario_id=usuario.id)
    db.add(registro)  # registrar(situação, data, quem); os anteriores ficam
    db.flush()
    auditoria.registrar(db, ator_id=usuario.id, acao="registrar_publicacao", entidade="publicacao_artigo",
                        entidade_id=pub.id, campo="situacao", anterior=situacao_antes,
                        novo=f"{dados.situacao} · {pub.veiculo} · {dados.data.isoformat()}")
    if dados.situacao != situacao_antes:  # CA-04 do RBN12.03: sem mudança de situação, sem e-mail
        _avisar(db, tarefas, tcc, pub, dados.situacao, dados.data)
    db.commit()
    db.refresh(tcc)
    return _saida(tcc, usuario)


# =================================================================== RBN12.03 · DS-FL08-A


def _avisar(db: Session, tarefas: BackgroundTasks, tcc: Tcc, pub: PublicacaoArtigo, situacao: str, quando: date) -> None:
    """notificarSituacao(idTcc, situação): um e-mail ao orientador e ao autor, com título, veículo, nova situação,
    data e o link do histórico (CA-02 e CA-03). Sem CPF, matrícula ou notas (CA-06). A falha de envio fica
    registrada na fila e não desfaz o registro (E1)."""
    destinatarios = [tcc.aluno.usuario]
    orientador = _orientador(tcc)
    if orientador is not None and orientador.id != tcc.aluno.usuario.id:
        destinatarios.append(orientador)
    for pessoa_ in destinatarios:
        corpo = (
            f"Olá, {pessoa_.nome}.\n\n"
            f"O artigo do TCC \"{tcc.titulo}\" passou para: {NOME_SITUACAO[situacao]}.\n\n"
            f"Veículo: {pub.veiculo}\n"
            f"Data da alteração: {quando.strftime('%d/%m/%Y')}\n\n"
            f"Histórico da publicação no SIGA UEA (exige login): {config.FRONTEND_URL}/tccs/{tcc.id}#artigo"
        )
        email.enfileirar(db, tarefas, pessoa_, TIPO_EMAIL, f"O seu artigo passou para: {NOME_SITUACAO[situacao]}",
                         corpo, entidade="publicacao_artigo", entidade_id=pub.id)
