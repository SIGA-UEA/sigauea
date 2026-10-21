"""Diagrama de implantação (UML deployment) do SIGA UEA: o sistema completo.

Gera docs/modelagem/diagrama-implantacao-siga-uea.drawio com três páginas:

  1. Produção        um servidor (VM Linux) com Docker Compose (HT06)
  2. Homologação     serviços gratuitos separados: Vercel (site), Render (API) e Neon/Supabase (banco)
  3. Desenvolvimento a máquina do desenvolvedor

Mostra o que já existe e o que os requisitos ainda pedem (em amarelo/laranja tracejado):
armazenamento dos PDFs (RAN07), gerador de PDF (RBN09.14 a 09.17, RBN13.06), agendador de
tarefas (RBN09.06, RBN01.11, RBN01.12), agenda pública (RAN14), backup (RNF03) e
monitoramento (RNF07). Cada página tem legenda, e o texto das ligações fica ao lado da linha.

Fontes: docker-compose.yml, Dockerfile, backend/Dockerfile, next.config.ts, backend/.env.exemplo,
backend/app/config.py, as fichas HT05 a HT08 e a planilha de requisitos.

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
        ("caixa", "fillColor=#dae8fc;strokeColor=#6c8ebf;", "Nó, ambiente ou artefato que já existe"),
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
def producao() -> Pagina:
    p = Pagina("1 · Produção (servidor com Docker)",
               "SIGA UEA · Diagrama de implantação · Produção: um servidor com Docker Compose (HT06)")
    p.forma("cli", "device", 40, 110, 260, 240, "Computador ou celular do usuário",
            "aluno, docente, coordenação e banca<br>(inclusive externos) · visitante da<br>agenda pública (RAN14)")
    p.forma("nav", "ambiente", 60, 205, 220, 130, "Navegador web", "Chrome ou Safari, a partir de 360 px", dentro="cli")
    p.forma("ui", "artefato", 75, 265, 190, 55, "Interface SIGA", dentro="nav")
    p.forma("git", "externo", 40, 450, 260, 150, "GitHub", "repositório SIGA-UEA/sigauea")
    p.forma("repo", "artefato", 60, 520, 220, 60, "código da branch main", dentro="git")
    p.forma("mon", "device_plan", 40, 680, 260, 130, "Monitoramento externo",
            "ex.: UptimeRobot · avisa a equipe<br>se o sistema cair (RNF07)")

    p.forma("srv", "device", 460, 70, 1300, 890, "Servidor de aplicação · VM Linux",
            "2 vCPU · 4 GB de RAM · 20 GB de disco · provedor a definir (HT06)")
    p.forma("dock", "ambiente", 480, 150, 1260, 790, "Docker Engine + Docker Compose", "docker-compose.yml",
            dentro="srv")
    p.forma("proxy", "planejado", 520, 225, 200, 190, "proxy · Caddy ou Nginx", "porta 443, a única exposta",
            dentro="dock")
    p.forma("cert", "artefato_plan", 535, 320, 170, 70, "certificado TLS<br>(Let's Encrypt)", dentro="proxy")
    p.forma("web", "container", 820, 225, 220, 190, "web · Node.js 24", "Next.js 16 · porta 3000", dentro="dock")
    p.forma("webimg", "artefato", 835, 300, 190, 55, "imagem web (Dockerfile)", dentro="web")
    p.forma("webcfg", "artefato", 835, 362, 190, 40, "API_URL=http://api:8000", dentro="web")
    p.forma("env", "artefato", 820, 480, 220, 120, ".env do servidor",
            "DATABASE_URL, POSTGRES_PASSWORD, FRONTEND_URL, COOKIE_SEGURO=1, SMTP_*", dentro="dock")
    p.forma("api", "container", 1140, 225, 260, 380, "api · Python 3.12 + Uvicorn", "FastAPI · porta 8000",
            dentro="dock")
    p.forma("apiimg", "artefato", 1155, 300, 230, 50, "imagem api (backend/Dockerfile)", dentro="api")
    p.forma("mig", "artefato", 1155, 358, 230, 50, "migrações Alembic", dentro="api")
    p.forma("seed", "artefato", 1155, 416, 230, 50, "carga inicial (python -m app.seed)", dentro="api")
    p.forma("pdf", "artefato_plan", 1155, 474, 230, 55, "gerador de PDF: ata, folha, certi-<br>"
            "ficados, relatório (RBN09.14 a 09.17)", dentro="api")
    p.forma("arq", "artefato_plan", 1155, 537, 230, 55, "volume <i>arquivos</i> montado na api:<br>"
            "PDFs até 20 MB, SHA-256 (RAN07)", dentro="api")
    p.forma("db", "container", 1500, 225, 200, 240, "db · PostgreSQL 16", "porta 5432 · rede interna", dentro="dock")
    p.forma("banco", "artefato", 1515, 300, 170, 55, "banco siga (23 tabelas<br>hoje, 45 no fim)", dentro="db")
    p.forma("vol", "artefato", 1515, 368, 170, 70, "volume <i>dados</i><br>(/var/lib/postgresql/<br>data)", dentro="db")
    p.forma("worker", "planejado", 1140, 700, 260, 210, "worker · Python 3.12", "mesma imagem da api · agendador",
            dentro="dock")
    p.forma("tarefas", "artefato_plan", 1155, 775, 230, 115, "tarefas agendadas:<br>lembrete 1 dia antes (RBN09.06)<br>"
            "revogar aluno após 7 dias (RBN01.11)<br>expirar conta externa (RBN01.12)<br>reenviar e-mails com falha",
            dentro="worker")

    p.forma("smtp", "externo", 1980, 110, 280, 140, "Servidor de e-mail", "smtp.gmail.com<br>conta siga.uea1@gmail.com")
    p.forma("nota", "nota", 1980, 300, 340, 330,
            "<b>Notas</b><br>• RNF02: só o proxy é exposto (443, TLS ≥ 1.2); site, API e banco ficam na rede interna "
            "do Compose. Cookie de sessão httponly e, em produção, Secure (COOKIE_SEGURO=1).<br>"
            "• RNF03: o log de auditoria fica no PostgreSQL e o banco não deixa alterar nem apagar; o backup guarda "
            "banco e arquivos por 5 anos após a conclusão do TCC.<br>"
            "• RNF07: 99% no pico; recuperação em até 30 min (reiniciar os contêineres ou restaurar o backup).<br>"
            "• A API aplica as migrações ao subir (alembic upgrade head) e só então atende.")
    p.forma("bkp", "device_plan", 1980, 700, 280, 140, "Armazenamento de backup",
            "fora do servidor (outro provedor<br>ou disco) · retenção de 5 anos")
    p.legenda(40, 880)

    p.liga("cli", "proxy", "HTTPS · :443<br>TLS ≥ 1.2", (1, 140 / 240), (0, 25 / 190))
    p.liga("proxy", "web", "HTTP · :3000", (1, 0.4), (0, 0.4))
    p.liga("web", "api", "HTTP · :8000<br>/api/v1/*", (1, 0.4), (0, 76 / 380))
    p.liga("api", "db", "TCP · :5432", (1, 76 / 380), (0, 76 / 240))
    p.liga("api", "smtp", "SMTP · :587<br>STARTTLS", (230 / 260, 0), (0, 85 / 140), pontos=[(1370, 195)])
    p.liga("worker", "db", "TCP · :5432", (1, 60 / 210), (0.5, 1), tipo="planejado", pontos=[(1600, 760)], trecho=1)
    p.liga("worker", "smtp", "SMTP · :587", (1, 160 / 210), (0, 120 / 140), tipo="planejado",
           pontos=[(1950, 860), (1950, 230)], trecho=0)
    p.liga("db", "bkp", "backup diário<br>(dump + arquivos)", (1, 195 / 240), (0, 0.5), tipo="planejado",
           pontos=[(1800, 420), (1800, 770)], trecho=2)
    p.liga("mon", "proxy", "HTTPS · a cada 5 min<br>(verificação)", (1, 0.5), (0.5, 1), tipo="planejado",
           pontos=[(620, 745)], trecho=1)
    p.liga("git", "srv", "«deploy» git pull +<br>docker compose up", (1, 75 / 150), (0, 455 / 890), tipo="deploy",
           lado="abaixo")
    return p


def homologacao() -> Pagina:
    p = Pagina("2 · Homologação (serviços gratuitos)",
               "SIGA UEA · Diagrama de implantação · Homologação: serviços gratuitos separados")
    p.forma("cli", "device", 40, 110, 260, 220, "Computador ou celular do usuário", "coordenação e equipe testando")
    p.forma("nav", "ambiente", 60, 175, 220, 135, "Navegador web", "Chrome ou Safari", dentro="cli")
    p.forma("ui", "artefato", 75, 240, 190, 55, "Interface SIGA", dentro="nav")
    p.forma("git", "externo", 40, 520, 260, 150, "GitHub", "repositório SIGA-UEA/sigauea")
    p.forma("repo", "artefato", 60, 590, 220, 60, "código da branch main", dentro="git")

    p.forma("vercel", "nuvem", 460, 90, 320, 290, "Vercel (plano Hobby)", "HTTPS automático · *.vercel.app")
    p.forma("vnode", "ambiente", 480, 165, 280, 195, "Node.js 24 (funções do Next)", dentro="vercel")
    p.forma("site", "artefato", 495, 225, 250, 55, "site Next.js 16 (build da main)", dentro="vnode")
    p.forma("vcfg", "artefato", 495, 290, 250, 55, "API_URL = endereço da API no Render", dentro="vnode")

    p.forma("render", "nuvem", 900, 90, 360, 420, "Render (Free Web Service)",
            "dorme após ~15 min sem uso; o 1º acesso leva 30 a 60 s")
    p.forma("rnode", "container", 920, 175, 320, 315, "Python 3.12 + Uvicorn", "FastAPI", dentro="render")
    p.forma("rapi", "artefato", 935, 245, 290, 50, "API SIGA (backend/)", dentro="rnode")
    p.forma("rstart", "artefato", 935, 302, 290, 50, "start: python -m app.seed && uvicorn …", dentro="rnode")
    p.forma("rcfg", "artefato", 935, 359, 290, 55, "DATABASE_URL, SMTP_*, FRONTEND_URL,<br>COOKIE_SEGURO=1", dentro="rnode")
    p.forma("rpdf", "artefato_plan", 935, 421, 290, 55, "gerador de PDF (RBN09.14 a 09.17)", dentro="rnode")

    p.forma("neon", "nuvem", 1420, 90, 330, 240, "Neon ou Supabase (plano grátis)",
            "Supabase: usar o Session pooler (IPv4)")
    p.forma("pg", "ambiente", 1440, 165, 290, 145, "PostgreSQL 16 gerenciado", "conexão com TLS", dentro="neon")
    p.forma("pbanco", "artefato", 1455, 235, 260, 55, "banco siga", dentro="pg")
    p.forma("stor", "device_plan", 1420, 400, 330, 150, "Armazenamento de arquivos",
            "Supabase Storage ou similar · PDFs do<br>TCC, ata e certificados (RAN07)")
    p.forma("smtp", "externo", 1420, 620, 330, 150, "Servidor de e-mail",
            "smtp.gmail.com :587 · se o Render bloquear SMTP,<br>trocar por Brevo ou Resend (API HTTPS)")
    p.forma("nota", "nota", 460, 800, 800, 125,
            "<b>Notas</b><br>• Ambiente para homologação e apresentação (HT06), sem custo e sem cartão.<br>"
            "• Não cumpre o RNF07 (99%): a API dorme. Abrir o sistema alguns minutos antes de apresentar.<br>"
            "• Tarefas agendadas (lembretes, revogação) precisam de um agendador: Render Cron Job ou GitHub "
            "Actions agendado.<br>"
            "• O cookie de sessão fica na mesma origem: o navegador só fala com a Vercel, que repassa /api/v1.")
    p.legenda(40, 720)

    p.liga("cli", "vercel", "HTTPS · :443", (1, 120 / 220), (0, 140 / 290))
    p.liga("vercel", "render", "HTTPS<br>/api/v1/*", (1, 0.45), (0, 130.5 / 420))
    p.liga("render", "neon", "TCP + TLS · :5432", (1, 126 / 420), (0, 126 / 240))
    p.liga("render", "stor", "HTTPS · PDFs", (1, 380 / 420), (0, 70 / 150), tipo="planejado")
    p.liga("render", "smtp", "SMTP · :587", (0.75, 1), (0, 75 / 150), pontos=[(1170, 695)], trecho=1)
    p.liga("git", "vercel", "«deploy» a cada push", (1, 45 / 150), (0.5, 1), pontos=[(620, 565)], tipo="deploy",
           trecho=0)
    p.liga("git", "render", "«deploy» a cada push", (1, 105 / 150), (0.3, 1), pontos=[(1008, 625)], tipo="deploy",
           trecho=0, lado="abaixo")
    return p


def desenvolvimento() -> Pagina:
    p = Pagina("3 · Desenvolvimento local", "SIGA UEA · Diagrama de implantação · Desenvolvimento local")
    p.forma("pc", "device", 40, 70, 1400, 560, "Computador do desenvolvedor", "Windows 11, macOS ou Linux")
    p.forma("nav", "ambiente", 60, 150, 220, 140, "Navegador web", dentro="pc")
    p.forma("url", "artefato", 75, 215, 190, 50, "http://localhost:3000", dentro="nav")
    p.forma("node", "ambiente", 360, 150, 280, 220, "Node.js 24", dentro="pc")
    p.forma("dev", "artefato", 375, 205, 250, 50, "npm run dev (Next.js, porta 3000)", dentro="node")
    p.forma("prx", "artefato", 375, 265, 250, 50, "proxy.ts + rewrites de /api/v1", dentro="node")
    p.forma("py", "ambiente", 720, 150, 320, 330, "Python 3.12 (backend/.venv)", dentro="pc")
    p.forma("uv", "artefato", 735, 205, 290, 50, "uvicorn app.main:app --reload (8000)", dentro="py")
    p.forma("tst", "artefato", 735, 265, 290, 50, "pytest (testes da API)", dentro="py")
    p.forma("denv", "artefato", 735, 325, 290, 60, "backend/.env (fora do git)<br>SMTP e FRONTEND_URL", dentro="py")
    p.forma("sd", "artefato", 735, 395, 290, 60, "python -m app.seed --demo<br>(contas e turma de demonstração)",
            dentro="py")
    p.forma("sqlite", "artefato", 1170, 160, 240, 60, "backend/siga_dev.db (SQLite)", dentro="pc")
    p.forma("pgl", "ambiente", 1170, 280, 240, 140, "PostgreSQL 16 (opcional)", "Docker ou instalação local",
            dentro="pc")
    p.forma("pgb", "artefato", 1185, 350, 210, 50, "banco de teste", dentro="pgl")
    p.forma("smtp", "externo", 1520, 150, 280, 160, "Servidor de e-mail",
            "smtp.gmail.com :587 · opcional: sem<br>SMTP, o e-mail sai no terminal da API")
    p.legenda(40, 680)

    p.liga("nav", "node", "HTTP · :3000", (1, 0.5), (0, 70 / 220))
    p.liga("node", "py", "HTTP · :8000<br>/api/v1/*", (1, 0.32), (0, 70.4 / 330))
    p.liga("py", "sqlite", "arquivo (SQLAlchemy)", (1, 40 / 330), (0, 0.5))
    p.liga("py", "pgl", "TCP · :5432<br>(TEST_DATABASE_URL)", (1, 200 / 330), (0, 70 / 140))
    p.liga("py", "smtp", "SMTP · :587 (via backend/.env)", (0.5, 1), (0.5, 1), pontos=[(880, 580), (1660, 580)],
           trecho=1)
    return p


def main() -> None:
    paginas = [producao(), homologacao(), desenvolvimento()]
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
