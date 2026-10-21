"""Contrato da API do SIGA UEA em formato legível (HT03 · SCRUM-108).

Junta três fontes, todas do repositório:
  docs/openapi.json                  rotas, corpos e respostas (gerado do próprio código da API)
  docs/arquitetura/status-observados.json   códigos que cada rota devolveu na suíte de testes
  docs/modelo-de-dados.md            quem pode usar cada rota e o requisito de origem

e gera docs/arquitetura/contrato-api-siga-uea.html (o PDF sai do HTML pelo Chrome, ver html_para_pdf.mjs).

    cd backend
    python -c "import json,sys; sys.path.insert(0,'.'); from app.main import app; \
json.dump(app.openapi(), open('../docs/openapi.json','w',encoding='utf8'), ensure_ascii=False, indent=2)"
    $env:PYTHONPATH="../docs/arquitetura"; pytest -q -p coleta_status
    cd ..; python docs/arquitetura/contrato_api.py
    node docs/arquitetura/html_para_pdf.mjs docs/arquitetura/contrato-api-siga-uea.html
"""

from __future__ import annotations

import html
import json
import re
from datetime import date
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
API = json.loads((RAIZ / "docs" / "openapi.json").read_text(encoding="utf8"))
OBS = json.loads((AQUI / "status-observados.json").read_text(encoding="utf8"))
TABELAS = (RAIZ / "docs" / "modelo-de-dados.md").read_text(encoding="utf8")
SAIDA = AQUI / "contrato-api-siga-uea.html"

SIGNIFICADO = {
    200: "Sucesso.",
    201: "Criado.",
    202: "Pedido aceito (resposta neutra, sem revelar se o e-mail existe).",
    204: "Sucesso, sem conteúdo.",
    400: "Validação: algum campo está ausente ou inválido. O corpo traz \"campos\" com a mensagem de cada um.",
    401: "Sem sessão válida, sessão expirada ou credenciais inválidas (mensagem genérica).",
    403: "O perfil não permite a ação, ou uma regra bloqueia (ex.: aluno sem matrícula, RN05).",
    404: "Não encontrado, ou o usuário não tem vínculo com o registro (RN07: não revela que existe).",
    405: "Método não permitido nesta rota (ex.: não existe exclusão de conta).",
    409: "Conflito: duplicidade ou situação que não permite a operação.",
    413: "Arquivo acima do limite.",
    415: "Formato de arquivo não aceito (conferido pelo conteúdo).",
    422: "Regra de negócio não atendida: senha fora do padrão, elegibilidade ou pendências do cadastro.",
    423: "Conta bloqueada por 15 minutos após 3 tentativas inválidas.",
}
GRUPOS = [  # ordem e título das seções, pela tag do OpenAPI
    ("autenticação", "Acesso e sessão (TEL01 · RBN01.04 a RBN01.07)"),
    ("meu perfil", "Meu perfil (RBN01.09, RBN01.10)"),
    ("usuários", "Usuários e perfis (TEL02 · RBN01.01, RBN01.03, RBN01.05, RBN01.08)"),
    ("áreas de interesse", "Áreas de interesse (RBN01.02)"),
    ("catálogo", "Catálogo (cursos, áreas e perfis)"),
    ("turmas", "Períodos e turmas (RBN08.01 a RBN08.03, RAN08)"),
    ("cadastro de TCC", "Cadastro de TCC e orientação (TEL04 a TEL08 · RBN03, RBN06)"),
    ("health", "Saúde do serviço"),
]


# Finalidade de cada operação, em português (o "summary" do OpenAPI vem do nome da função).
FINALIDADE = {
    "GET /health": "Informa se a API está no ar (usado pela hospedagem e pelo monitoramento).",
    "POST /auth/login": "Entra no sistema com e-mail e senha e cria a sessão.",
    "POST /auth/logout": "Sai do sistema e encerra a sessão.",
    "GET /auth/me": "Devolve o usuário da sessão atual, com os perfis.",
    "POST /auth/validar-token": "Confere se um link de ativação ou de recuperação ainda vale, antes de mostrar o formulário.",
    "POST /auth/ativar": "Ativa a conta pelo link do e-mail, definindo a primeira senha.",
    "POST /auth/esqueci-senha": "Pede o link de recuperação de senha por e-mail.",
    "POST /auth/redefinir-senha": "Define uma nova senha pelo link de recuperação.",
    "GET /usuarios/me": "Mostra os dados do próprio perfil.",
    "PUT /usuarios/me": "Altera os dados do próprio perfil que o usuário pode editar.",
    "POST /usuarios/me/senha": "Troca a própria senha, informando a atual.",
    "PUT /usuarios/me/foto": "Envia ou troca a própria foto.",
    "DELETE /usuarios/me/foto": "Remove a própria foto.",
    "GET /usuarios/{}/foto": "Mostra a foto de um usuário.",
    "PUT /usuarios/{}/foto": "Envia ou troca a foto de um docente (coordenação).",
    "DELETE /usuarios/{}/foto": "Remove a foto de um usuário (coordenação).",
    "POST /docentes": "Cadastra um docente e envia o link de ativação.",
    "GET /docentes": "Lista os docentes, com filtros por curso, cargo e busca.",
    "POST /alunos": "Cadastra um aluno e envia o link de ativação.",
    "GET /alunos": "Lista os alunos, com filtros por curso e busca.",
    "GET /alunos/{}": "Mostra o cadastro de um aluno.",
    "GET /docentes/{}": "Mostra o cadastro de um docente.",
    "PUT /usuarios/{}": "Altera o cadastro de um usuário.",
    "PATCH /usuarios/{}/inativar": "Inativa um usuário, sem apagar o histórico.",
    "PATCH /usuarios/{}/reativar": "Reativa um usuário inativado.",
    "POST /usuarios/{}/reenviar-ativacao": "Gera e envia um novo link de ativação.",
    "GET /areas/gestao": "Lista as áreas de interesse com quantos docentes usam cada uma.",
    "GET /areas": "Lista as áreas de interesse.",
    "POST /areas": "Cria uma área de interesse.",
    "PUT /areas/{}": "Renomeia uma área de interesse.",
    "DELETE /areas/{}": "Exclui uma área de interesse e desvincula os docentes.",
    "GET /perfis": "Lista os cinco perfis de acesso.",
    "GET /cursos": "Lista os cursos contemplados.",
    "GET /periodos": "Lista os períodos letivos.",
    "POST /periodos": "Cria um período letivo.",
    "GET /turmas": "Lista as turmas de TCC, com filtro por período.",
    "POST /turmas": "Cria uma turma de TCC1 ou TCC2 com o professor responsável.",
    "GET /turmas/minhas": "Lista as turmas do usuário: as que o docente conduz e a do aluno.",
    "GET /turmas/{}": "Mostra uma turma com os alunos e o TCC de cada um.",
    "POST /turmas/{}/alunos": "Inclui um aluno na turma.",
    "PATCH /turmas/{}/alunos/{}": "Altera a situação da matrícula do aluno na turma.",
    "GET /tccs/formulario": "Abre o formulário de cadastro: turma, orientadores elegíveis, áreas e rascunho existente.",
    "GET /tccs": "Lista os TCCs que o usuário pode ver.",
    "POST /tccs": "Cria o rascunho do cadastro de TCC.",
    "GET /tccs/{}": "Mostra o cadastro de um TCC, com orientação e histórico.",
    "PUT /tccs/{}": "Atualiza o rascunho ou o cadastro devolvido.",
    "POST /tccs/{}/submissao": "Envia o cadastro para análise e gera o protocolo.",
    "POST /tccs/{}/orientacoes": "Indica um novo orientador ou o coorientador.",
    "GET /orientacoes": "Lista os pedidos de orientação recebidos pelo docente.",
    "GET /orientacoes/{}": "Mostra um pedido de orientação.",
    "POST /orientacoes/{}/resposta": "Aceita ou recusa um pedido de orientação.",
}

def chave(metodo: str, caminho: str) -> str:
    return f"{metodo.upper()} {re.sub(r'\{[^}]+\}', '{}', caminho.removeprefix('/api/v1'))}"


def permissoes() -> dict[str, tuple[str, str]]:
    """Linhas das tabelas "Contrato da API" do modelo-de-dados.md: rota -> (quem pode, requisito)."""
    out = {}
    for linha in TABELAS.splitlines():
        if not linha.startswith("| `"):
            continue
        partes = [p.strip() for p in linha.strip().strip("|").split("|")]
        if len(partes) < 3:
            continue
        for m, c in re.findall(r"`(GET|POST|PUT|PATCH|DELETE) ([^`]+)`", partes[0]):
            out[chave(m, c)] = (partes[1].replace("`", ""), partes[2].replace("`", ""))
    out.setdefault("GET /health", ("público", "HT06 (verificação do Render)"))
    # linhas que agrupam operações com perfis diferentes: separadas aqui, conferidas no código das rotas
    out.update({
        "POST /auth/login": ("qualquer pessoa", "RBN01.06"),
        "POST /auth/logout": ("qualquer pessoa (encerra a sessão, se houver)", "RBN01.06"),
        "GET /auth/me": ("logado", "RBN01.06"),
        "GET /periodos": ("logado", "RBN08.01"),
        "POST /periodos": ("coordenador", "RBN08.01"),
    })
    return out


def resolver(ref_ou_schema: dict) -> dict:
    if "$ref" in ref_ou_schema:
        return API["components"]["schemas"][ref_ou_schema["$ref"].split("/")[-1]]
    return ref_ou_schema


def tipo(s: dict) -> str:
    if "$ref" in s:
        return s["$ref"].split("/")[-1]
    if "anyOf" in s:
        tipos = [tipo(x) for x in s["anyOf"] if x.get("type") != "null"]
        nulo = any(x.get("type") == "null" for x in s["anyOf"])
        return " ou ".join(tipos) + (" (ou nulo)" if nulo else "")
    if s.get("type") == "array":
        return f"lista de {tipo(s.get('items', {}))}"
    if "enum" in s:
        return " | ".join(map(str, s["enum"]))
    if "const" in s:
        return str(s["const"])
    t = s.get("type", "objeto")
    return {"string": "texto", "integer": "inteiro", "boolean": "booleano", "number": "número",
            "object": "objeto"}.get(t, t) + (f" ({s['format']})" if s.get("format") else "")


def restricoes(s: dict) -> str:
    alvo = s
    if "anyOf" in s:
        alvo = next((x for x in s["anyOf"] if x.get("type") != "null"), s)
    r = []
    for k, rot in (("minLength", "mín. {} caracteres"), ("maxLength", "máx. {} caracteres"),
                   ("minimum", "mín. {}"), ("maximum", "máx. {}"), ("pattern", "formato {}"),
                   ("minItems", "mín. {} itens"), ("maxItems", "máx. {} itens")):
        if k in alvo:
            r.append(rot.format(alvo[k]))
    if "default" in s:
        r.append(f"padrão {json.dumps(s['default'], ensure_ascii=False)}")
    return "; ".join(r)


def campos(schema_ref: dict) -> str:
    s = resolver(schema_ref)
    if s.get("type") == "array":
        return f"<p class='nota'>Lista de <b>{html.escape(tipo(s['items']))}</b>.</p>" + campos(s["items"])
    props = s.get("properties", {})
    if not props:
        return ""
    obrig = set(s.get("required", []))
    linhas = "".join(
        f"<tr><td><code>{html.escape(n)}</code></td><td>{html.escape(tipo(p))}</td>"
        f"<td>{'sim' if n in obrig else 'não'}</td><td>{html.escape(restricoes(p))}</td></tr>"
        for n, p in props.items())
    return ("<table class='campos'><tr><th>Campo</th><th>Tipo</th><th>Obrigatório</th><th>Restrições</th></tr>"
            f"{linhas}</table>")


def operacao(metodo: str, caminho: str, op: dict, perms: dict) -> str:
    k = chave(metodo, caminho)
    quem, req = perms.get(k, ("—", "—"))
    obs = {int(c): n for c, n in OBS.get(k.replace("{}", "{x}"), {}).items()}
    if not obs:  # o registrador usa o nome real do parâmetro: procurar por padrão
        alvo = re.compile("^" + re.escape(k).replace(r"\{\}", r"\{[^}]+\}") + "$")
        for rota, cods in OBS.items():
            if alvo.match(rota):
                obs = {int(c): n for c, n in cods.items()}
    corpo = op.get("requestBody", {}).get("content", {})
    if "application/json" in corpo:
        entrada = "<h4>Corpo (JSON)</h4>" + campos(corpo["application/json"]["schema"])
    elif "multipart/form-data" in corpo:
        entrada = "<h4>Corpo (multipart/form-data)</h4>" + campos(corpo["multipart/form-data"]["schema"])
    else:
        entrada = ""
    params = [p for p in op.get("parameters", []) if p["in"] in ("query", "path")]
    if params:
        entrada += ("<h4>Parâmetros</h4><table class='campos'><tr><th>Nome</th><th>Onde</th><th>Tipo</th>"
                    "<th>Obrigatório</th></tr>" + "".join(
                        f"<tr><td><code>{html.escape(p['name'])}</code></td><td>{'caminho' if p['in'] == 'path' else 'consulta'}"
                        f"</td><td>{html.escape(tipo(p.get('schema', {})))}</td><td>{'sim' if p.get('required') else 'não'}</td></tr>"
                        for p in params) + "</table>")
    sucesso = next((c for c in op.get("responses", {}) if c.startswith("2")), "200")
    resp = op["responses"].get(sucesso, {}).get("content", {}).get("application/json", {}).get("schema")
    saida = ""
    if resp and resolver(resp).get("properties") or (resp and resolver(resp).get("type") == "array"):
        nome = tipo(resp)
        saida = f"<h4>Resposta {sucesso}: {html.escape(nome)}</h4>" + campos(resp)
    codigos = sorted(set(obs) | {int(sucesso)})
    cods = "".join(
        f"<tr><td class='cod c{str(c)[0]}'>{c}</td><td>{html.escape(SIGNIFICADO.get(c, ''))}</td>"
        f"<td class='num'>{obs.get(c, 0)}</td></tr>" for c in codigos if c != 405)
    desc = html.escape((op.get("description") or "").strip()).replace("\n", "<br>")
    return (f"<section class='op'><h3><span class='met {metodo}'>{metodo.upper()}</span> <code>{html.escape(caminho)}</code></h3>"
            f"<p class='resumo'>{html.escape(FINALIDADE.get(k, op.get('summary', '')))}</p>"
            f"<p><b>Quem pode:</b> {html.escape(quem)} · <b>Requisito:</b> {html.escape(req)}</p>"
            + (f"<p class='nota'>{desc}</p>" if desc else "") + entrada + saida
            + "<h4>Respostas</h4><table class='cods'><tr><th>Código</th><th>Significado</th>"
            "<th>Vezes na suíte de testes</th></tr>" + cods + "</table></section>")


ESTILO = """
body{font-family:Arial,Helvetica,sans-serif;color:#1b2432;margin:32px auto;max-width:980px;line-height:1.45;font-size:13px}
h1{font-size:24px;margin:0 0 4px} h2{font-size:18px;margin:28px 0 8px;border-bottom:2px solid #1a73e8;padding-bottom:4px}
h3{font-size:14px;margin:0 0 4px} h4{font-size:12px;margin:12px 0 4px;color:#3a4556}
code{font-family:Consolas,monospace;font-size:12px} .sub{color:#5a6577;margin:0 0 18px}
table{border-collapse:collapse;width:100%;margin:4px 0 8px} th,td{border:1px solid #dde4ee;padding:4px 6px;text-align:left;vertical-align:top}
th{background:#f1f5fb;font-size:12px} .op{border:1px solid #dde4ee;border-radius:8px;padding:12px 14px;margin:12px 0;page-break-inside:avoid}
.met{display:inline-block;min-width:58px;text-align:center;border-radius:4px;color:#fff;font-size:11px;padding:2px 6px;margin-right:6px}
.get{background:#1a73e8}.post{background:#137333}.put{background:#92500a}.patch{background:#8430ce}.delete{background:#b3261e}
.resumo{margin:2px 0 6px;color:#3a4556} .nota{color:#5a6577;margin:4px 0} .num{text-align:right;width:120px}
.cod{font-weight:bold;width:60px}.c2{color:#137333}.c4{color:#b3261e}.c5{color:#b3261e}
.indice{columns:2;font-size:12px} .indice div{break-inside:avoid}
@media print{body{margin:0;max-width:none} .op{border-color:#c8d1dd}}
"""


def main():
    perms = permissoes()
    por_grupo: dict[str, list[str]] = {g: [] for g, _ in GRUPOS}
    indice: dict[str, list[str]] = {g: [] for g, _ in GRUPOS}
    total = 0
    for caminho, ops in API["paths"].items():
        for metodo, op in ops.items():
            g = (op.get("tags") or ["health"])[0]
            por_grupo.setdefault(g, []).append(operacao(metodo, caminho, op, perms))
            indice.setdefault(g, []).append(f"<span class='met {metodo}'>{metodo.upper()}</span> <code>{html.escape(caminho)}</code>")
            total += 1
    hoje = date.today().strftime("%d/%m/%Y")
    secoes = "".join(f"<h2>{html.escape(t)}</h2>" + "".join(por_grupo.get(g, [])) for g, t in GRUPOS if por_grupo.get(g))
    corpo = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Contrato da API · SIGA UEA</title>
<style>{ESTILO}</style></head><body>
<h1>SIGA UEA · Contrato da API</h1>
<p class="sub">HT03 (SCRUM-108) · versão {html.escape(API['info']['version'])} · gerado em {hoje} a partir do código
(docs/openapi.json) e da suíte de testes · {total} operações</p>

<h2>Como usar a API</h2>
<table>
<tr><th>Endereço base</th><td>Todas as rotas de negócio ficam sob <code>/api/v1</code>. No navegador, o site repassa
<code>/api/v1/*</code> para a API (rewrites do Next.js), então o endereço é o do próprio site. Localmente: API em
<code>http://localhost:8000</code>, documentação interativa em <code>/docs</code>.</td></tr>
<tr><th>Formato</th><td>JSON em UTF-8, nos dois sentidos. Fotos vão em <code>multipart/form-data</code>. Datas em ISO 8601
(UTC); a tela mostra no fuso de Manaus (RNF03).</td></tr>
<tr><th>Autenticação</th><td><code>POST /api/v1/auth/login</code> cria a sessão e grava o cookie <code>siga_sessao</code>
(httponly; Secure em produção). O token também pode ir no cabeçalho <code>Authorization: Bearer &lt;token&gt;</code>.
A sessão expira após 60 minutos sem uso e é renovada a cada requisição (RBN01.06).</td></tr>
<tr><th>Autorização</th><td>Cada rota exige um perfil (aluno, orientador, professor da disciplina, coordenador, membro da banca)
e o vínculo com o registro (RN07). Sem o perfil: 403. Sem vínculo com o registro: 404, para não revelar que ele existe.</td></tr>
<tr><th>Regras gerais de resposta</th><td>Toda rota que exige login responde <b>401</b> sem sessão válida. Toda rota com corpo
responde <b>400</b> quando o corpo é inválido (o padrão 422 do FastAPI foi trocado por 400, como pedem as fichas).
A tabela de cada rota mostra os códigos que ela devolveu na suíte de testes.</td></tr>
</table>

<h2>Formato dos erros</h2>
<p>Todo erro devolve um objeto JSON com <code>detail</code> (mensagem pronta para a tela) e, quando cabe, mais campos
(<code>backend/app/erros.py</code>):</p>
<table class="campos"><tr><th>Campo</th><th>Quando aparece</th><th>Exemplo</th></tr>
<tr><td><code>detail</code></td><td>sempre</td><td><code>"Confira os campos destacados."</code></td></tr>
<tr><td><code>campos</code></td><td>400: mensagem por campo</td><td><code>{{"email": "Campo obrigatório."}}</code></td></tr>
<tr><td><code>campo</code></td><td>409: campo duplicado</td><td><code>"email"</code></td></tr>
<tr><td><code>criterios</code></td><td>422: senha fora do padrão</td><td><code>[{{"descricao": "Uma letra maiúscula"}}]</code></td></tr>
<tr><td><code>motivo</code></td><td>link inválido ou cadastro bloqueado</td><td><code>"expirado"</code>, <code>"usado"</code>,
<code>"sem_matricula"</code>, <code>"duplicado"</code>, <code>"nao_editavel"</code></td></tr>
<tr><td><code>campos_pendentes</code></td><td>422 na submissão do TCC</td><td><code>["Aguarde o orientador aceitar a orientação."]</code></td></tr>
</table>
<table class="cods"><tr><th>Código</th><th>Significado no SIGA</th></tr>
{''.join(f"<tr><td class='cod c{str(c)[0]}'>{c}</td><td>{html.escape(s)}</td></tr>" for c, s in SIGNIFICADO.items() if c != 405)}
</table>

<h2>Índice das rotas</h2>
<div class="indice">{''.join(f"<div><b>{html.escape(t)}</b><br>" + "<br>".join(indice.get(g, [])) + "</div><br>"
                            for g, t in GRUPOS if indice.get(g))}</div>
{secoes}
</body></html>"""
    SAIDA.write_text(corpo, encoding="utf8")
    sem_perm = [chave(m, c) for c, ops in API["paths"].items() for m in ops if chave(m, c) not in perms]
    print(f"{total} operações; sem linha de permissão: {sem_perm or 'nenhuma'}; arquivo: {SAIDA}")


if __name__ == "__main__":
    main()
