"""Diagrama de implantação (UML deployment) do SIGA UEA.

Gera docs/modelagem/diagrama-implantacao-siga-uea.drawio com três páginas:

  1. Produção        um servidor (VM Linux) com Docker Compose: proxy HTTPS, site, API e PostgreSQL (HT06)
  2. Homologação     serviços gratuitos separados: Vercel (site), Render (API) e Neon/Supabase (banco)
  3. Desenvolvimento a máquina do desenvolvedor: next dev, uvicorn --reload e SQLite

Fontes: docker-compose.yml, Dockerfile, backend/Dockerfile, next.config.ts, backend/.env.exemplo,
backend/app/config.py e as fichas HT05 a HT08 (perfil do servidor, HTTPS, deploy e e-mail).
O provedor de produção ainda não foi escolhido (HT06): o nó do servidor diz "provedor a definir".

    python docs/modelagem/implantacao.py [pasta-para-as-previas-svg]
"""

from __future__ import annotations

import html
import sys
from pathlib import Path
from xml.sax.saxutils import quoteattr

AQUI = Path(__file__).resolve().parent

# Nó UML (caixa 3D) e ambiente de execução; o rótulo fica no topo, à esquerda.
# (sem direction=south: o visualizador do draw.io entra em recursão infinita com cubo contêiner girado)
NO = ("shape=cube;size=12;whiteSpace=wrap;html=1;verticalAlign=top;align=left;"
      "spacingLeft=18;spacingTop=14;spacingRight=8;container=1;collapsible=0;fontSize=11;")
ESTILOS = {
    "device": NO + "fillColor=#dae8fc;strokeColor=#6c8ebf;",
    "nuvem": NO + "fillColor=#e1d5e7;strokeColor=#9673a6;",
    "externo": NO + "fillColor=#f5f5f5;strokeColor=#999999;",
    "ambiente": NO + "fillColor=#ffffff;strokeColor=#6c8ebf;",
    "container": NO + "fillColor=#d5e8d4;strokeColor=#82b366;",
    "planejado": NO + "fillColor=#fff2cc;strokeColor=#d6b656;dashed=1;dashPattern=6 4;",
    "artefato": ("shape=note;size=12;whiteSpace=wrap;html=1;align=left;verticalAlign=middle;spacingLeft=8;"
                 "spacingRight=10;fontSize=10;fillColor=#ffffff;strokeColor=#666666;"),
    "nota": ("shape=note;size=14;whiteSpace=wrap;html=1;align=left;verticalAlign=top;spacing=10;fontSize=10.5;"
             "fillColor=#fffde7;strokeColor=#b7a63a;"),
}
ESTEREO = {"device": "«device»", "nuvem": "«device» «cloud»", "externo": "«device»", "ambiente": "«executionEnvironment»",
           "container": "«executionEnvironment» «container»", "planejado": "«executionEnvironment» «container»"}


class Pagina:
    def __init__(self, nome: str, titulo: str):
        self.nome, self.titulo = nome, titulo
        self.formas: dict[str, dict] = {}
        self.ordem: list[str] = []
        self.arestas: list[dict] = []

    def forma(self, fid, tipo, x, y, w, h, nome, detalhe="", dentro=None):
        """Coordenadas absolutas; a conversão para relativas ao pai é feita no XML."""
        if tipo == "artefato":
            rotulo = f"<font color=\"#666666\" style=\"font-size:9px\">«artifact»</font><br><b>{nome}</b>"
        elif tipo == "nota":
            rotulo = nome
        else:
            rotulo = (f"<font color=\"#555555\" style=\"font-size:9px\">{ESTEREO[tipo]}</font><br><b>{nome}</b>")
        if detalhe:
            rotulo += f"<br><font style=\"font-size:9.5px\">{detalhe}</font>"
        self.formas[fid] = dict(tipo=tipo, x=x, y=y, w=w, h=h, rotulo=rotulo, pai=dentro, nome=nome)
        self.ordem.append(fid)

    def liga(self, de, para, rotulo, saida, entrada, pontos=(), deploy=False):
        """saida/entrada: (fx, fy) relativos à forma (0..1). pontos: cotovelos absolutos."""
        self.arestas.append(dict(de=de, para=para, rotulo=rotulo, saida=saida, entrada=entrada,
                                 pontos=list(pontos), deploy=deploy))

    # ------------------------------------------------------------ conferência
    def conferir(self) -> list[str]:
        probs = []
        for fid, f in self.formas.items():
            p = f["pai"]
            if p:
                q = self.formas[p]
                if not (f["x"] >= q["x"] and f["y"] >= q["y"] + 30 and f["x"] + f["w"] <= q["x"] + q["w"] - 12
                        and f["y"] + f["h"] <= q["y"] + q["h"]):
                    probs.append(f"{fid} sai de dentro de {p}")
        irmaos: dict = {}
        for fid, f in self.formas.items():
            irmaos.setdefault(f["pai"], []).append(fid)
        for grupo in irmaos.values():
            for i, a in enumerate(grupo):
                for b in grupo[i + 1:]:
                    A, B = self.formas[a], self.formas[b]
                    if A["x"] < B["x"] + B["w"] and B["x"] < A["x"] + A["w"] and A["y"] < B["y"] + B["h"] and B["y"] < A["y"] + A["h"]:
                        probs.append(f"{a} sobrepõe {b}")
        for e in self.arestas:
            pts = self.pontos(e)
            dono = {e["de"], e["para"]}
            for anc in (e["de"], e["para"]):
                while self.formas[anc]["pai"]:
                    anc = self.formas[anc]["pai"]
                    dono.add(anc)
            for (ax, ay), (bx, by) in zip(pts, pts[1:]):
                for fid, f in self.formas.items():
                    if fid in dono or f["tipo"] in ("ambiente", "device", "nuvem", "externo") and self._contem_ponta(fid, e):
                        continue
                    x, y, w, h = f["x"], f["y"], f["w"], f["h"]
                    if min(ax, bx) < x + w - 1 and max(ax, bx) > x + 1 and min(ay, by) < y + h - 1 and max(ay, by) > y + 1:
                        probs.append(f"linha {e['de']}→{e['para']} atravessa {fid}")
        return probs

    def _contem_ponta(self, fid, e) -> bool:
        for ponta in (e["de"], e["para"]):
            while ponta:
                if ponta == fid:
                    return True
                ponta = self.formas[ponta]["pai"]
        return False

    def pontos(self, e):
        a, b = self.formas[e["de"]], self.formas[e["para"]]
        p0 = (a["x"] + a["w"] * e["saida"][0], a["y"] + a["h"] * e["saida"][1])
        p1 = (b["x"] + b["w"] * e["entrada"][0], b["y"] + b["h"] * e["entrada"][1])
        pts = [p0, *e["pontos"], p1]
        # Cotovelo automático: todo trecho fica horizontal ou vertical.
        out = [pts[0]]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            if ax != bx and ay != by:
                mx = round((ax + bx) / 2)
                out += [(mx, ay), (mx, by)]
            out.append((bx, by))
        return out

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
            estilo = ("dashed=1;endArrow=open;endSize=10;strokeColor=#7a7a7a;fontColor=#555555;" if e["deploy"]
                      else "endArrow=none;strokeColor=#333333;strokeWidth=1.4;")
            meio = "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in self.pontos(e)[1:-1])
            (sx, sy), (tx, ty) = e["saida"], e["entrada"]
            cells.append(
                f'<mxCell id="i{idx}-e{k}" value={quoteattr(e["rotulo"])} style="edgeStyle=none;rounded=1;'
                f"html=1;fontSize=10;labelBackgroundColor=#ffffff;exitX={sx};exitY={sy};exitDx=0;exitDy=0;entryX={tx};"
                f'entryY={ty};entryDx=0;entryDy=0;{estilo}" edge="1" parent="1" source="i{idx}-{e["de"]}" '
                f'target="i{idx}-{e["para"]}"><mxGeometry relative="1" as="geometry"><Array as="points">{meio}</Array>'
                f"</mxGeometry></mxCell>")
        largura = max(f["x"] + f["w"] for f in self.formas.values()) + 60
        altura = max(f["y"] + f["h"] for f in self.formas.values()) + 60
        return (f'<diagram name={quoteattr(self.nome)} id="impl-{idx}"><mxGraphModel dx="1600" dy="1000" grid="1" '
                f'gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
                f'pageWidth="{largura}" pageHeight="{altura}" math="0" shadow="0"><root><mxCell id="0"/>'
                f'<mxCell id="1" parent="0"/>' + "".join(cells) + "</root></mxGraphModel></diagram>")

    def svg(self) -> str:
        """Prévia para conferir posições (o entregável é o .drawio)."""
        W = max(f["x"] + f["w"] for f in self.formas.values()) + 40
        H = max(f["y"] + f["h"] for f in self.formas.values()) + 40
        cor = {"device": ("#dae8fc", "#6c8ebf"), "nuvem": ("#e1d5e7", "#9673a6"), "externo": ("#f5f5f5", "#999"),
               "ambiente": ("#fff", "#6c8ebf"), "container": ("#d5e8d4", "#82b366"), "planejado": ("#fff2cc", "#d6b656"),
               "artefato": ("#fff", "#666"), "nota": ("#fffde7", "#b7a63a")}
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="Arial">'
               f'<rect width="100%" height="100%" fill="#fff"/><text x="40" y="34" font-size="20" font-weight="bold">'
               f"{html.escape(self.titulo)}</text>"]
        for fid in self.ordem:
            f = self.formas[fid]
            fill, stroke = cor[f["tipo"]]
            tr = ' stroke-dasharray="6 4"' if f["tipo"] == "planejado" else ""
            out.append(f'<rect x="{f["x"]}" y="{f["y"]}" width="{f["w"]}" height="{f["h"]}" fill="{fill}" '
                       f'stroke="{stroke}"{tr}/>')
            texto = html.unescape(f["rotulo"].replace("<br>", "\n"))
            import re
            linhas = re.sub(r"<[^>]+>", "", texto).split("\n")
            for i, ln in enumerate(linhas[:6]):
                out.append(f'<text x="{f["x"] + 8}" y="{f["y"] + 16 + i * 13}" font-size="10">{html.escape(ln)}</text>')
        for e in self.arestas:
            pts = self.pontos(e)
            tr = ' stroke-dasharray="6 4"' if e["deploy"] else ""
            out.append(f'<polyline points="{" ".join(f"{x},{y}" for x, y in pts)}" fill="none" stroke="#c00" '
                       f'stroke-width="1.5"{tr}/>')
        out.append("</svg>")
        return "".join(out)


AVISOS = ("<b>Notas</b><br>• RNF02: só o proxy é exposto, na porta 443 (TLS ≥ 1.2); site, API e banco ficam na rede "
          "interna do Compose. O cookie de sessão é httponly e, em produção, Secure (COOKIE_SEGURO=1).<br>"
          "• RNF03: o log de auditoria fica no PostgreSQL, que o banco não deixa alterar nem apagar; "
          "o volume <i>dados</i> precisa de backup para a retenção de 5 anos.<br>"
          "• RNF07: 99% de disponibilidade no pico, com recuperação em até 30 min (reinício dos containers "
          "e restauração do backup).<br>"
          "• A API aplica as migrações ao subir (alembic upgrade head) e só então atende.<br>"
          "• Em amarelo tracejado: o que ainda não existe no repositório (proxy HTTPS).")


def producao() -> Pagina:
    p = Pagina("1 · Produção (servidor com Docker)",
               "SIGA UEA · Diagrama de implantação · Produção: um servidor com Docker Compose (HT06)")
    p.forma("cli", "device", 40, 110, 280, 220, "Computador ou celular do usuário",
            "aluno, docente, coordenação, banca")
    p.forma("nav", "ambiente", 60, 175, 240, 135, "Navegador web", "Chrome ou Safari, a partir de 360 px (RNF04)",
            dentro="cli")
    p.forma("ui", "artefato", 75, 240, 210, 55, "Interface SIGA", dentro="nav")
    p.forma("git", "externo", 40, 470, 280, 150, "GitHub", "repositório SIGA-UEA/sigauea")
    p.forma("repo", "artefato", 60, 540, 240, 60, "código da branch main", dentro="git")

    p.forma("srv", "device", 380, 70, 1120, 700, "Servidor de aplicação · VM Linux",
            "2 vCPU · 4 GB de RAM · 20 GB de disco · provedor a definir (HT06)")
    p.forma("dock", "ambiente", 400, 150, 1080, 600, "Docker Engine + Docker Compose", "docker-compose.yml",
            dentro="srv")
    p.forma("proxy", "planejado", 420, 225, 210, 190, "proxy · Caddy ou Nginx", "porta 443, a única exposta",
            dentro="dock")
    p.forma("cert", "artefato", 435, 320, 180, 70, "certificado TLS<br>(Let's Encrypt)", dentro="proxy")
    p.forma("web", "container", 670, 225, 230, 190, "web · Node.js 24", "Next.js 16 · porta 3000", dentro="dock")
    p.forma("webimg", "artefato", 685, 300, 200, 55, "imagem web (Dockerfile)", dentro="web")
    p.forma("webcfg", "artefato", 685, 362, 200, 40, "API_URL=http://api:8000", dentro="web")
    p.forma("api", "container", 940, 225, 260, 290, "api · Python 3.12 + Uvicorn", "FastAPI · porta 8000",
            dentro="dock")
    p.forma("apiimg", "artefato", 955, 300, 230, 50, "imagem api (backend/Dockerfile)", dentro="api")
    p.forma("mig", "artefato", 955, 358, 230, 50, "migrações Alembic 0001 a 0004", dentro="api")
    p.forma("seed", "artefato", 955, 416, 230, 50, "carga inicial (python -m app.seed)", dentro="api")
    p.forma("db", "container", 1240, 225, 220, 290, "db · PostgreSQL 16", "porta 5432 · só na rede interna",
            dentro="dock")
    p.forma("banco", "artefato", 1255, 300, 190, 55, "banco siga<br>(23 tabelas hoje, 45 no fim)", dentro="db")
    p.forma("vol", "artefato", 1255, 368, 190, 55, "volume <i>dados</i><br>(/var/lib/postgresql/data)", dentro="db")
    p.forma("env", "artefato", 670, 470, 230, 110, ".env do servidor",
            "DATABASE_URL, POSTGRES_PASSWORD, FRONTEND_URL, COOKIE_SEGURO=1, SMTP_*", dentro="dock")

    p.forma("smtp", "externo", 1580, 560, 260, 150, "Servidor de e-mail", "smtp.gmail.com · conta siga.uea1@gmail.com")
    p.forma("nota", "nota", 1580, 70, 340, 330, AVISOS)

    p.liga("cli", "proxy", "HTTPS · TLS ≥ 1.2 · :443", (1, 0.55), (0, 0.4))
    p.liga("proxy", "web", "HTTP · :3000", (1, 0.4), (0, 0.4))
    p.liga("web", "api", "HTTP · :8000<br>/api/v1/* (rewrite)", (1, 0.4), (0, 0.27))
    p.liga("api", "db", "TCP · :5432<br>psycopg", (1, 0.27), (0, 0.27))
    p.liga("api", "smtp", "SMTP · STARTTLS · :587<br>(ativação, senha, orientação)", (0.5, 1), (0, 0.5),
           pontos=[(1070, 635)])
    p.liga("git", "srv", "«deploy» git pull +<br>docker compose up --build", (1, 0.5), (0, 0.6), deploy=True)
    return p


def homologacao() -> Pagina:
    p = Pagina("2 · Homologação (serviços gratuitos)",
               "SIGA UEA · Diagrama de implantação · Homologação: serviços gratuitos separados")
    p.forma("cli", "device", 40, 110, 280, 220, "Computador ou celular do usuário", "coordenação e equipe testando")
    p.forma("nav", "ambiente", 60, 175, 240, 135, "Navegador web", "Chrome ou Safari", dentro="cli")
    p.forma("ui", "artefato", 75, 240, 210, 55, "Interface SIGA", dentro="nav")
    p.forma("git", "externo", 40, 500, 280, 150, "GitHub", "repositório SIGA-UEA/sigauea")
    p.forma("repo", "artefato", 60, 570, 240, 60, "código da branch main", dentro="git")

    p.forma("vercel", "nuvem", 400, 90, 320, 290, "Vercel (plano Hobby)", "HTTPS automático · domínio *.vercel.app")
    p.forma("vnode", "ambiente", 420, 165, 280, 195, "Node.js 24 (funções do Next)", dentro="vercel")
    p.forma("site", "artefato", 435, 225, 250, 55, "site Next.js 16 (build da main)", dentro="vnode")
    p.forma("vcfg", "artefato", 435, 290, 250, 55, "API_URL = endereço da API no Render", dentro="vnode")

    p.forma("render", "nuvem", 800, 90, 360, 360, "Render (Free Web Service)",
            "dorme após ~15 min sem uso; o 1º acesso leva 30 a 60 s")
    p.forma("rnode", "container", 820, 175, 320, 255, "Python 3.12 + Uvicorn", "FastAPI", dentro="render")
    p.forma("rapi", "artefato", 835, 245, 290, 50, "API SIGA (backend/)", dentro="rnode")
    p.forma("rstart", "artefato", 835, 302, 290, 50, "start: python -m app.seed && uvicorn …", dentro="rnode")
    p.forma("rcfg", "artefato", 835, 359, 290, 55, "DATABASE_URL, SMTP_*, FRONTEND_URL,<br>COOKIE_SEGURO=1", dentro="rnode")

    p.forma("neon", "nuvem", 1240, 90, 330, 240, "Neon ou Supabase (plano grátis)",
            "Supabase: usar o Session pooler (IPv4)")
    p.forma("pg", "ambiente", 1260, 165, 290, 145, "PostgreSQL 16 gerenciado", "conexão com TLS", dentro="neon")
    p.forma("pbanco", "artefato", 1275, 235, 260, 55, "banco siga", dentro="pg")

    p.forma("smtp", "externo", 1240, 420, 330, 160, "Servidor de e-mail",
            "smtp.gmail.com :587 · se o Render bloquear SMTP, trocar por Brevo ou Resend (API HTTPS)")
    p.forma("nota", "nota", 400, 680, 760, 120,
            "<b>Notas</b><br>• Ambiente para homologação e apresentação (HT06), sem custo e sem cartão.<br>"
            "• Não cumpre o RNF07 (99%): a API dorme. Abrir o sistema alguns minutos antes de apresentar.<br>"
            "• Os limites dos planos grátis mudam: conferir no site de cada serviço antes de criar as contas.<br>"
            "• O cookie de sessão continua na mesma origem: o navegador só fala com a Vercel, que repassa /api/v1.")

    p.liga("cli", "vercel", "HTTPS · :443", (1, 0.5), (0, 0.55))
    p.liga("vercel", "render", "HTTPS<br>/api/v1/* (rewrite)", (1, 0.45), (0, 0.4))
    p.liga("render", "neon", "TCP + TLS · :5432", (1, 0.3), (0, 0.4))
    p.liga("render", "smtp", "SMTP · STARTTLS · :587", (1, 0.85), (0, 0.4), pontos=[(1200, 396), (1200, 484)])
    p.liga("git", "vercel", "«deploy» automático a cada push", (1, 0.3), (0.5, 1), pontos=[(560, 545)], deploy=True)
    p.liga("git", "render", "«deploy» automático a cada push", (1, 0.7), (0.3, 1), pontos=[(908, 605)], deploy=True)
    return p


def desenvolvimento() -> Pagina:
    p = Pagina("3 · Desenvolvimento local", "SIGA UEA · Diagrama de implantação · Desenvolvimento local")
    p.forma("pc", "device", 40, 70, 1400, 560, "Computador do desenvolvedor", "Windows 11, macOS ou Linux")
    p.forma("nav", "ambiente", 60, 150, 220, 140, "Navegador web", dentro="pc")
    p.forma("url", "artefato", 75, 215, 190, 50, "http://localhost:3000", dentro="nav")
    p.forma("node", "ambiente", 330, 150, 280, 220, "Node.js 24", dentro="pc")
    p.forma("dev", "artefato", 345, 205, 250, 50, "npm run dev (Next.js, porta 3000)", dentro="node")
    p.forma("prx", "artefato", 345, 265, 250, 50, "proxy.ts + rewrites de /api/v1", dentro="node")
    p.forma("py", "ambiente", 660, 150, 320, 330, "Python 3.12 (backend/.venv)", dentro="pc")
    p.forma("uv", "artefato", 675, 205, 290, 50, "uvicorn app.main:app --reload (8000)", dentro="py")
    p.forma("tst", "artefato", 675, 265, 290, 50, "pytest (testes da API)", dentro="py")
    p.forma("denv", "artefato", 675, 325, 290, 60, "backend/.env (fora do git)<br>SMTP e FRONTEND_URL", dentro="py")
    p.forma("sd", "artefato", 675, 395, 290, 60, "python -m app.seed --demo<br>(contas e turma de demonstração)",
            dentro="py")
    p.forma("sqlite", "artefato", 1160, 160, 240, 60, "backend/siga_dev.db (SQLite)", dentro="pc")
    p.forma("pgl", "ambiente", 1160, 260, 240, 140, "PostgreSQL 16 (opcional)", "Docker ou instalação local",
            dentro="pc")
    p.forma("pgb", "artefato", 1175, 330, 210, 50, "banco de teste", dentro="pgl")

    p.forma("smtp", "externo", 1520, 150, 280, 160, "Servidor de e-mail",
            "smtp.gmail.com :587 · opcional: sem SMTP, o e-mail sai no terminal da API")

    p.liga("nav", "node", "HTTP · :3000", (1, 0.5), (0, 0.32))
    p.liga("node", "py", "HTTP · :8000<br>/api/v1/*", (1, 0.32), (0, 0.21))
    p.liga("py", "sqlite", "arquivo (SQLAlchemy)", (1, 0.12), (0, 0.5))
    p.liga("py", "pgl", "TCP · :5432<br>(TEST_DATABASE_URL)", (1, 0.55), (0, 0.5))
    p.liga("py", "smtp", "SMTP · :587 (via backend/.env)", (0.5, 1), (0.5, 1), pontos=[(820, 580), (1660, 580)])
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
    if len(sys.argv) > 1:
        for i, p in enumerate(paginas):
            Path(sys.argv[1], f"impl-{i}.svg").write_text(p.svg(), encoding="utf8")
    raise SystemExit(1 if total else 0)


if __name__ == "__main__":
    main()
