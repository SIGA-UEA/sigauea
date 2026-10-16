"""DER conceitual do SIGA UEA (notação de Peter Chen, cardinalidade (mín,máx) de Heuser).

Gera docs/modelagem/der-conceitual-siga-uea.drawio, uma página por módulo, e confere o
desenho: nenhuma forma sobreposta e nenhuma linha atravessando outra forma.

    python docs/modelagem/der_conceitual.py

Leitura da cardinalidade: o par ao lado de uma entidade diz com quantas ocorrências
DELA uma ocorrência da outra entidade se relaciona. Ex.: Aluno (1,1) —elabora— (0,N) TCC
= um aluno elabora de 0 a N TCCs; um TCC é elaborado por exatamente 1 aluno.

O conceitual mostra só o que é do negócio. Controles técnicos (sessão, link de
ativação, fila de e-mail, log de auditoria) e chaves estrangeiras ficam no modelo
lógico (docs/modelagem/modelo-logico-siga-uea.drawio).
"""

from __future__ import annotations

import html
import math
from pathlib import Path
from xml.sax.saxutils import quoteattr

AQUI = Path(__file__).resolve().parent

ENT_W, ENT_H = 150, 50
REL_W, REL_H = 130, 66
ATR_H = 30
TRI_W, TRI_H = 70, 46


def larg_atr(texto: str) -> int:
    return max(74, 8 * len(texto) + 22)


class Pagina:
    def __init__(self, nome: str, titulo: str):
        self.nome, self.titulo = nome, titulo
        self.formas: dict[str, dict] = {}  # id -> {tipo, x, y, w, h, rotulo, ...}
        self.ligacoes: list[dict] = []
        self.pendentes: list[tuple] = []

    # ---- formas
    def entidade(self, eid, rotulo, cx, cy, fraca=False, externa=False, w=ENT_W, h=ENT_H):
        self.formas[eid] = dict(tipo="ent", x=cx - w / 2, y=cy - h / 2, w=w, h=h,
                                rotulo=rotulo, fraca=fraca, externa=externa)

    def relacao(self, rid, rotulo, cx, cy, pares, identificadora=False, atributos=(), lado="N"):
        """pares: [(entidade, "(1,1)")] ou [(entidade, "(1,1)", (x, y))] com o ponto de chegada
        na borda da entidade (0 a 1), para separar linhas que chegariam no mesmo lugar."""
        self.formas[rid] = dict(tipo="rel", x=cx - REL_W / 2, y=cy - REL_H / 2, w=REL_W, h=REL_H,
                                rotulo=rotulo, identificadora=identificadora)
        for ent, card, *entrada in pares:
            self.ligacoes.append(dict(de=rid, para=ent, rotulo=card, entrada=entrada[0] if entrada else None))
        self._atributos(rid, atributos, lado)

    def atributos(self, eid, itens, lado="N", dist=30):
        self._atributos(eid, itens, lado, dist)

    def _atributos(self, dono, itens, lado, dist=30):
        """itens: texto; prefixo '#' = identificador, '*' = multivalorado, '~' = derivado.

        Só anota o pedido: os atributos são posicionados em posicionar_atributos(),
        depois que todas as entidades e relacionamentos da página existem.
        """
        if itens:
            self.pendentes.append((dono, list(itens), lado, dist))

    def posicionar_atributos(self):
        """Para cada atributo, procura em anéis ao redor do dono a posição mais perto do
        lado preferido que não encoste em nenhuma forma, não fique sobre nenhuma linha
        e cuja própria linha até o dono não atravesse nada."""
        for dono, itens, lado, dist in self.pendentes:
            f = self.formas[dono]
            cx, cy = f["x"] + f["w"] / 2, f["y"] + f["h"] / 2
            meio = {"N": -90, "S": 90, "E": 0, "W": 180}[lado]
            for i, item in enumerate(itens):
                tipo = {"#": "id", "*": "multi", "~": "deriv"}.get(item[0], "")
                texto = item[1:] if tipo else item
                w = larg_atr(texto)
                aid = f"{dono}__a{i}"
                escolhido = None
                for anel in range(0, 12):
                    extra = dist + anel * 26
                    rx, ry = f["w"] / 2 + w / 2 + extra, f["h"] / 2 + ATR_H / 2 + extra
                    for desvio in sorted(range(-180, 181, 8), key=abs):
                        ang = math.radians(meio + desvio)
                        ax, ay = cx + rx * math.cos(ang), cy + ry * math.sin(ang)
                        caixa = (ax - w / 2, ay - ATR_H / 2, w, ATR_H)
                        if self._livre(caixa, (ax, ay), dono):
                            escolhido = caixa
                            break
                    if escolhido:
                        break
                if escolhido is None:
                    raise SystemExit(f"{self.nome}: sem lugar para o atributo {texto} de {f['rotulo']}")
                x, y, w_, h_ = escolhido
                self.formas[aid] = dict(tipo="atr", x=x, y=y, w=w_, h=h_, rotulo=texto, sub=tipo)
                self.ligacoes.append(dict(de=aid, para=dono, rotulo=""))
        self.pendentes = []

    def _livre(self, caixa, centro_atr, dono) -> bool:
        x, y, w, h = caixa
        m = 10
        for f in self.formas.values():
            if x - m < f["x"] + f["w"] and f["x"] - m < x + w and y - m < f["y"] + f["h"] and f["y"] - m < y + h:
                return False
        for lig in self.ligacoes:  # nenhuma linha existente passa por cima do atributo
            (x1, y1), (x2, y2) = self.pontas(lig)
            if _segmento_cruza_caixa(x1, y1, x2, y2, x - 4, y - 4, w + 8, h + 8):
                return False
        cx, cy = self.centro(dono)  # e a linha nova não atravessa outra forma
        for fid, f in self.formas.items():
            if fid != dono and _segmento_cruza_caixa(centro_atr[0], centro_atr[1], cx, cy,
                                                     f["x"] - 4, f["y"] - 4, f["w"] + 8, f["h"] + 8):
                return False
        return True

    def especializacao(self, tid, cx, cy, geral, filhos, rotulo="(t,x)"):
        self.formas[tid] = dict(tipo="tri", x=cx - TRI_W / 2, y=cy - TRI_H / 2, w=TRI_W, h=TRI_H, rotulo=rotulo)
        self.ligacoes.append(dict(de=geral, para=tid, rotulo=""))
        for filho in filhos:
            self.ligacoes.append(dict(de=tid, para=filho, rotulo=""))

    # ---- conferência
    def centro(self, fid):
        f = self.formas[fid]
        return f["x"] + f["w"] / 2, f["y"] + f["h"] / 2

    def pontas(self, lig):
        """Pontos de saída e chegada de uma ligação (a chegada pode ser fixada, ex.: autorrelacionamento)."""
        x1, y1 = self.centro(lig["de"])
        if lig.get("entrada"):
            f = self.formas[lig["para"]]
            ex, ey = lig["entrada"]
            return (x1, y1), (f["x"] + ex * f["w"], f["y"] + ey * f["h"])
        return (x1, y1), self.centro(lig["para"])

    def posicao_rotulo(self, lig) -> float:
        """Posição do rótulo (-1 a 1, padrão do draw.io) a ~24 px da borda da entidade."""
        (x1, y1), (x2, y2) = self.pontas(lig)
        f = self.formas[lig["para"]]
        comp = math.hypot(x2 - x1, y2 - y1) or 1
        t_borda = 1.0
        for k in range(200):  # onde a linha entra na caixa da entidade
            t = k / 200
            px, py = x1 + t * (x2 - x1), y1 + t * (y2 - y1)
            if f["x"] <= px <= f["x"] + f["w"] and f["y"] <= py <= f["y"] + f["h"]:
                t_borda = t
                break
        t = max(0.5, t_borda - 24 / comp)
        return 2 * t - 1

    def conferir(self) -> list[str]:
        problemas = []
        ids = list(self.formas)
        margem = 6
        for i, a in enumerate(ids):
            fa = self.formas[a]
            for b in ids[i + 1:]:
                fb = self.formas[b]
                if (fa["x"] - margem < fb["x"] + fb["w"] and fb["x"] - margem < fa["x"] + fa["w"]
                        and fa["y"] - margem < fb["y"] + fb["h"] and fb["y"] - margem < fa["y"] + fa["h"]):
                    problemas.append(f"sobreposição: {fa['rotulo']} x {fb['rotulo']}")
        for lig in self.ligacoes:
            (x1, y1), (x2, y2) = self.pontas(lig)
            for fid, f in self.formas.items():
                if fid in (lig["de"], lig["para"]):
                    continue
                if _segmento_cruza_caixa(x1, y1, x2, y2, f["x"] + 3, f["y"] + 3, f["w"] - 6, f["h"] - 6):
                    problemas.append(
                        f"linha {self.formas[lig['de']]['rotulo']} → {self.formas[lig['para']]['rotulo']} "
                        f"atravessa {f['rotulo']}")
        return problemas

    # ---- draw.io
    def xml(self, idx: int) -> str:
        topo = min(f["y"] for f in self.formas.values()) - 70
        cells = [f'<mxCell id="c{idx}-t" value={quoteattr(self.titulo)} style="text;html=1;fontSize=20;'
                 f'fontStyle=1;align=left;" vertex="1" parent="1"><mxGeometry x="20" y="{topo:.0f}" width="1400" '
                 f'height="34" as="geometry"/></mxCell>']
        for fid, f in self.formas.items():
            cid = f"c{idx}-{fid}"
            if f["tipo"] == "ent":
                cor = "fillColor=#f5f5f5;strokeColor=#888888;" if f["externa"] else "fillColor=#dae8fc;strokeColor=#3b6aa0;"
                dupla = "shape=ext;double=1;" if f["fraca"] else ""
                estilo = f"rounded=0;whiteSpace=wrap;html=1;fontStyle=1;fontSize=13;{dupla}{cor}"
            elif f["tipo"] == "rel":
                dupla = "shape=ext;double=1;" if f["identificadora"] else ""
                estilo = f"rhombus;whiteSpace=wrap;html=1;fontSize=11;fillColor=#fff2cc;strokeColor=#b38f00;{dupla}"
            elif f["tipo"] == "tri":
                estilo = "triangle;direction=north;whiteSpace=wrap;html=1;fontSize=10;fillColor=#e1d5e7;strokeColor=#9673a6;verticalAlign=bottom;"
            else:
                sub = f["sub"]
                fonte = "fontStyle=4;" if sub == "id" else ""
                dupla = "shape=ext;double=1;" if sub == "multi" else ""
                tracejado = "dashed=1;" if sub == "deriv" else ""
                estilo = (f"ellipse;whiteSpace=wrap;html=1;fontSize=11;fillColor=#ffffff;strokeColor=#666666;"
                          f"{fonte}{dupla}{tracejado}")
            cells.append(f'<mxCell id="{cid}" value={quoteattr(f["rotulo"])} style="{estilo}" vertex="1" parent="1">'
                         f'<mxGeometry x="{f["x"]:.0f}" y="{f["y"]:.0f}" width="{f["w"]:.0f}" height="{f["h"]:.0f}" '
                         f'as="geometry"/></mxCell>')
        for n, lig in enumerate(self.ligacoes):
            rotulo = lig["rotulo"]
            dupla = ""
            de, para = self.formas[lig["de"]], self.formas[lig["para"]]
            # participação da entidade fraca no relacionamento identificador: linha dupla
            if de["tipo"] == "rel" and de.get("identificadora") and para.get("fraca"):
                dupla = "shape=link;"
            estilo = (f"endArrow=none;html=1;rounded=0;strokeColor=#555555;fontSize=12;fontStyle=1;"
                      f"labelBackgroundColor=#ffffff;{dupla}")
            if lig.get("entrada"):
                ex, ey = lig["entrada"]
                estilo += f"entryX={ex};entryY={ey};entryDx=0;entryDy=0;"
            geo = (f'<mxGeometry x="{self.posicao_rotulo(lig):.2f}" relative="1" as="geometry"><mxPoint as="offset"/></mxGeometry>'
                   if rotulo else '<mxGeometry relative="1" as="geometry"/>')
            cells.append(f'<mxCell id="c{idx}-l{n}" value={quoteattr(rotulo)} style="{estilo}" edge="1" parent="1" '
                         f'source="c{idx}-{lig["de"]}" target="c{idx}-{lig["para"]}">{geo}</mxCell>')
        larg = max(f["x"] + f["w"] for f in self.formas.values()) + 60
        alt = max(f["y"] + f["h"] for f in self.formas.values()) + 60
        legenda = ("<b>Legenda (notação de Chen, cardinalidade de Heuser)</b><br>"
                   "▭ entidade · ▭▭ entidade fraca · ◇ relacionamento · ◇◇ relacionamento identificador<br>"
                   "◯ atributo · <u>sublinhado</u> = identificador · ◯◯ multivalorado · tracejado = derivado<br>"
                   "△ (t,x) especialização total e exclusiva · cinza = entidade detalhada em outra página<br>"
                   "(mín,máx) ao lado da entidade = com quantas ocorrências dela uma ocorrência da outra se relaciona")
        cells.append(f'<mxCell id="c{idx}-leg" value={quoteattr(legenda)} style="text;html=1;align=left;verticalAlign=top;'
                     f'spacing=8;fillColor=#f5f5f5;strokeColor=#999999;rounded=1;fontSize=11;" vertex="1" parent="1">'
                     f'<mxGeometry x="20" y="{alt}" width="620" height="100" as="geometry"/></mxCell>')
        return (f'<diagram name={quoteattr(self.nome)} id="conceitual-{idx}"><mxGraphModel dx="1600" dy="1000" grid="1" '
                f'gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
                f'pageWidth="{larg:.0f}" pageHeight="{alt + 160:.0f}" math="0" shadow="0"><root><mxCell id="0"/>'
                f'<mxCell id="1" parent="0"/>' + "".join(cells) + "</root></mxGraphModel></diagram>")


def _segmento_cruza_caixa(x1, y1, x2, y2, bx, by, bw, bh) -> bool:
    # Liang-Barsky
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


# =====================================================================
# MOD01 · Usuários e acesso
# =====================================================================
def mod01() -> Pagina:
    p = Pagina("MOD01 · Usuários e acesso", "DER conceitual · MOD01 · Usuários e acesso")
    p.entidade("usuario", "Usuário", 770, 330)
    p.atributos("usuario", ["#id", "nome", "e-mail", "telefone", "senha", "situação", "foto"], "N")
    p.especializacao("esp", 770, 470, "usuario", ["aluno", "docente", "externo"])
    p.entidade("aluno", "Aluno", 420, 610)
    p.atributos("aluno", ["matrícula"], "W", dist=40)
    p.entidade("docente", "Docente", 770, 610)
    p.atributos("docente", ["cargo"], "W", dist=20)
    p.entidade("externo", "Membro externo", 1120, 610)
    p.atributos("externo", ["instituição"], "E", dist=40)
    p.entidade("perfil", "Perfil", 1360, 330)
    p.atributos("perfil", ["#código", "nome"], "S")
    p.relacao("possui", "possui", 1070, 330, [("usuario", "(0,N)"), ("perfil", "(1,N)")],
              atributos=["atribuído em"], lado="S")
    p.entidade("curso", "Curso", 420, 900)
    p.atributos("curso", ["#sigla", "nome"], "W", dist=40)
    p.entidade("nucleo", "Núcleo", 770, 1130)
    p.atributos("nucleo", ["#sigla", "nome"], "E", dist=40)
    p.entidade("area", "Área de interesse", 1120, 900)
    p.atributos("area", ["#nome"], "E", dist=40)
    p.relacao("cursa", "cursa", 420, 755, [("aluno", "(0,N)"), ("curso", "(1,1)")])
    p.relacao("atua", "atua em", 600, 790, [("docente", "(0,N)"), ("curso", "(0,1)")])
    p.relacao("pertence", "pertence a", 770, 950, [("docente", "(1,N)"), ("nucleo", "(1,1)")])
    p.relacao("oferece", "oferece", 560, 1050, [("nucleo", "(1,1)"), ("curso", "(1,N)")])
    p.relacao("interesse", "tem interesse em", 950, 790, [("docente", "(0,N)"), ("area", "(0,N)")])
    return p


# =====================================================================
# MOD02 · Ideias de TCC
# =====================================================================
def mod02() -> Pagina:
    p = Pagina("MOD02 · Ideias de TCC", "DER conceitual · MOD02 · Ideias de TCC")
    p.entidade("aluno", "Aluno", 200, 420, externa=True)
    p.entidade("proposta", "Proposta", 700, 420)
    p.atributos("proposta", ["#id", "título", "descrição", "destino", "data"], "S", dist=70)
    p.relacao("propoe", "propõe", 450, 420, [("aluno", "(1,1)"), ("proposta", "(0,N)")])
    p.entidade("area", "Área de interesse", 1250, 420, externa=True)
    p.relacao("direcionada", "direcionada à", 980, 420, [("proposta", "(0,N)"), ("area", "(0,1)")])
    p.entidade("docente", "Docente", 1250, 160, externa=True)
    p.relacao("enderecada", "endereçada a", 980, 250, [("proposta", "(0,N)"), ("docente", "(0,N)")])
    p.entidade("comentario", "Comentário", 700, 110, fraca=True)
    p.atributos("comentario", ["texto", "data", "oculto em"], "N", dist=50)
    p.relacao("recebe", "recebe", 700, 270, [("proposta", "(1,1)"), ("comentario", "(0,N)")], identificadora=True)
    p.relacao("escreve", "escreve", 1000, 70, [("docente", "(1,1)"), ("comentario", "(0,N)")])
    return p


# =====================================================================
# MOD03 · Gestão e acompanhamento dos TCCs
# =====================================================================
def mod03() -> Pagina:
    p = Pagina("MOD03 · Gestão dos TCCs", "DER conceitual · MOD03 · Gestão e acompanhamento dos TCCs")
    p.entidade("periodo", "Período letivo", 150, 120)
    p.atributos("periodo", ["#código", "início", "fim", "prazo versão final"], "W", dist=25)
    p.entidade("curso", "Curso", 150, 460, externa=True)
    p.entidade("turma", "Turma", 560, 300)
    p.atributos("turma", ["#código", "disciplina", "encerrada em"], "N", dist=60)
    p.relacao("ofertada", "ofertada em", 340, 180, [("turma", "(0,N)"), ("periodo", "(1,1)")])
    p.relacao("dacurso", "do curso", 340, 400, [("turma", "(0,N)"), ("curso", "(1,1)")])
    p.entidade("docente", "Docente", 1500, 120, externa=True)
    p.relacao("responsavel", "responsável por", 1030, 200, [("docente", "(1,1)"), ("turma", "(0,N)")])
    p.entidade("aluno", "Aluno", 560, 720, externa=True)
    p.relacao("matricula", "matricula-se", 560, 520, [("aluno", "(0,N)"), ("turma", "(0,N)")],
              atributos=["situação", "nota final"], lado="W")
    p.entidade("tcc", "TCC", 1030, 720, w=240, h=70)  # maior: é o centro de 10 relacionamentos
    p.atributos("tcc", ["#protocolo", "título", "resumo", "*palavra-chave", "etapa", "modalidade", "situação"], "N", dist=30)
    p.relacao("elabora", "elabora", 790, 720, [("aluno", "(1,1)"), ("tcc", "(0,N)")])
    p.relacao("vinculado", "vinculado a", 800, 470, [("tcc", "(0,N)"), ("turma", "(1,1)")])
    p.entidade("area", "Área de interesse", 1520, 760, externa=True)
    p.relacao("classificado", "classificado em", 1290, 760, [("tcc", "(0,N)", (1, 0.6)), ("area", "(1,1)")])
    p.relacao("orienta", "orienta", 1270, 420, [("docente", "(0,2)"), ("tcc", "(0,N)")],
              atributos=["papel", "status", "solicitado em", "respondido em"], lado="E")
    p.entidade("analise", "Análise de cadastro", 1500, 1000)
    p.atributos("analise", ["resultado", "parecer", "data"], "E", dist=40)
    p.relacao("analisado", "recebe", 1270, 1000, [("tcc", "(1,1)", (1, 0.85)), ("analise", "(0,N)")])
    p.relacao("decide", "decide", 1770, 560, [("docente", "(1,1)"), ("analise", "(0,N)")])
    p.relacao("origina", "origina", 1300, 560, [])
    p.ligacoes.append(dict(de="origina", para="tcc", rotulo="TCC1 (0,1)", entrada=(0.86, 0)))
    p.ligacoes.append(dict(de="origina", para="tcc", rotulo="TCC2 (0,1)", entrada=(1, 0.2)))
    p.entidade("documento", "Documento (versão)", 320, 1130, fraca=True)
    p.atributos("documento", ["#versão", "finalidade", "arquivo", "enviado em"], "W", dist=25)
    p.relacao("possuidoc", "possui", 560, 1000, [("tcc", "(1,1)", (0.08, 1)), ("documento", "(0,N)")], identificadora=True)
    p.entidade("tarefa", "Tarefa", 1030, 1400, fraca=True)
    p.atributos("tarefa", ["descrição", "prazo", "status"], "S", dist=40)
    p.relacao("temtarefa", "tem", 860, 1260, [("tcc", "(1,1)", (0.5, 1)), ("tarefa", "(0,N)")], identificadora=True)
    p.entidade("historico", "Histórico de situação", 1500, 1300, fraca=True)
    p.atributos("historico", ["situação nova", "data"], "S", dist=40)
    p.relacao("registra", "registra", 1270, 1200, [("tcc", "(1,1)", (0.82, 1)), ("historico", "(0,N)")], identificadora=True)
    return p


# =====================================================================
# MOD04 · Defesa e banca (inclui agenda, MOD07)
# =====================================================================
def mod04a() -> Pagina:
    p = Pagina("MOD04 · Defesa e banca", "DER conceitual · MOD04 · Defesa, banca e agenda (MOD07)")
    p.entidade("tcc", "TCC", 150, 400, externa=True)
    p.entidade("defesa", "Defesa", 650, 400)
    p.atributos("defesa", ["#id", "data", "início", "fim", "formato", "link", "situação", "publicada na agenda"], "N", dist=90)
    p.relacao("defendido", "é defendido em", 400, 400, [("tcc", "(1,1)"), ("defesa", "(0,N)")])
    p.entidade("local", "Local", 1150, 220)
    p.atributos("local", ["#nome"], "E", dist=40)
    p.relacao("ocorre", "ocorre em", 900, 220, [("defesa", "(0,N)"), ("local", "(0,1)")])
    p.entidade("usuario", "Usuário", 1150, 640, externa=True)
    p.relacao("compoe", "compõe a banca", 900, 520, [("usuario", "(3,5)"), ("defesa", "(0,N)")],
              atributos=["papel", "presente", "convocado em"], lado="E")
    p.relacao("agenda", "agenda", 900, 760, [("usuario", "(1,1)"), ("defesa", "(0,N)")])
    p.entidade("historico", "Histórico da defesa", 400, 700, fraca=True)
    p.atributos("historico", ["evento", "motivo", "data"], "W", dist=25)
    p.relacao("registra", "registra", 520, 560, [("defesa", "(1,1)"), ("historico", "(0,N)")], identificadora=True)
    p.entidade("ocorrencia", "Ocorrência", 650, 940, fraca=True)
    p.atributos("ocorrencia", ["texto", "data"], "S", dist=30)
    p.relacao("temocorr", "tem", 650, 760, [("defesa", "(1,1)"), ("ocorrencia", "(0,N)")], identificadora=True)
    p.entidade("ouvinte", "Ouvinte", 150, 940, fraca=True)
    p.atributos("ouvinte", ["nome", "matrícula"], "S", dist=30)
    p.relacao("assiste", "é assistida por", 150, 640, [("defesa", "(1,1)"), ("ouvinte", "(0,N)")], identificadora=True)
    return p


def mod04b() -> Pagina:
    p = Pagina("MOD04 · Avaliação e resultado", "DER conceitual · MOD04 · Avaliação, resultado, correções e documentos")
    p.entidade("defesa", "Defesa", 650, 160, externa=True)
    p.entidade("usuario", "Usuário (avaliador)", 150, 160, externa=True)
    p.entidade("avaliacao", "Avaliação", 400, 420)
    p.atributos("avaliacao", ["status", "parecer", "~nota total"], "W", dist=25)
    p.relacao("faz", "faz", 150, 300, [("usuario", "(1,1)"), ("avaliacao", "(0,N)")])
    p.relacao("recebeav", "recebe", 520, 290, [("defesa", "(1,1)"), ("avaliacao", "(0,N)")])
    p.entidade("instrumento", "Instrumento de avaliação", 1000, 420)
    p.atributos("instrumento", ["#versão", "vigente"], "N", dist=30)
    p.relacao("usa", "usa", 700, 420, [("avaliacao", "(0,N)"), ("instrumento", "(1,1)")])
    p.entidade("componente", "Componente", 1300, 640, fraca=True)
    p.atributos("componente", ["nome", "pontos"], "E", dist=40)
    p.relacao("compoe", "compõe-se de", 1300, 420, [("instrumento", "(1,1)"), ("componente", "(1,N)")], identificadora=True)
    p.entidade("criterio", "Critério", 1000, 860, fraca=True)
    p.atributos("criterio", ["nome", "peso", "textos dos conceitos"], "E", dist=40)
    p.relacao("temcrit", "tem", 1300, 860, [("componente", "(1,1)"), ("criterio", "(1,N)")], identificadora=True)
    p.relacao("pontua", "pontua", 650, 860, [("avaliacao", "(0,N)"), ("criterio", "(0,N)")],
              atributos=["conceito", "nota", "~nota ponderada"], lado="S")
    p.entidade("resultado", "Resultado (versão)", 1000, 160, fraca=True)
    p.atributos("resultado", ["#versão", "resultado", "parecer", "~nota final", "prazo", "anuência"], "N", dist=40)
    p.relacao("temres", "tem", 820, 160, [("defesa", "(1,1)"), ("resultado", "(0,N)")], identificadora=True)
    p.entidade("correcao", "Correção", 1550, 160, fraca=True)
    p.atributos("correcao", ["descrição", "situação"], "N", dist=40)
    p.relacao("exige", "exige", 1300, 160, [("resultado", "(1,1)"), ("correcao", "(0,N)")], identificadora=True)
    p.entidade("avaliador2", "Usuário (avaliador)", 1550, 640, externa=True)
    p.relacao("pede", "pede", 1550, 420, [("avaliador2", "(1,1)"), ("correcao", "(0,N)")])
    p.entidade("docof", "Documento oficial", 400, -60, fraca=True)
    p.atributos("docof", ["tipo", "versão", "vigente"], "W", dist=30)
    p.relacao("gera", "gera", 650, -60, [("defesa", "(1,1)"), ("docof", "(0,N)")], identificadora=True)
    return p


# =====================================================================
# MOD05 · Publicação
# =====================================================================
def mod05() -> Pagina:
    p = Pagina("MOD05 · Publicação", "DER conceitual · MOD05 · Publicação")
    p.entidade("tcc", "TCC (modalidade artigo)", 160, 300, externa=True)
    p.entidade("publicacao", "Publicação", 620, 300)
    p.atributos("publicacao", ["tipo de veículo", "veículo", "Qualis", "DOI", "situação atual"], "N", dist=50)
    p.relacao("submetido", "é submetido em", 390, 300, [("tcc", "(1,1)"), ("publicacao", "(0,N)")])
    p.entidade("historico", "Histórico editorial", 1100, 300, fraca=True)
    p.atributos("historico", ["situação", "data"], "N", dist=50)
    p.relacao("registra", "registra", 860, 300, [("publicacao", "(1,1)"), ("historico", "(1,N)")], identificadora=True)
    p.entidade("usuario", "Usuário", 1100, 560, externa=True)
    p.relacao("informa", "informa", 1100, 430, [("usuario", "(0,1)"), ("historico", "(0,N)")])
    return p


def previa_svg(p: Pagina) -> str:
    """Desenho aproximado da página, só para conferência visual (não é entregue)."""
    x0 = min(f["x"] for f in p.formas.values()) - 40
    y0 = min(f["y"] for f in p.formas.values()) - 40
    W = max(f["x"] + f["w"] for f in p.formas.values()) - x0 + 40
    H = max(f["y"] + f["h"] for f in p.formas.values()) - y0 + 40
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="{x0:.0f} {y0:.0f} {W:.0f} {H:.0f}" '
           f'font-family="Arial" font-size="11"><rect x="{x0}" y="{y0}" width="{W}" height="{H}" fill="white"/>']
    for lig in p.ligacoes:
        (x1, y1), (x2, y2) = p.pontas(lig)
        out.append(f'<line x1="{x1:.0f}" y1="{y1:.0f}" x2="{x2:.0f}" y2="{y2:.0f}" stroke="#555"/>')
    for f in p.formas.values():
        x, y, w, h = f["x"], f["y"], f["w"], f["h"]
        cx, cy = x + w / 2, y + h / 2
        t = html.escape(f["rotulo"])
        if f["tipo"] == "ent":
            cor = "#eee" if f["externa"] else "#dae8fc"
            out.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{w}" height="{h}" fill="{cor}" stroke="#335"/>')
            if f["fraca"]:
                out.append(f'<rect x="{x+4:.0f}" y="{y+4:.0f}" width="{w-8}" height="{h-8}" fill="none" stroke="#335"/>')
            out.append(f'<text x="{cx:.0f}" y="{cy+4:.0f}" text-anchor="middle" font-weight="bold" font-size="13">{t}</text>')
        elif f["tipo"] == "rel":
            out.append(f'<polygon points="{cx},{y} {x+w},{cy} {cx},{y+h} {x},{cy}" fill="#fff2cc" stroke="#b38f00"/>')
            out.append(f'<text x="{cx:.0f}" y="{cy+4:.0f}" text-anchor="middle">{t}</text>')
        elif f["tipo"] == "tri":
            out.append(f'<polygon points="{cx},{y} {x+w},{y+h} {x},{y+h}" fill="#e1d5e7" stroke="#9673a6"/>')
            out.append(f'<text x="{cx:.0f}" y="{y+h-6:.0f}" text-anchor="middle" font-size="10">{t}</text>')
        else:
            tr = ' stroke-dasharray="4 3"' if f["sub"] == "deriv" else ""
            out.append(f'<ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="{w/2}" ry="{h/2}" fill="white" stroke="#666"{tr}/>')
            if f["sub"] == "multi":
                out.append(f'<ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="{w/2-4}" ry="{h/2-4}" fill="none" stroke="#666"/>')
            deco = ' text-decoration="underline"' if f["sub"] == "id" else ""
            out.append(f'<text x="{cx:.0f}" y="{cy+4:.0f}" text-anchor="middle"{deco}>{t}</text>')
    for lig in p.ligacoes:
        (x1, y1), (x2, y2) = p.pontas(lig)
        if lig["rotulo"]:
            t = (p.posicao_rotulo(lig) + 1) / 2
            lx, ly = x1 + t * (x2 - x1), y1 + t * (y2 - y1) + 4
            out.append(f'<text x="{lx:.0f}" y="{ly:.0f}" font-weight="bold" fill="#c00" text-anchor="middle" '
                       f'stroke="white" stroke-width="3" paint-order="stroke">{lig["rotulo"]}</text>')
    out.append("</svg>")
    return "".join(out)


PAGINAS = [mod01, mod02, mod03, mod04a, mod04b, mod05]

if __name__ == "__main__":
    paginas = [f() for f in PAGINAS]
    for p in paginas:
        p.posicionar_atributos()
    total = 0
    for p in paginas:
        problemas = p.conferir()
        total += len(problemas)
        print(f"{p.nome}: {sum(1 for f in p.formas.values() if f['tipo'] == 'ent')} entidades, "
              f"{sum(1 for f in p.formas.values() if f['tipo'] == 'rel')} relacionamentos, {len(problemas)} problemas")
        for pr in problemas:
            print("   ", pr)
    xml = '<mxfile host="app.diagrams.net">' + "".join(p.xml(i) for i, p in enumerate(paginas)) + "</mxfile>"
    (AQUI / "der-conceitual-siga-uea.drawio").write_text(xml, encoding="utf8")
    import sys
    if len(sys.argv) > 1:  # pasta para as prévias em SVG (conferência visual)
        for i, p in enumerate(paginas):
            Path(sys.argv[1], f"conceitual-{i}.svg").write_text(previa_svg(p), encoding="utf8")
    raise SystemExit(1 if total else 0)
