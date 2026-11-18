"""Documentos oficiais em PDF (DocumentoOficial): geração, gravação e leitura conferida.

O banco guarda o caminho relativo à pasta ARQUIVOS_DIR e o SHA-256 do arquivo (documento_oficial,
RNF06). A gravação escreve num arquivo temporário e só então troca pelo definitivo, para uma falha no
meio não deixar um PDF pela metade. A leitura confere o SHA-256 antes de entregar.

Por ora gera a declaração de horas complementares do ouvinte (DS-FL09-B, RBN09.10, RN23). Ata, Folha
de Aprovação e certificados (RBN09.14 a RBN09.17) usam a mesma gravação.
"""

import hashlib
import os
from datetime import datetime, timedelta
from pathlib import Path

from fpdf import FPDF

from app import config
from app.erros import ErroAPI

FUSO_MANAUS = timedelta(hours=-4)  # America/Manaus não tem horário de verão (RNF03)
NOME_FORMATO = {"PRESENCIAL": "presencial", "REMOTO": "remota", "HIBRIDO": "híbrida"}
CABECALHO = (
    "UNIVERSIDADE DO ESTADO DO AMAZONAS",
    "ESCOLA SUPERIOR DE TECNOLOGIA",
    "NÚCLEO DE COMPUTAÇÃO (NUCOMP)",
)


# =================================================================== gravação e leitura


def _destino(caminho: str) -> Path:
    return Path(config.ARQUIVOS_DIR) / caminho


def gravar(caminho: str, conteudo: bytes) -> str:
    """Grava o arquivo em ARQUIVOS_DIR/caminho e devolve o SHA-256 do conteúdo."""
    destino = _destino(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(destino.suffix + ".tmp")
    temporario.write_bytes(conteudo)
    os.replace(temporario, destino)
    return hashlib.sha256(conteudo).hexdigest()


def ler(caminho: str, sha256: str) -> bytes:
    """Lê o arquivo e confere o SHA-256 gravado no banco (RNF06)."""
    destino = _destino(caminho)
    if not destino.is_file():
        raise ErroAPI(404, "O arquivo deste documento não foi encontrado.")
    conteudo = destino.read_bytes()
    if hashlib.sha256(conteudo).hexdigest() != sha256:
        raise ErroAPI(409, "O arquivo deste documento não confere com o registrado e não pode ser entregue.")
    return conteudo


def apagar(caminho: str) -> None:
    """Desfaz uma gravação cuja transação falhou."""
    _destino(caminho).unlink(missing_ok=True)


# =================================================================== declaração de horas (DS-FL09-B)
# Mesmo layout das declarações da UEA (Secretaria Acadêmica): brasão no topo, "DECLARAÇÃO" centralizado,
# texto "DECLARAMOS, para fins de direito..." com os dados em negrito, bloco de emissão no rodapé do texto
# e o endereço da universidade embaixo. O brasão e o logo entram se os arquivos oficiais estiverem em
# app/assets (brasao_amazonas.png e logo_uea.png); sem eles, o cabeçalho sai só em texto.

ASSETS = Path(__file__).resolve().parent.parent / "assets"
MESES = ("Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro",
         "Novembro", "Dezembro")
EMISSOR = ("NÚCLEO DE COMPUTAÇÃO (NUCOMP) DA ESCOLA SUPERIOR DE TECNOLOGIA DA UNIVERSIDADE DO ESTADO DO "
           "AMAZONAS.")
ENDERECO = ("Universidade do Estado do Amazonas", "Av. Djalma Batista, 3578 - Flores", "CEP 69050-010 - Manaus/AM",
            "www.uea.edu.br")


def _data(d) -> str:
    return d.strftime("%d/%m/%Y")


def _hora(h) -> str:
    return h.strftime("%H:%M")


def _negrito(texto: str) -> str:
    """Trecho em negrito no texto com marcação do FPDF, sem deixar o dado quebrar a marcação."""
    return "**" + texto.replace("*", "").replace("__", "_").replace("--", "-") + "**"


def carga_horaria(inicio, fim) -> str:
    """Duração da sessão, que é a carga horária da declaração: "1 h", "1 h 30 min" ou "20 min"."""
    minutos = (datetime.combine(datetime.min, fim) - datetime.combine(datetime.min, inicio)).seconds // 60
    horas, resto = divmod(minutos, 60)
    if horas and resto:
        return f"{horas} h {resto} min"
    return f"{horas} h" if horas else f"{resto} min"


def declaracao_horas(*, numero: int, ouvinte, defesa, tcc, gerado_em: datetime) -> bytes:
    """PDF da declaração de horas complementares de um ouvinte da defesa (RN23)."""
    pdf = FPDF(format="A4")
    pdf.set_margins(22, 18, 22)
    pdf.set_auto_page_break(False)
    pdf.set_title("Declaração de horas complementares")
    pdf.set_author("SIGA UEA")
    pdf.add_page()

    # cabeçalho: brasão do Governo do Estado do Amazonas
    brasao = ASSETS / "brasao_amazonas.png"  # já traz o nome "Governo do Estado do Amazonas"
    if brasao.is_file():
        pdf.image(str(brasao), x=(210 - 90) / 2, y=14, w=90)  # imagem sem bordas brancas
    else:
        pdf.set_y(24)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(0, 5, "GOVERNO DO ESTADO DO AMAZONAS", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(62)
    pdf.set_font("Times", "B", 22)
    pdf.cell(0, 10, "DECLARAÇÃO", align="C", new_x="LMARGIN", new_y="NEXT")

    local = f", em {defesa.local.nome}" if defesa.local else ""
    texto = (
        f"{_negrito('DECLARAMOS')}, para fins de direito e todos os efeitos, que {_negrito(ouvinte.nome)}, "
        f"matrícula nº {_negrito(ouvinte.matricula)}, assistiu como ouvinte à sessão pública de defesa do Trabalho de "
        f"Conclusão de Curso ({_negrito(tcc.etapa)}) intitulado {_negrito(tcc.titulo)}, de autoria de "
        f"{_negrito(tcc.aluno.usuario.nome)}, do curso de {_negrito(tcc.aluno.curso.nome)}, vinculado à "
        f"{_negrito('EST - Escola Superior de Tecnologia')}, realizada de forma {NOME_FORMATO[defesa.formato]}"
        f"{local}, em {_negrito(_data(defesa.data))}, das {_hora(defesa.inicio)} às {_hora(defesa.fim)}, "
        f"totalizando {_negrito(carga_horaria(defesa.inicio, defesa.fim))} de atividade complementar."
    )
    pdf.set_y(84)
    pdf.set_font("Times", "", 13)
    pdf.multi_cell(0, 8, texto, align="J", markdown=True, new_x="LMARGIN", new_y="NEXT")

    # bloco de emissão, como o da Secretaria Acadêmica
    emitido = gerado_em + FUSO_MANAUS
    pdf.set_y(224)
    pdf.set_font("Times", "", 10)
    pdf.multi_cell(0, 5, EMISSOR, align="L", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.cell(0, 5, f"Documento emitido às {emitido.strftime('%H:%M:%S')} do dia {emitido.day} / "
                   f"{MESES[emitido.month - 1]} / {emitido.year}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Times", "B", 10)
    pdf.cell(0, 5, f"Matrícula: {ouvinte.matricula}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Declaração Nº: {numero}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Times", "", 10)
    pdf.cell(0, 5, "Emitida pelo SIGA UEA a partir da lista de ouvintes registrada na defesa.",
             new_x="LMARGIN", new_y="NEXT")

    # rodapé: linha e endereço da universidade, com o logo da UEA à direita
    pdf.set_draw_color(0, 0, 0)
    pdf.line(15, 262, 195, 262)
    pdf.set_y(266)
    pdf.set_font("Times", "", 9.5)
    for linha in ENDERECO:
        pdf.cell(0, 4.5, linha, new_x="LMARGIN", new_y="NEXT")
    logo = ASSETS / "logo_uea.png"
    if logo.is_file():
        pdf.image(str(logo), x=172, y=265, w=20)
    return bytes(pdf.output())


# =================================================================== ata, Folha de Aprovação e certificado (RN15)
# Não há modelo oficial digitalizado no projeto: os três seguem o mesmo layout institucional da declaração de
# horas (brasão do Governo do Amazonas, título centralizado, texto da Secretaria Acadêmica e endereço da UEA no
# rodapé). O conteúdo de cada um é montado à parte (montar_*), para ser conferido sem abrir o PDF.

PAPEL_NA_BANCA = {"ORIENTADOR": "Orientador(a)", "COORIENTADOR": "Coorientador(a)", "AVALIADOR": "Avaliador(a)",
                  "SUPLENTE": "Suplente convocado(a)"}
NOME_RESULTADO = {"APROVADO": "APROVADO", "APROVADO_COM_CORRECOES": "APROVADO COM CORREÇÕES",
                  "REPROVADO": "REPROVADO"}
NOME_MODALIDADE = {"MONOGRAFIA": "monografia", "ARTIGO": "artigo"}


def _nota(valor) -> str:
    return f"{float(valor):.2f}".replace(".", ",")


def _por_extenso(d) -> str:
    return f"{d.day} de {MESES[d.month - 1].lower()} de {d.year}"


def _onde(defesa) -> str:
    """Local da sessão: a sala (presencial ou híbrida) e/ou a sala virtual (remota ou híbrida)."""
    partes = []
    if defesa.local is not None:
        partes.append(defesa.local.nome)
    if defesa.link:
        partes.append(f"sala virtual {defesa.link}")
    return " e ".join(partes)


def _instituicao(membro) -> str:
    externo = getattr(membro.usuario, "externo", None)
    instituicao = getattr(externo, "instituicao", None) if externo is not None else None
    if not membro.interno and instituicao:
        return instituicao
    return "UEA" if membro.interno else "Instituição externa"


def _papel(membro) -> str:
    return PAPEL_NA_BANCA.get(membro.papel, membro.papel.title())


def _pdf(titulo: str, *, paisagem: bool = False) -> FPDF:
    pdf = FPDF(orientation="L" if paisagem else "P", format="A4")
    pdf.set_margins(22, 18, 22)
    pdf.set_auto_page_break(True, margin=42)
    pdf.set_title(titulo)
    pdf.set_author("SIGA UEA")
    pdf.add_page()
    brasao = ASSETS / "brasao_amazonas.png"
    if brasao.is_file():
        pdf.image(str(brasao), x=(pdf.w - 80) / 2, y=12, w=80)
        pdf.set_y(50)
    else:
        pdf.set_y(20)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(0, 5, "GOVERNO DO ESTADO DO AMAZONAS", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Times", "B", 9)
    for linha in CABECALHO:
        pdf.cell(0, 4.5, linha, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    return pdf


def _rodape(pdf: FPDF, linhas: list[str]) -> bytes:
    """Bloco de emissão e endereço da universidade em cada página, com o logo da UEA à direita."""
    total = pdf.pages_count
    for pagina in range(1, total + 1):
        pdf.page = pagina
        pdf.set_auto_page_break(False)
        pdf.set_y(pdf.h - 40)
        pdf.set_font("Times", "", 8.5)
        for linha in linhas:
            pdf.multi_cell(pdf.w - 44 - 20, 3.8, linha, new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(0, 0, 0)
        pdf.line(15, pdf.h - 21, pdf.w - 15, pdf.h - 21)
        pdf.set_y(pdf.h - 19)
        pdf.set_font("Times", "", 8)
        pdf.cell(0, 3.6, " - ".join(ENDERECO), new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 3.6, f"Página {pagina} de {total}", new_x="LMARGIN", new_y="NEXT")
        logo = ASSETS / "logo_uea.png"
        if logo.is_file():
            pdf.image(str(logo), x=pdf.w - 34, y=pdf.h - 40, w=14)
    return bytes(pdf.output())


def _emissao(tipo: str, numero: int, versao: int, gerado_em: datetime, emitida: str = "emitida") -> list[str]:
    emitido = gerado_em + FUSO_MANAUS
    return [EMISSOR,
            f"{tipo} nº {numero}, versão {versao}, {emitida} pelo SIGA UEA às {emitido.strftime('%H:%M:%S')} de "
            f"{emitido.strftime('%d/%m/%Y')} (horário de Manaus). A integridade do arquivo é conferida pelo SHA-256 "
            "registrado no sistema."]


def _titulo(pdf: FPDF, texto: str, tamanho: int = 15) -> None:
    pdf.set_font("Times", "B", tamanho)
    pdf.multi_cell(0, 8, texto, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)


def _paragrafo(pdf: FPDF, texto: str, tamanho: float = 11.5, markdown: bool = True) -> None:
    pdf.set_font("Times", "", tamanho)
    pdf.multi_cell(0, 6.2, texto, align="J", markdown=markdown, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _subtitulo(pdf: FPDF, texto: str) -> None:
    pdf.set_font("Times", "B", 11.5)
    pdf.cell(0, 7, texto, new_x="LMARGIN", new_y="NEXT")


def _tabela(pdf: FPDF, cabecalho: list[str], linhas: list[list[str]], larguras: list[float]) -> None:
    pdf.set_font("Times", "B", 10)
    pdf.set_fill_color(230, 230, 230)
    for texto, w in zip(cabecalho, larguras):
        pdf.cell(w, 7, texto, border=1, fill=True)
    pdf.ln()
    pdf.set_font("Times", "", 10)
    for linha in linhas:
        for texto, w in zip(linha, larguras):
            pdf.cell(w, 7, texto, border=1)
        pdf.ln()
    pdf.ln(3)


def _assinaturas(pdf: FPDF, titulo: str, linhas: list[str]) -> None:
    """Título e linhas de assinatura juntos: se não couberem no fim da página, começam na próxima."""
    if pdf.get_y() + 8 + 17 * len(linhas) > pdf.h - 44:
        pdf.add_page()
    _subtitulo(pdf, titulo)
    pdf.set_font("Times", "", 10.5)
    for texto in linhas:
        if pdf.get_y() > pdf.h - 62:
            pdf.add_page()
        pdf.ln(11)
        pdf.cell(110, 0.1, "", border="T", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 5, texto, new_x="LMARGIN", new_y="NEXT")


# ------------------------------------------------------------------- ata da defesa (RBN09.14)


def montar_ata(*, defesa, tcc, membros, notas, resultado, retificacoes) -> dict:
    """Conteúdo da ata (CA-02 do RBN09.14): TCC, autor, banca, data, local, notas e resultado, parecer e
    correções exigidas. `membros` são os participantes da sessão com a presença; `notas` são (membro, nota)
    das avaliações enviadas; `retificacoes` são pares (versão anterior, versão nova) do resultado, em ordem."""
    abertura = (
        f"Aos {_por_extenso(defesa.data)}, das {_hora(defesa.inicio)} às {_hora(defesa.fim)}, realizou-se, de forma "
        f"{NOME_FORMATO[defesa.formato]}, em {_onde(defesa)}, a sessão pública de defesa do Trabalho de Conclusão "
        f"de Curso ({tcc.etapa}, modalidade {NOME_MODALIDADE.get(tcc.modalidade, tcc.modalidade.lower())}) "
        f"intitulado {_negrito(tcc.titulo)}, de autoria de {_negrito(tcc.aluno.usuario.nome)}, do curso de "
        f"{_negrito(tcc.aluno.curso.nome)}, vinculado à EST - Escola Superior de Tecnologia, perante a banca "
        "examinadora abaixo."
    )
    correcoes = ("As correções exigidas pela banca e o prazo para a entrega da versão final são registrados no SIGA "
                 "UEA, na etapa de correções do TCC." if resultado.resultado == "APROVADO_COM_CORRECOES"
                 else "Não se aplica.")
    retificadas = [
        f"Resultado {NOME_RESULTADO[antes.resultado].lower()} retificado para "
        f"{NOME_RESULTADO[depois.resultado].lower()} em "
        f"{(depois.confirmado_em + FUSO_MANAUS).strftime('%d/%m/%Y')} por {depois.autor.nome}. "
        f"Motivo: {depois.motivo_retificacao}"
        for antes, depois in retificacoes
    ]
    return {
        "titulo": "ATA DE DEFESA DE TRABALHO DE CONCLUSÃO DE CURSO",
        "abertura": abertura,
        "banca": [[m.usuario.nome, _papel(m), _instituicao(m), "Presente" if m.presente else "Ausente"]
                  for m in membros],
        "notas": [[m.usuario.nome, _papel(m), _nota(n)] for m, n in notas],
        "media": _nota(resultado.media),
        "nota_final": _nota(resultado.nota_final),
        "regra_qualis": resultado.regra_qualis,
        "resultado": NOME_RESULTADO[resultado.resultado],
        "parecer": resultado.parecer,
        "correcoes": correcoes,
        "retificacoes": retificadas,
        "assinaturas": [f"{m.usuario.nome} - {_papel(m)}" for m in membros if m.presente],
        "versao_resultado": resultado.versao,
    }


def ata_defesa(conteudo: dict, *, numero: int, versao: int, gerado_em: datetime) -> bytes:
    pdf = _pdf("Ata de defesa de TCC")
    _titulo(pdf, conteudo["titulo"])
    _paragrafo(pdf, conteudo["abertura"])
    _subtitulo(pdf, "Banca examinadora")
    _tabela(pdf, ["Nome", "Papel", "Instituição", "Presença"], conteudo["banca"], [62, 40, 38, 26])
    _subtitulo(pdf, "Notas")
    _tabela(pdf, ["Avaliador(a)", "Papel", "Nota"], conteudo["notas"], [88, 50, 28])
    regra = " (regra de exceção do artigo Qualis A ou B aplicada)" if conteudo["regra_qualis"] else ""
    _paragrafo(pdf, f"Média das notas: {_negrito(conteudo['media'])}. Nota final: "
                    f"{_negrito(conteudo['nota_final'])}{regra}.")
    _paragrafo(pdf, f"Resultado: {_negrito(conteudo['resultado'])}.")
    _subtitulo(pdf, "Parecer da banca")
    _paragrafo(pdf, conteudo["parecer"], markdown=False)
    _subtitulo(pdf, "Correções exigidas")
    _paragrafo(pdf, conteudo["correcoes"])
    if conteudo["retificacoes"]:
        _subtitulo(pdf, "Retificações do resultado")
        for linha in conteudo["retificacoes"]:
            _paragrafo(pdf, linha, 10.5, markdown=False)
    if versao > 1:
        _paragrafo(pdf, f"Esta é a versão {versao} da ata e substitui a versão {versao - 1}.", 10.5)
    _assinaturas(pdf, "Assinaturas da banca", conteudo["assinaturas"])
    return _rodape(pdf, _emissao("Ata", numero, versao, gerado_em))


# ------------------------------------------------------------------- Folha de Aprovação (RBN09.15)


def montar_folha(*, defesa, tcc, membros, resultado) -> dict:
    return {
        "titulo": "FOLHA DE APROVAÇÃO",
        "autor": tcc.aluno.usuario.nome,
        "tcc": tcc.titulo,
        "natureza": (f"Trabalho de Conclusão de Curso ({tcc.etapa}, modalidade "
                     f"{NOME_MODALIDADE.get(tcc.modalidade, tcc.modalidade.lower())}) apresentado ao curso de "
                     f"{tcc.aluno.curso.nome} da Escola Superior de Tecnologia da Universidade do Estado do Amazonas."),
        "aprovado_em": _data(defesa.data),
        "resultado": NOME_RESULTADO[resultado.resultado],
        "banca": [f"{m.usuario.nome} - {_papel(m)} ({_instituicao(m)})" for m in membros if m.presente],
        "versao_resultado": resultado.versao,
    }


def folha_aprovacao(conteudo: dict, *, numero: int, versao: int, gerado_em: datetime) -> bytes:
    pdf = _pdf("Folha de Aprovação")
    pdf.set_font("Times", "B", 13)
    pdf.cell(0, 8, conteudo["autor"].upper(), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.set_font("Times", "B", 14)
    pdf.multi_cell(0, 7, conteudo["tcc"], align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.set_x(pdf.w / 2)
    pdf.set_font("Times", "", 10.5)
    pdf.multi_cell(pdf.w / 2 - 22, 5.5, conteudo["natureza"], align="J", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    _titulo(pdf, conteudo["titulo"], 13)
    pdf.set_font("Times", "", 11.5)
    pdf.cell(0, 6, f"Aprovado em {conteudo['aprovado_em']}. Resultado: {conteudo['resultado']}.", align="C",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    _assinaturas(pdf, "BANCA EXAMINADORA", conteudo["banca"])
    if versao > 1:
        pdf.ln(4)
        _paragrafo(pdf, f"Esta é a versão {versao} da folha e substitui a versão {versao - 1}.", 10)
    return _rodape(pdf, _emissao("Folha de Aprovação", numero, versao, gerado_em))


# ------------------------------------------------------------------- certificado de participação (RBN09.17)


def montar_certificado(*, defesa, tcc, membro) -> dict:
    papel = _papel(membro).lower()
    texto = (
        f"Certificamos que {_negrito(membro.usuario.nome)} participou como {_negrito(papel)} da banca examinadora "
        f"da sessão pública de defesa do Trabalho de Conclusão de Curso ({tcc.etapa}) intitulado "
        f"{_negrito(tcc.titulo)}, de autoria de {_negrito(tcc.aluno.usuario.nome)}, do curso de "
        f"{_negrito(tcc.aluno.curso.nome)} da EST - Escola Superior de Tecnologia, realizada de forma "
        f"{NOME_FORMATO[defesa.formato]} em {_negrito(_data(defesa.data))}, das {_hora(defesa.inicio)} às "
        f"{_hora(defesa.fim)}."
    )
    return {"titulo": "CERTIFICADO", "texto": texto, "participante": membro.usuario.nome, "papel": papel}


def certificado_participacao(conteudo: dict, *, numero: int, gerado_em: datetime) -> bytes:
    pdf = _pdf("Certificado de participação em banca", paisagem=True)
    pdf.ln(4)
    _titulo(pdf, conteudo["titulo"], 24)
    pdf.set_left_margin(35)
    pdf.set_right_margin(35)
    pdf.set_x(35)
    _paragrafo(pdf, conteudo["texto"], 14)
    pdf.set_left_margin(22)
    pdf.set_right_margin(22)
    return _rodape(pdf, _emissao("Certificado", numero, 1, gerado_em, "emitido"))


# =================================================================== relatórios para distribuição (RBN13.06 e RBN14.03)
# Não são documentos oficiais: não ficam gravados nem numerados. Saem na hora, com os filtros da tela, quem gerou e
# quando. O texto vem do banco e pode ter caracteres fora do Latin-1 das fontes padrão do PDF; `_latin` troca os
# comuns (aspas e travessões) e põe "?" no resto, em vez de falhar.

_TROCAS = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-", "…": "...", "•": "-",
                         " ": " "})


def _latin(texto) -> str:
    return str(texto).translate(_TROCAS).encode("latin-1", "replace").decode("latin-1")


def _quando(gerado_em: datetime) -> str:
    local = gerado_em + FUSO_MANAUS
    return f"{local.strftime('%d/%m/%Y')} às {local.strftime('%H:%M')} (horário de Manaus)"


def _quadro(pdf: FPDF, cabecalho: list[str], linhas: list[list[str]], larguras: tuple[float, ...],
            tamanho: float = 9.5) -> None:
    """Tabela com quebra de linha nas células e o cabeçalho repetido em cada página."""
    pdf.set_font("Times", "", tamanho)
    pdf.set_draw_color(120, 120, 120)
    with pdf.table(col_widths=larguras, text_align="LEFT", line_height=4.8, padding=1.2,
                   headings_style=_estilo_cabecalho(), first_row_as_headings=True) as tabela:
        tabela.row([_latin(c) for c in cabecalho])
        for linha in linhas:
            tabela.row([_latin(c) for c in linha])
    pdf.ln(4)


def _estilo_cabecalho():
    from fpdf.fonts import FontFace

    return FontFace(family="Times", emphasis="BOLD", fill_color=(230, 230, 230))


def _filtros_usados(pdf: FPDF, linhas: list[tuple[str, str]]) -> None:
    pdf.set_font("Times", "", 10.5)
    for rotulo, valor in linhas:
        pdf.multi_cell(0, 5.4, f"**{_latin(rotulo)}:** {_latin(valor).replace('*', '')}", markdown=True,
                       new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)


def agenda_pdf(itens, *, curso: str | None, de, ate, so_proximas: bool, gerado_por: str,
               gerado_em: datetime) -> bytes:
    """RBN14.03: a agenda filtrada em tabela, em paisagem, para imprimir, afixar no mural ou mandar nos grupos. Só os
    campos que a agenda já divulga (RN08): sem contato, matrícula, nota ou banca."""
    pdf = _pdf("Agenda de apresentações", paisagem=True)
    _titulo(pdf, "AGENDA DE APRESENTAÇÕES DE TCC")
    if de and ate:
        periodo = f"de {_data(de)} a {_data(ate)}"
    elif de:
        periodo = f"a partir de {_data(de)}"
    elif ate:
        periodo = f"de hoje até {_data(ate)}" if so_proximas else f"até {_data(ate)}"
    else:
        periodo = "próximas apresentações, a partir de hoje" if so_proximas else "todas as apresentações publicadas"
    _filtros_usados(pdf, [("Curso", curso or "todos os cursos"), ("Período", periodo),
                          ("Gerada por", f"{gerado_por}, em {_quando(gerado_em)}")])
    if not itens:
        _paragrafo(pdf, "Nenhuma apresentação programada para os filtros escolhidos.", markdown=False)
    else:
        linhas = []
        for a in itens:
            onde = a.local or ("Remota" if a.formato == "REMOTO" else "Local a confirmar")
            if a.link:
                onde = f"{onde} - {a.link}" if a.local else a.link
            situacao = " (remarcada)" if a.remarcada else ""
            linhas.append([_data(a.data), f"{_hora(a.inicio)} às {_hora(a.fim)}{situacao}", a.titulo, a.autor,
                           a.orientador or "-", a.curso.sigla, NOME_FORMATO[a.formato].capitalize(), onde])
        _quadro(pdf, ["Data", "Horário", "Título", "Autor(a)", "Orientador(a)", "Curso", "Formato", "Local ou link"],
                linhas, (20, 27, 68, 32, 32, 13, 19, 42))
    return _rodape(pdf, [EMISSOR, "Agenda emitida pelo SIGA UEA para divulgação. Traz só o que a agenda do sistema "
                                  "divulga, sem contatos, matrículas ou notas; mudanças posteriores aparecem no sistema."])


def indicadores_pdf(secoes, *, filtros: list[tuple[str, str]], gerado_por: str, gerado_em: datetime) -> bytes:
    """RBN13.06: as tabelas dos indicadores (RBN13.02 a 13.05) com os filtros da tela. `secoes` é uma lista de
    (título, cabeçalho, linhas, larguras, observação). Nenhuma tabela traz nome de aluno (RN18)."""
    pdf = _pdf("Relatório de indicadores")
    _titulo(pdf, "RELATÓRIO DE INDICADORES DE TCC")
    _filtros_usados(pdf, [*filtros, ("Gerado por", f"{gerado_por}, em {_quando(gerado_em)}")])
    for titulo, cabecalho, linhas, larguras, observacao in secoes:
        if pdf.get_y() > pdf.h - 80:
            pdf.add_page()
        _subtitulo(pdf, _latin(titulo))
        if observacao:
            pdf.set_font("Times", "I", 9.5)
            pdf.multi_cell(0, 4.8, _latin(observacao), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        if linhas:
            _quadro(pdf, cabecalho, linhas, larguras, 10)
        else:
            _paragrafo(pdf, "Sem dados para os filtros escolhidos.", 10.5, markdown=False)
    return _rodape(pdf, [EMISSOR, "Relatório gerado pelo SIGA UEA com os filtros da tela de indicadores. Cada TCC é "
                                  "contado uma vez e nenhum dado identifica aluno."])
