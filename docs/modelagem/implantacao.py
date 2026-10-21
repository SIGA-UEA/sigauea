"""Diagrama de implantação (UML deployment) do SIGA UEA, com a decisão do Plano de Integração v2.3.

Gera docs/modelagem/diagrama-implantacao-siga-uea.drawio com duas páginas:

  1. Ambiente integrado  Vercel (site), Render (API) e Neon (PostgreSQL), com deploy pelo GitHub
  2. Ambiente local      Docker Compose na máquina da equipe (db, api e web)

Mostra o que já existe e, em amarelo/laranja tracejado, o que os requisitos ainda pedem:
armazenamento dos PDFs e backup (RAN07, RNF03), gerador de PDF (RBN09.14 a 09.17, RBN13.06),
tarefas agendadas (RBN09.06, RBN01.11, RBN01.12) e monitoramento (RNF07). Cada página tem legenda,
e o texto das ligações fica ao lado da linha (o gerador confere que não encosta em linha nem caixa).

Fontes: render.yaml, .vercelignore, docker-compose.yml, Dockerfile, backend/Dockerfile, next.config.ts,
backend/.env.exemplo, backend/app/config.py, ficha HT06 e Plano de Integração v2.3 (seções 2 e 4.6.3).

    python docs/modelagem/implantacao.py
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from xml.sax.saxutils import quoteattr

AQUI = Path(__file__).resolve().parent

# Nó UML (caixa 3D). Sem direction=south: o rótulo fica no topo, à esquerda.
NO = ("shape=cube;size=12;whiteSpace=wrap;html=1;verticalAlign=top;align=left;"
      "spacingLeft=18;spacingTop=14;spacingRight=8;container=1;collapsible=0;fontSize=11;")
PLANEJADO = "fillColor=#fff2cc;strokeColor=#d6b656;dashed=1;dashPattern=6 4;"
ESTILOS = {
    "device": NO + "fillColor=#dae8fc;strokeColor=#6c8ebf;",
    "nuvem": NO + "fillColor=#e1d5e7;strokeColor=#9673a6;",
    "externo": NO + "fillColor=#f5f5f5;strokeColor=#999999;",
    "ambiente": NO + "fillColor=#ffffff;strokeColor=#6c8ebf;",
    "container": NO + "fillColor=#d5e8d4;strokeColor=#82b366;",
    "planejado": NO + PLANEJADO,
    "device_plan": NO + PLANEJADO,
    "artefato": ("shape=note;size=12;whiteSpace=wrap;html=1;align=left;verticalAlign=middle;spacingLeft=8;"
                 "spacingRight=10;fontSize=10;fillColor=#ffffff;strokeColor=#666666;"),
    "artefato_plan": ("shape=note;size=12;whiteSpace=wrap;html=1;align=left;verticalAlign=middle;spacingLeft=8;"
                      "spacingRight=10;fontSize=10;" + PLANEJADO),
    "nota": ("shape=note;size=14;whiteSpace=wrap;html=1;align=left;verticalAlign=top;spacing=10;fontSize=10.5;"
             "fillColor=#fffde7;strokeColor=#b7a63a;"),
}
ESTEREO = {"device": "«device»", "device_plan": "«device»", "nuvem": "«device» «cloud»", "externo": "«device»",
           "ambiente": "«executionEnvironment»", "container": "«executionEnvironment» «container»",
           "planejado": "«executionEnvironment» «container»"}
LINHAS = {
    "existe": "endArrow=none;strokeColor=#333333;strokeWidth=1.4;",
    "planejado": "endArrow=none;strokeColor=#d79b00;strokeWidth=1.6;dashed=1;dashPattern=8 4;",
    "deploy": "endArrow=open;endSize=10;strokeColor=#7a7a7a;strokeWidth=1.2;dashed=1;dashPattern=4 4;",
}
CONTEINERES = ("device", "device_plan", "nuvem", "externo", "ambiente", "container", "planejado")
LEG_W, LEG_H = 300, 196


def tamanho_rotulo(texto: str) -> tuple[float, float]:
    linhas = re.sub(r"<[^>]+>", "", texto.replace("<br>", "\n")).split("\n")
    return max(len(html.unescape(ln)) for ln in linhas) * 5.6 + 8, len(linhas) * 12.5 + 4


def _cruza(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def _toca(seg, caixa, folga):
    """Trecho (x, y, w, h; w ou h zero) contra caixa, com folga (negativa tolera encostar na borda)."""
    x, y, w, h = seg
    bx, by, bw, bh = caixa
    return x < bx + bw + folga and bx - folga < x + w and y < by + bh + folga and by - folga < y + h


class Pagina:
    def __init__(self, nome: str, titulo: str):
        self.nome, self.titulo = nome, titulo
        self.formas: dict[str, dict] = {}
        self.ordem: list[str] = []
        self.arestas: list[dict] = []
        self.legenda_xy: tuple[int, int] = (0, 0)

    def forma(self, fid, tipo, x, y, w, h, nome, detalhe="", dentro=None):
        """Coordenadas absolutas; a conversão para relativas ao pai é feita no XML."""
        if tipo in ("artefato", "artefato_plan"):
            rotulo = f"<font color=\"#666666\" style=\"font-size:9px\">«artifact»</font><br><b>{nome}</b>"
        elif tipo == "nota":
            rotulo = nome
        else:
            rotulo = f"<font color=\"#555555\" style=\"font-size:9px\">{ESTEREO[tipo]}</font><br><b>{nome}</b>"
        if detalhe:
            rotulo += f"<br><font style=\"font-size:9.5px\">{detalhe}</font>"
        self.formas[fid] = dict(tipo=tipo, x=x, y=y, w=w, h=h, rotulo=rotulo, pai=dentro)
        self.ordem.append(fid)

    def liga(self, de, para, rotulo, saida, entrada, pontos=(), tipo="existe", lado=None, trecho=None):
        """saida/entrada: (fx, fy) relativos à forma; pontos: cotovelos absolutos.
        lado: onde fica o texto (acima, abaixo, direita, esquerda); trecho: em qual trecho da linha."""
        self.arestas.append(dict(de=de, para=para, rotulo=rotulo, saida=saida, entrada=entrada,
                                 pontos=list(pontos), tipo=tipo, lado=lado, trecho=trecho))

    def legenda(self, x, y):
        self.legenda_xy = (x, y)

    # ------------------------------------------------------------ geometria
    def caixa(self, fid):
        if fid == "__legenda":
            return (*self.legenda_xy, LEG_W, LEG_H)
        f = self.formas[fid]
        return (f["x"], f["y"], f["w"], f["h"])

    def pontos(self, e):
        a, b = self.formas[e["de"]], self.formas[e["para"]]
        p0 = (a["x"] + a["w"] * e["saida"][0], a["y"] + a["h"] * e["saida"][1])
        p1 = (b["x"] + b["w"] * e["entrada"][0], b["y"] + b["h"] * e["entrada"][1])
        pts = [p0, *e["pontos"], p1]
        out = [pts[0]]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            if round(ax) != round(bx) and round(ay) != round(by):  # cotovelo automático
                mx = round((ax + bx) / 2)
                out += [(mx, ay), (mx, by)]
            out.append((bx, by))
        return out

    def rotulo(self, e):
        """Centro e caixa do texto, ao lado (nunca em cima) do trecho escolhido da linha."""
        pts = self.pontos(e)
        segs = list(zip(pts, pts[1:]))
        tam = [abs(bx - ax) + abs(by - ay) for (ax, ay), (bx, by) in segs]
        i = e["trecho"] if e["trecho"] is not None else max(range(len(segs)), key=lambda k: tam[k])
        (ax, ay), (bx, by) = segs[i]
        mx, my = (ax + bx) / 2, (ay + by) / 2
        w, h = tamanho_rotulo(e["rotulo"])
        lado = e["lado"] or ("acima" if round(ay) == round(by) else "direita")
        folga = 5
        cx, cy = mx, my
        if lado == "acima":
            cy = my - h / 2 - folga
        elif lado == "abaixo":
            cy = my + h / 2 + folga
        elif lado == "direita":
            cx = mx + w / 2 + folga
        else:
            cx = mx - w / 2 - folga
        andado = sum(tam[:i]) + tam[i] / 2
        return dict(cx=cx, cy=cy, w=w, h=h, px=mx, py=my, frac=andado / (sum(tam) or 1),
                    caixa=(cx - w / 2, cy - h / 2, w, h))

    # ------------------------------------------------------------ conferência
    def _ancestrais(self, fid):
        out = set()
        while fid:
            out.add(fid)
            fid = self.formas[fid]["pai"]
        return out

    def conferir(self) -> list[str]:
        probs = []
        todos = [*self.formas, "__legenda"]
        for fid, f in self.formas.items():
            if f["pai"]:
                q = self.formas[f["pai"]]
                if not (f["x"] >= q["x"] and f["y"] >= q["y"] + 30 and f["x"] + f["w"] <= q["x"] + q["w"] - 12
                        and f["y"] + f["h"] <= q["y"] + q["h"]):
                    probs.append(f"{fid} sai de dentro de {f['pai']}")
        grupos: dict = {None: ["__legenda"]}
        for fid, f in self.formas.items():
            grupos.setdefault(f["pai"], []).append(fid)
        for g in grupos.values():
            for i, a in enumerate(g):
                for b in g[i + 1:]:
                    if _cruza(self.caixa(a), self.caixa(b)):
                        probs.append(f"{a} sobrepõe {b}")
        segmentos = []
        for e in self.arestas:
            pts = self.pontos(e)
            donos = self._ancestrais(e["de"]) | self._ancestrais(e["para"])
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                seg = (min(ax, bx), min(ay, by), abs(bx - ax), abs(by - ay))
                segmentos.append((e, seg))
                for fid in todos:
                    if fid in donos:
                        continue
                    if _toca(seg, self.caixa(fid), -1):
                        probs.append(f"linha {e['de']}→{e['para']} atravessa {fid}")
        rotulos = [(e, self.rotulo(e)["caixa"]) for e in self.arestas]
        for e, rc in rotulos:
            for fid in todos:
                bx = self.caixa(fid)
                dentro = bx[0] <= rc[0] and bx[1] <= rc[1] and rc[0] + rc[2] <= bx[0] + bx[2] and rc[1] + rc[3] <= bx[1] + bx[3]
                eh_conteiner = fid != "__legenda" and self.formas[fid]["tipo"] in CONTEINERES
                if _cruza(rc, bx) and not (dentro and eh_conteiner):
                    probs.append(f"texto '{_curto(e)}' encosta em {fid}")
            for f, seg in segmentos:
                if _toca(seg, rc, 1):
                    probs.append(f"texto '{_curto(e)}' sobre a linha {f['de']}→{f['para']}")
        for i, (e, a) in enumerate(rotulos):
            for f, b in rotulos[i + 1:]:
                if _cruza(a, b):
                    probs.append(f"textos '{_curto(e)}' e '{_curto(f)}' se sobrepõem")
        return probs

    # ------------------------------------------------------------ saída
    def xml(self, idx: int) -> str:
        cells = [f'<mxCell id="i{idx}-t" value={quoteattr(self.titulo)} style="text;html=1;fontSize=20;fontStyle=1;'
                 f'align=left;" vertex="1" parent="1"><mxGeometry x="40" y="12" width="1500" height="34" as="geometry"/></mxCell>']
        for fid in self.ordem:
            f = self.formas[fid]
            pai = f"i{idx}-{f['pai']}" if f["pai"] else "1"
            x, y = f["x"], f["y"]
            if f["pai"]:
                x -= self.formas[f["pai"]]["x"]
                y -= self.formas[f["pai"]]["y"]
            cells.append(f'<mxCell id="i{idx}-{fid}" value={quoteattr(f["rotulo"])} style="{ESTILOS[f["tipo"]]}" '
                         f'vertex="1" parent="{pai}"><mxGeometry x="{x}" y="{y}" width="{f["w"]}" height="{f["h"]}" '
                         f'as="geometry"/></mxCell>')
        for k, e in enumerate(self.arestas):
            pts = self.pontos(e)
            meio = "".join(f'<mxPoint x="{x:.0f}" y="{y:.0f}"/>' for x, y in pts[1:-1])
            (sx, sy), (tx, ty) = e["saida"], e["entrada"]
            r = self.rotulo(e)
            cells.append(
                f'<mxCell id="i{idx}-e{k}" value="" style="edgeStyle=none;rounded=1;html=1;exitX={sx:.4f};exitY={sy:.4f};'
                f'exitDx=0;exitDy=0;exitPerimeter=0;entryX={tx:.4f};entryY={ty:.4f};entryDx=0;entryDy=0;entryPerimeter=0;'
                f'{LINHAS[e["tipo"]]}" edge="1" parent="1" source="i{idx}-{e["de"]}" target="i{idx}-{e["para"]}">'
                f'<mxGeometry relative="1" as="geometry"><Array as="points">{meio}</Array></mxGeometry></mxCell>')
            # O texto é rótulo da própria linha, deslocado para o lado: acompanha a linha se ela for movida.
            cor = "#9a6700" if e["tipo"] == "planejado" else "#555555" if e["tipo"] == "deploy" else "#222222"
            cells.append(
                f'<mxCell id="i{idx}-e{k}-l" value={quoteattr(e["rotulo"])} style="edgeLabel;html=1;align=center;'
                f'verticalAlign=middle;resizable=0;points=[];fontSize=10;fontColor={cor};labelBackgroundColor=none;" '
                f'vertex="1" connectable="0" parent="i{idx}-e{k}"><mxGeometry x="{r["frac"] * 2 - 1:.4f}" '
                f'relative="1" as="geometry"><mxPoint x="{r["cx"] - r["px"]:.0f}" y="{r["cy"] - r["py"]:.0f}" '
                f'as="offset"/></mxGeometry></mxCell>')
        cells += legenda_xml(idx, *self.legenda_xy)
        largura = max(f["x"] + f["w"] for f in self.formas.values()) + 60
        altura = max([f["y"] + f["h"] for f in self.formas.values()] + [self.legenda_xy[1] + LEG_H]) + 60
        return (f'<diagram name={quoteattr(self.nome)} id="impl-{idx}"><mxGraphModel dx="1600" dy="1000" grid="1" '
                f'gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
                f'pageWidth="{largura}" pageHeight="{altura}" math="0" shadow="0"><root><mxCell id="0"/>'
                f'<mxCell id="1" parent="0"/>' + "".join(cells) + "</root></mxGraphModel></diagram>")


def _curto(e):
    return re.sub(r"<[^>]+>", " ", e["rotulo"])[:28]


def legenda_xml(idx, x, y) -> list[str]:
    """Legenda desenhada com amostras reais de cada estilo."""
    c = [f'<mxCell id="i{idx}-leg" value="&lt;b&gt;Legenda&lt;/b&gt;" style="rounded=1;arcSize=4;whiteSpace=wrap;'
         f'html=1;fillColor=#ffffff;strokeColor=#999999;verticalAlign=top;align=left;spacingLeft=10;spacingTop=4;'
         f'fontSize=11;" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{LEG_W}" height="{LEG_H}" '
         f'as="geometry"/></mxCell>']
    itens = [
        ("caixa", "fillColor=#dae8fc;strokeColor=#6c8ebf;", "Já existe no repositório (código ou configuração)"),
        ("caixa", PLANEJADO, "Planejado: pedido pelos requisitos, ainda não existe"),
        ("linha", LINHAS["existe"], "Comunicação que já existe (protocolo · porta)"),
        ("linha", LINHAS["planejado"], "Comunicação planejada"),
        ("linha", LINHAS["deploy"], "«deploy»: publicação a partir do GitHub"),
    ]
    for i, (tipo, estilo, texto) in enumerate(itens):
        yy = y + 32 + i * 32
        if tipo == "caixa":
            c.append(f'<mxCell id="i{idx}-leg{i}a" value="" style="rounded=0;html=1;{estilo}" vertex="1" parent="1">'
                     f'<mxGeometry x="{x + 12}" y="{yy}" width="44" height="22" as="geometry"/></mxCell>')
        else:
            c.append(f'<mxCell id="i{idx}-leg{i}a" value="" style="html=1;{estilo}" edge="1" parent="1">'
                     f'<mxGeometry relative="1" as="geometry"><mxPoint x="{x + 10}" y="{yy + 11}" as="sourcePoint"/>'
                     f'<mxPoint x="{x + 58}" y="{yy + 11}" as="targetPoint"/></mxGeometry></mxCell>')
        c.append(f'<mxCell id="i{idx}-leg{i}b" value={quoteattr(texto)} style="text;html=1;align=left;'
                 f'verticalAlign=middle;fontSize=10;whiteSpace=wrap;" vertex="1" parent="1">'
                 f'<mxGeometry x="{x + 66}" y="{yy - 3}" width="226" height="28" as="geometry"/></mxCell>')
    return c


# ================================================================ páginas
def integrado() -> Pagina:
    p = Pagina("1 · Ambiente integrado (Vercel, Render e Neon)",
               "SIGA UEA · Diagrama de implantação · Ambiente integrado: Vercel (site), Render (API) e Neon (banco)")
    p.forma("cli", "device", 40, 110, 260, 240, "Computador ou celular do usuário",
            "aluno, docente, coordenação e banca<br>(inclusive externos) · visitante da<br>agenda pública (RAN14)")
    p.forma("nav", "ambiente", 60, 205, 220, 130, "Navegador web", "Chrome ou Safari, a partir de 360 px", dentro="cli")
    p.forma("ui", "artefato", 75, 265, 190, 55, "Interface SIGA", dentro="nav")
    p.forma("git", "externo", 40, 470, 260, 150, "GitHub", "repositório SIGA-UEA/sigauea")
    p.forma("repo", "artefato", 60, 540, 220, 60, "código da branch main", dentro="git")
    p.forma("mon", "device_plan", 40, 700, 260, 130, "Monitoramento externo",
            "ex.: UptimeRobot · avisa a equipe<br>se o sistema cair (RNF07)")

    p.forma("vercel", "nuvem", 460, 90, 320, 300, "Vercel (plano Hobby)", "HTTPS automático · *.vercel.app")
    p.forma("vnode", "ambiente", 480, 165, 280, 205, "Node.js 24 (funções do Next.js 16)", dentro="vercel")
    p.forma("site", "artefato", 495, 222, 250, 45, "site SIGA (build da branch main)", dentro="vnode")
    p.forma("vprx", "artefato", 495, 272, 250, 45, "proxy.ts (sessão) + rewrites /api/v1", dentro="vnode")
    p.forma("vcfg", "artefato", 495, 322, 250, 45, "API_URL = endereço da API no Render", dentro="vnode")

    p.forma("render", "nuvem", 900, 90, 380, 640, "Render (Free Web Service)",
            "dorme após ~15 min sem uso; o 1º acesso leva 30 a 60 s")
    p.forma("rnode", "container", 920, 175, 340, 330, "Python 3.12 + Uvicorn", "FastAPI · render.yaml", dentro="render")
    p.forma("rapi", "artefato", 935, 245, 310, 45, "API SIGA (backend/)", dentro="rnode")
    p.forma("rstart", "artefato", 935, 297, 310, 50, "ao subir: migrações + carga inicial<br>(python -m app.seed)",
            dentro="rnode")
    p.forma("rcfg", "artefato", 935, 354, 310, 55, "DATABASE_URL, SMTP_*, FRONTEND_URL,<br>COOKIE_SEGURO=1", dentro="rnode")
    p.forma("rpdf", "artefato_plan", 935, 416, 310, 55, "gerador de PDF: ata, folha, certificados,<br>relatório "
            "(RBN09.14 a 09.17, RBN13.06)", dentro="rnode")
    p.forma("cron", "planejado", 920, 540, 340, 170, "Cron Job · Python 3.12", "mesmo código, banco e SMTP da API",
            dentro="render")
    p.forma("tarefas", "artefato_plan", 935, 605, 310, 95, "tarefas agendadas: lembrete da defesa<br>(RBN09.06), "
            "revogar aluno (RBN01.11),<br>expirar conta externa (RBN01.12), reenviar<br>e-mails, cópia diária do banco",
            dentro="cron")

    p.forma("neon", "nuvem", 1420, 90, 330, 240, "Neon (plano grátis)", "PostgreSQL gerenciado")
    p.forma("pg", "ambiente", 1440, 165, 290, 145, "PostgreSQL 16", "conexão com TLS (sslmode=require)", dentro="neon")
    p.forma("pbanco", "artefato", 1455, 235, 260, 55, "banco siga (23 tabelas hoje, 45 no fim)", dentro="pg")
    p.forma("stor", "device_plan", 1420, 400, 330, 150, "Armazenamento de arquivos e backup",
            "ex.: Supabase Storage · PDFs do TCC até 20 MB<br>(RAN07) e cópias do banco por 5 anos (RNF03)")
    p.forma("smtp", "externo", 1420, 620, 330, 140, "Servidor de e-mail",
            "smtp.gmail.com · conta siga.uea1@gmail.com<br>se o Render bloquear SMTP: Brevo ou Resend")

    p.forma("nota", "nota", 1830, 90, 330, 380,
            "<b>Notas</b><br>• O navegador só fala com a Vercel; a Vercel repassa /api/v1 ao Render. O cookie de "
            "sessão fica na mesma origem (httponly e Secure), sem CORS.<br>"
            "• RNF02: HTTPS em todo o caminho (TLS ≥ 1.2) e TLS também até o banco.<br>"
            "• RNF03: o log de auditoria fica no PostgreSQL, que recusa alterar ou apagar registros.<br>"
            "• RNF07: o plano grátis do Render dorme; para 99% no pico é preciso um plano pago ou o "
            "monitoramento acordando a API.<br>"
            "• Deploy automático a cada push na main (HT06, CA-02).<br>"
            "• Configuração no repositório: render.yaml, .vercelignore e README (Publicar na internet).<br>"
            "• Situação em 20/10/2026: configuração pronta; a publicação depende de criar as contas na Vercel, no "
            "Render e no Neon.")
    p.legenda(40, 880)

    p.liga("cli", "vercel", "HTTPS · :443", (1, 0.5), (0, 140 / 300))
    p.liga("vercel", "render", "HTTPS<br>/api/v1/*", (1, 0.5), (0, 150 / 640))
    p.liga("render", "neon", "TCP + TLS · :5432", (1, 126 / 640), (0, 126 / 240))
    p.liga("render", "stor", "HTTPS · PDFs", (1, 380 / 640), (0, 70 / 150), tipo="planejado")
    p.liga("render", "smtp", "SMTP · :587", (1, 600 / 640), (0, 70 / 140))
    p.liga("mon", "render", "HTTPS · /health<br>a cada 5 min", (1, 0.5), (0, 630 / 640), tipo="planejado",
           pontos=[(600, 765), (600, 720)], trecho=2)
    p.liga("git", "vercel", "«deploy» a cada push", (1, 50 / 150), (0.5, 1), pontos=[(620, 520)], tipo="deploy",
           trecho=0)
    p.liga("git", "render", "«deploy» a cada push", (1, 110 / 150), (0, 490 / 640), tipo="deploy", lado="abaixo")
    return p


def local() -> Pagina:
    p = Pagina("2 · Ambiente local (Docker Compose)",
               "SIGA UEA · Diagrama de implantação · Ambiente local: Docker Compose na máquina da equipe")
    p.forma("pc", "device", 40, 70, 1360, 640, "Computador da equipe", "Windows 11, macOS ou Linux")
    p.forma("nav", "ambiente", 60, 150, 160, 140, "Navegador web", dentro="pc")
    p.forma("url", "artefato", 72, 215, 136, 50, "localhost:3000", dentro="nav")
    p.forma("dock", "ambiente", 340, 150, 1040, 520, "Docker Engine + Docker Compose", "docker-compose.yml",
            dentro="pc")
    p.forma("web", "container", 380, 225, 240, 200, "web · Node.js 24", "Next.js 16 · porta 3000 publicada",
            dentro="dock")
    p.forma("webimg", "artefato", 395, 300, 210, 50, "imagem web (Dockerfile)", dentro="web")
    p.forma("webcfg", "artefato", 395, 358, 210, 45, "API_URL=http://api:8000", dentro="web")
    p.forma("env", "artefato", 380, 470, 240, 110, "variáveis do Compose",
            "POSTGRES_PASSWORD, FRONTEND_URL,<br>COOKIE_SEGURO, SMTP_* (opcionais)", dentro="dock")
    p.forma("api", "container", 720, 225, 280, 300, "api · Python 3.12 + Uvicorn", "FastAPI · porta 8000 publicada",
            dentro="dock")
    p.forma("apiimg", "artefato", 735, 300, 250, 50, "imagem api (backend/Dockerfile)", dentro="api")
    p.forma("mig", "artefato", 735, 358, 250, 50, "ao subir: alembic upgrade head", dentro="api")
    p.forma("seed", "artefato", 735, 416, 250, 50, "docker compose run api<br>python -m app.seed", dentro="api")
    p.forma("db", "container", 1100, 225, 260, 260, "db · PostgreSQL 16", "imagem postgres:16-alpine<br>"
            "porta 5432 só na rede do Compose", dentro="dock")
    p.forma("banco", "artefato", 1115, 315, 230, 55, "banco siga", dentro="db")
    p.forma("vol", "artefato", 1115, 380, 230, 60, "volume <i>dados</i><br>(/var/lib/postgresql/data)", dentro="db")

    p.forma("nota", "nota", 1440, 70, 330, 320,
            "<b>Notas</b><br>• Subir tudo: docker compose up --build -d (README, seção Com Docker).<br>"
            "• Sem Docker também funciona: npm run dev, uvicorn --reload e SQLite (README, Como rodar).<br>"
            "• A execução registrada em docs/testes rodou fora do Docker: API e site locais (build de "
            "produção) com PostgreSQL 16 e SQLite.<br>"
            "• Sem SMTP configurado, os e-mails aparecem no log da API (docker compose logs -f api).")
    p.forma("smtp", "externo", 1440, 430, 330, 140, "Servidor de e-mail", "smtp.gmail.com :587 · opcional")
    p.legenda(40, 760)

    p.liga("nav", "web", "HTTP · :3000", (1, 100 / 140), (0, 25 / 200))
    p.liga("web", "api", "HTTP · :8000<br>/api/v1/*", (1, 76 / 200), (0, 76 / 300))
    p.liga("api", "db", "TCP · :5432", (1, 76 / 300), (0, 76 / 260))
    p.liga("api", "smtp", "SMTP · :587 (opcional, via .env)", (0.5, 1), (0.5, 1), pontos=[(860, 620), (1605, 620)],
           trecho=1)
    return p


def main() -> None:
    paginas = [integrado(), local()]
    total = 0
    for p in paginas:
        probs = p.conferir()
        total += len(probs)
        print(f"{p.nome}: {len(p.formas)} elementos, {len(p.arestas)} ligações, {len(probs)} problemas")
        for x in probs:
            print("   ", x)
    (AQUI / "diagrama-implantacao-siga-uea.drawio").write_text(
        '<mxfile host="app.diagrams.net">' + "".join(p.xml(i) for i, p in enumerate(paginas)) + "</mxfile>",
        encoding="utf8")
    raise SystemExit(1 if total else 0)


if __name__ == "__main__":
    main()
