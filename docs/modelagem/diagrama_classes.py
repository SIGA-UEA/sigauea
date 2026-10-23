"""Diagrama de classes do SIGA UEA, lido do código (não é escrito à mão).

Tudo o que aparece nas páginas 1 a 4 sai do código no momento em que o script roda:

  1. Domínio         backend/app/models.py (SQLAlchemy): atributos com o tipo do banco,
                     multiplicidade, padrão, CHECK, UNIQUE, propriedades derivadas e
                     associações (uma por FK, com o nome do relationship em cada ponta)
  2. Controle        backend/app/routes (cada rota com método, caminho, perfil exigido e
                     resposta) e backend/app/services (cada função com a assinatura do código)
  3. Fronteira       telas do Next.js (app/, components/, lib/) e as rotas da API que cada uma chama
  4. DTOs            backend/app/schemas (Pydantic): campos, validadores e tipos
  5. Planejado       o que ainda não está no código: tabelas e colunas planejadas do modelo
                     lógico (modelo_logico.py) e as operações previstas na análise

Gera docs/modelagem/diagrama-classes-siga-uea.drawio. O layout é do ELK (elk_layout.mjs):

    npm i --no-save elkjs@0.9.3
    python docs/modelagem/diagrama_classes.py [pasta-para-as-previas-svg]

Falha (código 1) se uma tela chamar uma rota que a API não tem ou se uma linha atravessar uma caixa.
"""

from __future__ import annotations

import ast
import html
import importlib
import inspect
import pkgutil
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import quoteattr

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
BACKEND = RAIZ / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(AQUI))

import der_pe_de_galinha as pg  # noqa: E402  (layout, pontos e rótulos das linhas)
import modelo_logico as ml  # noqa: E402

import pydantic  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402
from sqlalchemy import CheckConstraint, UniqueConstraint  # noqa: E402

import app.models as mo  # noqa: E402
import app.routes  # noqa: E402
import app.schemas  # noqa: E402
import app.services  # noqa: E402

PREFIXO_API = "/api/v1"
CW, LH = 6.0, 14  # largura de um caractere (Courier New 10) e altura de uma linha
FONTE = "fontFamily=Courier New;fontSize=10;"

COR = {
    "entidade": ("#dae8fc", "#6c8ebf"),
    "enum": ("#fff2cc", "#d6b656"),
    "controle": ("#d5e8d4", "#82b366"),
    "servico": ("#ffe6cc", "#d79b00"),
    "util": ("#f5f5f5", "#666666"),
    "fronteira": ("#e1d5e7", "#9673a6"),
    "dto": ("#f8cecc", "#b85450"),
    "ref": ("#ffffff", "#999999"),
}


@dataclass
class Caixa:
    id: str
    nome: str
    estereotipo: str = ""
    secoes: list[list[str]] = field(default_factory=list)
    tipo: str = "entidade"
    tracejado: bool = False

    @property
    def cab(self) -> int:
        return 18 + 14 * (bool(self.estereotipo) + 1)

    def alturas(self) -> list[int]:
        return [max(1, len(s)) * LH + 8 for s in self.secoes]

    @property
    def largura(self) -> int:
        linhas = [ln for s in self.secoes for ln in s]
        corpo = max([len(ln) for ln in linhas] + [0]) * CW + 20
        cab = max(len(self.nome) * 7.6, len(self.estereotipo) * 6.4) + 30
        return int(max(150, corpo, cab))

    @property
    def altura(self) -> int:
        return self.cab + sum(self.alturas())


@dataclass
class Ligacao:
    de: str
    para: str
    tipo: str = "assoc"  # assoc, comp, dep, gen
    rot_de: str = ""  # rótulo na ponta "de" (papel e multiplicidade)
    rot_para: str = ""
    rot_meio: str = ""
    nav_de: bool = False  # "para" enxerga "de" (seta na ponta "de")
    nav_para: bool = False  # "de" enxerga "para" (seta na ponta "para")
    id: str = ""


def pascal(nome: str) -> str:
    return "".join(p.capitalize() for p in nome.split("_"))


def snake(nome: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", nome).lower()


def papel_util(papel: str, alvo: str) -> str:
    """O papel só vai para o desenho quando diz algo além do nome da classe (usuario -> Usuario não diz)."""
    return "" if papel in (snake(alvo), snake(alvo) + "_id") else papel


def submodulos(pacote) -> list:
    return [importlib.import_module(f"{pacote.__name__}.{m.name}")
            for m in sorted(pkgutil.iter_modules(pacote.__path__), key=lambda m: m.name)]


def imports_app(modulo) -> dict[str, list[str]]:
    """{'app.models': ['Tcc', ...], 'app.services': ['email', ...]} lidos do import no topo do arquivo."""
    arvore = ast.parse(Path(modulo.__file__).read_text(encoding="utf8"))
    saida: dict[str, list[str]] = {}
    for no in arvore.body:
        if isinstance(no, ast.ImportFrom) and (no.module or "").startswith("app"):
            saida.setdefault(no.module, []).extend(a.name for a in no.names)
        elif isinstance(no, ast.Import):
            for a in no.names:
                if a.name.startswith("app."):
                    pai, _, nome = a.name.rpartition(".")
                    saida.setdefault(pai, []).append(nome)
    return saida


def assinatura(fn: ast.FunctionDef, pular_self: bool = False) -> str:
    a = fn.args
    pos = a.posonlyargs + a.args
    padroes = [None] * (len(pos) - len(a.defaults)) + list(a.defaults)
    partes = []
    for arg, padrao in zip(pos, padroes):
        if pular_self and arg.arg in ("self", "cls"):
            continue
        txt = arg.arg + (f": {ast.unparse(arg.annotation)}" if arg.annotation else "")
        if padrao is not None:
            txt += f" = {ast.unparse(padrao)}"
        partes.append(txt)
    if a.vararg:
        partes.append("*" + a.vararg.arg + (f": {ast.unparse(a.vararg.annotation)}" if a.vararg.annotation else ""))
    elif a.kwonlyargs:
        partes.append("*")
    for arg, padrao in zip(a.kwonlyargs, a.kw_defaults):
        txt = arg.arg + (f": {ast.unparse(arg.annotation)}" if arg.annotation else "")
        partes.append(txt + (f" = {ast.unparse(padrao)}" if padrao is not None else ""))
    if a.kwarg:
        partes.append("**" + a.kwarg.arg)
    ret = f" : {ast.unparse(fn.returns)}" if fn.returns else ""
    vis = "-" if fn.name.startswith("_") and not fn.name.startswith("__") else "+"
    return f"{vis} {fn.name}({', '.join(partes)}){ret}"


def operacoes_do_modulo(modulo) -> list[str]:
    """Funções e classes de nível de módulo, na ordem do arquivo."""
    linhas = []
    for no in ast.parse(Path(modulo.__file__).read_text(encoding="utf8")).body:
        if isinstance(no, ast.FunctionDef):
            linhas.append(assinatura(no))
        elif isinstance(no, ast.ClassDef):
            bases = ", ".join(ast.unparse(b) for b in no.bases)
            linhas.append(f"«classe» {no.name}({bases})")
            linhas += ["    " + assinatura(f, True) for f in no.body if isinstance(f, ast.FunctionDef)]
    return linhas


# ====================================================================== 1 · domínio
CONSTANTES = {k: v for k, v in vars(mo).items() if k.isupper() and isinstance(v, tuple)}


def nome_enum(tabela: str, coluna: str, valores: tuple[str, ...]) -> str:
    for k, v in CONSTANTES.items():
        if tuple(v) == valores:
            return k
    return f"{tabela}.{coluna}"


def tipo_sql(t) -> str:
    nome = type(t).__name__
    if nome == "Numeric":
        return f"Numeric({t.precision},{t.scale})"
    comp = getattr(t, "length", None)
    return f"{nome}({comp})" if comp else nome


def padrao(col) -> str:
    if col.default is None:
        return ""
    arg = col.default.arg
    if callable(arg):  # SQLAlchemy embrulha a função, mas mantém o __name__ dela
        return f" = {arg.__name__}()"
    return f" = {arg!r}"


def triggers_das_migracoes() -> dict[str, list[str]]:
    """Regras que só existem no banco (criadas por migração, não pelo models.py)."""
    saida: dict[str, list[str]] = {}
    for arq in sorted((BACKEND / "migrations" / "versions").glob("*.py")):
        texto = arq.read_text(encoding="utf8")
        for nome, quando, tabela in re.findall(r"CREATE TRIGGER (\w+) BEFORE ([A-Z ]+?) ON (\w+)", texto):
            saida.setdefault(tabela, []).append(
                f"{{imutável: trigger {nome} recusa {quando} (migração {arq.name[:4]})}}")
    return saida


def classes_mapeadas() -> list:
    cls = [m.class_ for m in mo.Base.registry.mappers]
    return sorted(cls, key=lambda c: inspect.getsourcelines(c)[1])


def pagina_dominio() -> tuple[list[Caixa], list[Ligacao], dict]:
    classes = classes_mapeadas()
    por_tabela = {c.__table__.name: c for c in classes}
    triggers = triggers_das_migracoes()
    caixas, ligs, enums = [], [], {}
    usos_enum: list[tuple[str, str]] = []

    for cls in classes:
        tabela = cls.__table__
        mapper = mo.Base.registry._class_registry[cls.__name__].__mapper__
        doms = {}
        restr = []
        for ck in tabela.constraints:
            if isinstance(ck, CheckConstraint):
                texto = str(ck.sqltext)
                m = re.fullmatch(r"(\w+) IN \((.*)\)", texto)
                if m:
                    vals = tuple(re.findall(r"'([^']*)'", m.group(2)))
                    en = nome_enum(tabela.name, m.group(1), vals)
                    enums[en] = vals
                    doms[m.group(1)] = en
                    usos_enum.append((cls.__name__, en))
                else:
                    restr.append(f"{{{ck.name}: {texto}}}")
            elif isinstance(ck, UniqueConstraint) and len(ck.columns) > 1:
                restr.append(f"{{unique({', '.join(c.name for c in ck.columns)})}}")
        for ix in sorted(tabela.indexes, key=lambda i: i.name):
            if ix.unique and any(not hasattr(e, "table") for e in ix.expressions):
                restr.append(f"{{unique {', '.join(str(e) for e in ix.expressions)}}}")
        restr += triggers.get(tabela.name, [])

        attrs = []
        pks = [c for c in tabela.columns if c.primary_key]
        for col in tabela.columns:
            props = []
            if col.primary_key:
                props.append("PK")
            for fk in col.foreign_keys:
                props.append(f"FK {fk.target_fullname}")
            if col.unique:
                props.append("unique")
            if getattr(mapper.attrs[col.key], "deferred", False):
                props.append("deferred")
            if col.name in doms:
                props.append(f"in {doms[col.name]}")
            mult = " [0..1]" if col.nullable and not col.primary_key else ""
            extra = f" {{{', '.join(props)}}}" if props else ""
            attrs.append(f"+ {col.key} : {tipo_sql(col.type)}{mult}{padrao(col)}{extra}")
        for nome, obj in vars(cls).items():
            if isinstance(obj, property):
                ret = obj.fget.__annotations__.get("return", "")
                tipo = str(ret) if getattr(ret, "__args__", None) else getattr(ret, "__name__", str(ret))
                attrs.append(f"+ /{nome} : {tipo}  {{derivado}}")
        secoes = [attrs] + ([restr] if restr else [])
        # a legenda diz que a tabela é o nome da classe em snake_case; vale para todas
        assert snake(cls.__name__) == tabela.name, f"{cls.__name__} -> {tabela.name}: atualize a legenda"
        caixas.append(Caixa(cls.__name__, cls.__name__, secoes=secoes, tipo="entidade"))

        # associações: uma por FK desta tabela, com os relationships das duas pontas
        for col in tabela.columns:
            for fk in col.foreign_keys:
                alvo = por_tabela[fk.column.table.name]
                ida = next((r for r in mapper.relationships if r.direction.name == "MANYTOONE"
                            and col in r.local_columns), None)
                volta = next((r for r in alvo.__mapper__.relationships if r.direction.name == "ONETOMANY"
                              and r.mapper.class_ is cls and col in r.remote_side), None)
                um = (col.primary_key and len(pks) == 1) or col.unique
                mult_alvo = "0..1" if col.nullable else "1"
                mult_cls = "0..1" if um or (volta is not None and not volta.uselist) else "*"
                comp = volta is not None and volta.cascade.delete_orphan
                papel_alvo = ida.key if ida else col.key
                papel_cls = ""
                if volta is not None:
                    papel_cls = volta.key + (" {readOnly}" if volta.viewonly else "")
                ligs.append(Ligacao(
                    de=cls.__name__, para=alvo.__name__, tipo="comp" if comp else "assoc",
                    rot_para=mult_alvo, rot_meio=papel_util(papel_alvo, alvo.__name__),
                    rot_de=f"{papel_cls} {mult_cls}".strip(),
                    nav_para=ida is not None, nav_de=volta is not None and not comp,
                    id=f"{tabela.name}.{col.name}"))
        # muitos-para-muitos por tabela associativa (relationship com secondary)
        for r in mapper.relationships:
            if r.secondary is not None:
                ligs.append(Ligacao(
                    de=cls.__name__, para=r.mapper.class_.__name__, rot_para="*", rot_de="*",
                    rot_meio=f"{r.key} (via {pascal(r.secondary.name)})", nav_para=True,
                    id=f"{cls.__name__}.{r.key}"))

    # valores usados pelo código sem CHECK no banco
    tokens = tuple(v for k, v in vars(mo).items() if k.startswith("TOKEN_"))
    sem_check = [
        ("PERFIS", tuple(mo.PERFIS), "Perfil", "códigos de perfil.codigo (carga inicial); "
         f"PERFIS_DOCENTE = {', '.join(mo.PERFIS_DOCENTE)}"),
        ("TOKEN_*", tokens, "TokenUsuario", "valores de token_usuario.tipo"),
    ]
    for nome, vals, cls_nome, nota in sem_check:
        caixas.append(Caixa(f"enum-{nome}", nome, "«enumeration»",
                            [list(vals), ["{sem CHECK no banco}"] + quebrar(nota, 60)], "enum"))
        ligs.append(Ligacao(cls_nome, f"enum-{nome}", "dep", id=f"usa-{cls_nome}-{nome}"))
    for nome, vals in enums.items():
        caixas.append(Caixa(f"enum-{nome}", nome, "«enumeration»", [list(vals)], "enum"))
    for cls_nome, en in dict.fromkeys(usos_enum):
        ligs.append(Ligacao(cls_nome, f"enum-{en}", "dep", id=f"usa-{cls_nome}-{en}"))
    return caixas, ligs, {"classes": len(classes), "enums": len(enums) + len(sem_check)}


# ====================================================================== 2 · controle
def perfis_exigidos(rota: APIRoute) -> str:
    perfis: list[str] = []
    autenticado = False
    for d in rota.dependant.dependencies:
        if d.call.__name__ == "usuario_atual":
            autenticado = True
        elif d.call.__name__ == "_verificar":
            perfis += list(inspect.getclosurevars(d.call).nonlocals.get("perfis", ()))
    if perfis:
        return "|".join(perfis)
    return "autenticado" if autenticado else "público"


def nome_tipo(t) -> str:
    if t is None:
        return ""
    if getattr(t, "__origin__", None) is list:
        return f"list[{nome_tipo(t.__args__[0])}]"
    return getattr(t, "__name__", str(t))


def parametros(rota: APIRoute) -> str:
    out = []
    for p in inspect.signature(rota.endpoint).parameters.values():
        if type(p.default).__name__ == "Depends" or p.name in ("db", "eu", "tarefas", "request", "resposta"):
            continue
        anot = p.annotation
        if inspect.isclass(anot) and (issubclass(anot, pydantic.BaseModel) or anot.__name__ == "UploadFile"):
            out.append(f"{p.name}: {anot.__name__}")
        else:
            out.append(p.name + ("?" if p.default is not inspect.Parameter.empty else ""))
    return ", ".join(out)


def rotas_da_api() -> list[dict]:
    """Todas as rotas, lidas dos módulos routes/ (o main inclui todas sob /api/v1, menos o health)."""
    rotas = []
    for mod in submodulos(app.routes):
        prefixo = "" if mod.__name__.endswith(".health") else PREFIXO_API
        for r in mod.router.routes:
            if not isinstance(r, APIRoute):
                continue
            for metodo in sorted(r.methods):
                rotas.append(dict(modulo=mod, metodo=metodo, caminho=prefixo + r.path, rota=r,
                                  regex=re.compile("^" + re.sub(r"\{[^}]+\}", "[^/]+", prefixo + r.path) + "$")))
    return rotas


def nome_controle(mod) -> str:
    return "Controlador" + pascal(mod.__name__.rsplit(".", 1)[1])


def pagina_controle(rotas: list[dict]) -> tuple[list[Caixa], list[Ligacao], dict]:
    caixas, ligs = [], []
    servicos = {m.__name__: m for m in submodulos(app.services)}
    for mod in submodulos(app.routes):
        ops = []
        for d in (x for x in rotas if x["modulo"] is mod):
            r = d["rota"]
            resp = nome_tipo(r.response_model) or ("arquivo" if r.response_model is None and r.status_code != 204 else "")
            status = f" {r.status_code}" if r.status_code else ""
            caminho = d["caminho"].removeprefix(PREFIXO_API)
            ops.append(f"+ {d['metodo']} {caminho} → {r.endpoint.__name__}({parametros(r)})"
                       f"{' : ' + resp if resp else ''}{status} [{perfis_exigidos(r)}]")
        imps = imports_app(mod)
        usa = [f"app.services.{s}" for s in imps.get("app.services", [])]
        infra = sorted({k.removeprefix("app.") for k in imps if k not in ("app.services", "app.schemas", "app.models")}
                       | ({"models"} if "app.models" in imps else set()))
        rodape = [f"tag OpenAPI: {', '.join(mod.router.tags)}"] + ([f"infra: {', '.join(infra)}"] if infra else [])
        cid = mod.__name__
        caixas.append(Caixa(cid, nome_controle(mod), "«controle»", [ops, rodape], "controle"))
        for s in usa:
            ligs.append(Ligacao(cid, s, "dep", rot_meio="«usa»", id=f"{cid}->{s}"))

    for nome, mod in servicos.items():
        imps = imports_app(mod)
        ents = imps.get("app.models", [])
        classes = [e for e in ents if e in vars(mo) and inspect.isclass(getattr(mo, e))]
        consts = [e for e in ents if e not in classes]
        rodape = []
        if classes:
            rodape.append("entidades: " + ", ".join(classes))
        if consts:
            rodape.append("constantes: " + ", ".join(consts))
        dtos = [n for k, v in imps.items() if k.startswith("app.schemas") for n in v]
        if dtos:
            rodape.append("DTOs: " + ", ".join(dtos))
        infra = sorted(k.removeprefix("app.") for k in imps
                       if k not in ("app.models", "app.services") and not k.startswith("app.schemas"))
        if infra:
            rodape.append("infra: " + ", ".join(infra))
        rodape = [ln for r in rodape for ln in quebrar(r, 90)]
        caixas.append(Caixa(nome, "Servico" + pascal(nome.rsplit(".", 1)[1]), "«serviço»",
                            [operacoes_do_modulo(mod), rodape], "servico"))
        for s in imps.get("app.services", []):
            ligs.append(Ligacao(nome, f"app.services.{s}", "dep", rot_meio="«usa»", id=f"{nome}->{s}"))

    for nome in ("deps", "security", "erros", "database"):
        mod = importlib.import_module(f"app.{nome}")
        caixas.append(Caixa(f"app.{nome}", pascal(nome), "«utilitário»", [operacoes_do_modulo(mod)], "util"))
    return caixas, ligs, {"controles": len(submodulos(app.routes)), "servicos": len(servicos), "rotas": len(rotas)}


def quebrar(texto: str, n: int) -> list[str]:
    linhas, atual = [], ""
    for palavra in texto.split(" "):
        if atual and len(atual) + len(palavra) + 1 > n:
            linhas.append(atual)
            atual = "    " + palavra
        else:
            atual = f"{atual} {palavra}" if atual else palavra
    return linhas + [atual]


# ====================================================================== 3 · fronteira
LITERAL = r"""(`[^`]*`|"[^"]*"|'[^']*')"""
# Único caminho montado em tempo de execução que a leitura não resolve sozinha:
# a aba da tela de usuários (type Aba = "docente" | "aluno" | "area"; a aba "area" não lista por aqui).
EXPANSOES = {"/${aba}s": ["/docentes", "/alunos"]}


def primeiro_argumento(texto: str, inicio: int) -> tuple[str, int]:
    """Texto do 1º argumento de uma chamada que começa em texto[inicio] e onde ele termina."""
    nivel, aspas, i = 0, None, inicio
    while i < len(texto):
        ch = texto[i]
        if aspas:
            aspas = None if ch == aspas else aspas
        elif ch in "`'\"":
            aspas = ch
        elif ch in "([{":
            nivel += 1
        elif ch in ")]}":
            if nivel == 0:
                break
            nivel -= 1
        elif ch == "," and nivel == 0:
            break
        i += 1
    return texto[inicio:i].strip(), i


def chamadas_da_tela(texto: str) -> list[tuple[str, str | None]]:
    """(caminho, método) de cada chamada à API no arquivo."""
    saida = []
    for m in re.finditer(r"(?<!function )\bapi(?:<[^()]*?>)?\(", texto):  # chamadas, não a declaração
        arg, fim = primeiro_argumento(texto, m.end())
        resto, _ = primeiro_argumento(texto, fim + 1) if texto[fim:fim + 1] == "," else ("", fim)
        metodo = re.search(r'metodo:\s*"(\w+)"', resto)
        metodo = metodo.group(1) if metodo else None
        literais = [x[1:-1] for x in re.findall(LITERAL, arg)]
        if not literais and "." in arg:  # objeto.campo: os valores atribuídos a "campo:" no arquivo
            literais = [x[1:-1] for x in re.findall(rf"\b{arg.rsplit('.', 1)[1]}:\s*{LITERAL}", texto)]
        elif not literais:  # parâmetro de função: os literais passados como 1º argumento nas chamadas dela
            fn = re.search(rf"function (\w+)\(\s*{arg}\b", texto)
            literais = [x[1:-1] for x in re.findall(rf"\b{fn.group(1)}\(\s*{LITERAL}", texto)] if fn else [arg]
        saida += [(lit, metodo) for lit in literais]
    # endereço completo fora do api(): fetch no servidor (sessão) e <img src> da foto
    for lit in re.findall(LITERAL, texto):
        m = re.search(r"/api/v1(/[^`'\"]+)", lit)
        if m:
            saida.append((m.group(1), "GET"))
    return saida


def resolver(caminho: str, metodo: str | None, rotas: list[dict]) -> list[dict]:
    # o que vem depois do caminho é query string, literal ("?periodo=") ou em variável ("${filtro}")
    base = re.sub(r"(?<!/)\$\{[^}]+\}$", "", caminho.split("?")[0])
    for k, v in EXPANSOES.items():
        if base == k:
            return [x for c in v for x in resolver(c, metodo, rotas)]
    url = PREFIXO_API + re.sub(r"\$\{[^}]+\}", "X", base)
    cand = [r for r in rotas if r["regex"].match(url)]
    # caminho literal vence o com parâmetro (ex.: /turmas/minhas antes de /turmas/{turma_id})
    exatos = [r for r in cand if "{" not in r["caminho"]]
    cand = exatos or cand
    if len({r["metodo"] for r in cand}) > 1:
        cand = [r for r in cand if r["metodo"] == (metodo or "GET")]
    return cand


def pagina_fronteira(rotas: list[dict]) -> tuple[list[Caixa], list[Ligacao], dict, list[str]]:
    arquivos = sorted(p for pasta in ("app", "components", "lib") for p in (RAIZ / pasta).rglob("*.ts*")
                      if p.suffix in (".ts", ".tsx"))
    caixas, ligs, erros = [], [], []
    chama: dict[str, list[dict]] = {}
    for arq in arquivos:
        rel = arq.relative_to(RAIZ).as_posix()
        # comentários de linha ficam de fora (lib/api.ts mostra api("/caminho") como exemplo)
        texto = re.sub(r"(?m)^\s*//.*$", "", arq.read_text(encoding="utf8"))
        achadas = []
        for caminho, metodo in chamadas_da_tela(texto):
            r = resolver(caminho, metodo, rotas)
            if not r:
                erros.append(f"{rel}: {metodo or '?'} {caminho} não existe na API")
            achadas += r
        if achadas or arq.name == "page.tsx":
            chama[rel] = list({id(r): r for r in achadas}.values())
    usados = set(chama)
    # lib/ (sessão, tipos) é usada por quase todas as telas: vira contagem na caixa, não linha
    usuarios_lib: dict[str, int] = {}
    for rel in chama:
        texto = (RAIZ / rel).read_text(encoding="utf8")
        for imp in re.findall(r'from\s+"((?:@/|\.\.?/)[^"]+)"', texto):
            base = (RAIZ / imp[2:]) if imp.startswith("@/") else (RAIZ / rel).parent / imp
            for ext in (".tsx", ".ts"):
                alvo = Path(str(base.resolve()) + ext)
                if not alvo.exists() or alvo.relative_to(RAIZ).as_posix() not in usados:
                    continue
                alvo_rel = alvo.relative_to(RAIZ).as_posix()
                if alvo_rel.startswith("lib/"):
                    usuarios_lib[alvo_rel] = usuarios_lib.get(alvo_rel, 0) + 1
                else:
                    ligs.append(Ligacao(rel, alvo_rel, "dep", rot_meio="«usa»", id=f"{rel}->{imp}"))
    for rel, rs in chama.items():
        rota_tela = "/" + "/".join(p for p in Path(rel).parent.parts[1:] if not p.startswith("("))
        nome = rota_tela if rel.endswith("page.tsx") else Path(rel).stem
        linhas = [f"{r['metodo']} {r['caminho'].removeprefix(PREFIXO_API)} → {r['rota'].endpoint.__name__}()"
                  for r in sorted(rs, key=lambda r: (r["caminho"], r["metodo"]))] or ["(não chama a API)"]
        secoes = [linhas] + ([[f"importado por {usuarios_lib[rel]} telas e componentes"]] if rel in usuarios_lib else [])
        caixas.append(Caixa(rel, nome, "«fronteira»" if rel.endswith("page.tsx") else "«componente»",
                            secoes, "fronteira"))
        for mod in dict.fromkeys(r["modulo"] for r in rs):
            ligs.append(Ligacao(rel, mod.__name__, "dep", id=f"{rel}->{mod.__name__}"))
    nomes = [c.nome for c in caixas]
    assert len(nomes) == len(set(nomes)), "duas telas ou componentes com o mesmo nome no diagrama"
    for mod in dict.fromkeys(r["modulo"] for rs in chama.values() for r in rs):
        caixas.append(Caixa(mod.__name__, nome_controle(mod), "«controle»", [], "controle"))
    chamadas = {(r["metodo"], r["caminho"]) for rs in chama.values() for r in rs}
    return caixas, ligs, {"telas": len(chama), "chamadas": chamadas}, erros


# ====================================================================== 4 · DTOs
def pagina_dtos() -> tuple[list[Caixa], list[Ligacao], dict]:
    caixas, ligs = [], []
    modulos = submodulos(app.schemas)
    todas = {n for m in modulos for n, c in vars(m).items()
             if inspect.isclass(c) and issubclass(c, pydantic.BaseModel) and c.__module__ == m.__name__}
    for mod in modulos:
        arvore = ast.parse(Path(mod.__file__).read_text(encoding="utf8"))
        tipos = []
        for no in arvore.body:
            if isinstance(no, ast.Assign) and isinstance(no.targets[0], ast.Name):
                tipos.append(f"{no.targets[0].id} = {ast.unparse(no.value)}")
            elif isinstance(no, ast.ClassDef):
                campos, ops, restr = [], [], []
                for item in no.body:
                    if isinstance(item, ast.AnnAssign):
                        nome = item.target.id
                        anot = ast.unparse(item.annotation)
                        val = f" = {ast.unparse(item.value)}" if item.value is not None else ""
                        campos.append(f"+ {nome} : {anot}{val}")
                        refs = [n for n in re.findall(r"\b\w+\b", anot) if n in todas]
                        for ref in dict.fromkeys(refs):
                            mult = "*" if "list[" in anot else ("0..1" if "None" in anot else "1")
                            ligs.append(Ligacao(ref, no.name, "comp", rot_de=mult, nav_de=True,
                                                rot_meio=papel_util(nome, ref.removesuffix("Out")),
                                                id=f"{no.name}.{nome}->{ref}"))
                    elif isinstance(item, ast.Assign) and ast.unparse(item.targets[0]) == "model_config":
                        restr.append(f"{{{ast.unparse(item.value)}}}")
                    elif isinstance(item, ast.FunctionDef):
                        decos = [ast.unparse(d) for d in item.decorator_list]
                        ops.append((f"«{', '.join(decos)}» " if decos else "") + assinatura(item, True))
                for b in no.bases:
                    if ast.unparse(b) in todas:
                        ligs.append(Ligacao(no.name, ast.unparse(b), "gen", id=f"{no.name}-gen"))
                secoes = [campos or ["(sem campos próprios)"]] + ([ops] if ops else []) + ([restr] if restr else [])
                caixas.append(Caixa(no.name, no.name, "«DTO»", secoes, "dto"))
        if tipos:
            modulo = mod.__name__.rsplit(".", 1)[1]
            caixas.append(Caixa(f"tipos-{mod.__name__}", f"Tipos{pascal(modulo)}", "«tipos e constantes»",
                                [[ln for t in tipos for ln in quebrar(t, 100)]], "enum"))
    return caixas, ligs, {"dtos": len(todas)}


# ====================================================================== 5 · planejado
# Operações da análise (diagramas de sequência) que ainda não têm rota. As que já existem
# com outro nome ou caminho estão nas páginas 2 e 3.
PLANEJADO_CONTROLE = {
    "CalculadoraNotaFinal": ["+ calcularNotaFinal(idDefesa, idTcc, modalidade)", "+ calcularMedia(notas[])",
                             "usa: Avaliacao, PublicacaoArtigo"],
    "ControladorAgenda": ["+ GET /defesas/{idDefesa}/divulgacao", "+ POST /defesas/{idDefesa}/publicacao",
                          "+ validarCondicoes(defesa)", "+ POST /defesas/{idDefesa}/retirada",
                          "+ GET /agenda?curso&de&até", "+ POST /agenda/pdf", "+ gerarPdf(apresentações[])",
                          "usa: Defesa, LocalDefesa, Orientacao, TCC"],
    "ControladorAgendamentoDefesa": [
        "+ POST /tccs/{idTcc}/defesa", "+ validarComposicao(banca[])", "+ GET /tccs/{idTcc}/defesa/banca",
        "+ POST /defesas/banca/validar", "+ validarComposicao(membros[])", "+ POST /usuarios/membros-externos",
        "+ POST /defesas/{idDefesa}/remarcacao", "+ POST /defesas/{idDefesa}/cancelamento",
        "+ POST /defesas/{idDefesa}/suplente",
        "usa: AcessoLimitado, BancaMembro, Curso, Defesa, DocumentoTCC, HistoricoDefesa,",
        "     LocalDefesa, NotificacaoEmail, Orientacao, TCC, Usuario"],
    "ControladorAnaliseCadastro": ["+ POST /cadastros/{idTcc}/decisao", "+ GET /cadastros?curso=&periodo=&situacao=",
                                   "+ GET /cadastros/{idTcc}",
                                   "usa: AnaliseCadastro, DocumentoTCC, HistoricoSituacao, NotificacaoEmail,",
                                   "     Orientacao, TCC, Usuario"],
    "ControladorAvaliacaoDefesa": [
        "+ GET /defesas/{idDefesa}/resultado", "+ POST /defesas/{idDefesa}/resultado",
        "+ GET /defesas/{idDefesa}/avaliacao", "+ POST /defesas/{idDefesa}/avaliacao/criterios",
        "+ validarNota(conceito, nota)", "+ calcularPonderada(nota, peso) = nota × peso × 10",
        "+ POST /defesas/{idDefesa}/avaliacao/envio", "+ POST /defesas/{idDefesa}/resultado/retificacao",
        "+ calcularNotaFinal(avaliações[], publicação)", "+ verificarVinculo(usuário, defesa)",
        "+ GET /defesas/{idDefesa}/documentos",
        "usa: Avaliacao, AvaliacaoCriterio, BancaMembro, Defesa, DocumentoOficial,",
        "     InstrumentoAvaliacao, ResultadoDefesa"],
    "ControladorCorrecoes": [
        "+ GET /tccs/{idTcc}/correcoes", "+ POST /tccs/{idTcc}/correcoes/anuencia", "+ POST /tccs/{idTcc}/documentos",
        "+ compararPrazo(enviadoEm, prazo)", "+ POST /tccs/{idTcc}/correcoes/atendidas",
        "+ criarLista(idResultado, exigências[])", "+ GET /correcoes/{idCorrecao}",
        "+ POST /correcoes/{idCorrecao}/decisao", "+ verificarConclusao(idTcc)",
        "+ POST /tccs/{idTcc}/correcoes/atraso", "+ POST /tccs/{idTcc}/correcoes/prazo",
        "usa: Correcao, DocumentoTCC, HistoricoSituacao, PeriodoLetivo, ResultadoDefesa, TCC, Turma"],
    "ControladorDocumentosDefesa": ["+ POST /defesas/{idDefesa}/documentos/ata", "+ gerarPdf(modelo da ata, dados)",
                                    "+ gerarPdf(modelo da folha, dados)",
                                    "+ POST /defesas/{idDefesa}/documentos/certificados",
                                    "usa: BancaMembro, Defesa, DocumentoOficial, NotificacaoEmail, ResultadoDefesa, TCC"],
    "ControladorIndicadores": ["+ GET /indicadores/producao-cientifica?curso&período",
                               "+ contarPorSituacao(situações[])", "+ POST /indicadores/relatorio",
                               "+ gerarPdf(indicadores, filtros)", "usa: HistoricoPublicacao, TCC, Usuario"],
    "ControladorLembretes": ["(tarefa agendada, sem rota)", "usa: BancaMembro, Defesa, NotificacaoEmail, TCC"],
    "ControladorNotificacao": ["+ notificarSituacao(idTcc, idPublicacao, situação)",
                               "usa: NotificacaoEmail, Orientacao, TCC"],
    "ControladorOcorrencias": [
        "+ GET /defesas/{idDefesa}/ocorrencias", "+ POST /defesas/{idDefesa}/ocorrencias",
        "+ POST /defesas/{idDefesa}/ouvintes", "+ PUT /defesas/{idDefesa}/ocorrencias/{id} ou /ouvintes/{id}",
        "+ POST /defesas/{idDefesa}/declaracoes", "+ registrarPendência(ouvinte)",
        "usa: Defesa, DocumentoOficial, LogAuditoria, OcorrenciaDefesa, OuvinteDefesa"],
    "ControladorPublicacao": ["+ GET /tccs/{idTcc}/publicacao", "+ POST /tccs/{idTcc}/publicacao",
                              "+ GET /tccs/{idTcc}/publicacoes/historico",
                              "usa: HistoricoPublicacao, PublicacaoArtigo, TCC"],
    "ControladorTccs (pendente)": ["+ POST /tccs/{idTcc}/orientacoes/substituicao",
                                   "usa: Defesa, NotificacaoEmail, Orientacao, TCC, Usuario"],
    "ControladorTurmas (pendente)": ["+ POST /turmas/{idTurma}/encerramento",
                                     "(turma.encerrada_em existe, mas nenhuma rota o preenche)"],
}


def pagina_planejado() -> tuple[list[Caixa], list[Ligacao], dict]:
    no_codigo = {c.__table__.name: c.__name__ for c in classes_mapeadas()}
    caixas, ligs, refs = [], [], set()

    def rotulo(c) -> str:
        chaves = [k for k, v in (("PK", c.pk), ("FK " + (c.fk or ""), bool(c.fk)), ("unique", c.uk)) if v]
        return (f"+ {c.nome} : {c.tipo}{' [0..1]' if c.nulo else ''}"
                f"{' {' + ', '.join(chaves) + '}' if chaves else ''}"
                f"{' {in ' + '|'.join(c.valores) + '}' if c.valores else ''}")

    for t in ml.T:
        if t.nome in no_codigo:
            novas = [c for c in t.cols if c.novo]
            if not novas:
                continue
            nome, cols, cid = f"{no_codigo[t.nome]} (colunas novas)", novas, f"novo-{t.nome}"
        else:
            nome, cols, cid = pascal(t.nome), t.cols, t.nome
        caixas.append(Caixa(cid, nome, f"«planejada · {t.modulo}»", [[rotulo(c) for c in cols]], "entidade", True))
        for c in cols:
            if not c.fk:
                continue
            alvo = c.fk
            if alvo in no_codigo:
                refs.add(alvo)
                alvo = f"ref-{alvo}"
            ligs.append(Ligacao(cid, alvo, rot_para="0..1" if c.nulo else "1", rot_meio=papel_util(c.nome, pascal(c.fk)),
                                rot_de="0..1" if c.uk else "*", nav_para=True, id=f"{cid}.{c.nome}"))
    for t in sorted(refs):
        caixas.append(Caixa(f"ref-{t}", no_codigo[t], "", [], "ref"))
    for nome, linhas in PLANEJADO_CONTROLE.items():
        caixas.append(Caixa(f"ctl-{nome}", nome, "«controle»", [linhas], "controle", True))
    return caixas, ligs, {"tabelas": sum(1 for c in caixas if c.id in ml.POR_NOME)}


# ====================================================================== draw.io
def grafo(gid: str, caixas: list[Caixa], ligs: list[Ligacao], direcao: str) -> dict:
    # Cada ponta de linha tem a sua porta e a caixa cresce até as portas caberem a 20 px:
    # sem isso as ~20 FKs que chegam em Usuario se amontoam numa caixa de 40 px.
    nos = {c.id: dict(id=c.id, width=c.largura, height=c.altura, ports=[], layoutOptions={
        "elk.portConstraints": "FREE", "elk.nodeSize.constraints": "PORTS MINIMUM_SIZE",
        "elk.nodeSize.minimum": f"({c.largura}, {c.altura})", "elk.spacing.portPort": "20"}) for c in caixas}
    arestas = []
    for k, lg in enumerate(ligs):
        assert lg.de in nos and lg.para in nos, f"{gid}: ligação {lg.de} -> {lg.para} sem caixa"
        lg.id = lg.id or f"e{k}"
        labels = []
        for txt, onde in ((lg.rot_de, "TAIL"), (lg.rot_meio, "CENTER"), (lg.rot_para, "HEAD")):
            if txt:
                labels.append(dict(id=f"{lg.id}|{onde}", text=txt, width=len(txt) * 5.4 + 8, height=13,
                                   layoutOptions={"elk.edgeLabels.placement": onde}))
        de, para = f"{lg.de}#{lg.id}#de", f"{lg.para}#{lg.id}#para"
        nos[lg.de]["ports"].append(dict(id=de, width=1, height=1))
        nos[lg.para]["ports"].append(dict(id=para, width=1, height=1))
        arestas.append(dict(id=lg.id, sources=[de], targets=[para], labels=labels))
    nos = list(nos.values())
    opcoes = {"elk.direction": direcao, "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES",
              "elk.layered.spacing.nodeNodeBetweenLayers": "110", "elk.spacing.nodeNode": "40",
              # linhas paralelas a 18 px: com os 9 px do DER, um feixe parece uma linha só
              "elk.spacing.edgeEdge": "18", "elk.layered.spacing.edgeEdgeBetweenLayers": "16",
              "elk.layered.wrapping.strategy": "OFF", "elk.aspectRatio": "1.6"}
    return dict(id=gid, children=nos, edges=arestas, layoutOptions=opcoes)


def _cobre(r1, r2, folga: float = 0) -> bool:
    (x1, y1, w1, h1), (x2, y2, w2, h2) = r1, r2
    return min(x1 + w1, x2 + w2) - max(x1, x2) > folga and min(y1 + h1, y2 + h2) - max(y1, y2) > folga


def posicionar_rotulos(g: dict) -> None:
    """Põe cada rótulo de ponta (papel e multiplicidade) em lugar livre.

    O ELK deixa os rótulos de ponta colados na caixa e não separa os das várias linhas que
    chegam na mesma caixa. Aqui cada um anda pelo último trecho da sua linha, dos dois lados
    dela, até a primeira posição que não cobre outro rótulo, uma caixa ou outra linha.
    """
    caixas = [(n["x"], n["y"], n["width"], n["height"]) for n in g["children"]]
    trechos = []
    for e in g["edges"]:
        pts = pg.pontos_da_aresta(e)
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            trechos.append((e["id"], (min(ax, bx) - 1, min(ay, by) - 1, abs(bx - ax) + 2, abs(by - ay) + 2)))
    ocupados = [(lab["x"], lab["y"], lab["width"], lab["height"]) for e in g["edges"] for lab in e.get("labels", [])
                if lab["id"].endswith("|CENTER")]
    for e in g["edges"]:
        pts = pg.pontos_da_aresta(e)
        for lab in e.get("labels", []):
            onde = lab["id"].rsplit("|", 1)[1]
            if onde == "CENTER" and encostado(lab, pts):
                continue  # o do meio fica onde o ELK pôs, a menos que tenha ficado longe da linha (laço)
            caminho = pts[::-1] if onde == "HEAD" else pts  # da ponta do rótulo para o meio da linha
            w, h = lab["width"], lab["height"]
            melhor, andado = None, 0.0
            for (px, py), (qx, qy) in zip(caminho, caminho[1:]):
                comprimento = abs(qx - px) + abs(qy - py)
                vertical = abs(qx - px) < 0.5
                sx, sy = (qx > px) - (qx < px), (qy > py) - (qy < py)
                for d in range(4, int(max(comprimento - (h if vertical else w), 4)) + 1, 6):
                    for lado in (1, -1):  # sempre encostado na própria linha, de um lado ou do outro
                        if vertical:
                            cx, cy = px + lado * (w / 2 + 3), py + sy * (d + h / 2)
                        else:
                            cx, cy = px + sx * (d + w / 2), py + lado * (h / 2 + 2)
                        r = (cx - w / 2, cy - h / 2, w, h)
                        nota = (100 * sum(_cobre(r, o) for o in ocupados)
                                + 100 * sum(_cobre(r, c, 1) for c in caixas)
                                + 10 * sum(_cobre(r, t) for eid, t in trechos if eid != e["id"])
                                + (andado + d) / 100)
                        if melhor is None or nota < melhor[0]:
                            melhor = (nota, r)
                    if melhor[0] < 10:
                        break
                if melhor[0] < 10:
                    break
                andado += comprimento
            lab["x"], lab["y"] = melhor[1][0], melhor[1][1]
            ocupados.append(melhor[1])


def sobreposicoes(g: dict) -> list[str]:
    """Trechos de duas linhas diferentes correndo um sobre o outro e rótulos que se cobrem."""
    trechos = []
    for e in g["edges"]:
        pts = pg.pontos_da_aresta(e)
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            if abs(ax - bx) < 0.5:
                trechos.append((e["id"], "v", ax, min(ay, by), max(ay, by)))
            elif abs(ay - by) < 0.5:
                trechos.append((e["id"], "h", ay, min(ax, bx), max(ax, bx)))
    probs = set()
    for i, (e1, o1, c1, a1, b1) in enumerate(trechos):
        for e2, o2, c2, a2, b2 in trechos[i + 1:]:
            if e1 != e2 and o1 == o2 and abs(c1 - c2) < 3 and min(b1, b2) - max(a1, a2) > 4:
                probs.add(f"linhas {e1} e {e2} sobrepostas")
    rotulos = [(e["id"], lab["text"], lab["x"], lab["y"], lab["width"], lab["height"])
               for e in g["edges"] for lab in e.get("labels", [])]
    for i, (e1, t1, *r1) in enumerate(rotulos):
        for e2, t2, *r2 in rotulos[i + 1:]:
            if _cobre(r1, r2, 2):
                probs.add(f"rótulos '{t1}' ({e1}) e '{t2}' ({e2}) se cobrem")
        for n in g["children"]:
            if _cobre(r1, (n["x"], n["y"], n["width"], n["height"]), 2):
                probs.add(f"rótulo '{t1}' ({e1}) em cima da caixa {n['id']}")
    # cada rótulo encostado na sua linha: senão não se sabe de qual linha ele é
    for e in g["edges"]:
        for lab in e.get("labels", []):
            if not encostado(lab, pg.pontos_da_aresta(e)):
                probs.add(f"rótulo '{lab['text']}' ({e['id']}) longe da sua linha")
    return sorted(probs)


def encostado(lab: dict, pts) -> bool:
    r = (lab["x"], lab["y"], lab["width"], lab["height"])
    return any(_cobre(r, (min(ax, bx) - 6, min(ay, by) - 6, abs(bx - ax) + 12, abs(by - ay) + 12))
               for (ax, ay), (bx, by) in zip(pts, pts[1:]))


ESTILO_LIGACAO = {
    "assoc": "endFill=0;startFill=0;",
    "comp": "endFill=1;startFill=0;",
    "dep": "dashed=1;endArrow=open;startArrow=none;endFill=0;",
    "gen": "endArrow=block;endFill=0;startArrow=none;endSize=12;",
}


def pontas(lg: Ligacao) -> str:
    if lg.tipo in ("dep", "gen"):
        return ""
    fim = "diamondThin;endSize=14" if lg.tipo == "comp" else ("open;endSize=10" if lg.nav_para else "none")
    ini = "open;startSize=10" if lg.nav_de else "none"
    return f"endArrow={fim};startArrow={ini};"


def alturas_no_desenho(c: Caixa, n: dict) -> list[int]:
    """Altura de cada compartimento; o que o ELK aumentou na caixa (por causa das portas) vai para o último."""
    alts = c.alturas()
    if alts:
        alts[-1] += int(n["height"] - c.altura)
    return alts


def caixa_xml(p: int, c: Caixa, n: dict) -> list[str]:
    fill, stroke = COR[c.tipo]
    tr = "dashed=1;dashPattern=6 4;" if c.tracejado else ""
    cab = (f"<i>{html.escape(c.estereotipo)}</i><br>" if c.estereotipo else "") + f"<b>{html.escape(c.nome)}</b>"
    cid = f"p{p}-{c.id}"
    x, y, w, h = n["x"], n["y"], n["width"], n["height"]
    cells = [
        f'<mxCell id={quoteattr(cid)} value={quoteattr(cab)} style="swimlane;html=1;whiteSpace=wrap;fontStyle=0;'
        f'align=center;verticalAlign=top;childLayout=stackLayout;horizontal=1;startSize={c.cab};horizontalStack=0;'
        f'resizeParent=1;resizeParentMax=0;resizeLast=0;collapsible=0;marginBottom=0;fillColor={fill};'
        f'strokeColor={stroke};fontSize=12;{tr}" vertex="1" parent="1">'
        f'<mxGeometry x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" as="geometry"/></mxCell>']
    topo = c.cab
    for i, (sec, alt) in enumerate(zip(c.secoes, alturas_no_desenho(c, n))):
        borda = "strokeColor=" + stroke + ";" if i else "strokeColor=none;"
        cells.append(
            f'<mxCell id={quoteattr(f"{cid}-s{i}")} value={quoteattr(chr(10).join(sec))} style="text;{borda}'
            f'fillColor=#ffffff;align=left;verticalAlign=top;spacingLeft=6;spacingTop=2;overflow=hidden;'
            f'rotatable=0;whiteSpace=nowrap;html=0;{FONTE}" vertex="1" parent={quoteattr(cid)}>'
            f'<mxGeometry y="{topo}" width="{w:.0f}" height="{alt}" as="geometry"/></mxCell>')
        topo += alt
    return cells


def pagina_xml(p: int, nome: str, titulo: str, caixas: list[Caixa], ligs: list[Ligacao], g: dict,
               legenda: str) -> str:
    por_id = {n["id"]: n for n in g["children"]}
    lig_por_id = {lg.id: lg for lg in ligs}
    cells = [f'<mxCell id="p{p}-t" value={quoteattr(titulo)} style="text;html=1;fontSize=22;fontStyle=1;'
             f'align=left;" vertex="1" parent="1"><mxGeometry x="40" y="14" width="1600" height="36" '
             f'as="geometry"/></mxCell>']
    for c in caixas:
        cells += caixa_xml(p, c, por_id[c.id])
    for e in g["edges"]:
        lg = lig_por_id[e["id"]]
        pts = pg.pontos_da_aresta(e)
        a, b = por_id[lg.de], por_id[lg.para]

        def rel(no, pt):
            return (min(1, max(0, (pt[0] - no["x"]) / no["width"])), min(1, max(0, (pt[1] - no["y"]) / no["height"])))

        ex, ey = rel(a, pts[0])
        nx, ny = rel(b, pts[-1])
        meio = "".join(f'<mxPoint x="{x:.0f}" y="{y:.0f}"/>' for x, y in pts[1:-1])
        eid = f"p{p}-{lg.id}"
        cor = "#888888" if lg.tipo == "dep" else "#333333"
        cells.append(
            f'<mxCell id={quoteattr(eid)} value="" style="edgeStyle=none;rounded=0;html=1;{ESTILO_LIGACAO[lg.tipo]}'
            f'{pontas(lg)}strokeColor={cor};exitX={ex:.4f};exitY={ey:.4f};exitDx=0;exitDy=0;exitPerimeter=0;'
            f'entryX={nx:.4f};entryY={ny:.4f};entryDx=0;entryDy=0;entryPerimeter=0;" edge="1" parent="1" '
            f'source={quoteattr(f"p{p}-{lg.de}")} target={quoteattr(f"p{p}-{lg.para}")}>'
            f'<mxGeometry relative="1" as="geometry"><mxPoint x="{pts[0][0]:.0f}" y="{pts[0][1]:.0f}" '
            f'as="sourcePoint"/><mxPoint x="{pts[-1][0]:.0f}" y="{pts[-1][1]:.0f}" as="targetPoint"/>'
            f'<Array as="points">{meio}</Array></mxGeometry></mxCell>')
        for j, lab in enumerate(e.get("labels", [])):
            fx, dx, dy = pg.posicao_rotulo(pts, lab["x"] + lab["width"] / 2, lab["y"] + lab["height"] / 2)
            cells.append(
                f'<mxCell id={quoteattr(f"{eid}-l{j}")} value={quoteattr(lab["text"])} style="edgeLabel;html=0;'
                f'align=center;verticalAlign=middle;resizable=0;points=[];fontSize=9;fontColor=#333333;'
                f'labelBackgroundColor=#ffffff;" vertex="1" connectable="0" parent={quoteattr(eid)}>'
                f'<mxGeometry x="{fx:.4f}" relative="1" as="geometry"><mxPoint x="{dx:.0f}" y="{dy:.0f}" '
                f'as="offset"/></mxGeometry></mxCell>')
    cells.append(f'<mxCell id="p{p}-leg" value={quoteattr(legenda)} style="text;html=1;align=left;verticalAlign=top;'
                 f'spacing=12;fillColor=#fafafa;strokeColor=#999999;rounded=1;arcSize=2;fontSize=11;whiteSpace=wrap;" '
                 f'vertex="1" parent="1"><mxGeometry x="{g["width"] + 20:.0f}" y="70" width="{LEG_W}" '
                 f'height="{altura_legenda(legenda)}" as="geometry"/></mxCell>')
    altura = max(g["height"], 70 + altura_legenda(legenda)) + 40
    return (f'<diagram name={quoteattr(nome)} id="classes-{p}"><mxGraphModel dx="1600" dy="1000" grid="1" '
            f'gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
            f'pageWidth="{g["width"] + LEG_W + 60:.0f}" pageHeight="{altura:.0f}" math="0" shadow="0"><root>'
            f'<mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(cells) + "</root></mxGraphModel></diagram>")


def svg(caixas: list[Caixa], ligs: list[Ligacao], g: dict, legenda: str) -> str:
    """Prévia para conferir o desenho (o entregável é o .drawio)."""
    por_id = {n["id"]: n for n in g["children"]}
    lig_por_id = {lg.id: lg for lg in ligs}
    alt_leg = altura_legenda(legenda)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{g["width"] + LEG_W + 40:.0f}" '
           f'height="{max(g["height"], 70 + alt_leg) + 20:.0f}" font-family="Arial">'
           f'<rect width="100%" height="100%" fill="#fff"/>'
           f'<rect x="{g["width"] + 20:.0f}" y="70" width="{LEG_W}" height="{alt_leg}" rx="4" fill="#fafafa" '
           f'stroke="#999"/>']
    for i, ln in enumerate(linhas_legenda(legenda)):
        out.append(f'<text x="{g["width"] + 32:.0f}" y="{90 + i * LEG_LH:.0f}" font-size="11">{ln}</text>')
    for e in g["edges"]:
        lg = lig_por_id[e["id"]]
        pts = pg.pontos_da_aresta(e)
        traco = ' stroke-dasharray="5 4"' if lg.tipo == "dep" else ""
        out.append(f'<polyline points="{" ".join(f"{x:.0f},{y:.0f}" for x, y in pts)}" fill="none" '
                   f'stroke="{"#888" if lg.tipo == "dep" else "#333"}"{traco}/>')
        (x, y), (x2, y2) = pts[-1], pts[-2]
        if lg.tipo == "comp":
            out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="5" fill="#333"/>')
        elif lg.tipo == "gen":
            out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="6" fill="#fff" stroke="#333"/>')
        elif lg.tipo == "dep" or lg.nav_para:
            out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="3" fill="#333"/>')
        for lab in e.get("labels", []):
            out.append(f'<text x="{lab["x"] + lab["width"] / 2:.0f}" y="{lab["y"] + 10:.0f}" font-size="9" '
                       f'text-anchor="middle" stroke="#fff" stroke-width="3" paint-order="stroke">'
                       f'{html.escape(lab["text"])}</text>')
    for c in caixas:
        n = por_id[c.id]
        fill, stroke = COR[c.tipo]
        tr = ' stroke-dasharray="6 4"' if c.tracejado else ""
        out.append(f'<rect x="{n["x"]:.0f}" y="{n["y"]:.0f}" width="{n["width"]:.0f}" height="{n["height"]:.0f}" '
                   f'fill="#fff" stroke="{stroke}"{tr}/><rect x="{n["x"]:.0f}" y="{n["y"]:.0f}" '
                   f'width="{n["width"]:.0f}" height="{c.cab}" fill="{fill}" stroke="{stroke}"{tr}/>')
        cab = [s for s in (c.estereotipo, c.nome) if s]
        for i, s in enumerate(cab):
            peso = ' font-weight="bold"' if s == c.nome else ""
            out.append(f'<text x="{n["x"] + n["width"] / 2:.0f}" y="{n["y"] + 16 + i * 14:.0f}" font-size="11"'
                       f'{peso} text-anchor="middle">{html.escape(s)}</text>')
        topo = n["y"] + c.cab
        for sec, alt in zip(c.secoes, alturas_no_desenho(c, n)):
            out.append(f'<line x1="{n["x"]:.0f}" y1="{topo:.0f}" x2="{n["x"] + n["width"]:.0f}" y2="{topo:.0f}" '
                       f'stroke="{stroke}"/>')
            for i, ln in enumerate(sec):
                out.append(f'<text x="{n["x"] + 6:.0f}" y="{topo + 14 + i * LH:.0f}" font-size="10" '
                           f'font-family="Courier New,monospace" xml:space="preserve">{html.escape(ln)}</text>')
            topo += alt
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------- legenda
LEG_W, LEG_LH, LEG_CHARS = 470, 15, 74  # largura, altura de linha e caracteres por linha (Arial 11)


def cor(tipo: str, texto: str) -> str:
    fill, stroke = COR[tipo]
    return f'<font color="{stroke}">■</font> {texto}'


def legenda(*blocos: tuple[str, list[str]]) -> str:
    return "<br><br>".join(f"<b>{titulo}</b><br>" + "<br>".join(linhas) for titulo, linhas in blocos)


def linhas_legenda(texto: str) -> list[str]:
    """As linhas como aparecem na caixa: quebra nos <br> e nas linhas longas (sem as tags)."""
    saida = []
    for ln in texto.split("<br>"):
        limpo = html.unescape(re.sub(r"<[^>]+>", "", ln))
        saida += [html.escape(x) for x in (quebrar(limpo, LEG_CHARS) if limpo else [""])]
    return saida


def altura_legenda(texto: str) -> int:
    return len(linhas_legenda(texto)) * LEG_LH + 30


NOTACAO = ("Notação UML", [
    "Linha contínua: associação; seta aberta no lado navegável",
    "Losango cheio: composição (a parte não existe sem o todo)",
    "Triângulo vazio: herança",
    "Linha tracejada com seta: dependência («usa»)",
    "Na ponta: multiplicidade (1 = um, 0..1 = zero ou um, * = vários)",
    "No meio da linha: papel, quando não repete o nome da classe (ex.: professor)",
])


def gerar(previas: str | None = None) -> tuple[list[str], list[str]]:
    """As cinco páginas (XML do draw.io) e os problemas de desenho encontrados."""
    rotas = rotas_da_api()
    dom = pagina_dominio()
    ctl = pagina_controle(rotas)
    fr_caixas, fr_ligs, fr_info, erros = pagina_fronteira(rotas)
    dto = pagina_dtos()
    pla = pagina_planejado()
    sem_tela = sorted(f"{r['metodo']} {r['caminho']}" for r in rotas
                      if (r["metodo"], r["caminho"]) not in fr_info["chamadas"])
    specs = [
        ("1 · Domínio", f"SIGA UEA · Diagrama de classes · domínio ({dom[2]['classes']} classes)", *dom[:2], "DOWN",
         legenda(
             ("Cores", [cor("entidade", "Entidade persistida (classe SQLAlchemy)"),
                        cor("enum", "Enumeração: valores aceitos por uma coluna")]),
             ("Onde está no código", [
                 "Cada classe está em backend/app/models.py com o mesmo nome (Tcc = class Tcc)",
                 "Tabela = nome da classe em snake_case (UsuarioPerfil → usuario_perfil)",
                 "Enumeração = constante de mesmo nome no models.py (SITUACOES_TCC), conferida "
                 "por CHECK no banco, exceto as marcadas {sem CHECK no banco}"]),
             ("Atributos", [
                 "Tipo = tipo da coluna no banco (String(150), Numeric(3,1)...)",
                 "[0..1] aceita nulo · = valor padrão · /situacao: calculado (@property), não é coluna",
                 "{PK} chave primária · {FK tcc.id} chave estrangeira para tcc.id · {unique} valor único",
                 "{in SITUACOES_TCC}: só aceita os valores dessa enumeração",
                 "Compartimento de baixo: restrições da tabela (CHECK, UNIQUE composto, índice e trigger)"]),
             NOTACAO)),
        ("2 · Controle e serviços", f"SIGA UEA · Diagrama de classes · controle e serviços ({ctl[2]['rotas']} rotas)",
         *ctl[:2], "RIGHT",
         legenda(
             ("Cores", [cor("controle", "«controle»: recebe a requisição HTTP"),
                        cor("servico", "«serviço»: regra de negócio e acesso ao banco"),
                        cor("util", "«utilitário»: sessão, senha, erros e conexão")]),
             ("Onde está no código", [
                 "ControladorTccs = backend/app/routes/tccs.py (o que vem depois de Controlador é o arquivo)",
                 "ServicoTccs = backend/app/services/tccs.py (idem depois de Servico)",
                 "Deps = backend/app/deps.py; o mesmo para Security, Erros e Database"]),
             ("Operações", [
                 "Leitura de uma linha do controle, ex.: POST /tccs → criar_rascunho(dados: TccSalvar)",
                 "    : TccOut 201 [aluno] = método e caminho, função que atende, o que recebe,",
                 "    o que devolve, status HTTP e perfil exigido",
                 f"Todos os caminhos ficam sob {PREFIXO_API}, menos /health",
                 "status? = parâmetro opcional da URL · [público] não exige login · [autenticado] qualquer perfil",
                 "Serviço: + função pública · - função interna (nome começa com _, ex.: _vinculo)",
                 "Rodapé: entidades, DTOs e módulos que o arquivo importa"]),
             ("Ligações", ["Tracejado «usa»: o arquivo importa o serviço"]))),
        ("3 · Fronteira (telas)", f"SIGA UEA · Diagrama de classes · fronteira ({fr_info['telas']} telas e componentes)",
         fr_caixas, fr_ligs, "RIGHT",
         legenda(
             ("Cores", [cor("fronteira", "«fronteira»: tela · «componente»: parte reaproveitada"),
                        cor("controle", "«controle»: módulo de rotas da API (página 2)")]),
             ("Onde está no código", [
                 "Tela pelo endereço: /tccs/cadastro = app/(sistema)/tccs/cadastro/page.tsx",
                 "Componente pelo arquivo: formulario-usuario = formulario-usuario.tsx",
                 "ControladorTccs = backend/app/routes/tccs.py"]),
             ("Conteúdo", [
                 "Cada linha é uma chamada, ex.: GET /tccs → listar() = a tela faz GET /api/v1/tccs",
                 "    e quem atende na API é a função listar()",
                 "Tracejado: a tela usa o componente ou chama o controle",
                 "lib/sessao e lib/tipos são usados por quase todas as telas: a caixa diz quantas"]),
             ("Rotas que nenhuma tela chama", [html.escape(s) for s in sem_tela]))),
        ("4 · DTOs (schemas)", f"SIGA UEA · Diagrama de classes · DTOs ({dto[2]['dtos']} classes Pydantic)",
         *dto[:2], "RIGHT",
         legenda(
             ("Cores", [cor("dto", "«DTO»: formato de entrada ou saída da API"),
                        cor("enum", "Tipos e constantes usados nos campos")]),
             ("Onde está no código", [
                 "Cada DTO é a classe de mesmo nome em backend/app/schemas/ (TccOut está em tcc.py;",
                 "    LoginEntrada em auth.py; UsuarioOut em usuario.py)",
                 "TiposTcc = tipos e constantes do topo de schemas/tcc.py (idem TiposAuth, TiposUsuario)"]),
             ("Conteúdo", [
                 "Campos exatamente como declarados (tipo, restrições e padrão)",
                 "«field_validator»: validação extra do campo",
                 "Losango: um DTO dentro de outro (TccOut.aluno é um PessoaOut)",
                 "    nome do campo no meio da linha; na ponta, list = * e | None = 0..1"]),
             NOTACAO)),
        ("5 · Planejado (fora do código)", "SIGA UEA · Diagrama de classes · planejado (ainda NÃO está no código)",
         *pla[:2], "RIGHT",
         legenda(
             ("Cores", [cor("entidade", "«planejada · MOD04»: tabela ou colunas ainda sem migração, e o módulo"),
                        cor("controle", "«controle»: operações ainda sem rota"),
                        cor("ref", "Branco: classe que já existe (detalhe na página 1)")]),
             ("De onde vem", [
                 "Tabelas e colunas: modelo lógico aprovado (docs/modelagem/modelo_logico.py)",
                 "Operações: diagramas de sequência FL01 a FL10",
                 "Borda tracejada: planejado; sai desta página quando for implementado"]),
             NOTACAO)),
    ]
    grafos = [grafo(f"g{i}", s[2], s[3], s[4]) for i, s in enumerate(specs)]
    saidas = pg.layout(grafos)
    paginas, problemas = [], list(erros)
    for i, (spec, g) in enumerate(zip(specs, saidas)):
        nome, titulo, caixas, ligs, _, leg = spec
        posicionar_rotulos(g)
        paginas.append(pagina_xml(i, nome, titulo, caixas, ligs, g, leg))
        probs = pg.conferir(g) + sobreposicoes(g)
        problemas += [f"{nome}: {p}" for p in probs]
        print(f"{nome}: {len(caixas)} caixas, {len(ligs)} ligações, {len(probs)} problemas de desenho")
        if previas:
            Path(previas, f"classes-{i}.svg").write_text(svg(caixas, ligs, g, leg), encoding="utf8")
    print(f"rotas sem tela: {len(sem_tela)}")
    for p in problemas:
        print("   ", p)
    return paginas, problemas


def main() -> None:
    paginas, problemas = gerar(sys.argv[1] if len(sys.argv) > 1 else None)
    (AQUI / "diagrama-classes-siga-uea.drawio").write_text(
        '<mxfile host="app.diagrams.net">' + "".join(paginas) + "</mxfile>", encoding="utf8")
    raise SystemExit(1 if problemas else 0)


if __name__ == "__main__":
    main()
