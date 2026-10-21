"""Monta documentos no formato dos documentos do grupo (Plano de Integração, Plano de Configuração).

O conteúdo é descrito uma vez, como uma lista de blocos, e sai em dois formatos:
  .docx  a partir do modelo do grupo (estilos, margens e rodapé com número de página herdados)
  .pdf   pelo Chrome, com as mesmas medidas (A4, margens 3/2 cm, Arial, cabeçalho preto nas tabelas)

O sumário do PDF tem número de página: o PDF é gerado duas vezes, e a segunda já usa as páginas
encontradas na primeira. O .docx leva um campo de sumário com essas páginas e se atualiza no Word.

Dependências: python-docx, pypdf e o playwright-core do projeto (npm i --no-save playwright-core@1.48.2).
"""

from __future__ import annotations

import base64
import copy
import html
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

AQUI = Path(__file__).resolve().parent
MODELO = AQUI / "modelo-documento-siga.docx"  # cópia do Plano de Integração v1.6, só com estilos e rodapé
EQUIPE = ("Davih Taumaturgo Soares, Igor Leite de Almeida, Igor Meireles de Lima Taveira, "
          "Matheus Maia Braga e Samuel Ogino Barbosa.")


@dataclass
class Doc:
    titulo: str
    identificacao: list[tuple[str, str]]
    blocos: list[tuple] = field(default_factory=list)

    # ---------------------------------------------------------- blocos
    def h1(self, texto):
        self.blocos.append(("h1", texto))

    def h2(self, texto):
        self.blocos.append(("h2", texto))

    def h3(self, texto):
        self.blocos.append(("h3", texto))

    def p(self, texto):
        """Parágrafo justificado; **negrito** e `código` são aceitos."""
        self.blocos.append(("p", texto))

    def lista(self, itens, numerada=True):
        self.blocos.append(("lista", list(itens), numerada))

    def tabela(self, cabecalho, linhas, larguras=None, rotulo=False):
        """rotulo=True: tabela de duas colunas com a 1ª em cinza (como a de identificação)."""
        self.blocos.append(("tabela", list(cabecalho) if cabecalho else None, [list(l) for l in linhas],
                            larguras, rotulo))

    def figura(self, caminho, legenda, largura_cm=16):
        self.blocos.append(("figura", Path(caminho), legenda, largura_cm))

    def quebra(self):
        self.blocos.append(("quebra",))

    def titulos(self):
        return [(b[0], b[1]) for b in self.blocos if b[0] in ("h1", "h2")]


# ================================================================ texto com marcação simples
_MARCA = re.compile(r"(\*\*[^*]+\*\*|`[^`]+`)")


def _pedacos(texto):
    for parte in _MARCA.split(texto):
        if not parte:
            continue
        if parte.startswith("**"):
            yield parte[2:-2], True, False
        elif parte.startswith("`"):
            yield parte[1:-1], False, True
        else:
            yield parte, False, False


def _html_inline(texto):
    out = []
    for t, negrito, codigo in _pedacos(texto):
        t = html.escape(t)
        out.append(f"<b>{t}</b>" if negrito else f"<code>{t}</code>" if codigo else t)
    return "".join(out)


# ================================================================ .docx
def _run(par, texto, tam=11, negrito=False, cor="000000", fonte="Arial"):
    r = par.add_run(texto)
    r.font.name = fonte
    r._element.rPr.rFonts.set(qn("w:eastAsia"), fonte)
    r._element.rPr.rFonts.set(qn("w:cs"), fonte)
    r.font.size = Pt(tam)
    r.font.bold = negrito
    r.font.color.rgb = RGBColor.from_string(cor)
    return r


def _runs(par, texto, tam=11, cor="000000"):
    for t, negrito, codigo in _pedacos(texto):
        _run(par, t, tam=tam - (0.5 if codigo else 0), negrito=negrito, cor=cor,
             fonte="Consolas" if codigo else "Arial")


def _espaco(par, antes=0, depois=120, linha=None, alinhamento=None):
    f = par.paragraph_format
    f.space_before = Pt(antes / 20)
    f.space_after = Pt(depois / 20)
    if linha:
        f.line_spacing = linha / 240
    if alinhamento:
        f.alignment = alinhamento


def _bordas(tabela):
    tblPr = tabela._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{lado}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "6")
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), "000000")
        b.append(e)
    tblPr.append(b)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)


def _celula(cel, texto, cabecalho=False, rotulo=False, largura=None):
    tcPr = cel._tc.get_or_add_tcPr()
    if cabecalho or rotulo:
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:fill"), "000000" if cabecalho else "EDEDED")
        tcPr.append(shd)
    mar = OxmlElement("w:tcMar")
    for lado, v in (("top", 60), ("left", 100), ("bottom", 60), ("right", 100)):
        e = OxmlElement(f"w:{lado}")
        e.set(qn("w:w"), str(v))
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    tcPr.append(mar)
    if largura:
        cel.width = largura
    linhas = str(texto).split("\n")
    par = cel.paragraphs[0]
    for i, ln in enumerate(linhas):
        if i:
            par = cel.add_paragraph()
        _espaco(par, 0, 40, 260, WD_ALIGN_PARAGRAPH.LEFT)
        if cabecalho:
            _run(par, ln, 10, True, "FFFFFF")
        elif rotulo:
            _run(par, ln, 10, True)
        else:
            _runs(par, ln, 10)


def _linha_cabecalho(linha, repetir=True, nao_quebrar=True):
    trPr = linha._tr.get_or_add_trPr()
    if repetir:
        e = OxmlElement("w:tblHeader")
        e.set(qn("w:val"), "1")
        trPr.append(e)
    if nao_quebrar:
        e = OxmlElement("w:cantSplit")
        e.set(qn("w:val"), "1")
        trPr.append(e)


def _campo_sumario(doc, entradas):
    """Campo TOC do Word com as entradas já preenchidas (páginas do PDF); o Word atualiza ao abrir."""
    def fld(par, tipo, instr=None):
        r = OxmlElement("w:r")
        if instr is None:
            f = OxmlElement("w:fldChar")
            f.set(qn("w:fldCharType"), tipo)
            r.append(f)
        else:
            t = OxmlElement("w:instrText")
            t.set(qn("xml:space"), "preserve")
            t.text = instr
            r.append(t)
        par._p.append(r)

    primeiro = True
    for nivel, texto, pagina in entradas:
        par = doc.add_paragraph()
        _espaco(par, 0, 60, 260)
        par.paragraph_format.left_indent = Cm(0 if nivel == "h1" else 0.6)
        par.paragraph_format.tab_stops.add_tab_stop(Cm(16), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        if primeiro:
            fld(par, "begin")
            fld(par, None, ' TOC \\o "1-2" \\h \\z \\u ')
            fld(par, "separate")
            primeiro = False
        _run(par, f"{texto}\t{pagina}", 11, nivel == "h1")
    fim = doc.add_paragraph()
    fld(fim, "end")


def gerar_docx(d: Doc, saida: Path, paginas: dict[str, int]):
    doc = Document(MODELO)
    corpo = doc.element.body
    for el in list(corpo):
        if el.tag != qn("w:sectPr"):
            corpo.remove(el)
    s = doc.sections[0]
    s.top_margin, s.left_margin, s.bottom_margin, s.right_margin = Cm(3), Cm(3), Cm(2), Cm(2)
    # o Word pergunta se quer atualizar o sumário (números de página) ao abrir
    upd = OxmlElement("w:updateFields")
    upd.set(qn("w:val"), "true")
    doc.settings.element.append(upd)

    t = doc.add_paragraph(style="Title")
    _espaco(t, 1200, 480, None, WD_ALIGN_PARAGRAPH.CENTER)
    _run(t, d.titulo, 18, True)
    tab = doc.add_table(rows=0, cols=2)
    _bordas(tab)
    for k, v in d.identificacao:
        cel = tab.add_row().cells
        _celula(cel[0], k, rotulo=True, largura=Cm(5))
        _celula(cel[1], v, largura=Cm(11))
        _linha_cabecalho(tab.rows[-1], repetir=False)
    doc.add_paragraph().add_run().add_break(_quebra_pagina())
    sp = doc.add_paragraph()
    _espaco(sp, 0, 200)
    _run(sp, "SUMÁRIO", 15, True)
    _campo_sumario(doc, [(n, tx, paginas.get(tx, "")) for n, tx in d.titulos()])
    doc.add_paragraph().add_run().add_break(_quebra_pagina())

    for b in d.blocos:
        tipo = b[0]
        if tipo in ("h1", "h2", "h3"):
            par = doc.add_paragraph(style={"h1": "Heading 1", "h2": "Heading 2", "h3": "Heading 3"}[tipo])
            antes, depois, tam = {"h1": (360, 200, 15), "h2": (280, 140, 13), "h3": (220, 100, 11.5)}[tipo]
            _espaco(par, antes, depois)
            par.paragraph_format.keep_with_next = True
            _runs(par, b[1], tam) if tipo == "h3" else _run(par, b[1], tam, True)
            if tipo == "h3":
                for r in par.runs:
                    r.font.bold = True
        elif tipo == "p":
            par = doc.add_paragraph()
            _espaco(par, 0, 120, 276, WD_ALIGN_PARAGRAPH.JUSTIFY)
            _runs(par, b[1])
        elif tipo == "lista":
            for i, item in enumerate(b[1], start=1):
                par = doc.add_paragraph()
                _espaco(par, 0, 80, 276, WD_ALIGN_PARAGRAPH.JUSTIFY)
                par.paragraph_format.left_indent = Cm(0.9)
                par.paragraph_format.first_line_indent = Cm(-0.6)
                _run(par, f"{i}.\t" if b[2] else "•\t")
                par.paragraph_format.tab_stops.add_tab_stop(Cm(0.9))
                _runs(par, item)
        elif tipo == "tabela":
            _, cab, linhas, larguras, rotulo = b
            ncol = len(cab) if cab else len(linhas[0])
            larg = [Cm(x) for x in (larguras or [16 / ncol] * ncol)]
            tab = doc.add_table(rows=0, cols=ncol)
            _bordas(tab)
            if cab:
                cel = tab.add_row().cells
                for j, txt in enumerate(cab):
                    _celula(cel[j], txt, cabecalho=True, largura=larg[j])
                _linha_cabecalho(tab.rows[-1])
            for l in linhas:
                cel = tab.add_row().cells
                for j, txt in enumerate(l):
                    _celula(cel[j], txt, rotulo=rotulo and j == 0, largura=larg[j])
                _linha_cabecalho(tab.rows[-1], repetir=False)
            esp = doc.add_paragraph()
            _espaco(esp, 0, 60)
        elif tipo == "figura":
            _, caminho, legenda, largura = b
            par = doc.add_paragraph()
            _espaco(par, 120, 60, None, WD_ALIGN_PARAGRAPH.CENTER)
            par.add_run().add_picture(str(caminho), width=Cm(largura))
            leg = doc.add_paragraph()
            _espaco(leg, 0, 160, None, WD_ALIGN_PARAGRAPH.CENTER)
            _run(leg, legenda, 9)
        elif tipo == "quebra":
            doc.add_paragraph().add_run().add_break(_quebra_pagina())
    doc.save(saida)


def _quebra_pagina():
    from docx.enum.text import WD_BREAK
    return WD_BREAK.PAGE


# ================================================================ HTML e PDF
CSS = """
@page{size:A4;margin:30mm 20mm 20mm 30mm}
body{font-family:Arial,Helvetica,sans-serif;font-size:11pt;color:#000;margin:0}
.titulo{font-size:18pt;font-weight:bold;text-align:center;margin:60pt 0 24pt}
h1{font-size:15pt;font-weight:bold;margin:18pt 0 10pt;page-break-after:avoid}
h2{font-size:13pt;font-weight:bold;margin:14pt 0 7pt;page-break-after:avoid}
h3{font-size:11.5pt;font-weight:bold;margin:11pt 0 5pt;page-break-after:avoid}
p{text-align:justify;line-height:1.15;margin:0 0 6pt}
ol,ul{margin:0 0 6pt 0;padding-left:0.9cm} li{text-align:justify;line-height:1.15;margin:0 0 4pt}
table{border-collapse:collapse;width:16cm;margin:0 0 9pt;font-size:10pt;table-layout:fixed}
th,td{border:0.75pt solid #000;padding:3pt 5pt;text-align:left;vertical-align:top;line-height:1.08;word-wrap:break-word}
th{background:#000;color:#fff;font-weight:bold} thead{display:table-header-group} tr{page-break-inside:avoid}
td.rotulo{background:#ededed;font-weight:bold}
code{font-family:Consolas,monospace;font-size:9.5pt}
.sumario{font-size:15pt;font-weight:bold;margin:0 0 10pt}
.toc{display:flex;font-size:11pt;margin:0 0 3pt}.toc .t{flex:none}.toc .pt{flex:1;border-bottom:1px dotted #000;margin:0 4pt 4pt}
.toc.n2{padding-left:0.6cm;font-weight:normal}.toc.n1{font-weight:bold}
.figura{text-align:center;margin:6pt 0 3pt}.figura img{max-width:16cm}.legenda{text-align:center;font-size:9pt;margin:0 0 8pt}
.quebra{page-break-after:always}
"""


def gerar_html(d: Doc, paginas: dict[str, int]) -> str:
    out = [f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>{html.escape(d.titulo)}</title>'
           f"<style>{CSS}</style></head><body>",
           f'<div class="titulo">{html.escape(d.titulo)}</div><table>'
           + "".join(f'<tr><td class="rotulo" style="width:5cm">{html.escape(k)}</td><td>{_html_inline(v)}</td></tr>'
                     for k, v in d.identificacao) + '</table><div class="quebra"></div>',
           '<div class="sumario">SUMÁRIO</div>']
    for nivel, tx in d.titulos():
        out.append(f'<div class="toc {"n1" if nivel == "h1" else "n2"}"><span class="t">{html.escape(tx)}</span>'
                   f'<span class="pt"></span><span>{paginas.get(tx, "")}</span></div>')
    out.append('<div class="quebra"></div>')
    for b in d.blocos:
        tipo = b[0]
        if tipo in ("h1", "h2", "h3"):
            out.append(f"<{tipo}>{_html_inline(b[1])}</{tipo}>")
        elif tipo == "p":
            out.append(f"<p>{_html_inline(b[1])}</p>")
        elif tipo == "lista":
            tag = "ol" if b[2] else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{_html_inline(i)}</li>" for i in b[1]) + f"</{tag}>")
        elif tipo == "tabela":
            _, cab, linhas, larguras, rotulo = b
            cols = "".join(f'<col style="width:{w}cm">' for w in larguras) if larguras else ""
            t = f"<table><colgroup>{cols}</colgroup>"
            if cab:
                t += "<thead><tr>" + "".join(f"<th>{html.escape(c)}</th>" for c in cab) + "</tr></thead>"
            t += "<tbody>" + "".join(
                "<tr>" + "".join(
                    f'<td{" class=rotulo" if rotulo and j == 0 else ""}>'
                    + "<br>".join(_html_inline(x) for x in str(c).split("\n")) + "</td>"
                    for j, c in enumerate(l)) + "</tr>" for l in linhas) + "</tbody></table>"
            out.append(t)
        elif tipo == "figura":
            _, caminho, legenda, largura = b
            dados = base64.b64encode(caminho.read_bytes()).decode()
            out.append(f'<div class="figura"><img style="width:{largura}cm" src="data:image/png;base64,{dados}"></div>'
                       f'<div class="legenda">{html.escape(legenda)}</div>')
        elif tipo == "quebra":
            out.append('<div class="quebra"></div>')
    out.append("</body></html>")
    return "".join(out)


def _pdf(html_txt: str, saida: Path):
    with tempfile.TemporaryDirectory() as tmp:
        arq = Path(tmp) / "doc.html"
        arq.write_text(html_txt, encoding="utf8")
        script = AQUI / "html_para_pdf.mjs"
        r = subprocess.run(["node", str(script), str(arq), "--siga"], capture_output=True, text=True,
                           cwd=AQUI.parent.parent)
        if r.returncode:
            raise SystemExit(r.stderr)
        (Path(tmp) / "doc.pdf").replace(saida)


def _paginas_dos_titulos(pdf: Path, d: Doc) -> dict[str, int]:
    from pypdf import PdfReader

    textos = [re.sub(r"\s+", " ", pg.extract_text() or "") for pg in PdfReader(str(pdf)).pages]
    achadas, inicio = {}, 2  # o sumário fica nas primeiras páginas; procura depois dele
    for _, tx in d.titulos():
        alvo = re.sub(r"\s+", " ", tx)
        for i in range(inicio, len(textos)):
            if alvo in textos[i]:
                achadas[tx] = i + 1
                inicio = i
                break
    return achadas


def gerar(d: Doc, base: Path):
    """Gera base.docx e base.pdf. Devolve o número de páginas do PDF."""
    from pypdf import PdfReader

    pdf = base.with_suffix(".pdf")
    _pdf(gerar_html(d, {tx: "00" for _, tx in d.titulos()}), pdf)
    paginas = _paginas_dos_titulos(pdf, d)
    _pdf(gerar_html(d, paginas), pdf)
    gerar_docx(d, base.with_suffix(".docx"), paginas)
    faltando = [tx for _, tx in d.titulos() if tx not in paginas]
    return len(PdfReader(str(pdf)).pages), faltando
