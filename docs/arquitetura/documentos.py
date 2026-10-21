"""Documento de Arquitetura e Contrato da API no formato dos documentos do grupo (.docx e .pdf).

    python docs/arquitetura/documentos.py

Gera docs/arquitetura/Arquitetura_do_Sistema_SIGA_UEA.{docx,pdf} e Contrato_da_API_SIGA_UEA.{docx,pdf}.
O contrato é montado do docs/openapi.json e dos códigos observados na suíte (ver contrato_api.py).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import contrato_api as ca  # noqa: E402
from formato_siga import EQUIPE, Doc, gerar  # noqa: E402

DATA = "20/10/2026"
PROJETO = "SIGA UEA – Sistema de Gestão de TCC do NUCOMP-UEA"
INSTITUICAO = "UEA – Universidade do Estado do Amazonas, Escola Superior de Tecnologia (EST) – NUCOMP"
CLIENTE = "Profª Drª Diana Maria da Câmara – Coordenação do NUCOMP"


def identificacao(referencia, versao="1.0"):
    return [("Nome do Projeto:", PROJETO), ("Instituição:", INSTITUICAO), ("Patrocinadora / Cliente:", CLIENTE),
            ("Equipe / Gerentes do Projeto:", EQUIPE), ("Documento de referência:", referencia),
            ("Data:", DATA), ("Versão:", versao)]


def finais(d: Doc, n: int, descricao_v1: str, referencias: list[str]):
    d.h1(f"{n}. REGISTRO DE ALTERAÇÕES")
    d.tabela(["Versão", "Data", "Descrição", "Responsável"],
             [["1.0", DATA, descricao_v1, "Igor Leite"]], [1.8, 2.4, 8.8, 3.0])
    d.h1(f"{n + 1}. APROVAÇÕES")
    d.p("Os campos abaixo se destinam à assinatura de quem aprova este documento. Enquanto não houver aprovação, "
        "permanecem em branco.")
    d.tabela(["Assinatura – Equipe de desenvolvimento", "Assinatura – Profª Drª Diana Maria da Câmara / "
              "Coordenação NUCOMP", "Data"], [["\n\n", "", ""]], [6.5, 6.5, 3.0])
    d.h1(f"{n + 2}. REFERÊNCIAS")
    for r in referencias:
        d.p(r)


REF_PLANO = "SIGA UEA. Plano de Integração do Projeto. Versão 2.3. Manaus: NUCOMP – EST/UEA, 20 out. 2026."
REF_REQ = ("SIGA UEA. Requisitos_SIGA_UEA.xlsx: matriz de requisitos, regras de negócio, requisitos não funcionais, "
           "fluxos, telas e rastreabilidade. Manaus: NUCOMP – EST/UEA, 2026.")
REF_CONF = "SIGA UEA. Plano de Gerenciamento de Configuração. Versão 1.1. Manaus: NUCOMP – EST/UEA, 20 out. 2026."


# ================================================================ arquitetura
def arquitetura() -> Doc:
    d = Doc("DOCUMENTO DE ARQUITETURA DO SISTEMA",
            identificacao("Plano de Integração do Projeto, versão 2.3, seções 4.6.1 e 4.6.2; história HT03 "
                          "(SCRUM-108)"))
    d.h1("1. INTRODUÇÃO")
    d.p("Este documento descreve a arquitetura do SIGA UEA – Sistema de Gestão de TCC do NUCOMP-UEA: como o sistema "
        "está organizado em camadas, o caminho de uma requisição e as decisões que sustentam essa organização. Ele "
        "atende à parte de arquitetura da história HT03 (Arquitetura e contrato de API) e detalha a estratégia de "
        "integração da seção 4.6.1 do Plano de Integração do Projeto.")
    d.h2("1.1 Objetivo")
    d.p("Dar à equipe uma descrição única de onde cada responsabilidade fica no código, para que o frontend e o "
        "backend evoluam em paralelo sem retrabalho e para que cada requisito novo encontre o seu lugar.")
    d.h2("1.2 Escopo")
    d.p("Descreve o sistema como está na branch dev em 20/10/2026 (módulo de usuários, turmas e cadastro de TCC) e "
        "a organização que os próximos módulos seguem (defesa, publicação, indicadores e agenda).")
    d.h2("1.3 Documentos de referência")
    d.lista([
        "Plano de Integração do Projeto – SIGA UEA, versão 2.3, seções 4.6.1 (estratégia de integração) e 4.6.2 "
        "(dependências de integração).",
        "Contrato da API do SIGA UEA (documento que acompanha este): as 51 operações, com corpo, resposta e códigos.",
        "Diagramas UML de componentes, pacotes e implantação (D04, pasta 04_Arquitetura).",
        "Requisitos_SIGA_UEA.xlsx: requisitos, regras de negócio e requisitos não funcionais.",
    ], numerada=False)
    d.h2("1.4 Siglas")
    d.tabela(["Sigla", "Significado"], [
        ["API", "Interface de comunicação entre o site e o servidor (REST/JSON, sob /api/v1)."],
        ["ORM", "Mapeamento entre as classes do código e as tabelas do banco (SQLAlchemy)."],
        ["REST", "Estilo de API em que cada recurso tem um endereço e as operações usam os métodos HTTP."],
        ["RN, RNF, RBN", "Regra de negócio, requisito não funcional e requisito de baixo nível da planilha."],
        ["DS-FLxx", "Diagrama de sequência do fluxo FLxx (Documento de Sequência)."],
    ], [3.5, 12.5])

    d.h1("2. VISÃO GERAL")
    d.p("O SIGA UEA é uma aplicação web em três partes, que conversam somente por contratos explícitos: o site e a "
        "API integram-se pelo contrato da API; a API e o banco, pelo esquema versionado nas migrações. O serviço de "
        "e-mail fica encapsulado em um componente próprio e pode ser trocado sem alterar o restante.")
    d.tabela(["Parte", "Tecnologia", "Papel"], [
        ["Site", "Next.js 16 com React 19 (TypeScript, Tailwind)",
         "Telas e navegação. Não guarda regra de negócio nem acessa o banco."],
        ["API", "Python 3.12 com FastAPI, SQLAlchemy 2.1 e Alembic",
         "Regras de negócio, autorização, validação e auditoria, expostas como REST/JSON sob /api/v1."],
        ["Banco", "PostgreSQL 16 (SQLite no desenvolvimento)",
         "Dados, restrições de integridade e o log de auditoria imutável. Esquema criado por migrações."],
    ], [2.2, 5.3, 8.5])
    d.p("O sistema é um **monólito modular**: uma única API, organizada por módulo de negócio (usuários, turmas e "
        "cadastro de TCC; depois defesa, publicação e agenda), e não um conjunto de microsserviços. Para uma equipe "
        "de cinco pessoas com 8 h semanais, um único serviço para publicar, testar e manter reduz o risco de "
        "integração, apontado no Plano de Integração como o principal risco técnico do projeto.")
    d.p("O caminho completo é: navegador → site (HTTPS) → repasse de /api/v1 → API → PostgreSQL, com a API enviando "
        "e-mails pela API HTTPS da Brevo no ambiente integrado (o plano grátis do Render bloqueia SMTP) e pelo "
        "SMTP do Gmail no ambiente local.")

    d.h1("3. CAMADAS DO SITE")
    d.p("O site fica nas pastas app/, components/ e lib/ do repositório, além do arquivo proxy.ts.")
    d.tabela(["Camada", "Onde", "Responsabilidade"], [
        ["Páginas", "app/(publico)/ e app/(sistema)/",
         "Uma pasta por tela: acesso e sessão (TEL01), usuários e perfis, meu perfil, TCCs, cadastro, "
         "acompanhamento, orientações e turmas. As telas internas são componentes de cliente que chamam a API e "
         "mostram o resultado."],
        ["Componentes de interface", "components/",
         "Peças reutilizadas (campo, botão, modal, aviso, casca, selos de situação, cartão de turma), sem acesso à "
         "API. Garantem o mesmo visual e a acessibilidade em todas as telas."],
        ["Cliente da API e sessão", "lib/api.ts, lib/sessao.tsx, lib/sessao-servidor.ts, lib/tipos.ts",
         "api.ts é o único ponto que faz chamadas HTTP: monta a requisição, lê o erro no formato padrão e leva ao "
         "login quando a API responde 401. sessao-servidor.ts pergunta à API quem é o usuário antes de desenhar uma "
         "tela interna; tipos.ts espelha os esquemas da API."],
        ["Proxy de navegação e repasse", "proxy.ts e next.config.ts",
         "proxy.ts leva ao login quem abre uma tela interna sem o cookie de sessão. Os rewrites repassam /api/v1 "
         "para a API, de modo que o navegador fala com uma única origem."],
    ], [3.6, 4.6, 7.8])
    d.p("Regra da camada: o site nunca decide permissão. Esconder um item do menu é apenas conveniência; a "
        "autorização é conferida pela API em toda rota.")

    d.h1("4. CAMADAS DA API")
    d.p("A API fica em backend/app/. Cada camada só chama a de baixo: rotas → serviços → modelos → banco. Os "
        "esquemas, a segurança e os módulos transversais apoiam as rotas e os serviços.")
    d.tabela(["Camada", "Onde", "Responsabilidade", "Não faz"], [
        ["Rotas", "routes/", "Recebe a requisição, declara o perfil exigido, converte a entrada pelo esquema e chama "
         "um serviço.", "Não tem regra de negócio nem consulta o banco."],
        ["Esquemas", "schemas/ (Pydantic)", "Formato de entrada e saída de cada rota: tipos, obrigatoriedade, "
         "tamanhos e validações de campo. Entrada inválida responde 400 com a mensagem de cada campo.",
         "Não acessa o banco."],
        ["Segurança e sessão", "deps.py, security.py", "Exige sessão válida e renova os 60 minutos; recusa com 403 "
         "quem não tem o perfil; aplica a regra de senha, o hash bcrypt (custo ≥ 10) e os tokens de link.",
         "Não conhece as telas."],
        ["Serviços", "services/", "Regras de negócio (RN04, RN05, RN07, elegibilidade do orientador, protocolo, "
         "situações). Cada operação é uma transação e grava o log de auditoria. Os comentários citam o passo do "
         "diagrama de sequência.", "Não monta resposta HTTP: sinaliza o erro com ErroAPI(código, mensagem)."],
        ["Modelos", "models.py (SQLAlchemy)", "Tabelas, relacionamentos e restrições, com os nomes do modelo lógico.",
         "Não tem regra de negócio."],
        ["Acesso ao banco e esquema", "database.py, migrations/, seed.py", "Uma sessão por requisição, fechada assim "
         "que a rota termina; migrações versionadas 0001 a 0004; carga inicial repetível.", "—"],
    ], [2.6, 3.0, 6.6, 3.8])
    d.p("Módulos transversais: erros.py dá o formato único de erro; config.py lê as variáveis de ambiente; "
        "services/auditoria.py grava o log que o banco não deixa alterar (RNF03); services/email.py registra cada "
        "envio em notificacao_email e envia depois da resposta, sem atrasar quem fez o pedido. A pasta "
        "repositories/ está reservada: hoje os serviços usam o ORM diretamente.")

    d.h1("5. CAMINHO DE UMA REQUISIÇÃO")
    d.p("Exemplo do envio do cadastro de TCC para análise, POST /api/v1/tccs/{id}/submissao (DS-FL01, RBN03.03 e "
        "RBN03.04):")
    d.lista([
        "No passo 3 de TEL05, o aluno confirma o envio. lib/api.ts faz a chamada ao próprio endereço do site, "
        "levando o cookie de sessão.",
        "O repasse do Next.js entrega a chamada à API.",
        "A rota confere a sessão (401 se inválida) e o perfil de aluno (403) e chama o serviço de submissão.",
        "O serviço carrega o TCC travando a linha (SELECT … FOR UPDATE), para que dois cliques não gerem dois "
        "protocolos (RNF06), e confere o dono (404, RN07), a matrícula (403, RN05) e as pendências (422 com "
        "campos_pendentes).",
        "Se o cadastro já estava em análise, devolve o mesmo protocolo. Se não, gera TCC-AAAA-NNNNN, muda a "
        "situação para EM_ANALISE e grava o histórico e a auditoria na mesma transação, agendando o e-mail ao "
        "orientador.",
        "A API responde 200 com o protocolo; a sessão do banco fecha e o e-mail sai em seguida, com conexão própria.",
        "A tela mostra o protocolo e bloqueia a edição.",
    ])
    d.p("Esse caminho foi medido com 30 envios simultâneos: p95 de 0,73 s, para a meta de 3 s do RNF01 (Relatório "
        "de Execução de Testes, aba Desempenho RNF01).")

    d.h1("6. SEGURANÇA")
    d.tabela(["Ameaça ou requisito", "Como a arquitetura responde"], [
        ["Roubo de sessão por script na página", "Token só em cookie httponly, SameSite=Lax e Secure em produção "
         "(COOKIE_SEGURO=1)."],
        ["Senha vazada do banco", "Só o hash bcrypt (custo ≥ 10) fica gravado; tokens de link e de sessão também "
         "só como hash."],
        ["Força bruta no login", "Bloqueio de 15 minutos após 3 tentativas e mensagem genérica, que não revela se o "
         "e-mail existe."],
        ["Acesso a dado de outro usuário", "Autorização por perfil em toda rota e por vínculo no serviço (RN07); "
         "sem vínculo, a API responde 404, sem revelar que o registro existe."],
        ["Interceptação", "HTTPS em todo o caminho (RNF02) e TLS também entre a API e o banco no ambiente integrado."],
        ["Alteração do histórico", "Log de auditoria com gatilho no banco que recusa UPDATE e DELETE (migração "
         "0003, RNF03)."],
        ["Dados pessoais (LGPD)", "Cada perfil vê só o que precisa (RN07), os testes usam dados fictícios e as "
         "alterações ficam auditadas. Não se presume conformidade jurídica certificada (risco R08)."],
    ], [5.0, 11.0])

    d.h1("7. DADOS E CONSISTÊNCIA")
    d.lista([
        "Integridade garantida também pelo banco: e-mail único sem diferenciar maiúsculas, um TCC por aluno e "
        "período, protocolo único e domínios de situação com CHECK.",
        "Transações curtas: cada operação do serviço é uma transação, e a sessão fecha quando a rota termina, antes "
        "das tarefas em segundo plano. Sem isso, sob carga, cada requisição segurava duas conexões e o conjunto de "
        "conexões se esgotava; a correção foi feita na S03 e confirmada no teste de carga.",
        "Esquema só por migração: o mesmo esquema no SQLite de desenvolvimento e no PostgreSQL, e um teste falha se "
        "o modelo mudar sem a migração correspondente.",
    ], numerada=False)

    d.h1("8. AMBIENTES")
    d.tabela(["Ambiente", "Onde roda", "Uso"], [
        ["Local", "npm run dev, uvicorn --reload e SQLite, ou Docker Compose", "Desenvolvimento e testes de cada "
         "integrante (README, seção Como rodar)."],
        ["Integrado e homologação", "Vercel (site), Render (API), Neon (PostgreSQL) e Brevo (e-mail)", "Testes de integração e "
         "validação com a coordenação (HT06). Configuração em render.yaml, .vercelignore e README."],
    ], [3.6, 5.6, 6.8])
    img = AQUI / "diagrama-implantacao-1-ambiente-integrado.png"
    d.figura(img, "Figura 1 – Diagrama de implantação do ambiente integrado. Fonte: elaborado pelos autores (2026).")

    d.h1("9. DECISÕES DE ARQUITETURA")
    d.tabela(["Decisão", "Motivo", "Alternativa descartada"], [
        ["Monólito modular", "Equipe pequena e integração como maior risco; um só serviço para publicar e testar",
         "Microsserviços por módulo"],
        ["Site e API na mesma origem, com repasse de /api/v1", "Cookie de sessão sem CORS e sem expor a API "
         "diretamente", "Site chamando a API em outro domínio"],
        ["Sessão em cookie httponly", "Protege o token de scripts na página", "Token no armazenamento do navegador"],
        ["Regras no serviço e rotas finas", "Regras testáveis sem HTTP e reaproveitáveis", "Regra na rota ou na tela"],
        ["Validação responde 400; regra de negócio, 409 ou 422", "É o que as fichas pedem; separa campo inválido de "
         "operação não permitida", "O 422 padrão do FastAPI para tudo"],
        ["Esquema por migrações", "Mesmo banco em todos os ambientes e histórico no Git (HT05)",
         "Criar as tabelas ao iniciar a aplicação"],
        ["E-mail depois da resposta, registrado em notificacao_email", "A falha de envio não desfaz o cadastro e "
         "pode ser reenviada (RBN01.05, RBN03.06)", "Enviar dentro da requisição"],
        ["E-mail pela API HTTPS da Brevo no Render", "O plano grátis do Render bloqueia as portas de SMTP (25, 465 e "
         "587); HTTPS passa em qualquer hospedagem. Sem a chave, a API usa SMTP", "Gmail por SMTP direto; plano pago "
         "do Render"],
        ["Restrições no banco além do código", "Duplicidade e concorrência barradas mesmo com dois cliques (RNF06)",
         "Conferir só no código"],
    ], [5.2, 6.4, 4.4])

    d.h1("10. ATENDIMENTO AOS REQUISITOS NÃO FUNCIONAIS")
    d.p("A tabela compara cada requisito não funcional da planilha Requisitos_SIGA_UEA.xlsx com o que o sistema faz "
        "em 20/10/2026. Atendido: cumprido e verificado; Parcial: parte cumprida e parte pendente; Planejado: "
        "depende de um módulo ou do ambiente ainda não entregue.")
    d.tabela(["RNF", "O que a planilha exige", "Como o sistema atende", "Situação"], [
        ["RNF01", "Submissão do cadastro em até 3 s (p95) com 30 envios simultâneos.",
         "Trava de linha, transação curta e e-mail depois da resposta. Medido: p95 de 0,73 s com 30 envios, em "
         "PostgreSQL 16 local.", "Atendido localmente; repetir no ambiente integrado"],
        ["RNF02", "bcrypt custo ≥ 10; HTTPS com TLS ≥ 1.2; sessão de 60 min; LGPD; agenda pública sem dados "
         "pessoais.", "bcrypt custo 12, sessão de 60 min com renovação e acesso por perfil e vínculo. O HTTPS vem "
         "da Vercel e do Render. A agenda pública é do MOD07.", "Parcial: HTTPS depende da publicação; agenda "
         "planejada"],
        ["RNF03", "Log não editável com usuário, data/hora (America/Manaus), campo, valor anterior e novo; "
         "retenção de 5 anos.", "Log com todos esses campos; o banco recusa alterar ou apagar (migração 0003). A "
         "data é gravada em UTC e mostrada no fuso de Manaus.", "Parcial: a retenção de 5 anos depende do backup "
         "planejado"],
        ["RNF04", "Sem rolagem horizontal em 360 e 768 px, no Chrome e no Safari móveis.",
         "Telas testadas em 360 e 768 px no Google Chrome, sem rolagem horizontal (59 checagens).",
         "Parcial: falta o teste no Safari"],
        ["RNF05", "Ata em PDF em até 5 s (p95) após a confirmação do resultado.",
         "Gerador de PDF previsto na API (MOD04).", "Planejado"],
        ["RNF06", "Sem protocolo duplicado; falha de envio não apaga a versão anterior; SHA-256 conferido no envio "
         "e na leitura.", "Protocolo com trava de linha e restrição única; arquivo validado antes de substituir o "
         "anterior; SHA-256 gravado no envio e conferido ao ler (fotos). Os PDFs do TCC seguem o mesmo padrão.",
         "Atendido para fotos e protocolo; PDFs com o RAN07"],
        ["RNF07", "99% de disponibilidade no pico e recuperação em até 30 min.",
         "No plano grátis do Render a API dorme sem uso; o diagrama de implantação prevê monitoramento e backup.",
         "Planejado: exige plano pago ou monitoramento"],
    ], [1.6, 4.6, 6.4, 3.4])
    d.p("Pontos em que o sistema difere da planilha, por decisão registrada da equipe:")
    d.lista([
        "RN16 diz que as recusas de orientação não são guardadas. O sistema guarda a recusa e o motivo, porque o "
        "RNF03 exige registrar toda alteração; a recusa não vale como vínculo. Sugere-se ajustar o texto da RN16.",
        "A planilha fala em e-mail institucional; por decisão da equipe, o cadastro aceita qualquer e-mail válido.",
        "O DS-FL01 envia o e-mail ao orientador só na submissão; como o RBN03.03 exige o aceite antes, o aviso sai "
        "quando o aluno indica o orientador, e outro sai na submissão.",
    ], numerada=False)

    d.h1("11. VERIFICAÇÃO DA ARQUITETURA")
    d.lista([
        "Suíte da API (backend/tests, pytest): 123 execuções em SQLite e em PostgreSQL 16, cobrindo as 51 operações "
        "do contrato.",
        "Testes no navegador (docs/testes/e2e): fluxos completos pela tela e responsividade em 360 e 768 px.",
        "Teste de carga (backend/scripts/carga_rnf01.py): RNF01 e RNF06.",
        "Resultados e evidências: Relatório de Execução de Testes (pasta 07_Testes).",
    ], numerada=False)
    finais(d, 12, "Criação do documento.", [REF_PLANO, REF_REQ, REF_CONF,
           "SIGA UEA. Contrato da API. Versão 1.0. Manaus: NUCOMP – EST/UEA, 20 out. 2026."])
    return d


# ================================================================ contrato da API
def _sem_html(t):
    return re.sub(r"<[^>]+>", "", t or "")


def contrato() -> Doc:
    d = Doc("CONTRATO DA API",
            identificacao("Plano de Integração do Projeto, versão 2.3, seção 4.6.1; história HT03 (SCRUM-108)"))
    perms = ca.permissoes()
    ops = [(m, c, op) for c, metodos in ca.API["paths"].items() for m, op in metodos.items()]

    d.h1("1. INTRODUÇÃO")
    d.p("Este documento é o contrato da API do SIGA UEA: as rotas que o site usa para falar com o servidor, o que "
        "cada uma recebe e devolve, quem pode usá-la e os códigos de resposta. Ele atende à parte de contrato da "
        "história HT03 e é a referência para o frontend e o backend integrarem sem retrabalho (risco R02 do Plano "
        "de Integração).")
    d.h2("1.1 Objetivo")
    d.p("Registrar, para cada operação, o método, o caminho, o perfil exigido, o requisito de origem, o corpo da "
        "requisição, a resposta e os códigos de erro, com o mesmo formato de erro em toda a API.")
    d.h2("1.2 Escopo")
    d.p(f"As {len(ops)} operações existentes na branch dev em {DATA}: acesso e sessão, meu perfil, usuários, áreas "
        "de interesse, catálogo, períodos e turmas, cadastro de TCC e orientação. As rotas dos próximos módulos "
        "entram em novas versões deste documento.")
    d.h2("1.3 Documentos de referência")
    d.lista([
        "Plano de Integração do Projeto – SIGA UEA, versão 2.3, seções 4.6.1 e 4.6.2.",
        "docs/openapi.json: o mesmo contrato em OpenAPI 3, gerado do código da API.",
        "Relatório de Execução de Testes: os códigos de resposta deste documento são os observados na suíte.",
        "Documento de Arquitetura do Sistema: camadas e caminho de uma requisição.",
    ], numerada=False)
    d.h2("1.4 Siglas")
    d.tabela(["Sigla", "Significado"], [
        ["JSON", "Formato de texto usado no corpo das requisições e respostas."],
        ["HTTP", "Protocolo das requisições; o código da resposta indica o resultado (200, 400, 404…)."],
        ["CT", "Caso de teste da matriz de testes."],
        ["RN07", "Regra de negócio de perfis e vínculos de acesso."],
    ], [3.5, 12.5])

    d.h1("2. CONVENÇÕES GERAIS")
    d.tabela(None, [
        ["Endereço base", "As rotas de negócio ficam sob /api/v1. No navegador, o site repassa /api/v1 para a API, "
         "então o endereço é o do próprio site. Localmente: API em http://localhost:8000, documentação interativa "
         "em /docs."],
        ["Formato", "JSON em UTF-8. Fotos vão em multipart/form-data. Datas em ISO 8601 (UTC); a tela mostra no "
         "fuso de Manaus (RNF03)."],
        ["Autenticação", "POST /api/v1/auth/login cria a sessão e grava o cookie siga_sessao (httponly; Secure em "
         "produção). O token também é aceito no cabeçalho Authorization: Bearer. A sessão expira após 60 minutos "
         "sem uso e é renovada a cada requisição (RBN01.06)."],
        ["Autorização", "Cada rota exige um perfil e o vínculo com o registro (RN07). Sem o perfil: 403. Sem vínculo "
         "com o registro: 404, para não revelar que ele existe."],
        ["Regras gerais", "Toda rota que exige login responde 401 sem sessão válida. Toda rota com corpo responde "
         "400 quando o corpo é inválido. As tabelas de cada operação mostram os códigos que ela devolveu na suíte."],
    ], [3.6, 12.4], rotulo=True)

    d.h1("3. FORMATO DOS ERROS")
    d.p("Todo erro devolve um objeto JSON com detail, a mensagem pronta para a tela, e, quando cabe, outros campos:")
    d.tabela(["Campo", "Quando aparece", "Exemplo"], [
        ["detail", "Sempre", "\"Confira os campos destacados.\""],
        ["campos", "400: mensagem por campo", "{\"email\": \"Campo obrigatório.\"}"],
        ["campo", "409: campo duplicado", "\"email\""],
        ["criterios", "422: senha fora do padrão", "[{\"descricao\": \"Uma letra maiúscula\"}]"],
        ["motivo", "Link inválido ou cadastro bloqueado", "\"expirado\", \"usado\", \"sem_matricula\", \"duplicado\""],
        ["campos_pendentes", "422 na submissão do TCC", "[\"Aguarde o orientador aceitar a orientação.\"]"],
    ], [3.4, 5.0, 7.6])
    d.tabela(["Código", "Significado no SIGA"],
             [[str(c), s] for c, s in ca.SIGNIFICADO.items() if c != 405], [2.0, 14.0])

    d.h1("4. ÍNDICE DAS OPERAÇÕES")
    linhas = []
    for m, c, op in ops:
        quem, req = perms.get(ca.chave(m, c), ("—", "—"))
        linhas.append([m.upper(), c, quem, req])
    d.tabela(["Método", "Caminho", "Quem pode", "Requisito"], linhas, [1.8, 6.4, 3.8, 4.0])

    n = 5
    for tag, titulo in ca.GRUPOS:
        do_grupo = [(m, c, op) for m, c, op in ops if (op.get("tags") or ["health"])[0] == tag]
        if not do_grupo:
            continue
        nome = re.sub(r"\s*\(.*\)$", "", titulo).upper()
        d.h1(f"{n}. {nome}")
        for k, (m, c, op) in enumerate(do_grupo, start=1):
            _operacao(d, f"{n}.{k}", m, c, op, perms)
        n += 1
    finais(d, n, "Criação do documento, gerado do código e dos testes da branch dev.",
           [REF_PLANO, REF_REQ, REF_CONF])
    return d


def _operacao(d: Doc, num, m, c, op, perms):
    quem, req = perms.get(ca.chave(m, c), ("—", "—"))
    d.h2(f"{num} {m.upper()} {c}")
    info = [["Finalidade", ca.FINALIDADE.get(ca.chave(m, c), op.get("summary", ""))], ["Quem pode", quem],
            ["Requisito", req]]
    desc = (op.get("description") or "").strip()
    if desc:
        info.append(["Observação", desc.replace("\n", " ")])
    d.tabela(None, info, [3.6, 12.4], rotulo=True)
    corpo = op.get("requestBody", {}).get("content", {})
    for tipo_mime, rot in (("application/json", "Corpo da requisição (JSON)"),
                           ("multipart/form-data", "Corpo da requisição (multipart/form-data)")):
        if tipo_mime in corpo:
            linhas = _campos(corpo[tipo_mime]["schema"])
            if linhas:
                d.h3(rot)
                d.tabela(["Campo", "Tipo", "Obrigatório", "Restrições"], linhas, [3.8, 5.6, 2.4, 4.2])
    params = [p for p in op.get("parameters", []) if p["in"] in ("query", "path")]
    if params:
        d.h3("Parâmetros")
        d.tabela(["Nome", "Onde", "Tipo", "Obrigatório"],
                 [[p["name"], "caminho" if p["in"] == "path" else "consulta", ca.tipo(p.get("schema", {})),
                   "sim" if p.get("required") else "não"] for p in params], [4.0, 3.0, 6.4, 2.6])
    sucesso = next((x for x in op.get("responses", {}) if x.startswith("2")), "200")
    resp = op["responses"].get(sucesso, {}).get("content", {}).get("application/json", {}).get("schema")
    if resp:
        linhas = _campos(resp)
        if linhas:
            d.h3(f"Resposta {sucesso}: {ca.tipo(resp)}")
            d.tabela(["Campo", "Tipo", "Obrigatório", "Restrições"], linhas, [3.8, 5.6, 2.4, 4.2])
    obs = _observados(m, c)
    cods = sorted(set(obs) | {int(sucesso)})
    d.h3("Respostas")
    d.tabela(["Código", "Significado", "Vezes na suíte de testes"],
             [[str(x), ca.SIGNIFICADO.get(x, ""), str(obs.get(x, 0))] for x in cods if x != 405], [2.0, 10.6, 3.4])


def _campos(schema):
    s = ca.resolver(schema)
    if s.get("type") == "array":
        s = ca.resolver(s["items"])
    obrig = set(s.get("required", []))
    return [[n, ca.tipo(p), "sim" if n in obrig else "não", ca.restricoes(p) or "—"]
            for n, p in s.get("properties", {}).items()]


def _observados(m, c):
    k = ca.chave(m, c)
    alvo = re.compile("^" + re.escape(k).replace(r"\{\}", r"\{[^}]+\}") + "$")
    for rota, cods in ca.OBS.items():
        if alvo.match(rota):
            return {int(x): n for x, n in cods.items()}
    return {}


def main():
    for d, nome in ((arquitetura(), "Arquitetura_do_Sistema_SIGA_UEA"), (contrato(), "Contrato_da_API_SIGA_UEA")):
        paginas, faltando = gerar(d, AQUI / nome)
        print(f"{nome}: {paginas} páginas no PDF; títulos sem página no sumário: {faltando or 'nenhum'}")


if __name__ == "__main__":
    main()
