"""Diagramas de robustez e de sequência do SIGA UEA (FL01 a FL11), gerados de fluxos_sequencia.py.

Cada diagrama de sequência segue a ordem em que o usuário age no sistema: a tela em que
ele está, o que ele clica, as chamadas que a tela faz à API e o que a API consulta e grava.
Os fluxos já implementados foram conferidos percorrendo o site (roteiro em fluxos_sequencia.py);
os ainda não implementados seguem as telas do protótipo.

Gera docs/modelagem/diagramas-sequencia-siga-uea.drawio, com, para cada fluxo, a página de
robustez e as de sequência, e no fim as páginas do diagrama de classes (diagrama_classes.py):

    npm i --no-save elkjs@0.9.3      (para as páginas de classes)
    python docs/modelagem/diagramas_sequencia.py
"""

from __future__ import annotations

import html
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import quoteattr

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

# ---------------------------------------------------------------- modelo dos diagramas


@dataclass
class Part:
    """Participante: ator, tela (fronteira), controle, entidade, interface (fronteira de sistema) ou externo."""

    chave: str
    tipo: str
    nome: str
    sub: str = ""  # segunda linha (rota da tela, papel)


@dataclass
class Msg:
    de: str
    para: str
    texto: str
    tipo: str = "sync"  # sync, ret, async, self


@dataclass
class Nota:
    texto: str
    de: str | None = None
    ate: str | None = None


@dataclass
class Frag:
    tipo: str  # alt, opt, loop, par
    secoes: list[tuple[str, list]]


@dataclass
class Ref:
    texto: str
    de: str
    ate: str


@dataclass
class Diagrama:
    id: str  # DS-FL01-A
    titulo: str
    requisitos: str
    caminho: str  # a sequência de telas e cliques, como o usuário vê
    participantes: list[str]
    passos: list
    fonte: str = "sistema"  # sistema (conferido no site), prototipo ou previsto (sem tela em nenhum dos dois)


@dataclass
class Fluxo:
    id: str  # FL01
    titulo: str
    requisitos: str
    diagramas: list[Diagrama]
    situacao: str = ""  # nota da página de robustez


# atalhos usados em fluxos_sequencia.py
def acao(ator, tela, texto):
    return Msg(ator, tela, texto)


def chama(de, para, texto):
    return Msg(de, para, texto)


def volta(de, para, texto=""):
    return Msg(de, para, texto, "ret")


def proprio(quem, texto):
    return Msg(quem, quem, texto, "self")


def assinc(de, para, texto):
    return Msg(de, para, texto, "async")


def alt(*secoes):
    return Frag("alt", list(secoes))


def opt(guarda, passos):
    return Frag("opt", [(guarda, passos)])


def loop(guarda, passos):
    return Frag("loop", [(guarda, passos)])


def ref(texto, de, ate):
    return Ref(texto, de, ate)


def nota(texto, de=None, ate=None):
    return Nota(texto, de, ate)


# ---------------------------------------------------------------- medidas
CW = 6.3  # largura média de um caractere (Helvetica 11)
LH = 14  # altura de linha
QUEBRA = 44  # caracteres por linha nos textos das mensagens
TOPO_ICONE = 150
ALT_ICONE = 44
INICIO = TOPO_ICONE + ALT_ICONE + 46  # primeira mensagem

ESTILO_PART = {
    "ator": "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;fillColor=#ffffff;strokeColor=#333333;strokeWidth=1.6;",
    "externo": "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;fillColor=#f5f5f5;strokeColor=#777777;strokeWidth=1.6;",
    "tela": "shape=umlBoundary;verticalLabelPosition=bottom;verticalAlign=top;html=1;fillColor=#dae8fc;strokeColor=#4a6fa5;strokeWidth=1.6;",
    "interface": "shape=umlBoundary;verticalLabelPosition=bottom;verticalAlign=top;html=1;fillColor=#f5f5f5;strokeColor=#777777;strokeWidth=1.6;",
    "controle": "shape=umlControl;verticalLabelPosition=bottom;verticalAlign=top;html=1;fillColor=#d5e8d4;strokeColor=#5b8f3e;strokeWidth=1.6;",
    "entidade": "shape=umlEntity;verticalLabelPosition=bottom;verticalAlign=top;html=1;fillColor=#fff2cc;strokeColor=#b8962e;strokeWidth=1.6;",
}
LARG_ICONE = {"ator": 30, "externo": 30, "tela": 50, "interface": 50, "controle": 40, "entidade": 40}


def quebrar(texto: str, n: int = QUEBRA) -> list[str]:
    linhas = []
    for bloco in texto.split("\n"):
        atual = ""
        for palavra in bloco.split(" "):
            if atual and len(atual) + 1 + len(palavra) > n:
                linhas.append(atual)
                atual = palavra
            else:
                atual = f"{atual} {palavra}" if atual else palavra
        linhas.append(atual)
    return linhas


def largura_texto(linhas: list[str]) -> float:
    return max((len(ln) for ln in linhas), default=0) * CW + 12


def texto_html(linhas: list[str]) -> str:
    return "<br>".join(html.escape(ln) for ln in linhas)


# ---------------------------------------------------------------- numeração e varredura
def mensagens(passos):
    for p in passos:
        if isinstance(p, Msg):
            yield p
        elif isinstance(p, Frag):
            for _, sub in p.secoes:
                yield from mensagens(sub)


def numerar(passos, n=None):
    """Numera as mensagens que não são retorno, na ordem em que acontecem."""
    n = n if n is not None else [0]
    for p in passos:
        if isinstance(p, Msg) and p.tipo != "ret" and not re.match(r"^\d+: ", p.texto):
            n[0] += 1
            p.texto = f"{n[0]}: {p.texto}"
        elif isinstance(p, Frag):
            for _, sub in p.secoes:
                numerar(sub, n)


def usados(passos) -> set[str]:
    s = set()
    for p in passos:
        if isinstance(p, Msg):
            s |= {p.de, p.para}
        elif isinstance(p, Frag):
            for _, sub in p.secoes:
                s |= usados(sub)
        elif isinstance(p, Ref):
            s |= {p.de, p.ate}
        elif isinstance(p, Nota) and p.de:
            s |= {p.de, p.ate or p.de}
    return s


# ---------------------------------------------------------------- desenho de uma página de sequência
class Pagina:
    def __init__(self, pid: str):
        self.pid = pid
        self.cells: list[str] = []
        self.k = 0

    def novo_id(self) -> str:
        self.k += 1
        return f"{self.pid}-{self.k}"

    def caixa(self, x, y, w, h, valor, estilo, pai="1") -> str:
        cid = self.novo_id()
        self.cells.append(
            f'<mxCell id="{cid}" value={quoteattr(valor)} style="{estilo}" vertex="1" parent="{pai}">'
            f'<mxGeometry x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" as="geometry"/></mxCell>'
        )
        return cid

    def linha(self, pontos, estilo, valor="", origem=None, destino=None) -> str:
        cid = self.novo_id()
        (x1, y1), (x2, y2) = pontos[0], pontos[-1]
        meio = "".join(f'<mxPoint x="{x:.0f}" y="{y:.0f}"/>' for x, y in pontos[1:-1])
        liga = (f' source="{origem}"' if origem else "") + (f' target="{destino}"' if destino else "")
        self.cells.append(
            f'<mxCell id="{cid}" value={quoteattr(valor)} style="{estilo}" edge="1" parent="1"{liga}>'
            f'<mxGeometry relative="1" as="geometry"><mxPoint x="{x1:.0f}" y="{y1:.0f}" as="sourcePoint"/>'
            f'<mxPoint x="{x2:.0f}" y="{y2:.0f}" as="targetPoint"/>'
            + (f'<Array as="points">{meio}</Array>' if meio else "")
            + "</mxGeometry></mxCell>"
        )
        return cid


ROTULO = ("text;html=1;align=center;verticalAlign=top;fontFamily=Helvetica;fontSize=11;fontColor=#111111;"
          "whiteSpace=nowrap;labelBackgroundColor=#ffffff;spacing=0;")


def colunas(d: Diagrama, partes: dict[str, Part]) -> dict[str, float]:
    """x de cada linha de vida: afasta as colunas até o texto de cada mensagem caber entre elas."""
    ordem = d.participantes
    idx = {k: i for i, k in enumerate(ordem)}
    larg = [max(largura_texto(quebrar(partes[k].nome, 22) + quebrar(partes[k].sub, 26)), 90) for k in ordem]
    gaps = [max(60.0, (larg[i] + larg[i + 1]) / 2 + 24) for i in range(len(ordem) - 1)]
    pedidos = []
    for m in mensagens(d.passos):
        w = largura_texto(quebrar(m.texto)) + 24
        a, b = idx[m.de], idx[m.para]
        if a == b:
            if a < len(gaps):
                pedidos.append((a, a + 1, w + 50))
        else:
            pedidos.append((min(a, b), max(a, b), w))
    for a, b, w in sorted(pedidos, key=lambda p: p[1] - p[0]):
        falta = w - sum(gaps[a:b])
        if falta > 0:
            for i in range(a, b):
                gaps[i] += falta / (b - a)
    x, xs = 70 + larg[0] / 2, {}
    for i, k in enumerate(ordem):
        xs[k] = x
        if i < len(gaps):
            x += gaps[i]
    return xs


def desenhar_sequencia(d: Diagrama, partes: dict[str, Part], pid: str) -> tuple[str, int, int]:
    numerar(d.passos)
    faltam = usados(d.passos) - set(d.participantes)
    assert not faltam, f"{d.id}: participantes fora da lista: {faltam}"
    xs = colunas(d, partes)
    pg = Pagina(pid)
    direita = max(xs.values()) + 140

    # cabeçalho: título, requisitos, o caminho nas telas e de onde veio a sequência
    pg.caixa(24, 14, 1400, 24, html.escape(f"{d.id} – {d.titulo}"),
             "text;html=1;align=left;verticalAlign=top;fontSize=16;fontStyle=1;fontFamily=Helvetica;")
    pg.caixa(24, 40, 1400, 18, html.escape(d.requisitos),
             "text;html=1;align=left;verticalAlign=top;fontSize=11;fontColor=#555555;fontFamily=Helvetica;")
    origem, cor = {
        "sistema": ("Sequência conferida no sistema: mesma ordem de telas, cliques e chamadas à API.", "#2e7d32"),
        "prototipo": ("Ainda não implementado: sequência das telas do protótipo (docs/prototipos).", "#b26a00"),
        "previsto": ("Ainda não implementado e sem tela no protótipo: sequência prevista pela análise.", "#b3261e"),
    }[d.fonte]
    linhas_cam = quebrar(d.caminho, 150)
    cam = (f"<b>Caminho na tela:</b> {texto_html(linhas_cam)}<br>"
           f'<font color="{cor}">{html.escape(origem)}</font>')
    alt_cam = (len(linhas_cam) + 1) * LH + 14
    pg.caixa(24, 64, max(direita - 24, 980), alt_cam, cam,
             "rounded=1;arcSize=6;html=1;align=left;verticalAlign=top;spacingLeft=8;spacingTop=4;fontSize=11;"
             "fontFamily=Helvetica;fillColor=#f7f9fc;strokeColor=#9fb3cf;whiteSpace=wrap;")
    topo = 64 + alt_cam + 30

    # participantes e linhas de vida
    for k in d.participantes:
        p = partes[k]
        w = LARG_ICONE[p.tipo]
        rot = f"<b>{html.escape(p.nome)}</b>" + (
            f'<br><font style="font-size:10px" color="#555555">{html.escape(p.sub)}</font>' if p.sub else "")
        pg.caixa(xs[k] - w / 2, topo, w, ALT_ICONE, rot, ESTILO_PART[p.tipo] + "fontSize=11;fontFamily=Helvetica;")
    y = topo + ALT_ICONE + 46 + (14 if any(partes[k].sub for k in d.participantes) else 0)

    ativas: dict[str, list[float]] = {}  # barras de ativação abertas: participante -> [início, fim]
    barras: list[tuple[str, float, float]] = []

    def toca(k, yy):
        if partes[k].tipo in ("ator", "externo"):
            return
        if k in ativas:
            ativas[k][1] = max(ativas[k][1], yy)
        else:
            ativas[k] = [yy, yy]

    def fecha(chaves=None):
        for k in list(ativas):
            if chaves is None or k in chaves:
                ini, fim = ativas.pop(k)
                barras.append((k, ini - 4, max(fim + 6, ini + 16)))

    def msg(m: Msg, yy: float) -> float:
        linhas = quebrar(m.texto)
        h = len(linhas) * LH
        x1, x2 = xs[m.de], xs[m.para]
        if m.tipo == "self":
            ya = yy + 4
            pg.linha([(x1 + 5, ya), (x1 + 42, ya), (x1 + 42, ya + 20), (x1 + 6, ya + 20)],
                     "html=1;endArrow=block;endFill=1;rounded=0;strokeColor=#333333;strokeWidth=1.2;"
                     "labelPosition=right;align=left;verticalAlign=middle;spacingLeft=6;fontSize=11;"
                     "fontFamily=Helvetica;labelBackgroundColor=#ffffff;", texto_html(linhas))
            toca(m.de, ya + 20)
            return yy + max(h, 24) + 18
        ya = yy + h + 4
        if m.tipo == "ret":
            estilo = "dashed=1;endArrow=open;endFill=0;strokeColor=#555555;"
        elif m.tipo == "async":
            estilo = "endArrow=open;endFill=0;strokeColor=#333333;"
        else:
            estilo = "endArrow=block;endFill=1;strokeColor=#333333;"
        dx = 5 if x2 > x1 else -5
        if partes[m.para].tipo in ("ator", "externo"):
            dx2 = 0
        else:
            dx2 = -5 if x2 > x1 else 5
        pg.linha([(x1 + (dx if partes[m.de].tipo not in ("ator", "externo") else 0), ya), (x2 + dx2, ya)],
                 f"html=1;rounded=0;strokeWidth=1.2;{estilo}verticalAlign=bottom;spacingBottom=2;fontSize=11;"
                 "fontFamily=Helvetica;labelBackgroundColor=#ffffff;", texto_html(linhas))
        toca(m.de, ya)
        toca(m.para, ya)
        if m.tipo == "ret" and partes[m.de].tipo == "entidade":
            fecha([m.de])
        return ya + 16

    def limites(passos, extra: tuple[str, ...] = ()) -> tuple[float, float]:
        ks = usados(passos) | set(extra)
        return min(xs[k] for k in ks), max(xs[k] for k in ks)

    def bloco(passos, yy: float, nivel: int) -> float:
        for i, p in enumerate(passos):
            if isinstance(p, Msg):
                if partes[p.de].tipo == "ator" and p.tipo != "ret" and nivel == 0:
                    fecha()  # nova ação do usuário: as ativações do bloco anterior terminam
                    yy += 6
                yy = msg(p, yy)
                seguinte = passos[i + 1] if i + 1 < len(passos) else None
                responde = (isinstance(seguinte, Msg) and seguinte.tipo == "ret" and seguinte.de == p.para)
                if (p.tipo in ("sync", "async") and partes[p.para].tipo in ("entidade", "interface")
                        and not responde):
                    fecha([p.para])  # gravação sem retorno: a entidade fica ativa só durante a chamada
            elif isinstance(p, Nota):
                linhas = quebrar(p.texto, 70)
                w = largura_texto(linhas) + 16
                if p.de:
                    xa, xb = sorted((xs[p.de], xs[p.ate or p.de]))
                    w = max(w, xb - xa + 60)
                    x0 = (xa + xb) / 2 - w / 2
                else:
                    x0 = 80
                h = len(linhas) * LH + 10
                pg.caixa(x0, yy + 4, w, h, texto_html(linhas),
                         "shape=note;size=10;html=1;align=left;verticalAlign=top;spacingLeft=6;spacingTop=2;"
                         "fontSize=11;fontFamily=Helvetica;fillColor=#fffbe6;strokeColor=#d6b656;whiteSpace=wrap;")
                yy += h + 14
            elif isinstance(p, Ref):
                xa, xb = sorted((xs[p.de], xs[p.ate]))
                linhas = quebrar(p.texto, 70)
                h = len(linhas) * LH + 30
                largura = max(xb - xa + 80, largura_texto(linhas) + 70)
                pg.caixa(xa - 40, yy + 4, largura, h, "ref",
                         "shape=umlFrame;whiteSpace=wrap;html=1;width=40;height=20;fontStyle=1;fontSize=11;"
                         "fontFamily=Helvetica;fillColor=#ffffff;strokeColor=#555555;")
                pg.caixa(xa, yy + 18, largura - 80, h - 18, texto_html(linhas),
                         "text;html=1;align=center;verticalAlign=middle;fontSize=11;fontFamily=Helvetica;")
                yy += h + 16
            elif isinstance(p, Frag):
                todos = [q for _, sub in p.secoes for q in sub]
                xa, xb = limites(todos)
                pad = 52 - 10 * nivel
                fx, fw = xa - pad, xb - xa + 2 * pad
                y0 = yy + 4
                guardas = [quebrar(g, 60) for g, _ in p.secoes]
                fw = max(fw, max(largura_texto(g) for g in guardas) + 70)
                yy = y0 + 22
                separadores = []
                for i, ((g, sub), gl) in enumerate(zip(p.secoes, guardas)):
                    if i:
                        separadores.append(yy)
                        yy += 4
                    pg.caixa(fx + (46 if i == 0 else 8), yy - (18 if i == 0 else 0), largura_texto(gl), len(gl) * LH,
                             f"<b>{texto_html(gl)}</b>",
                             "text;html=1;align=left;verticalAlign=top;fontSize=11;fontFamily=Helvetica;"
                             "fontColor=#333333;labelBackgroundColor=#ffffff;")
                    yy += len(gl) * LH - (14 if i == 0 else 0) + 4
                    yy = bloco(sub, yy, nivel + 1)
                y1 = yy + 8
                pg.caixa(fx, y0, fw, y1 - y0, p.tipo,
                         "shape=umlFrame;whiteSpace=wrap;html=1;width=40;height=20;fontStyle=1;fontSize=11;"
                         "fontFamily=Helvetica;fillColor=none;strokeColor=#555555;verticalAlign=top;align=left;"
                         "spacingLeft=4;")
                for ys in separadores:
                    pg.linha([(fx, ys), (fx + fw, ys)],
                             "html=1;endArrow=none;dashed=1;strokeColor=#555555;strokeWidth=1;")
                yy = y1 + 8
        return yy

    y = bloco(d.passos, y, 0)
    fecha()
    fim = y + 30

    # linhas de vida e barras de ativação (desenhadas depois para ficar por baixo das setas no draw.io)
    fundo = []
    for k in d.participantes:
        fundo.append((k, None))
    cells_mensagens, pg.cells = pg.cells, []
    for k in d.participantes:
        pg.linha([(xs[k], topo + ALT_ICONE + 4), (xs[k], fim)],
                 "html=1;endArrow=none;dashed=1;strokeColor=#8a8a8a;strokeWidth=1;")
    for k, ini, f in barras:
        pg.caixa(xs[k] - 5, ini, 10, f - ini, "", "html=1;fillColor=#ffffff;strokeColor=#333333;strokeWidth=1;")
    pg.cells = pg.cells + cells_mensagens
    largura = int(max(direita, 1100))
    return "".join(pg.cells), largura, int(fim + 30)


# ---------------------------------------------------------------- robustez
def desenhar_robustez(f: Fluxo, partes: dict[str, Part], pid: str) -> tuple[str, int, int]:
    """Atores, telas, controles e entidades de todo o fluxo e quem conversa com quem."""
    pares: dict[tuple[str, str], str] = {}
    ordem: list[str] = []
    for d in f.diagramas:
        for k in d.participantes:
            if k in usados(d.passos) and k not in ordem:
                ordem.append(k)
        for m in mensagens(d.passos):
            if m.tipo == "ret" or m.de == m.para:
                continue
            a, b = m.de, m.para
            tipos = (partes[a].tipo, partes[b].tipo)
            if tipos == ("tela", "tela"):
                pares.setdefault((a, b), "navega")  # desenhada em azul tracejado, sem texto (ver legenda)
            else:
                pares.setdefault(tuple(sorted((a, b), key=ordem.index)), "")
    colunas_tipo = {"ator": 0, "tela": 1, "controle": 2, "entidade": 3, "interface": 3, "externo": 4}
    xcol = [90, 330, 620, 900, 1150]
    grupos: dict[int, list[str]] = {}
    for k in ordem:
        grupos.setdefault(colunas_tipo[partes[k].tipo], []).append(k)
    pg = Pagina(pid)
    pg.caixa(24, 14, 1400, 24, html.escape(f"Robustez {f.id} – {f.titulo}"),
             "text;html=1;align=left;verticalAlign=top;fontSize=16;fontStyle=1;fontFamily=Helvetica;")
    pg.caixa(24, 40, 1400, 18, html.escape(f.requisitos),
             "text;html=1;align=left;verticalAlign=top;fontSize=11;fontColor=#555555;fontFamily=Helvetica;")
    if f.situacao:
        pg.caixa(24, 62, 1200, 20, html.escape(f.situacao),
                 "text;html=1;align=left;verticalAlign=top;fontSize=11;fontColor=#b26a00;fontFamily=Helvetica;")
    maior = max(len(v) for v in grupos.values())
    passo_y = 125
    ids, centro = {}, {}
    for col, ks in grupos.items():
        y0 = 120 + (maior - len(ks)) * passo_y / 2
        for i, k in enumerate(ks):
            p = partes[k]
            w = LARG_ICONE[p.tipo]
            rot = f"<b>{html.escape(p.nome)}</b>" + (
                f'<br><font style="font-size:10px" color="#555555">{html.escape(p.sub)}</font>' if p.sub else "")
            ids[k] = pg.caixa(xcol[col] - w / 2, y0 + i * passo_y, w, ALT_ICONE, rot,
                              ESTILO_PART[p.tipo] + "fontSize=11;fontFamily=Helvetica;")
            centro[k] = (xcol[col], y0 + i * passo_y + ALT_ICONE / 2)
    desvio = 0
    for (a, b), rot in pares.items():
        if rot:  # navegação entre telas: sai pela esquerda da coluna para não cruzar os ícones do meio
            desvio += 1
            xl = centro[a][0] - 40 - 9 * desvio
            pg.linha([(0, 0), (xl, centro[a][1]), (xl, centro[b][1]), (0, 0)],
                     "html=1;endArrow=open;endFill=0;dashed=1;strokeColor=#4a6fa5;edgeStyle=none;rounded=1;"
                     "exitX=0;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;",
                     "", ids[a], ids[b])
        else:
            pg.linha([(0, 0), (0, 0)], "html=1;endArrow=none;strokeColor=#555555;strokeWidth=1.2;edgeStyle=none;",
                     "", ids[a], ids[b])
    altura = int(120 + maior * passo_y + 60)
    leg = ("<b>Robustez (ICONIX)</b><br>Ator fala só com tela; tela fala com controle; controle fala com "
           "entidade e com a interface de e-mail.<br>Seta azul tracejada: a tela leva a outra tela (navegação).")
    pg.caixa(24, altura, 620, 54, leg, "text;html=1;align=left;verticalAlign=top;spacing=8;fontSize=11;"
             "fontFamily=Helvetica;fillColor=#f5f5f5;strokeColor=#999999;rounded=1;whiteSpace=wrap;")
    return "".join(pg.cells), 1300, altura + 80


def pagina(pid: str, nome: str, conteudo: str, w: int, h: int) -> str:
    return (f'<diagram name={quoteattr(nome)} id="{pid}"><mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" '
            f'guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{w}" '
            f'pageHeight="{h}" math="0" shadow="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>{conteudo}'
            "</root></mxGraphModel></diagram>")


def main() -> None:
    import diagrama_classes
    import fluxos_sequencia as fs

    paginas = []
    for i, f in enumerate(fs.FLUXOS):
        cont, w, h = desenhar_robustez(f, fs.PARTES, f"r{i}")
        paginas.append(pagina(f"r{i}", f"Robustez {f.id}", cont, w, h))
        for j, d in enumerate(f.diagramas):
            cont, w, h = desenhar_sequencia(d, fs.PARTES, f"s{i}-{j}")
            paginas.append(pagina(f"s{i}-{j}", f"{d.id} {d.titulo}"[:60], cont, w, h))
        print(f"{f.id}: robustez + {len(f.diagramas)} sequências")
    classes, problemas = diagrama_classes.gerar()
    paginas += [p.replace('name="', 'name="Classes ', 1) for p in classes]
    destino = AQUI / "diagramas-sequencia-siga-uea.drawio"
    destino.write_text('<mxfile host="app.diagrams.net">' + "".join(paginas) + "</mxfile>", encoding="utf8")
    print(f"{len(paginas)} páginas em {destino.name}")
    raise SystemExit(1 if problemas else 0)


if __name__ == "__main__":
    # Chama pelo módulo importado: fluxos_sequencia importa diagramas_sequencia, e as classes
    # (Msg, Frag...) precisam ser as mesmas dos dois lados para o isinstance funcionar.
    import diagramas_sequencia

    diagramas_sequencia.main()
