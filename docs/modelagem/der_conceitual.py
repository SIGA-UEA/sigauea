"""DER conceitual do SIGA UEA no estilo brModelo.

Gera docs/modelagem/der-conceitual-siga-uea.drawio (uma página por módulo) e confere
o desenho: nenhuma forma sobreposta, nenhuma linha atravessando forma ou atributo.

    python docs/modelagem/der_conceitual.py [pasta_para_previas_svg]

Convenções (as do brModelo):
  retângulo = entidade · retângulo duplo = entidade fraca
  losango = relacionamento · retângulo com losango dentro = entidade associativa
  bolinha preta = identificador · bolinha branca = atributo · "Nome (1, n)" = multivalorado
  triângulo = especialização (Usuário em Aluno, Docente e Membro externo)
  (mín,máx) ao lado da entidade = com quantas ocorrências dela uma ocorrência
  do outro lado se relaciona. Ex.: Aluno (1,1) -elabora- (0,n) TCC.

O conceitual mostra só o negócio: chaves estrangeiras, tipos e controles técnicos
(sessão, link de ativação, fila de e-mail, log) ficam no modelo lógico
(docs/modelagem/modelo-logico-siga-uea.drawio).
"""

from __future__ import annotations

import html
import sys
from pathlib import Path
from xml.sax.saxutils import quoteattr

AQUI = Path(__file__).resolve().parent

ENT_W, ENT_H = 150, 50
REL_W, REL_H = 130, 60
ASS_W, ASS_H = 190, 80
TRI_W, TRI_H = 70, 50
LINHA_ATR = 24
FONTE = 7.2  # largura média de um caractere (px) para estimar o texto


def larg_texto(t: str) -> float:
    return FONTE * len(t) + 6


class Pagina:
    def __init__(self, nome: str, titulo: str):
        self.nome, self.titulo = nome, titulo
        self.formas: dict[str, dict] = {}
        self.atrs: list[dict] = []  # bolinhas + textos
        self.pentes: list[tuple] = []  # segmentos das linhas dos atributos (x1,y1,x2,y2,dono)
        self.ligacoes: list[dict] = []  # relacionamento <-> entidade, já roteadas
        self.retas: list[dict] = []  # linhas da especialização
        self.cards: list[dict] = []
        self._pedidos: list[tuple] = []

    # ------------------------------------------------------------ formas
    def ent(self, eid, rotulo, x, y, atributos=(), fraca=False, ref=False, w=ENT_W, h=ENT_H, pente="S"):
        self.formas[eid] = dict(
            tipo="ent", x=x, y=y, w=w, h=h, rotulo=rotulo, fraca=fraca, ref=ref, pente=pente
        )
        self._pente(eid, atributos)

    def assoc(self, aid, rotulo, rel, x, y, atributos=(), pente="S"):
        self.formas[aid] = dict(tipo="assoc", x=x, y=y, w=ASS_W, h=ASS_H, rotulo=rotulo, rel=rel, pente=pente)
        self._pente(aid, atributos)

    def rel(self, rid, rotulo, x=None, y=None, atributos=(), identificadora=False):
        """Sem x/y, o losango é posicionado automaticamente em rotear()."""
        self.formas[rid] = dict(
            tipo="rel",
            x=x,
            y=y,
            w=REL_W,
            h=REL_H,
            rotulo=rotulo,
            ident=identificadora,
            pente="S",
            auto=x is None,
            atrs_pend=list(atributos),
        )
        if x is not None:
            self._pente(rid, atributos, tronco=True)

    def tri(self, tid, x, y, geral, filhos):
        self.formas[tid] = dict(tipo="tri", x=x, y=y, w=TRI_W, h=TRI_H, rotulo="")
        self._pedidos.append(("geral", tid, geral, ""))
        for f in filhos:
            topo = self.formas[f]
            self.retas.append(
                dict(de=tid, para=f, pts=[(x + TRI_W / 2, y + TRI_H), (topo["x"] + topo["w"] / 2, topo["y"])])
            )

    def liga(self, rid, eid, card, prefer=None):
        self._pedidos.append(("rel", rid, eid, card, prefer))

    def _pente(self, dono, atributos, tronco=False):
        """Atributos em pente embaixo da forma, como no brModelo."""
        if not atributos:
            return
        f = self.formas[dono]
        n = len(atributos)
        cima = f.get("pente") == "N"
        base = f["y"] if cima else f["y"] + f["h"]
        sinal = -1 if cima else 1
        passo = min(13, (0.45 * f["w"]) / max(n, 1))
        cx = f["x"] + max(0.62 * f["w"], 24 + n * passo) if not tronco else f["x"] + f["w"] / 2 + 22
        for i, a in enumerate(atributos):
            ident = a.startswith("#")
            texto = a[1:] if ident else a
            k = (n - 1 - i) if cima else i  # o identificador fica sempre mais perto da entidade
            ry = base + sinal * (18 + k * LINHA_ATR)
            ex = (f["x"] + f["w"] / 2) if tronco else f["x"] + 12 + ((n - 1 - k) * passo)
            self.pentes.append((ex, base, ex, ry, dono))
            self.pentes.append((ex, ry, cx - 6, ry, dono))
            self.atrs.append(dict(dono=dono, cx=cx, cy=ry, texto=texto, ident=ident, ex=ex))

    # ------------------------------------------------------------ obstáculos
    def caixas(self):
        """Tudo que uma linha não pode atravessar: formas, bolinhas+textos, cardinalidades."""
        out = []
        for fid, f in self.formas.items():
            if f.get("auto"):  # losango ainda sem posição
                continue
            out.append((fid, f["x"], f["y"], f["w"], f["h"]))
        for a in self.atrs:
            out.append((a["dono"] + "#atr", a["cx"] - 7, a["cy"] - 9, 14 + 4 + larg_texto(a["texto"]), 18))
        for c in self.cards:
            out.append(("card", c["x"], c["y"], c["w"], c["h"]))
        return out

    def segmentos(self, excluir=None):
        segs = [(x1, y1, x2, y2, "pente:" + d) for x1, y1, x2, y2, d in self.pentes]
        for lig in self.ligacoes + self.retas:
            if lig is excluir:
                continue
            pts = lig["pts"]
            for (a, b), (c, d) in zip(pts, pts[1:]):
                segs.append((a, b, c, d, "lig"))
        return segs

    # ------------------------------------------------------------ roteamento
    @staticmethod
    def _porta(f, lado, frac=0.5):
        x, y, w, h = f["x"], f["y"], f["w"], f["h"]
        if f["tipo"] in ("rel", "tri") or lado == "N" and f["tipo"] == "tri":
            frac = 0.5  # losango e triângulo só ligam pelos vértices
        return {
            "W": (x, y + frac * h),
            "E": (x + w, y + frac * h),
            "N": (x + frac * w, y),
            "S": (x + frac * w, y + h),
        }[lado]

    def _rotas(self, a, b, lados_a, lados_b, fracs=(0.5, 0.3, 0.7, 0.15, 0.85)):
        fa, fb = self.formas[a], self.formas[b]
        for la in lados_a:
            for lb in lados_b:
                for frac in fracs:
                    p1 = self._porta(fa, la, 0.5)
                    p2 = self._porta(fb, lb, frac)
                    horiz_a = la in "WE"
                    horiz_b = lb in "WE"
                    if horiz_a and horiz_b:
                        if abs(p1[1] - p2[1]) < 1:
                            yield la, lb, frac, [p1, p2]
                        else:
                            mx = (p1[0] + p2[0]) / 2
                            yield la, lb, frac, [p1, (mx, p1[1]), (mx, p2[1]), p2]
                    elif not horiz_a and not horiz_b:
                        if abs(p1[0] - p2[0]) < 1:
                            yield la, lb, frac, [p1, p2]
                        else:
                            my = (p1[1] + p2[1]) / 2
                            yield la, lb, frac, [p1, (p1[0], my), (p2[0], my), p2]
                    elif horiz_a:
                        yield la, lb, frac, [p1, (p2[0], p1[1]), p2]
                    else:
                        yield la, lb, frac, [p1, (p1[0], p2[1]), p2]

    def _sentido_ok(self, f, lado, pts):
        """A linha sai da forma para fora (não entra pela própria forma)."""
        (x1, y1), (x2, y2) = pts[0], pts[1]
        return {"W": x2 <= x1, "E": x2 >= x1, "N": y2 <= y1, "S": y2 >= y1}[lado] and (x1, y1) != (x2, y2)

    def _custo(self, pts, ignorar, eu=None):
        rigido = getattr(self, "rigido", False)
        comp = sum(abs(a - c) + abs(b - d) for (a, b), (c, d) in zip(pts, pts[1:]))
        for (a, b), (c, d) in zip(pts, pts[1:]):
            for fid, x, y, w, h in self.caixas():
                if fid in ignorar:
                    continue
                if _seg_caixa(a, b, c, d, x - 3, y - 3, w + 6, h + 6):
                    return None
            for x1, y1, x2, y2, tipo in self.segmentos(excluir=eu):
                if tipo.startswith("pente:"):
                    if _seg_seg(a, b, c, d, x1, y1, x2, y2):
                        return None
                elif _seg_seg(a, b, c, d, x1, y1, x2, y2, folga=2):
                    if rigido:
                        return None  # na escolha do losango, primeiro tenta sem cruzar nada
                    comp += 1500  # cruzar outra linha é permitido, mas muito caro
        for (a, b), (c, d) in zip(pts, pts[1:]):
            if 0 < abs(a - c) + abs(b - d) < 24:
                comp += 600  # degrau pequeno fica feio: prefira linha reta
        return comp + 120 * (len(pts) - 2)

    def rotear(self):
        fixos = [pd for pd in self._pedidos if pd[0] != "rel" or not self.formas[pd[1]].get("auto")]
        self.problemas = self._rotear_lista(fixos)
        self._posicionar_losangos()
        self._refinar()
        return self.problemas

    def _cruzamentos(self) -> int:
        segs = []
        for n, lig in enumerate(self.ligacoes + self.retas):
            for (a, b), (c, d) in zip(lig["pts"], lig["pts"][1:]):
                segs.append((n, a, b, c, d))
        total = 0
        for i, (n1, *s1) in enumerate(segs):
            for n2, *s2 in segs[i + 1 :]:
                if n1 != n2 and _seg_seg(*s1, *s2, folga=2):
                    total += 1
        return total

    def _refinar(self, rodadas=4):
        """Com os losangos já no lugar, retraça cada ligação considerando todas as
        outras; trocar de porta costuma desfazer cruzamentos criados pela ordem."""
        for _ in range(rodadas):
            antes = self._cruzamentos()
            for i, lig in enumerate(list(self.ligacoes)):
                card = self.cards[i]
                del self.ligacoes[i], self.cards[i]
                prefer = lig.get("prefer")
                r = self._melhor_rota(lig["de"], lig["para"], prefer, lig["card"])
                if r is None:  # mantém a rota antiga
                    self.ligacoes.insert(i, lig)
                    self.cards.insert(i, card)
                    continue
                nova = dict(lig, pts=r[1])
                self.ligacoes.insert(i, nova)
                self.cards.insert(i, self._cardinalidade(lig["card"], r[1][-1], r[2]))
            if self._cruzamentos() >= antes:
                break

    def _rotear_lista(self, pedidos):
        problemas = []
        for pedido in pedidos:
            if pedido[0] == "geral":
                _, tid, geral, _ = pedido
                melhor = None
                for la, lb, frac, pts in self._rotas(geral, tid, "WENS", "N"):
                    if not self._sentido_ok(self.formas[geral], la, pts):
                        continue
                    if la == "S" and any(a["dono"] == geral for a in self.atrs):
                        continue
                    c = self._custo(pts, {geral, tid})
                    if c is not None and (melhor is None or c < melhor[0]):
                        melhor = (c, pts)
                if melhor is None:
                    problemas.append(f"sem rota: {geral} -> especialização")
                    continue
                self.retas.append(dict(de=geral, para=tid, pts=melhor[1]))
                continue
            _, rid, eid, card, prefer = pedido
            fe = self.formas[eid]
            melhor = self._melhor_rota(rid, eid, prefer, card)
            if melhor is None:
                problemas.append(f"sem rota: {self.formas[rid]['rotulo']} -> {fe['rotulo']}")
                continue
            _, pts, le = melhor
            lig = dict(de=rid, para=eid, pts=pts, card=card, prefer=prefer)
            self.ligacoes.append(lig)
            self.cards.append(self._cardinalidade(card, pts[-1], le))
        return problemas

    def _lados_livres(self, fid):
        f = self.formas[fid]
        if any(a["dono"] == fid for a in self.atrs):
            return "WENS".replace(f.get("pente", "S"), "")
        return "WENS"

    def _posicionar_losangos(self):
        """Para cada losango sem posição, testa posições numa grade e fica com a que dá
        o menor custo somado das ligações (comprimento, curvas, cruzamentos)."""
        for rid, f in self.formas.items():
            if not f.get("auto"):
                continue
            pedidos = [pd for pd in self._pedidos if pd[0] == "rel" and pd[1] == rid]
            alvos = [self.formas[pd[2]] for pd in pedidos]
            xs = [a["x"] + a["w"] / 2 for a in alvos]
            ys = [a["y"] + a["h"] / 2 for a in alvos]
            melhor = None
            extra = 24 * len(f["atrs_pend"]) + 30 if f["atrs_pend"] else 0
            candidatos = [
                (cx, cy)
                for cx in range(int(min(xs)) - 300, int(max(xs)) + 301, 20)
                for cy in range(int(min(ys)) - 300, int(max(ys)) + 301, 20)
            ]
            for self.rigido in (False,):
                if melhor is not None:
                    break
                for cx, cy in candidatos:
                    f["x"], f["y"] = cx - REL_W / 2, cy - REL_H / 2
                    if any(
                        fid != rid
                        and _sobrepoe(f["x"] - 16, f["y"] - 16, REL_W + 32, REL_H + 32 + extra, x, y, w, h)
                        for fid, x, y, w, h in self.caixas()
                    ):
                        continue
                    if any(
                        _seg_caixa(x1, y1, x2, y2, f["x"] - 8, f["y"] - 8, REL_W + 16, REL_H + 16 + extra)
                        for x1, y1, x2, y2, _ in self.segmentos()
                    ):
                        continue
                    # avalia em sequência, como no traçado real: cada ligação já
                    # traçada (e sua cardinalidade) vira obstáculo para a próxima
                    total, ok, n_lig, n_card = 0, True, len(self.ligacoes), len(self.cards)
                    f["auto"] = False  # nesta posição o losango já conta como obstáculo
                    for _, _, eid, card, prefer in pedidos:
                        r = self._melhor_rota(rid, eid, prefer, card)
                        if r is None:
                            ok = False
                            break
                        total += r[0]
                        self.ligacoes.append(dict(de=rid, para=eid, pts=r[1], card=card))
                        self.cards.append(self._cardinalidade(card, r[1][-1], r[2]))
                    del self.ligacoes[n_lig:], self.cards[n_card:]
                    f["auto"] = True
                    if ok and (melhor is None or total < melhor[0]):
                        melhor = (total, f["x"], f["y"])
            self.rigido = False
            if melhor is None:
                f["x"], f["y"] = 0, 0
                f["auto"] = False
                self.problemas.append(f"sem lugar para o losango {f['rotulo']}")
                continue
            f["x"], f["y"] = melhor[1], melhor[2]
            f["auto"] = False
            if f["atrs_pend"]:
                self._pente(rid, f["atrs_pend"], tronco=True)
            # já roteia as ligações deste losango, para os próximos desviarem delas
            for pd in pedidos:
                self.problemas += self._rotear_lista([pd])

    def _melhor_rota(self, rid, eid, prefer, card):
        fe = self.formas[eid]
        fracs = (0.5, 0.3, 0.7, 0.15, 0.85)
        if isinstance(prefer, tuple):  # porta fixa: (lado, altura de 0 a 1)
            prefer, frac_fixa = prefer
            fracs = (frac_fixa,)
        lados_e = prefer or self._lados_livres(eid)
        lados_r = "WEN" if self.formas[rid].get("atrs_pend") else self._lados_livres(rid)
        melhor = None
        for lr, le, frac, pts in self._rotas(rid, eid, lados_r, lados_e, fracs):
            if not self._sentido_ok(self.formas[rid], lr, pts):
                continue
            if not self._sentido_ok(fe, le, list(reversed(pts))):
                continue
            k = self._cardinalidade(card, pts[-1], le)
            if any(_sobrepoe(k["x"], k["y"], k["w"], k["h"], x, y, w, h) for _, x, y, w, h in self.caixas()):
                continue
            c = self._custo(pts, {rid, eid})
            if c is not None and (melhor is None or c < melhor[0]):
                melhor = (c, pts, le)
        return melhor

    @staticmethod
    def _cardinalidade(texto, p, lado):
        w, h = larg_texto(texto) + 2, 16
        x, y = p
        pos = {
            "W": (x - w - 3, y - h - 2),
            "E": (x + 4, y - h - 2),
            "N": (x + 5, y - h - 3),
            "S": (x + 5, y + 3),
        }[lado]
        return dict(texto=texto, x=pos[0], y=pos[1], w=w, h=h)

    # ------------------------------------------------------------ conferência final
    def conferir(self):
        prob = []
        cx = self.caixas()
        for i, (ia, xa, ya, wa, ha) in enumerate(cx):
            for ib, xb, yb, wb, hb in cx[i + 1 :]:
                if ia.split("#")[0] == ib.split("#")[0] and "#atr" in ia + ib and ia != ib:
                    continue
                if ia == ib and ia.endswith("#atr"):
                    continue
                if xa < xb + wb and xb < xa + wa and ya < yb + hb and yb < ya + ha:
                    prob.append(f"sobreposição: {ia} x {ib}")
        for lig in self.ligacoes + self.retas:
            pts = lig["pts"]
            for (a, b), (c, d) in zip(pts, pts[1:]):
                for fid, x, y, w, h in cx:
                    if fid in (lig["de"], lig["para"]) or fid == "card":
                        continue
                    if _seg_caixa(a, b, c, d, x + 2, y + 2, w - 4, h - 4):
                        prob.append(f"linha {lig['de']}->{lig['para']} atravessa {fid}")
        return sorted(set(prob))

    # ------------------------------------------------------------ draw.io
    def xml(self, idx):
        c = []
        add = c.append
        topo = min([f["y"] for f in self.formas.values()]) - 70
        add(
            _vertice(
                f"t{idx}", self.titulo, 20, topo, 1400, 34, "text;html=1;fontSize=20;fontStyle=1;align=left;"
            )
        )
        for fid, f in self.formas.items():
            cid = f"p{idx}-{fid}"
            if f["tipo"] == "ent":
                cor = (
                    "fillColor=#f5f5f5;strokeColor=#888888;fontColor=#555555;"
                    if f["ref"]
                    else "fillColor=#ffffff;strokeColor=#000000;"
                )
                dupla = "shape=ext;double=1;" if f["fraca"] else ""
                add(
                    _vertice(
                        cid,
                        f["rotulo"],
                        f["x"],
                        f["y"],
                        f["w"],
                        f["h"],
                        f"rounded=0;whiteSpace=wrap;html=1;fontStyle=1;fontSize=13;{dupla}{cor}",
                    )
                )
            elif f["tipo"] == "rel":
                dupla = "shape=ext;double=1;" if f["ident"] else ""
                add(
                    _vertice(
                        cid,
                        f["rotulo"],
                        f["x"],
                        f["y"],
                        f["w"],
                        f["h"],
                        f"rhombus;whiteSpace=wrap;html=1;fontSize=12;fontStyle=1;fillColor=#ffffff;strokeColor=#000000;{dupla}",
                    )
                )
            elif f["tipo"] == "assoc":
                add(
                    _vertice(
                        cid,
                        f["rotulo"],
                        f["x"],
                        f["y"],
                        f["w"],
                        f["h"],
                        "rounded=0;whiteSpace=wrap;html=1;fontSize=12;fontStyle=1;align=left;verticalAlign=top;"
                        "spacingLeft=4;spacingTop=-2;fillColor=#ffffff;strokeColor=#000000;",
                    )
                )
                add(
                    _vertice(
                        cid + "-r",
                        f["rel"],
                        f["x"] + 18,
                        f["y"] + 18,
                        f["w"] - 36,
                        f["h"] - 24,
                        "rhombus;whiteSpace=wrap;html=1;fontSize=12;fontStyle=1;fillColor=#ffffff;strokeColor=#000000;",
                    )
                )
            else:
                add(
                    _vertice(
                        cid,
                        "",
                        f["x"],
                        f["y"],
                        f["w"],
                        f["h"],
                        "triangle;direction=north;html=1;fillColor=#ffffff;strokeColor=#000000;",
                    )
                )
        for n, (x1, y1, x2, y2, _) in enumerate(self.pentes):
            add(_aresta(f"p{idx}-pe{n}", [(x1, y1), (x2, y2)]))
        for n, a in enumerate(self.atrs):
            cor = "#000000" if a["ident"] else "#ffffff"
            add(
                _vertice(
                    f"p{idx}-ab{n}",
                    "",
                    a["cx"] - 6,
                    a["cy"] - 6,
                    12,
                    12,
                    f"ellipse;html=1;fillColor={cor};strokeColor=#000000;",
                )
            )
            add(
                _vertice(
                    f"p{idx}-at{n}",
                    html.escape(a["texto"]),
                    a["cx"] + 9,
                    a["cy"] - 9,
                    larg_texto(a["texto"]) + 6,
                    18,
                    "text;html=1;align=left;verticalAlign=middle;fontSize=12;fontStyle=1;spacing=0;",
                )
            )
        for n, lig in enumerate(self.ligacoes + self.retas):
            add(_aresta(f"p{idx}-l{n}", lig["pts"]))
        for n, k in enumerate(self.cards):
            add(
                _vertice(
                    f"p{idx}-c{n}",
                    k["texto"],
                    k["x"],
                    k["y"],
                    k["w"],
                    k["h"],
                    "text;html=1;align=center;verticalAlign=middle;fontSize=12;fontStyle=1;spacing=0;",
                )
            )
        fundo = max(f["y"] + f["h"] for f in self.formas.values())
        fundo = max([fundo] + [a["cy"] + 12 for a in self.atrs]) + 50
        legenda = (
            "<b>Legenda (brModelo)</b><br>▭ entidade · ▭▭ entidade fraca · ◇ relacionamento · "
            "▭◇ entidade associativa · △ especialização<br>"
            "● identificador · ○ atributo · Nome (1, n) multivalorado · cinza: entidade detalhada em outra página<br>"
            "(mín,máx) ao lado da entidade: com quantas ocorrências dela uma ocorrência do outro lado se relaciona"
        )
        add(
            _vertice(
                f"p{idx}-leg",
                legenda,
                20,
                fundo,
                760,
                70,
                "text;html=1;align=left;verticalAlign=top;spacing=8;fillColor=#f5f5f5;strokeColor=#999999;fontSize=11;",
            )
        )
        larg = max(f["x"] + f["w"] for f in self.formas.values()) + 300
        return (
            f'<diagram name={quoteattr(self.nome)} id="der-{idx}"><mxGraphModel dx="1600" dy="1000" grid="1" '
            f'gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
            f'pageWidth="{larg:.0f}" pageHeight="{fundo + 120:.0f}" math="0" shadow="0"><root><mxCell id="0"/>'
            f'<mxCell id="1" parent="0"/>' + "".join(c) + "</root></mxGraphModel></diagram>"
        )

    def svg(self):
        xs = [f["x"] for f in self.formas.values()] + [a["cx"] for a in self.atrs]
        ys = [f["y"] for f in self.formas.values()] + [a["cy"] - 12 for a in self.atrs]
        x0, y0 = min(xs) - 40, min(ys) - 40
        x1 = (
            max(
                [f["x"] + f["w"] for f in self.formas.values()]
                + [a["cx"] + larg_texto(a["texto"]) + 20 for a in self.atrs]
            )
            + 40
        )
        y1 = max([f["y"] + f["h"] for f in self.formas.values()] + [a["cy"] + 20 for a in self.atrs]) + 40
        o = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{x1-x0:.0f}" height="{y1-y0:.0f}" '
            f'viewBox="{x0:.0f} {y0:.0f} {x1-x0:.0f} {y1-y0:.0f}" font-family="Arial" font-size="12" font-weight="bold">'
            f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="white"/>'
        ]
        for x1_, y1_, x2_, y2_, _ in self.pentes:
            o.append(f'<line x1="{x1_}" y1="{y1_}" x2="{x2_}" y2="{y2_}" stroke="black"/>')
        for lig in self.ligacoes + self.retas:
            pts = " ".join(f"{a:.0f},{b:.0f}" for a, b in lig["pts"])
            o.append(f'<polyline points="{pts}" fill="none" stroke="black"/>')
        for f in self.formas.values():
            x, y, w, h = f["x"], f["y"], f["w"], f["h"]
            t = html.escape(f["rotulo"])
            if f["tipo"] in ("ent", "assoc"):
                o.append(
                    f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{"#f5f5f5" if f.get("ref") else "white"}" stroke="black"/>'
                )
                if f.get("fraca"):
                    o.append(
                        f'<rect x="{x+4}" y="{y+4}" width="{w-8}" height="{h-8}" fill="none" stroke="black"/>'
                    )
                if f["tipo"] == "assoc":
                    rx, ry, rw, rh = x + 18, y + 18, w - 36, h - 24
                    o.append(
                        f'<polygon points="{rx+rw/2},{ry} {rx+rw},{ry+rh/2} {rx+rw/2},{ry+rh} {rx},{ry+rh/2}" fill="white" stroke="black"/>'
                    )
                    o.append(
                        f'<text x="{x+4}" y="{y+13}">{t}</text><text x="{rx+rw/2}" y="{ry+rh/2+4}" text-anchor="middle">{html.escape(f["rel"])}</text>'
                    )
                else:
                    o.append(
                        f'<text x="{x+w/2}" y="{y+h/2+4}" text-anchor="middle" font-size="13">{t}</text>'
                    )
            elif f["tipo"] == "rel":
                o.append(
                    f'<polygon points="{x+w/2},{y} {x+w},{y+h/2} {x+w/2},{y+h} {x},{y+h/2}" fill="white" stroke="black"/>'
                )
                o.append(f'<text x="{x+w/2}" y="{y+h/2+4}" text-anchor="middle">{t}</text>')
            else:
                o.append(f'<polygon points="{x+w/2},{y} {x+w},{y+h} {x},{y+h}" fill="white" stroke="black"/>')
        for a in self.atrs:
            o.append(
                f'<circle cx="{a["cx"]}" cy="{a["cy"]}" r="6" fill="{"black" if a["ident"] else "white"}" stroke="black"/>'
            )
            o.append(f'<text x="{a["cx"]+10}" y="{a["cy"]+4}">{html.escape(a["texto"])}</text>')
        for k in self.cards:
            o.append(f'<text x="{k["x"]+k["w"]/2}" y="{k["y"]+12}" text-anchor="middle">{k["texto"]}</text>')
        o.append("</svg>")
        return "".join(o)


def _vertice(cid, valor, x, y, w, h, estilo):
    return (
        f'<mxCell id="{cid}" value={quoteattr(valor)} style="{estilo}" vertex="1" parent="1">'
        f'<mxGeometry x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" as="geometry"/></mxCell>'
    )


def _aresta(cid, pts):
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    meio = "".join(f'<mxPoint x="{a:.1f}" y="{b:.1f}"/>' for a, b in pts[1:-1])
    return (
        f'<mxCell id="{cid}" style="endArrow=none;html=1;rounded=0;edgeStyle=none;strokeColor=#000000;" '
        f'edge="1" parent="1"><mxGeometry relative="1" as="geometry">'
        f'<mxPoint x="{x1:.1f}" y="{y1:.1f}" as="sourcePoint"/><mxPoint x="{x2:.1f}" y="{y2:.1f}" as="targetPoint"/>'
        + (f'<Array as="points">{meio}</Array>' if meio else "")
        + "</mxGeometry></mxCell>"
    )


def _sobrepoe(ax, ay, aw, ah, bx, by, bw, bh):
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def _seg_caixa(x1, y1, x2, y2, bx, by, bw, bh):
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - bx), (dx, bx + bw - x1), (-dy, y1 - by), (dy, by + bh - y1)):
        if p == 0:
            if q < 0:
                return False
        else:
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return False
    return True


def _seg_seg(ax, ay, bx, by, cx, cy, dx, dy, folga=0):
    """Segmentos horizontais/verticais se cruzam (ou se sobrepõem)."""

    def caixa(x1, y1, x2, y2):
        return min(x1, x2) - folga, min(y1, y2) - folga, max(x1, x2) + folga, max(y1, y2) + folga

    a = caixa(ax, ay, bx, by)
    b = caixa(cx, cy, dx, dy)
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


# =====================================================================
# Páginas. Só as entidades têm posição fixa; os losangos sem x/y são
# posicionados automaticamente (ver _posicionar_losangos).
# =====================================================================
def mod01():
    p = Pagina("MOD01 · Usuários e acesso", "DER conceitual · MOD01 · Usuários e acesso")
    p.ent(
        "usuario",
        "Usuário",
        620,
        40,
        ["#Id_usuario", "Nome", "E-mail", "Telefone", "Senha", "Situação", "Foto"],
    )
    p.ent("perfil", "Perfil", 1200, 40, ["#Código", "Nome"])
    p.rel("possui", "Possui", atributos=["Atribuído_em"])
    p.liga("possui", "usuario", "(0,n)")
    p.liga("possui", "perfil", "(1,n)")
    p.tri("esp", 470, 330, "usuario", [])
    p.ent("aluno", "Aluno", 60, 470, ["Matrícula"])
    p.ent("docente", "Docente", 620, 470, ["Cargo"])
    p.ent("externo", "Membro externo", 1200, 470, ["Instituição"])
    for filho in ("aluno", "docente", "externo"):
        f = p.formas[filho]
        p.retas.append(dict(de="esp", para=filho, pts=[(505, 380), (f["x"] + f["w"] / 2, f["y"])]))
    p.ent("curso", "Curso", 60, 820, ["#Sigla", "Nome"])
    p.rel("cursa", "Cursa")
    p.liga("cursa", "aluno", "(0,n)")
    p.liga("cursa", "curso", "(1,1)")
    p.ent("nucleo", "Núcleo", 620, 1040, ["#Sigla", "Nome"])
    p.rel("oferece", "Oferece")
    p.liga("oferece", "nucleo", "(1,1)")
    p.liga("oferece", "curso", "(1,n)")
    p.rel("atua", "Atua em")
    p.liga("atua", "docente", "(0,n)")
    p.liga("atua", "curso", "(0,1)")
    p.rel("pertence", "Pertence a")
    p.liga("pertence", "docente", "(1,n)")
    p.liga("pertence", "nucleo", "(1,1)")
    p.ent("area", "Área de interesse", 1200, 820, ["#Nome"])
    p.rel("interesse", "Tem interesse")
    p.liga("interesse", "docente", "(0,n)")
    p.liga("interesse", "area", "(0,n)")
    return p


def mod02():
    p = Pagina("MOD02 · Ideias de TCC", "DER conceitual · MOD02 · Ideias de TCC")
    p.ent("aluno", "Aluno", 40, 360, ref=True)
    p.ent("proposta", "Proposta", 560, 360, ["#Id_proposta", "Título", "Descrição", "Destino", "Data"])
    p.rel("propoe", "Propõe")
    p.liga("propoe", "aluno", "(1,1)")
    p.liga("propoe", "proposta", "(0,n)")
    p.ent("area", "Área de interesse", 1140, 360, ref=True)
    p.rel("direcionada", "Direcionada à")
    p.liga("direcionada", "proposta", "(0,n)")
    p.liga("direcionada", "area", "(0,1)")
    p.ent("docente", "Docente", 1140, 60, ref=True)
    p.rel("enderecada", "Endereçada a")
    p.liga("enderecada", "proposta", "(0,n)")
    p.liga("enderecada", "docente", "(0,n)")
    p.ent("comentario", "Comentário", 560, 60, ["Texto", "Data", "Oculto_em"], fraca=True, pente="N")
    p.rel("recebe", "Recebe", identificadora=True)
    p.liga("recebe", "proposta", "(1,1)")
    p.liga("recebe", "comentario", "(0,n)")
    p.rel("escreve", "Escreve")
    p.liga("escreve", "docente", "(1,1)")
    p.liga("escreve", "comentario", "(0,n)")
    return p


def mod03a():
    p = Pagina("MOD03 · Turmas e matrícula", "DER conceitual · MOD03 · Turmas e matrícula")
    # Turma ocupa x 600-770, y 160-230 (centro y 195); as portas abaixo seguem esse retângulo.
    p.ent("periodo", "Período letivo", 60, 170, ["#Código", "Início", "Fim", "Prazo_versão_final"], pente="N")
    p.ent("turma", "Turma", 600, 160, ["#Código", "Disciplina", "Encerrada_em"], pente="N", w=170, h=70)
    p.rel("ofertada", "Ofertada em", 330, 165)
    p.liga("ofertada", "turma", "(0,n)", prefer=("W", 0.5))
    p.liga("ofertada", "periodo", "(1,1)")
    p.ent("docente", "Docente", 1140, 170, ref=True)
    p.rel("responsavel", "Responsável", 870, 165)
    p.liga("responsavel", "docente", "(1,1)")
    p.liga("responsavel", "turma", "(0,n)", prefer=("E", 0.5))
    p.ent("curso", "Curso", 60, 460, ref=True)
    p.rel("docurso", "Do curso", 330, 455)
    p.liga("docurso", "turma", "(0,n)", prefer=("S", 0.1))
    p.liga("docurso", "curso", "(1,1)")
    p.ent("aluno", "Aluno", 60, 760, ref=True)
    p.assoc("matricula", "Matrícula", "Matricula-se", 582, 560, ["Situação", "Nota_final"])
    p.liga("matricula", "turma", "(0,n)", prefer=("S", 0.45))
    p.liga("matricula", "aluno", "(0,n)")
    p.ent("tcc", "TCC", 1140, 460, ref=True)
    p.rel("vinculado", "Vinculado a", 850, 455)
    p.liga("vinculado", "turma", "(1,1)", prefer=("S", 0.8))
    p.liga("vinculado", "tcc", "(0,n)")
    return p


def mod03b():
    p = Pagina(
        "MOD03 · TCC e acompanhamento", "DER conceitual · MOD03 · TCC, orientação, análise e acompanhamento"
    )
    p.ent(
        "tcc",
        "TCC",
        700,
        560,
        [
            "#Protocolo",
            "Título",
            "Subtítulo",
            "Resumo",
            "Palavra-chave (1, 10)",
            "Etapa",
            "Modalidade",
            "Situação",
        ],
        w=200,
        h=120,
    )
    p.rel("origina", "Origina", 495, 420)  # autorrelacionamento: TCC1 origina TCC2
    p.liga("origina", "tcc", "(0,1) TCC1", prefer=("N", 0.3))
    p.liga("origina", "tcc", "(0,1) TCC2", prefer=("W", 0.08))
    p.ent("aluno", "Aluno", 80, 565, ref=True)
    p.rel("elabora", "Elabora", 330, 560)
    p.liga("elabora", "aluno", "(1,1)")
    p.liga("elabora", "tcc", "(0,n)", prefer=("W", 0.25))
    p.ent("docente", "Docente", 1500, 120, ref=True)
    p.assoc(
        "orientacao",
        "Orientação",
        "Orienta",
        1000,
        300,
        ["Papel", "Status", "Solicitado_em", "Respondido_em"],
        pente="N",
    )
    p.liga("orientacao", "docente", "(0,2)")
    p.liga("orientacao", "tcc", "(0,n)", prefer=("N", 0.85))
    p.ent("area", "Área de interesse", 1500, 565, ref=True)
    p.rel("classificado", "Classificado", 1085, 560)
    p.liga("classificado", "tcc", "(0,n)", prefer=("E", 0.25))
    p.liga("classificado", "area", "(1,1)")
    p.ent("analise", "Análise de cadastro", 1500, 900, ["Resultado", "Parecer", "Data"])
    p.rel("recebe", "Recebe", 1335, 750)
    p.liga("recebe", "tcc", "(1,1)", prefer=("E", 0.6))
    p.liga("recebe", "analise", "(0,n)")
    p.rel("decide", "Decide", 1735, 470)
    p.liga("decide", "docente", "(1,1)")
    p.liga("decide", "analise", "(0,n)")
    p.ent("documento", "Documento", 80, 900, ["#Versão", "Finalidade", "Arquivo", "Enviado_em"], fraca=True)
    p.rel("possuidoc", "Possui", 90, 730, identificadora=True)
    p.liga("possuidoc", "tcc", "(1,1)", prefer=("W", 0.6))
    p.liga("possuidoc", "documento", "(0,n)")
    p.ent("tarefa", "Tarefa", 330, 1180, ["Descrição", "Prazo", "Status"], fraca=True)
    p.rel("temtarefa", "Tem", 340, 980, identificadora=True)
    p.liga("temtarefa", "tcc", "(1,1)", prefer=("W", 0.85))
    p.liga("temtarefa", "tarefa", "(0,n)")
    p.ent("historico", "Histórico de situação", 1250, 1180, ["Situação_nova", "Data"], fraca=True)
    p.rel("registra", "Registra", 1260, 980, identificadora=True)
    p.liga("registra", "tcc", "(1,1)", prefer=("E", 0.85))
    p.liga("registra", "historico", "(0,n)")
    return p


def mod04a():
    p = Pagina("MOD04 · Defesa e banca", "DER conceitual · MOD04 · Defesa, banca e agenda (MOD07)")
    # Defesa ocupa x 560-710, y 300-410; as portas abaixo seguem esse retângulo.
    p.ent("tcc", "TCC", 40, 300, ref=True)
    p.ent("defesa", "Defesa", 560, 300, ["#Id_defesa", "Data", "Início", "Fim", "Formato", "Link", "Situação",
                                         "Publicada_na_agenda"], h=110, pente="N")
    p.rel("defendido", "É defendido em", 250, 295)
    p.liga("defendido", "tcc", "(1,1)")
    p.liga("defendido", "defesa", "(0,n)", prefer=("W", 25 / 110))
    p.ent("local", "Local", 1140, 300, ["#Nome"], pente="N")
    p.rel("ocorre", "Ocorre em", 830, 295)
    p.liga("ocorre", "defesa", "(0,n)", prefer=("E", 25 / 110))
    p.liga("ocorre", "local", "(0,1)")
    p.ent("historico", "Histórico da defesa", 40, 600, ["Evento", "Motivo", "Data"], fraca=True)
    p.rel("registra", "Registra", 250, 595, identificadora=True)
    p.liga("registra", "defesa", "(1,1)", prefer=("W", 0.6))
    p.liga("registra", "historico", "(0,n)")
    p.ent("ocorrencia", "Ocorrência", 500, 860, ["Texto", "Data"], fraca=True)
    p.rel("temocorr", "Tem", 510, 520, identificadora=True)
    p.liga("temocorr", "defesa", "(1,1)", prefer=("S", 0.1))
    p.liga("temocorr", "ocorrencia", "(0,n)")
    p.ent("usuario", "Usuário", 1140, 620, ref=True)
    p.assoc("banca", "Banca", "Compõe", 800, 520, ["Papel", "Presente", "Convocado_em"])
    p.liga("banca", "usuario", "(3,5)")
    p.liga("banca", "defesa", "(0,n)", prefer=("S", 0.9))
    p.rel("agenda", "Agenda", 1085, 690)
    p.liga("agenda", "usuario", "(1,1)")
    p.liga("agenda", "defesa", "(0,n)", prefer=("S", 0.6))
    p.ent("ouvinte", "Ouvinte", 1325, 960, ["Nome", "Matrícula"], fraca=True)
    p.rel("assiste", "É assistida por", 1335, 770, identificadora=True)
    p.liga("assiste", "defesa", "(1,1)", prefer=("E", 0.85))
    p.liga("assiste", "ouvinte", "(0,n)")
    return p


def mod04b():
    p = Pagina(
        "MOD04 · Avaliação e resultado",
        "DER conceitual · MOD04 · Avaliação, resultado, correções e documentos",
    )
    p.ent("usuario", "Usuário", 40, 300, ref=True)
    p.ent("defesa", "Defesa", 560, 300, ref=True)
    p.ent("avaliacao", "Avaliação", 300, 600, ["Status", "Parecer", "Nota_total (derivado)"])
    p.rel("faz", "Faz")
    p.liga("faz", "usuario", "(1,1)")
    p.liga("faz", "avaliacao", "(0,n)")
    p.rel("recebeav", "Recebe")
    p.liga("recebeav", "defesa", "(1,1)")
    p.liga("recebeav", "avaliacao", "(0,n)")
    p.ent("instrumento", "Instrumento", 1000, 600, ["#Versão", "Vigente"])
    p.rel("usa", "Usa", 660, 585)
    p.liga("usa", "avaliacao", "(0,n)", prefer=("E", 0.3))
    p.liga("usa", "instrumento", "(1,1)", prefer=("W", 0.3))
    p.ent("componente", "Componente", 1500, 600, ["Nome", "Pontos"], fraca=True)
    p.rel("compoe", "Compõe-se de", 1240, 595, identificadora=True)
    p.liga("compoe", "instrumento", "(1,1)", prefer=("E", 0.5))
    p.liga("compoe", "componente", "(1,n)", prefer=("W", 0.5))
    p.ent("criterio", "Critério", 1000, 895, ["Nome", "Peso", "Textos_dos_conceitos"], fraca=True)
    p.rel("temcrit", "Tem", 1600, 890, identificadora=True)
    p.liga("temcrit", "componente", "(1,1)", prefer=("E", 0.5))
    p.liga("temcrit", "criterio", "(1,n)", prefer=("E", 0.5))
    p.assoc("pontuacao", "Pontuação", "Pontua", 520, 880, ["Conceito", "Nota", "Nota_ponderada (derivado)"])
    p.liga("pontuacao", "avaliacao", "(0,n)", prefer=("E", 0.8))
    p.liga("pontuacao", "criterio", "(0,n)", prefer=("W", 0.5))
    p.ent(
        "resultado",
        "Resultado",
        1000,
        300,
        ["#Versão", "Resultado", "Parecer", "Nota_final (derivado)", "Prazo", "Anuência_em"],
        fraca=True,
        pente="N",
    )
    p.rel("temres", "Tem", identificadora=True)
    p.liga("temres", "defesa", "(1,1)")
    p.liga("temres", "resultado", "(0,n)")
    p.ent("correcao", "Correção", 1500, 300, ["Descrição", "Situação"], fraca=True, pente="N")
    p.rel("exige", "Exige", identificadora=True)
    p.liga("exige", "resultado", "(1,1)")
    p.liga("exige", "correcao", "(0,n)")
    p.ent("avaliador2", "Usuário", 1900, 300, ref=True)
    p.rel("pede", "Pede")
    p.liga("pede", "avaliador2", "(1,1)")
    p.liga("pede", "correcao", "(0,n)")
    p.ent("docof", "Documento oficial", 560, 40, ["Tipo", "Versão", "Vigente"], fraca=True, pente="N")
    p.rel("gera", "Gera", identificadora=True)
    p.liga("gera", "defesa", "(1,1)")
    p.liga("gera", "docof", "(0,n)")
    return p


def mod05():
    p = Pagina("MOD05 · Publicação", "DER conceitual · MOD05 · Publicação")
    p.ent("tcc", "TCC", 40, 60, ref=True)
    p.ent("publicacao", "Publicação", 560, 60, ["Tipo_de_veículo", "Veículo", "Qualis", "DOI", "Situação_atual"])
    p.rel("submetido", "É submetido em", 290, 55)
    p.liga("submetido", "tcc", "(1,1)")
    p.liga("submetido", "publicacao", "(0,n)", prefer=("W", 0.5))
    p.ent("historico", "Histórico editorial", 1080, 60, ["Situação", "Data"], fraca=True)
    p.rel("registra", "Registra", 810, 55, identificadora=True)
    p.liga("registra", "publicacao", "(1,1)", prefer=("E", 0.5))
    p.liga("registra", "historico", "(1,n)", prefer=("W", 0.5))
    p.ent("usuario", "Usuário", 1320, 330, ref=True)
    p.rel("informa", "Informa", 1330, 55)
    p.liga("informa", "historico", "(0,n)", prefer=("E", 0.5))
    p.liga("informa", "usuario", "(0,1)", prefer=("N", 0.5))
    return p


PAGINAS = [mod01, mod02, mod03a, mod03b, mod04a, mod04b, mod05]

if __name__ == "__main__":
    paginas = [f() for f in PAGINAS]
    total = 0
    for p in paginas:
        prob = p.rotear() + p.conferir()
        total += len(prob)
        print(
            f"{p.nome}: {sum(f['tipo'] in ('ent', 'assoc') for f in p.formas.values())} entidades, "
            f"{len(p.ligacoes)} ligações, {len(prob)} problemas"
        )
        for x in prob:
            print("   ", x)
    xml = '<mxfile host="app.diagrams.net">' + "".join(p.xml(i) for i, p in enumerate(paginas)) + "</mxfile>"
    (AQUI / "der-conceitual-siga-uea.drawio").write_text(xml, encoding="utf8")
    if len(sys.argv) > 1:
        for i, p in enumerate(paginas):
            Path(sys.argv[1], f"brm-{i}.svg").write_text(p.svg(), encoding="utf8")
    raise SystemExit(1 if total else 0)
