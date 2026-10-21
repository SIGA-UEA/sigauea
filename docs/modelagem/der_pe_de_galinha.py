"""DER do SIGA UEA na notação pé de galinha (crow's foot), gerado do modelo lógico.

A fonte é a mesma de modelo_logico.py (tabelas, colunas e chaves); aqui só muda o desenho.
Gera docs/modelagem/der-pe-de-galinha-siga-uea.drawio com três páginas:

  1. Visão geral      as 46 entidades (só o nome) e todos os relacionamentos com cardinalidade
  2. Completo         as 46 tabelas com todas as colunas; cada linha liga a FK à PK
  3. Implementado     as tabelas que já existem nas migrações (S02 e S03)

O posicionamento e o roteamento das linhas são do ELK (elk_layout.mjs):

    npm i --no-save elkjs@0.9.3
    python docs/modelagem/der_pe_de_galinha.py [pasta-para-as-previas-svg]
"""

from __future__ import annotations

import html
import json
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import quoteattr

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import modelo_logico as ml  # noqa: E402

RAIZ = AQUI.parent.parent
CAB, LIN = 30, 20
NOME_MOD = {
    "MOD01": "Usuários e acesso",
    "MOD02": "Ideias de TCC",
    "MOD03": "Gestão e acompanhamento",
    "MOD04": "Defesa e agenda",
    "MOD05": "Publicação",
}


# ---------------------------------------------------------------- relacionamentos
def relacoes(tabelas: set[str], so_implementado: bool) -> list[dict]:
    """Uma relação por FK: pai (tabela referenciada) -> filho (tabela com a FK)."""
    out = []
    for t in ml.T:
        if t.nome not in tabelas:
            continue
        pks = [k for k in t.cols if k.pk]
        for col in t.cols:
            if not col.fk or col.fk not in tabelas or (so_implementado and col.novo):
                continue
            um_para_um = (col.pk and len(pks) == 1) or col.uk
            out.append(dict(
                id=f"{t.nome}.{col.nome}",
                pai=col.fk,
                filho=t.nome,
                coluna=col.nome,
                ponta_pai="ERzeroToOne" if col.nulo else "ERmandOne",
                ponta_filho="ERzeroToOne" if um_para_um else "ERzeroToMany",
                # quem registrou/decidiu: relação real, mas secundária no desenho
                secundaria=col.fk == "usuario"
                and (col.nome.endswith("_por") or t.nome.startswith("historico_") or t.nome == "log_auditoria"),
            ))
    return out


def colunas(t, so_implementado: bool):
    return [c for c in t.cols if not (so_implementado and c.novo)]


def texto_coluna(c) -> str:
    chaves = " ".join(k for k, v in (("PK", c.pk), ("FK", bool(c.fk)), ("UK", c.uk)) if v)
    return f"{chaves:<8} {c.nome}: {c.tipo}{'' if c.nulo else ' NN'}"


def largura_tabela(t, cols) -> int:
    maior = max([len(texto_coluna(c)) for c in cols] + [len(t.nome) + 8])
    return max(200, int(maior * 6.1) + 34)


# ---------------------------------------------------------------- grafos para o ELK
def grafo(pid: str, nomes: list[str], detalhe: bool, so_implementado: bool) -> tuple[dict, list[dict]]:
    tabelas = set(nomes)
    rels = relacoes(tabelas, so_implementado)
    if not detalhe:  # visão geral: as ligações de registro ficam só nas páginas com atributos
        rels = [r for r in rels if not r["secundaria"]]
    nos = []
    for nome in nomes:
        t = ml.POR_NOME[nome]
        if not detalhe:
            nos.append(dict(id=nome, width=max(150, int(len(nome) * 7.6) + 34), height=44))
            continue
        cols = colunas(t, so_implementado)
        w = largura_tabela(t, cols)
        portas = []
        for i, c in enumerate(cols):
            y = CAB + i * LIN + LIN / 2
            if c.pk:  # PK recebe as linhas dos filhos pelos dois lados
                portas.append(dict(id=f"{nome}#{c.nome}#E", x=w, y=y, width=1, height=1,
                                   layoutOptions={"elk.port.side": "EAST"}))
            if c.fk:
                portas.append(dict(id=f"{nome}#{c.nome}#W", x=-1, y=y, width=1, height=1,
                                   layoutOptions={"elk.port.side": "WEST"}))
        nos.append(dict(id=nome, width=w, height=CAB + LIN * len(cols), ports=portas,
                        layoutOptions={"elk.portConstraints": "FIXED_POS"}))
    arestas = []
    for r in rels:
        if detalhe:
            pk = next(c.nome for c in ml.POR_NOME[r["pai"]].cols if c.pk)
            fonte, alvo = f"{r['pai']}#{pk}#E", f"{r['filho']}#{r['coluna']}#W"
        else:
            fonte, alvo = r["pai"], r["filho"]
        a = dict(id=r["id"], sources=[fonte], targets=[alvo])
        if not detalhe and rotulo_visivel(r):
            a["labels"] = [dict(text=r["coluna"], width=len(r["coluna"]) * 5.6 + 8, height=13)]
        arestas.append(a)
    opcoes = {"elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES"}
    return dict(id=pid, children=nos, edges=arestas, layoutOptions=opcoes), rels


def rotulo_visivel(r) -> bool:
    """Na visão geral, só o nome da FK que diz algo além de "<pai>_id"."""
    return r["coluna"] != f"{r['pai']}_id" and not r["secundaria"]


def layout(grafos: list[dict]) -> list[dict]:
    proc = subprocess.run(["node", str(AQUI / "elk_layout.mjs")], input=json.dumps(grafos),
                          capture_output=True, text=True, encoding="utf8", cwd=RAIZ)
    if proc.returncode:
        raise SystemExit("ELK falhou (rode `npm i --no-save elkjs@0.9.3`):\n" + proc.stderr)
    return json.loads(proc.stdout)


# ---------------------------------------------------------------- draw.io
def pontos_da_aresta(e) -> list[tuple[float, float]]:
    s = e["sections"][0]
    return [(s["startPoint"]["x"], s["startPoint"]["y"])] + \
        [(p["x"], p["y"]) for p in s.get("bendPoints", [])] + [(s["endPoint"]["x"], s["endPoint"]["y"])]


def posicao_rotulo(pts, cx, cy):
    """Converte o centro absoluto do rótulo para o formato do draw.io (fração ao longo da linha + deslocamento)."""
    tam = [((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5 for (ax, ay), (bx, by) in zip(pts, pts[1:])]
    total = sum(tam) or 1
    melhor = (float("inf"), 0.0, pts[0])
    andado = 0.0
    for ((ax, ay), (bx, by)), L in zip(zip(pts, pts[1:]), tam):
        t = 0.0 if L == 0 else max(0.0, min(1.0, ((cx - ax) * (bx - ax) + (cy - ay) * (by - ay)) / (L * L)))
        px, py = ax + t * (bx - ax), ay + t * (by - ay)
        d = (px - cx) ** 2 + (py - cy) ** 2
        if d < melhor[0]:
            melhor = (d, andado + t * L, (px, py))
        andado += L
    _, dist, (px, py) = melhor
    return dist / total * 2 - 1, cx - px, cy - py


def pagina(idx: int, nome_pag: str, titulo: str, g: dict, rels: list[dict], detalhe: bool,
           so_implementado: bool, legenda: str) -> str:
    por_id = {n["id"]: n for n in g["children"]}
    rel_por_id = {r["id"]: r for r in rels}
    cells = [f'<mxCell id="p{idx}-t" value={quoteattr(titulo)} style="text;html=1;fontSize=22;fontStyle=1;align=left;" '
             f'vertex="1" parent="1"><mxGeometry x="40" y="14" width="1400" height="36" as="geometry"/></mxCell>']
    for n in g["children"]:
        t = ml.POR_NOME[n["id"]]
        fill, stroke = ml.CORES[t.modulo]
        tracejado = "" if t.implementada else "dashed=1;dashPattern=6 4;"
        cid = f"p{idx}-{t.nome}"
        if not detalhe:
            rot = (f"<b>{html.escape(t.nome)}</b><br><font style=\"font-size:9px\" color=\"#555555\">"
                   f"{t.modulo} · {html.escape(NOME_MOD[t.modulo])}</font>")
            cells.append(f'<mxCell id="{cid}" value={quoteattr(rot)} style="rounded=1;arcSize=8;whiteSpace=wrap;html=1;'
                         f'fillColor={fill};strokeColor={stroke};strokeWidth=1.5;fontSize=12;{tracejado}" vertex="1" '
                         f'parent="1"><mxGeometry x="{n["x"]:.0f}" y="{n["y"]:.0f}" width="{n["width"]:.0f}" '
                         f'height="{n["height"]:.0f}" as="geometry"/></mxCell>')
            continue
        cells.append(
            f'<mxCell id="{cid}" value={quoteattr(t.nome)} style="swimlane;fontStyle=1;childLayout=stackLayout;horizontal=1;'
            f"startSize={CAB};horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=0;marginBottom=0;"
            f'html=1;fillColor={fill};strokeColor={stroke};fontSize=12;rounded=1;arcSize=4;{tracejado}" vertex="1" parent="1">'
            f'<mxGeometry x="{n["x"]:.0f}" y="{n["y"]:.0f}" width="{n["width"]:.0f}" height="{n["height"]:.0f}" '
            f'as="geometry"/></mxCell>')
        for i, c in enumerate(colunas(t, so_implementado)):
            cells.append(
                f'<mxCell id="{cid}-{i}" value={quoteattr(ml.rotulo_coluna(c))} style="text;strokeColor=none;fillColor=none;'
                f'align=left;verticalAlign=middle;spacingLeft=6;overflow=hidden;html=1;fontSize=10;" vertex="1" '
                f'parent="{cid}"><mxGeometry y="{CAB + i * LIN}" width="{n["width"]:.0f}" height="{LIN}" '
                f'as="geometry"/></mxCell>')
    for k, e in enumerate(g["edges"]):
        r = rel_por_id[e["id"]]
        pts = pontos_da_aresta(e)
        pai, filho = por_id[r["pai"]], por_id[r["filho"]]

        def rel_xy(no, p):
            return (min(1, max(0, (p[0] - no["x"]) / no["width"])), min(1, max(0, (p[1] - no["y"]) / no["height"])))

        ex, ey = rel_xy(pai, pts[0])
        nx, ny = rel_xy(filho, pts[-1])
        cor = "#b3b3b3" if r["secundaria"] else "#444444"
        largura = 1 if r["secundaria"] else 1.4
        meio = "".join(f'<mxPoint x="{x:.0f}" y="{y:.0f}"/>' for x, y in pts[1:-1])
        eid = f"p{idx}-r{k}"
        cells.append(
            f'<mxCell id="{eid}" value="" style="edgeStyle=none;rounded=1;html=1;startArrow={r["ponta_pai"]};'
            f'endArrow={r["ponta_filho"]};startFill=0;endFill=0;startSize=10;endSize=10;strokeColor={cor};'
            f'strokeWidth={largura};exitX={ex:.4f};exitY={ey:.4f};exitDx=0;exitDy=0;exitPerimeter=0;entryX={nx:.4f};'
            f'entryY={ny:.4f};entryDx=0;entryDy=0;entryPerimeter=0;" edge="1" parent="1" source="p{idx}-{r["pai"]}" '
            f'target="p{idx}-{r["filho"]}"><mxGeometry relative="1" as="geometry">'
            f'<mxPoint x="{pts[0][0]:.0f}" y="{pts[0][1]:.0f}" as="sourcePoint"/>'
            f'<mxPoint x="{pts[-1][0]:.0f}" y="{pts[-1][1]:.0f}" as="targetPoint"/>'
            f'<Array as="points">{meio}</Array></mxGeometry></mxCell>')
        for j, lab in enumerate(e.get("labels", [])):
            fx, dx, dy = posicao_rotulo(pts, lab["x"] + lab["width"] / 2, lab["y"] + lab["height"] / 2)
            cells.append(
                f'<mxCell id="{eid}-l{j}" value={quoteattr(lab["text"])} style="edgeLabel;html=1;align=center;'
                f'verticalAlign=middle;resizable=0;points=[];fontSize=9;fontColor=#555555;labelBackgroundColor=#ffffff;" '
                f'vertex="1" connectable="0" parent="{eid}"><mxGeometry x="{fx:.4f}" relative="1" as="geometry">'
                f'<mxPoint x="{dx:.0f}" y="{dy:.0f}" as="offset"/></mxGeometry></mxCell>')
    largura_pag, altura_pag = g["width"], g["height"]
    cells.append(f'<mxCell id="p{idx}-leg" value={quoteattr(legenda)} style="text;html=1;align=left;verticalAlign=top;'
                 f'spacing=10;fillColor=#f5f5f5;strokeColor=#999999;rounded=1;fontSize=11;whiteSpace=wrap;" vertex="1" '
                 f'parent="1"><mxGeometry x="{largura_pag + 20:.0f}" y="70" width="380" height="250" as="geometry"/></mxCell>')
    return (f'<diagram name={quoteattr(nome_pag)} id="pe-{idx}"><mxGraphModel dx="1600" dy="1000" grid="1" gridSize="10" '
            f'guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
            f'pageWidth="{largura_pag + 440:.0f}" pageHeight="{altura_pag + 40:.0f}" math="0" shadow="0"><root>'
            f'<mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(cells) + "</root></mxGraphModel></diagram>")


LEGENDA_BASE = (
    "<b>Notação pé de galinha (crow's foot)</b><br>"
    "Ponta no lado <b>pai</b>: <b>||</b> exatamente um (FK obrigatória) · <b>o|</b> zero ou um (FK opcional)<br>"
    "Ponta no lado <b>filho</b>: <b>o&lt;</b> zero ou muitos · <b>o|</b> zero ou um (FK única)<br>"
    "Linha cinza clara: quem registrou ou decidiu (FK para usuario em histórico, log e colunas *_por)<br><br>"
    "<b>Cores por módulo</b><br>"
    + "<br>".join(f'<font color="{ml.CORES[m][1]}">■</font> {m} · {n}' for m, n in NOME_MOD.items())
)


def svg(g: dict, rels: list[dict], detalhe: bool, so_implementado: bool) -> str:
    """Prévia para conferir o desenho (o entregável é o .drawio)."""
    W, H = g["width"] + 20, g["height"] + 20
    rel_por_id = {r["id"]: r for r in rels}
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" font-family="Arial">'
           f'<rect width="100%" height="100%" fill="#fff"/>']
    for e in g["edges"]:
        r = rel_por_id[e["id"]]
        pts = pontos_da_aresta(e)
        cor = "#bbb" if r["secundaria"] else "#444"
        out.append(f'<polyline points="{" ".join(f"{x:.0f},{y:.0f}" for x, y in pts)}" fill="none" stroke="{cor}" '
                   f'stroke-width="1.3"/>')
        for (x, y), (x2, y2), ponta in ((pts[-1], pts[-2], r["ponta_filho"]), (pts[0], pts[1], r["ponta_pai"])):
            dx, dy = x2 - x, y2 - y
            L = (dx * dx + dy * dy) ** 0.5 or 1
            ux, uy = dx / L, dy / L
            vx, vy = -uy, ux
            if ponta == "ERzeroToMany":
                for s in (-1, 0, 1):
                    out.append(f'<line x1="{x + vx * 6 * s:.1f}" y1="{y + vy * 6 * s:.1f}" x2="{x + ux * 10:.1f}" '
                               f'y2="{y + uy * 10:.1f}" stroke="{cor}"/>')
                out.append(f'<circle cx="{x + ux * 15:.1f}" cy="{y + uy * 15:.1f}" r="3" fill="#fff" stroke="{cor}"/>')
            else:
                out.append(f'<line x1="{x + ux * 8 + vx * 6:.1f}" y1="{y + uy * 8 + vy * 6:.1f}" '
                           f'x2="{x + ux * 8 - vx * 6:.1f}" y2="{y + uy * 8 - vy * 6:.1f}" stroke="{cor}"/>')
                if ponta == "ERmandOne":
                    out.append(f'<line x1="{x + ux * 13 + vx * 6:.1f}" y1="{y + uy * 13 + vy * 6:.1f}" '
                               f'x2="{x + ux * 13 - vx * 6:.1f}" y2="{y + uy * 13 - vy * 6:.1f}" stroke="{cor}"/>')
                else:
                    out.append(f'<circle cx="{x + ux * 15:.1f}" cy="{y + uy * 15:.1f}" r="3" fill="#fff" stroke="{cor}"/>')
        for lab in e.get("labels", []):
            out.append(f'<text x="{lab["x"] + lab["width"] / 2:.0f}" y="{lab["y"] + 10:.0f}" font-size="9" '
                       f'text-anchor="middle" fill="#555" stroke="#fff" stroke-width="3" paint-order="stroke">'
                       f'{html.escape(lab["text"])}</text>')
    for n in g["children"]:
        t = ml.POR_NOME[n["id"]]
        fill, stroke = ml.CORES[t.modulo]
        tr = "" if t.implementada else ' stroke-dasharray="6 4"'
        out.append(f'<rect x="{n["x"]:.0f}" y="{n["y"]:.0f}" width="{n["width"]:.0f}" height="{n["height"]:.0f}" '
                   f'rx="5" fill="{fill if not detalhe else "#fff"}" stroke="{stroke}" stroke-width="1.5"{tr}/>')
        if detalhe:
            out.append(f'<rect x="{n["x"]:.0f}" y="{n["y"]:.0f}" width="{n["width"]:.0f}" height="{CAB}" rx="5" '
                       f'fill="{fill}" stroke="{stroke}"/>')
            out.append(f'<text x="{n["x"] + n["width"] / 2:.0f}" y="{n["y"] + 20:.0f}" font-size="12" '
                       f'font-weight="bold" text-anchor="middle">{t.nome}</text>')
            for i, c in enumerate(colunas(t, so_implementado)):
                out.append(f'<text x="{n["x"] + 6:.0f}" y="{n["y"] + CAB + i * LIN + 14:.0f}" font-size="10" '
                           f'xml:space="preserve" font-family="Consolas,monospace">'
                           f'{html.escape(texto_coluna(c))}</text>')
        else:
            out.append(f'<text x="{n["x"] + n["width"] / 2:.0f}" y="{n["y"] + 20:.0f}" font-size="12" '
                       f'font-weight="bold" text-anchor="middle">{t.nome}</text>')
            out.append(f'<text x="{n["x"] + n["width"] / 2:.0f}" y="{n["y"] + 35:.0f}" font-size="9" fill="#555" '
                       f'text-anchor="middle">{t.modulo} · {html.escape(NOME_MOD[t.modulo])}</text>')
    out.append("</svg>")
    return "".join(out)


def conferir(g: dict) -> list[str]:
    """Nenhum trecho de linha pode atravessar uma tabela que não é a sua ponta."""
    probs = []
    caixas = {n["id"]: (n["x"], n["y"], n["width"], n["height"]) for n in g["children"]}
    for e in g["edges"]:
        pts = pontos_da_aresta(e)
        pontas = {s.split("#")[0] for s in e["sources"] + e["targets"]}
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            for nome, (x, y, w, h) in caixas.items():
                if nome in pontas:
                    continue
                if min(ax, bx) < x + w - 1 and max(ax, bx) > x + 1 and min(ay, by) < y + h - 1 and max(ay, by) > y + 1:
                    probs.append(f"{e['id']} atravessa {nome}")
    return probs


def main() -> None:
    ml.validar()
    todas = [t.nome for t in ml.T]
    feitas = [t.nome for t in ml.T if t.implementada]
    specs = [
        (f"1 · Visão geral ({len(todas)} entidades)", "SIGA UEA · DER pé de galinha · visão geral do sistema", todas, False, False),
        ("2 · Completo com atributos", "SIGA UEA · DER pé de galinha · sistema completo, com atributos", todas, True, False),
        (f"3 · Implementado ({len(feitas)} tabelas)",
         f"SIGA UEA · DER pé de galinha · o que já está no banco (S02 e S03, {len(feitas)} tabelas)", feitas, True, True),
    ]
    entradas, todas_rels = [], []
    for i, (_, _, nomes, detalhe, so_impl) in enumerate(specs):
        g, rels = grafo(f"g{i}", nomes, detalhe, so_impl)
        entradas.append(g)
        todas_rels.append(rels)
    saidas = layout(entradas)
    paginas, total = [], 0
    for i, ((nome_pag, titulo, nomes, detalhe, so_impl), g, rels) in enumerate(zip(specs, saidas, todas_rels)):
        extra = ("<br><br>Borda contínua: tabela já criada por migração · tracejada: planejada"
                 if not so_impl else "<br><br>Só tabelas e colunas que já existem nas migrações 0001 a 0004.")
        if detalhe and not so_impl:
            extra += "<br><i>Itálico</i>: coluna planejada em tabela que já existe"
        if not detalhe:
            extra += ("<br>Rótulo na linha: nome da FK quando não é &lt;pai&gt;_id"
                      "<br>Ligações de registro (quem cadastrou ou decidiu) estão na página 2")
        paginas.append(pagina(i, nome_pag, titulo, g, rels, detalhe, so_impl, LEGENDA_BASE + extra))
        probs = conferir(g)
        total += len(probs)
        print(f"{nome_pag}: {len(g['children'])} tabelas, {len(g['edges'])} relacionamentos, "
              f"{len(probs)} cruzamentos de caixa")
        for p in probs[:10]:
            print("   ", p)
        if len(sys.argv) > 1:
            Path(sys.argv[1], f"pe-{i}.svg").write_text(svg(g, rels, detalhe, so_impl), encoding="utf8")
    (AQUI / "der-pe-de-galinha-siga-uea.drawio").write_text(
        '<mxfile host="app.diagrams.net">' + "".join(paginas) + "</mxfile>", encoding="utf8")
    raise SystemExit(1 if total else 0)


if __name__ == "__main__":
    main()
