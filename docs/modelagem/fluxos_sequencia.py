"""Os fluxos FL01 a FL11, passo a passo, na ordem em que o usuário age no sistema.

Fluxos implementados (fonte="sistema"): a ordem foi conferida percorrendo o site com as contas
de demonstração (seed --demo): cada clique, a tela em que acontece, as chamadas que chegam à API
(log do uvicorn) e o que os serviços consultam e gravam, na ordem do código em backend/app/services.
Fluxos ainda sem tela (fonte="prototipo"): seguem as telas e botões do protótipo
(docs/prototipos/SIGA UEA — Protótipo.html).

Os nomes de controles e entidades são os do diagrama de classes (diagrama_classes.py).
Desenho: diagramas_sequencia.py.
"""

from diagramas_sequencia import (
    Diagrama,
    Fluxo,
    Part,
    acao,
    alt,
    assinc,
    chama,
    loop,
    nota,
    opt,
    proprio,
    ref,
    volta,
)

P = Part
PARTES = {p.chave: p for p in [
    # atores
    P("aluno", "ator", "Aluno"),
    P("orientador", "ator", "Orientador"),
    P("coord", "ator", "Coordenação"),
    P("professor", "ator", "Professor da disciplina"),
    P("banca", "ator", "Membro da banca"),
    P("todos", "ator", "Usuário", "qualquer perfil"),
    P("novo", "ator", "Pessoa cadastrada", "ainda sem senha"),
    P("relogio", "externo", "Agendador", "tarefa diária"),
    # telas do sistema (rota real)
    P("entrar", "tela", "TEL01 Entrar", "/entrar"),
    P("esqueci", "tela", "TEL01 Esqueci minha senha", "/esqueci-senha"),
    P("defsenha", "tela", "TEL01 Ativar conta / Nova senha", "/ativar · /redefinir-senha"),
    P("inicio", "tela", "Início", "/inicio"),
    P("casca", "tela", "Menu do sistema", "cabeçalho e menu lateral"),
    P("tel02", "tela", "TEL02 Usuários e perfis", "/usuarios"),
    P("tel04", "tela", "TEL04 TCCs (Meu TCC)", "/tccs"),
    P("tel05", "tela", "TEL05 Cadastro de TCC", "/tccs/cadastro"),
    P("tel06", "tela", "TEL06 Acompanhamento do TCC", "/tccs/{id}"),
    P("tel08", "tela", "TEL08 Orientações", "/orientacoes"),
    P("turmas", "tela", "Turmas de TCC", "/turmas (coordenação)"),
    P("minhas", "tela", "Minhas turmas", "/turmas (professor e aluno)"),
    P("turma", "tela", "Turma", "/turmas/{id}"),
    # controles (backend/app/routes) e a conferência de sessão (deps.py)
    P("cauth", "controle", "ControladorAuth", "routes/auth.py"),
    P("cusu", "controle", "ControladorUsuarios", "routes/usuarios.py"),
    P("ccat", "controle", "ControladorCatalogo", "routes/catalogo.py"),
    P("ctur", "controle", "ControladorTurmas", "routes/turmas.py"),
    P("ctcc", "controle", "ControladorTccs", "routes/tccs.py"),
    P("deps", "controle", "Deps", "usuario_atual · exigir_perfil"),
    # entidades (backend/app/models.py)
    P("Usuario", "entidade", "Usuario"),
    P("Sessao", "entidade", "Sessao"),
    P("TokenUsuario", "entidade", "TokenUsuario"),
    P("UsuarioPerfil", "entidade", "UsuarioPerfil"),
    P("Docente", "entidade", "Docente"),
    P("Aluno", "entidade", "Aluno"),
    P("Curso", "entidade", "Curso"),
    P("AreaInteresse", "entidade", "AreaInteresse"),
    P("PeriodoLetivo", "entidade", "PeriodoLetivo"),
    P("Turma", "entidade", "Turma"),
    P("MatriculaTurma", "entidade", "MatriculaTurma"),
    P("Tcc", "entidade", "Tcc"),
    P("HistoricoSituacao", "entidade", "HistoricoSituacao"),
    P("Orientacao", "entidade", "Orientacao"),
    P("PublicacaoArtigo", "entidade", "PublicacaoArtigo"),
    P("NotificacaoEmail", "entidade", "NotificacaoEmail"),
    P("LogAuditoria", "entidade", "LogAuditoria"),
    # telas do protótipo para o que ainda não foi implementado (espaço do TCC e suas abas)
    P("tel07", "tela", "TEL07 Análise de cadastros", "menu Análise de cadastros"),
    P("tel09", "tela", "TEL09 Documentos", "espaço do TCC, aba Documentos"),
    P("tel10", "tela", "TEL10 Banca", "espaço do TCC, aba Banca"),
    P("tel11", "tela", "TEL11 Agendamento", "aba Defesa › Agendamento"),
    P("tel18", "tela", "TEL18 Divulgação na agenda", "aba Defesa › Divulgação"),
    P("tel19", "tela", "TEL19 Presença e ocorrências", "aba Defesa › Presença"),
    P("tel12", "tela", "TEL12 Avaliação", "aba Resultado › Avaliação"),
    P("tel13", "tela", "TEL13 Ata e certificados", "aba Resultado › Ata e certificados"),
    P("tel14", "tela", "TEL14 Correções", "espaço do TCC, aba Correções"),
    P("tel15", "tela", "TEL15 Artigo", "espaço do TCC, aba Artigo"),
    P("tel16", "tela", "TEL16 Indicadores", "menu Indicadores"),
    P("tel17", "tela", "TEL17 Agenda", "menu Agenda"),
    # controles planejados (página 5 do diagrama de classes)
    P("cana", "controle", "ControladorAnaliseCadastro", "planejado"),
    P("cagd", "controle", "ControladorAgendamentoDefesa", "planejado"),
    P("cage", "controle", "ControladorAgenda", "planejado"),
    P("cava", "controle", "ControladorAvaliacaoDefesa", "planejado"),
    P("cnota", "controle", "CalculadoraNotaFinal", "planejado"),
    P("cdocd", "controle", "ControladorDocumentosDefesa", "planejado"),
    P("ccor", "controle", "ControladorCorrecoes", "planejado"),
    P("cpub", "controle", "ControladorPublicacao", "planejado"),
    P("cind", "controle", "ControladorIndicadores", "planejado"),
    P("coco", "controle", "ControladorOcorrencias", "planejado"),
    P("clem", "controle", "ControladorLembretes", "planejado"),
    P("cnot", "controle", "ControladorNotificacao", "planejado"),
    # entidades planejadas (modelo lógico)
    P("AnaliseCadastro", "entidade", "AnaliseCadastro"),
    P("DocumentoTcc", "entidade", "DocumentoTcc"),
    P("Defesa", "entidade", "Defesa"),
    P("BancaMembro", "entidade", "BancaMembro"),
    P("UsuarioExterno", "entidade", "UsuarioExterno"),
    P("AcessoLimitado", "entidade", "AcessoLimitado"),
    P("LocalDefesa", "entidade", "LocalDefesa"),
    P("HistoricoDefesa", "entidade", "HistoricoDefesa"),
    P("InstrumentoAvaliacao", "entidade", "InstrumentoAvaliacao"),
    P("Avaliacao", "entidade", "Avaliacao"),
    P("AvaliacaoCriterio", "entidade", "AvaliacaoCriterio"),
    P("ResultadoDefesa", "entidade", "ResultadoDefesa"),
    P("Correcao", "entidade", "Correcao"),
    P("DocumentoOficial", "entidade", "DocumentoOficial"),
    P("OcorrenciaDefesa", "entidade", "OcorrenciaDefesa"),
    P("OuvinteDefesa", "entidade", "OuvinteDefesa"),
    P("HistoricoPublicacao", "entidade", "HistoricoPublicacao"),
    P("doi", "externo", "Base de DOI", "Crossref"),
    # envio de e-mail (services/email.py) e o servidor de e-mail
    P("iemail", "interface", "InterfaceEmail", "services/email.py"),
    P("smtp", "externo", "Serviço de e-mail", "SMTP ou Brevo"),
]}


def email_depois(ctl: str, quem: str, assunto: str) -> list:
    """Envio do e-mail: só depois que a resposta já saiu para a tela (BackgroundTasks, RNF01)."""
    return [
        assinc(ctl, "iemail", f"processar(notificação): {assunto}"),
        chama("iemail", "smtp", f"enviar e-mail para {quem}"),
        alt(
            ("[e-mail aceito]", [
                volta("smtp", "iemail", "aceito"),
                chama("iemail", "NotificacaoEmail", "marcar enviado (status enviado, enviado_em)"),
            ]),
            ("[falha de envio]", [
                volta("smtp", "iemail", "erro"),
                chama("iemail", "NotificacaoEmail", "marcar falha (status falha, erro); fica para reenvio"),
            ]),
        ),
    ]


def enfileirar(ctl: str, tipo: str) -> list:
    return [chama(ctl, "NotificacaoEmail", f"registrar({tipo}) → status pendente")]


def sessao_da_tela(tela: str, ator: str = "todos") -> list:
    """Toda tela interna confere a sessão no servidor do Next antes de aparecer (FL10-A)."""
    return [ref("DS-FL10-A: a tela confere a sessão (GET /auth/me) antes de aparecer", ator, tela)]


# =====================================================================================
# FL10 · Acesso: autenticar, sessão, senha e cadastro de usuários
# =====================================================================================
FL10 = Fluxo("FL10", "Autenticar, sessão e usuários",
             "SCRUM-8 RAN01 · SCRUM-21, SCRUM-23 a SCRUM-27 · RNF02 · TEL01, TEL02", [
    Diagrama(
        "DS-FL10", "Entrar no sistema", "SCRUM-8 RAN01 · SCRUM-26 RBN01.06 · RNF02 · TEL01",
        "abrir o endereço do sistema → TEL01 Entrar (/entrar) → informar e-mail e senha → botão Entrar → "
        "Início (/inicio) com o menu do perfil",
        ["todos", "entrar", "inicio", "cauth", "deps", "Usuario", "Sessao", "LogAuditoria"],
        [
            acao("todos", "entrar", "Abrir o endereço do sistema"),
            nota("Sem o cookie de sessão, o site leva direto a /entrar (proxy.ts).", "entrar", "entrar"),
            volta("entrar", "todos", "Exibe Entrar: e-mail e senha"),
            acao("todos", "entrar", "Informar e-mail e senha e clicar em Entrar"),
            chama("entrar", "cauth", "POST /auth/login {email, senha}"),
            chama("cauth", "Usuario", "buscar por e-mail (sem diferenciar maiúsculas)"),
            volta("Usuario", "cauth", "usuário ou vazio"),
            alt(
                ("[e-mail não cadastrado]", [
                    chama("cauth", "LogAuditoria", "registrar(login_falha, email_inexistente)"),
                    volta("cauth", "entrar", "401 E-mail ou senha incorretos"),
                    volta("entrar", "todos", "Exibe o erro sem dizer qual campo falhou"),
                ]),
                ("[conta bloqueada: bloqueado_ate no futuro]", [
                    chama("cauth", "LogAuditoria", "registrar(login_falha, conta_bloqueada)"),
                    volta("cauth", "entrar", "423 Conta bloqueada por 15 minutos"),
                    volta("entrar", "todos", "Exibe o bloqueio"),
                ]),
                ("[conta inativada ou sem senha (ativação pendente)]", [
                    chama("cauth", "LogAuditoria", "registrar(login_falha, conta_inativa)"),
                    volta("cauth", "entrar", "401 E-mail ou senha incorretos"),
                    volta("entrar", "todos", "Exibe o mesmo erro"),
                ]),
                ("[senha incorreta]", [
                    proprio("cauth", "verificarSenha(senha, hash) → não confere"),
                    chama("cauth", "Usuario", "somar tentativa; na 3ª seguida bloqueia 15 min"),
                    chama("cauth", "LogAuditoria", "registrar(login_falha, senha_incorreta)"),
                    volta("cauth", "entrar", "401 incorretos (ou 423 na 3ª)"),
                    volta("entrar", "todos", "Exibe o erro"),
                ]),
                ("[credenciais válidas]", [
                    proprio("cauth", "verificarSenha(senha, hash) → confere (bcrypt)"),
                    chama("cauth", "Usuario", "zerar tentativas e bloqueio"),
                    chama("cauth", "Sessao", "criar(token_hash, expira em 60 min)"),
                    chama("cauth", "LogAuditoria", "registrar(login_sucesso)"),
                    volta("cauth", "entrar", "200 {usuário, perfis} + cookie de sessão"),
                    chama("entrar", "inicio", "ir para /inicio"),
                    chama("inicio", "deps", "GET /auth/me (cookie)"),
                    chama("deps", "Sessao", "obter(token_hash) e renovar 60 min"),
                    volta("Sessao", "deps", "sessão válida"),
                    volta("deps", "inicio", "200 {usuário, perfis}"),
                    volta("inicio", "todos", "Exibe o Início com o menu e os cartões do perfil"),
                ]),
            ),
        ]),
    Diagrama(
        "DS-FL10-A", "Sessão: conferir em cada tela, sair e expirar", "SCRUM-26 RBN01.06 · RNF02 · todas as telas internas",
        "em qualquer tela interna → clicar num item do menu → a tela confere a sessão antes de aparecer; "
        "botão Sair no cabeçalho → TEL01 Entrar",
        ["todos", "casca", "entrar", "deps", "cauth", "Sessao", "Usuario", "LogAuditoria"],
        [
            acao("todos", "casca", "Clicar num item do menu (ex.: TCCs)"),
            chama("casca", "deps", "GET /auth/me (cookie de sessão)"),
            chama("deps", "Sessao", "obter(token_hash)"),
            volta("Sessao", "deps", "sessão ou vazio"),
            alt(
                ("[sem cookie, sessão vencida (60 min sem uso) ou conta inativada]", [
                    volta("deps", "casca", "401 Sessão expirada"),
                    chama("casca", "entrar", "ir para /entrar?motivo=sessao"),
                    volta("entrar", "todos", "Exibe Entrar com o aviso de sessão expirada"),
                ]),
                ("[sessão válida]", [
                    chama("deps", "Sessao", "renovar: expira_em = agora + 60 min"),
                    volta("deps", "casca", "200 {usuário}"),
                    volta("casca", "todos", "Exibe a tela pedida"),
                ]),
            ),
            acao("todos", "casca", "Clicar em Sair"),
            chama("casca", "cauth", "POST /auth/logout"),
            chama("cauth", "Sessao", "encerrar: expira_em = agora"),
            chama("cauth", "LogAuditoria", "registrar(logout)"),
            volta("cauth", "casca", "200 + apaga o cookie"),
            chama("casca", "entrar", "ir para /entrar?motivo=saiu"),
            volta("entrar", "todos", "Exibe Entrar"),
        ]),
    Diagrama(
        "DS-FL10-B", "Esqueci a senha: pedir o link", "SCRUM-27 RBN01.07 · TEL01",
        "TEL01 Entrar → link \"Esqueci minha senha\" → /esqueci-senha → informar o e-mail → "
        "botão \"Enviar link de recuperação\" → mensagem de envio",
        ["todos", "entrar", "esqueci", "cauth", "Usuario", "TokenUsuario", "NotificacaoEmail", "LogAuditoria",
         "iemail", "smtp"],
        [
            acao("todos", "entrar", "Clicar em \"Esqueci minha senha\""),
            chama("entrar", "esqueci", "ir para /esqueci-senha"),
            volta("esqueci", "todos", "Exibe o campo de e-mail"),
            acao("todos", "esqueci", "Informar o e-mail e clicar em \"Enviar link de recuperação\""),
            chama("esqueci", "cauth", "POST /auth/esqueci-senha {email}"),
            chama("cauth", "Usuario", "buscar por e-mail"),
            volta("Usuario", "cauth", "usuário ou vazio"),
            alt(
                ("[e-mail não cadastrado ou conta não ativa]", [
                    volta("cauth", "esqueci", "202 (mesma resposta: não revela se o e-mail existe)"),
                    volta("esqueci", "todos", "Exibe \"se o e-mail estiver cadastrado, enviamos o link\""),
                ]),
                ("[conta ativa]", [
                    chama("cauth", "TokenUsuario", "invalidar links de recuperação anteriores"),
                    chama("cauth", "TokenUsuario", "criar(RECUPERACAO, hash, vale 10 min)"),
                    *enfileirar("cauth", "RECUPERACAO"),
                    chama("cauth", "LogAuditoria", "registrar(pedir_recuperacao)"),
                    volta("cauth", "esqueci", "202 Solicitação recebida"),
                    volta("esqueci", "todos", "Exibe a mesma mensagem de envio"),
                    *email_depois("cauth", "o usuário", "link /redefinir-senha?token="),
                ]),
            ),
        ]),
    Diagrama(
        "DS-FL10-C", "Definir a senha pelo link (ativar conta ou nova senha)",
        "SCRUM-24 RBN01.04 · SCRUM-25 RBN01.05 · SCRUM-27 RBN01.07 · TEL01",
        "abrir o link do e-mail → /ativar?token= (conta nova) ou /redefinir-senha?token= (esqueci a senha) → "
        "a tela confere o link → informar e confirmar a senha → botão \"Ativar conta\" ou \"Salvar nova senha\" "
        "→ TEL01 Entrar",
        ["novo", "defsenha", "entrar", "cauth", "TokenUsuario", "Usuario", "Sessao", "LogAuditoria"],
        [
            acao("novo", "defsenha", "Abrir o link recebido por e-mail"),
            chama("defsenha", "cauth", "POST /auth/validar-token {token, tipo}"),
            chama("cauth", "TokenUsuario", "obter(hash do token, tipo)"),
            volta("TokenUsuario", "cauth", "token (usado_em, expira_em) ou vazio"),
            alt(
                ("[link inválido, usado ou vencido]", [
                    volta("cauth", "defsenha", "200 {valido: false, motivo}"),
                    volta("defsenha", "novo", "Exibe o motivo e o link para pedir outro"),
                ]),
                ("[link válido]", [
                    volta("cauth", "defsenha", "200 {valido: true}"),
                    volta("defsenha", "novo", "Exibe Nova senha e Confirmar senha com os critérios"),
                    acao("novo", "defsenha", "Informar e confirmar a senha e clicar em Ativar conta / Salvar nova senha"),
                    nota("A tela confere antes de enviar: 8 caracteres, 1 maiúscula, 1 número, 1 especial "
                         "e as duas senhas iguais.", "defsenha", "defsenha"),
                    chama("defsenha", "cauth", "POST /auth/ativar ou /auth/redefinir-senha {token, senha}"),
                    chama("cauth", "TokenUsuario", "conferir de novo (pode ter vencido)"),
                    volta("TokenUsuario", "cauth", "token válido"),
                    alt(
                        ("[senha fora dos critérios]", [
                            volta("cauth", "defsenha", "422 {criterios não atendidos}"),
                            volta("defsenha", "novo", "Marca os critérios que faltam"),
                        ]),
                        ("[ativação]", [
                            proprio("cauth", "gerarHash(senha) (bcrypt)"),
                            chama("cauth", "Usuario", "gravar senha e ativar a conta"),
                            chama("cauth", "TokenUsuario", "marcar usado"),
                            chama("cauth", "LogAuditoria", "registrar(ativar_conta)"),
                            volta("cauth", "defsenha", "200 Conta ativada"),
                            chama("defsenha", "entrar", "ir para /entrar?motivo=ativada"),
                            volta("entrar", "novo", "Exibe Entrar com \"conta ativada\""),
                        ]),
                        ("[redefinição]", [
                            proprio("cauth", "gerarHash(senha) (bcrypt)"),
                            chama("cauth", "Usuario", "gravar senha, zerar tentativas e desbloquear"),
                            chama("cauth", "TokenUsuario", "marcar usado"),
                            chama("cauth", "Sessao", "encerrar as sessões abertas"),
                            chama("cauth", "LogAuditoria", "registrar(redefinir_senha)"),
                            volta("cauth", "defsenha", "200 Senha redefinida"),
                            chama("defsenha", "entrar", "ir para /entrar?motivo=redefinida"),
                            volta("entrar", "novo", "Exibe Entrar com \"senha redefinida\""),
                        ]),
                    ),
                ]),
            ),
        ]),
    Diagrama(
        "DS-FL10-D", "Cadastrar usuário e enviar a ativação",
        "SCRUM-21 RBN01.01 · SCRUM-23 RBN01.03 · SCRUM-25 RBN01.05 · TEL02",
        "menu \"Usuários e perfis\" → TEL02 (/usuarios), aba Docentes ou Alunos → botão \"Novo docente\" / "
        "\"Novo aluno\" → janela com os dados → botão \"Salvar e enviar ativação\" → a pessoa aparece na lista "
        "como \"aguardando ativação\"",
        ["coord", "tel02", "ccat", "cusu", "deps", "Usuario", "Docente", "Aluno", "UsuarioPerfil", "TokenUsuario",
         "NotificacaoEmail", "LogAuditoria", "iemail", "smtp"],
        [
            acao("coord", "tel02", "Clicar em \"Usuários e perfis\" no menu"),
            *sessao_da_tela("tel02", "coord"),
            chama("tel02", "ccat", "GET /cursos e GET /areas"),
            volta("ccat", "tel02", "cursos[], áreas[]"),
            chama("tel02", "cusu", "GET /docentes (aba inicial)"),
            volta("cusu", "tel02", "docentes[] com a situação"),
            volta("tel02", "coord", "Exibe a lista de docentes, com busca e filtros"),
            opt("[cadastrar aluno]", [
                acao("coord", "tel02", "Clicar na aba Alunos"),
                chama("tel02", "cusu", "GET /alunos"),
                volta("cusu", "tel02", "alunos[]"),
            ]),
            acao("coord", "tel02", "Clicar em \"Novo docente\" (ou \"Novo aluno\")"),
            volta("tel02", "coord", "Abre a janela: docente (nome, e-mail, telefone, cargo, curso, perfis, áreas); "
                  "aluno (nome, e-mail, matrícula, curso)"),
            acao("coord", "tel02", "Preencher e clicar em \"Salvar e enviar ativação\""),
            chama("tel02", "cusu", "POST /docentes ou POST /alunos {dados}"),
            chama("cusu", "deps", "exigir_perfil(coordenador)"),
            volta("deps", "cusu", "ok (senão 403)"),
            chama("cusu", "Usuario", "e-mail livre? (aluno: matrícula livre?)"),
            volta("Usuario", "cusu", "sim / não"),
            alt(
                ("[e-mail ou matrícula já cadastrados]", [
                    volta("cusu", "tel02", "409 {campo}"),
                    volta("tel02", "coord", "Marca o campo duplicado na janela"),
                ]),
                ("[dados obrigatórios faltando ou curso inválido]", [
                    volta("cusu", "tel02", "400 {campos}"),
                    volta("tel02", "coord", "Marca os campos na janela"),
                ]),
                ("[dados válidos]", [
                    chama("cusu", "Usuario", "criar(sem senha, inativo)"),
                    chama("cusu", "Docente", "criar(cargo, núcleo, curso, áreas) — se docente"),
                    chama("cusu", "Aluno", "criar(matrícula, curso) — se aluno"),
                    chama("cusu", "UsuarioPerfil", "atribuir perfis (atribuido_por = coordenação)"),
                    chama("cusu", "LogAuditoria", "registrar(criar_docente / criar_aluno) por campo"),
                    chama("cusu", "TokenUsuario", "criar(ATIVACAO, vale 48 h)"),
                    *enfileirar("cusu", "ATIVACAO"),
                    volta("cusu", "tel02", "201 {usuário, situação aguardando_ativacao}"),
                    opt("[docente com foto escolhida]", [
                        chama("tel02", "cusu", "PUT /usuarios/{id}/foto"),
                        volta("cusu", "tel02", "200"),
                    ]),
                    chama("tel02", "cusu", "GET /docentes (ou /alunos)"),
                    volta("cusu", "tel02", "lista atualizada"),
                    volta("tel02", "coord", "Fecha a janela e mostra a pessoa como \"aguardando ativação\""),
                    *email_depois("cusu", "a pessoa cadastrada", "link /ativar?token="),
                ]),
            ),
            nota("Depois, a pessoa abre o link do e-mail: DS-FL10-C.", "coord", "tel02"),
        ]),
])


# =====================================================================================
# FL11 · Turmas e matrículas
# =====================================================================================
FL11 = Fluxo("FL11", "Gerenciar turmas e matrículas",
             "SCRUM-14 RAN08 · SCRUM-42 a SCRUM-44, SCRUM-46 · tela Turmas de TCC", [
    Diagrama(
        "DS-FL11-A", "Cadastrar período letivo", "SCRUM-42 RBN08.01 · Turmas de TCC",
        "menu \"Turmas\" → Turmas de TCC (/turmas) → botão \"Novo período\" → janela Novo período letivo "
        "(código, início, fim) → botão Salvar → o período fica selecionado",
        ["coord", "turmas", "ctur", "ccat", "cusu", "deps", "PeriodoLetivo", "Turma", "LogAuditoria"],
        [
            acao("coord", "turmas", "Clicar em \"Turmas\" no menu"),
            *sessao_da_tela("turmas", "coord"),
            chama("turmas", "ctur", "GET /periodos"),
            volta("ctur", "turmas", "períodos[] (o mais recente fica selecionado)"),
            chama("turmas", "ccat", "GET /cursos"),
            chama("turmas", "cusu", "GET /docentes e GET /alunos"),
            chama("turmas", "ctur", "GET /turmas?periodo={id}"),
            volta("ctur", "turmas", "turmas do período com os alunos"),
            volta("turmas", "coord", "Exibe as turmas do período, com Novo período e Nova turma"),
            acao("coord", "turmas", "Clicar em \"Novo período\""),
            volta("turmas", "coord", "Abre a janela Novo período letivo"),
            acao("coord", "turmas", "Informar código (AAAA/N), início e fim e clicar em Salvar"),
            chama("turmas", "ctur", "POST /periodos {codigo, inicio, fim}"),
            chama("ctur", "deps", "exigir_perfil(coordenador)"),
            volta("deps", "ctur", "ok (senão 403)"),
            alt(
                ("[fim não é depois do início]", [
                    volta("ctur", "turmas", "400 {fim: deve ser depois do início}"),
                    volta("turmas", "coord", "Marca o campo Fim"),
                ]),
                ("[datas válidas]", [
                    chama("ctur", "PeriodoLetivo", "existe com este código?"),
                    volta("PeriodoLetivo", "ctur", "sim / não"),
                    alt(
                        ("[código já cadastrado]", [
                            volta("ctur", "turmas", "409 Este período letivo já existe"),
                            volta("turmas", "coord", "Marca o campo Código"),
                        ]),
                        ("[código novo]", [
                            chama("ctur", "PeriodoLetivo", "criar(codigo, inicio, fim)"),
                            chama("ctur", "LogAuditoria", "registrar(criar_periodo)"),
                            volta("ctur", "turmas", "201 {período}"),
                            chama("turmas", "ctur", "GET /turmas?periodo={novo}"),
                            volta("ctur", "turmas", "turmas[] (vazia)"),
                            volta("turmas", "coord", "Fecha a janela e seleciona o novo período"),
                        ]),
                    ),
                ]),
            ),
        ]),
    Diagrama(
        "DS-FL11", "Cadastrar turma", "SCRUM-14 RAN08 · SCRUM-42 RBN08.01 · RN24, RN26 · Turmas de TCC",
        "Turmas de TCC (/turmas) → botão \"Nova turma\" → janela Nova turma de TCC (disciplina, período, curso, "
        "professor da disciplina ou orientador responsável) → botão Salvar → a turma aparece no período",
        ["coord", "turmas", "ctur", "deps", "Curso", "PeriodoLetivo", "Docente", "Turma", "LogAuditoria"],
        [
            ref("DS-FL11-A: a coordenação está em Turmas de TCC, com o período escolhido", "coord", "ctur"),
            acao("coord", "turmas", "Clicar em \"Nova turma\""),
            volta("turmas", "coord", "Abre a janela; o rótulo do docente muda com a disciplina "
                  "(TCC1: professor da disciplina; TCC2: orientador responsável)"),
            acao("coord", "turmas", "Escolher disciplina, período, curso e docente e clicar em Salvar"),
            chama("turmas", "ctur", "POST /turmas {disciplina, curso_id, periodo_id, professor_id}"),
            chama("ctur", "deps", "exigir_perfil(coordenador)"),
            volta("deps", "ctur", "ok (senão 403)"),
            chama("ctur", "Curso", "obter(curso_id)"),
            chama("ctur", "PeriodoLetivo", "obter(periodo_id)"),
            chama("ctur", "Docente", "obter(professor_id) com perfis"),
            volta("Docente", "ctur", "docente, perfis e se está inativado"),
            alt(
                ("[curso ou período inválido, docente inativado ou sem o perfil exigido (RN26)]", [
                    volta("ctur", "turmas", "400 {campos}"),
                    volta("turmas", "coord", "Marca o campo na janela"),
                ]),
                ("[dados válidos]", [
                    chama("ctur", "Turma", "contar turmas com o mesmo prefixo"),
                    chama("ctur", "Turma", "criar(código DISCIPLINA-SIGLA-PERÍODO-n)"),
                    alt(
                        ("[já existe turma igual (curso, disciplina, período e docente)]", [
                            volta("Turma", "ctur", "violação de unicidade"),
                            volta("ctur", "turmas", "409 Já existe uma turma igual"),
                            volta("turmas", "coord", "Exibe o aviso na janela"),
                        ]),
                        ("[turma criada]", [
                            chama("ctur", "LogAuditoria", "registrar(criar_turma, código)"),
                            volta("ctur", "turmas", "201 {turma}"),
                            chama("turmas", "ctur", "GET /turmas?periodo={id}"),
                            volta("ctur", "turmas", "turmas[]"),
                            volta("turmas", "coord", "Fecha a janela e mostra a turma, pronta para receber alunos"),
                        ]),
                    ),
                ]),
            ),
        ]),
    Diagrama(
        "DS-FL11-B", "Incluir aluno na turma", "SCRUM-43 RBN08.02 · Turmas de TCC",
        "Turmas de TCC (/turmas) → no cartão da turma, lista \"Incluir aluno…\" → escolher o aluno → "
        "botão Incluir → o aluno aparece na turma como Matriculado",
        ["coord", "turmas", "ctur", "deps", "Turma", "Aluno", "MatriculaTurma", "LogAuditoria"],
        [
            ref("DS-FL11-A: a coordenação está em Turmas de TCC", "coord", "ctur"),
            acao("coord", "turmas", "Escolher o aluno em \"Incluir aluno…\" no cartão da turma e clicar em Incluir"),
            chama("turmas", "ctur", "POST /turmas/{id}/alunos {aluno_id}"),
            chama("ctur", "deps", "exigir_perfil(coordenador)"),
            volta("deps", "ctur", "ok (senão 403)"),
            chama("ctur", "Turma", "obter(id)"),
            volta("Turma", "ctur", "turma, encerrada_em, alunos"),
            alt(
                ("[turma inexistente]", [
                    volta("ctur", "turmas", "404 Turma não encontrada"),
                    volta("turmas", "coord", "Exibe o erro"),
                ]),
                ("[turma encerrada (RBN08.05)]", [
                    volta("ctur", "turmas", "409 Turma encerrada não aceita novos alunos"),
                    volta("turmas", "coord", "Exibe o erro"),
                ]),
                ("[turma aberta]", [
                    chama("ctur", "Aluno", "obter(aluno_id)"),
                    volta("Aluno", "ctur", "aluno ou vazio, inativado?"),
                    chama("ctur", "MatriculaTurma", "já está nesta turma ou em outra da mesma disciplina no período?"),
                    volta("MatriculaTurma", "ctur", "matrícula encontrada ou vazio"),
                    alt(
                        ("[aluno inexistente ou inativado]", [
                            volta("ctur", "turmas", "400 {aluno_id}"),
                            volta("turmas", "coord", "Exibe o erro"),
                        ]),
                        ("[já matriculado nesta ou em outra turma da disciplina]", [
                            volta("ctur", "turmas", "409 O aluno já está na turma X"),
                            volta("turmas", "coord", "Exibe a turma em que o aluno já está"),
                        ]),
                        ("[inclusão válida; o curso do aluno pode ser outro]", [
                            chama("ctur", "MatriculaTurma", "criar(MATRICULADO, incluido_por)"),
                            chama("ctur", "LogAuditoria", "registrar(incluir_aluno_turma)"),
                            volta("ctur", "turmas", "201 {turma com os alunos}"),
                            volta("turmas", "coord", "Mostra o aluno na turma como Matriculado"),
                        ]),
                    ),
                ]),
            ),
        ]),
    Diagrama(
        "DS-FL11-C", "Alterar a situação de matrícula", "SCRUM-44 RBN08.03 · Turmas de TCC",
        "Turmas de TCC (/turmas) → no cartão da turma, a lista de situação ao lado do aluno → escolher "
        "Matriculado, Desistente, Aprovado ou Reprovado (salva ao escolher)",
        ["coord", "turmas", "ctur", "deps", "Turma", "MatriculaTurma", "LogAuditoria"],
        [
            ref("DS-FL11-A: a coordenação está em Turmas de TCC", "coord", "ctur"),
            acao("coord", "turmas", "Escolher a nova situação na lista ao lado do aluno"),
            chama("turmas", "ctur", "PATCH /turmas/{id}/alunos/{matricula_id} {situacao}"),
            chama("ctur", "deps", "exigir_perfil(coordenador)"),
            volta("deps", "ctur", "ok (senão 403)"),
            chama("ctur", "Turma", "obter(id)"),
            volta("Turma", "ctur", "turma, encerrada_em"),
            alt(
                ("[turma inexistente]", [
                    volta("ctur", "turmas", "404 Turma não encontrada"),
                    volta("turmas", "coord", "Exibe o erro"),
                ]),
                ("[turma encerrada (RBN08.05)]", [
                    volta("ctur", "turmas", "409 Turma encerrada não aceita mudança de situação"),
                    volta("turmas", "coord", "Exibe o erro"),
                ]),
                ("[turma aberta]", [
                    chama("ctur", "MatriculaTurma", "obter(matricula_id)"),
                    volta("MatriculaTurma", "ctur", "matrícula ou vazio"),
                    alt(
                        ("[matrícula inexistente ou de outra turma]", [
                            volta("ctur", "turmas", "404 Aluno não encontrado nesta turma"),
                            volta("turmas", "coord", "Exibe o erro"),
                        ]),
                        ("[alteração válida]", [
                            opt("[situação nova diferente da atual]", [
                                chama("ctur", "LogAuditoria", "registrar(alterar_situacao_matricula, anterior, nova)"),
                                chama("ctur", "MatriculaTurma", "alterar situação e situacao_alterada_em"),
                            ]),
                            volta("ctur", "turmas", "200 {turma com os alunos}"),
                            volta("turmas", "coord", "Mostra a nova situação; nada é excluído"),
                        ]),
                    ),
                ]),
            ),
        ]),
    Diagrama(
        "DS-FL11-E", "Consultar turmas e seus alunos", "SCRUM-14 RAN08 · RN07, RN24 · Minhas turmas, Turma",
        "menu \"Minhas turmas\" (professor) ou \"Minha turma\" (aluno) → cartões das turmas → "
        "link \"Ver turma\" → Turma (/turmas/{id}) com os alunos, a situação e o TCC de cada um",
        ["professor", "minhas", "turma", "ctur", "Turma", "MatriculaTurma", "Tcc", "Orientacao"],
        [
            acao("professor", "minhas", "Clicar em \"Minhas turmas\" no menu"),
            *sessao_da_tela("minhas", "professor"),
            chama("minhas", "ctur", "GET /turmas/minhas"),
            chama("ctur", "Turma", "listar as que conduz ou em que está matriculado"),
            volta("Turma", "ctur", "turmas, com matrículas e TCCs"),
            chama("ctur", "Orientacao", "contar pedidos de orientação pendentes para mim"),
            volta("ctur", "minhas", "200 {cartões: código, período, professor, alunos, com TCC, pendentes}"),
            volta("minhas", "professor", "Exibe um cartão por turma"),
            acao("professor", "minhas", "Clicar em \"Ver turma\" no cartão"),
            chama("minhas", "turma", "ir para /turmas/{id}"),
            chama("turma", "ctur", "GET /turmas/{id}"),
            chama("ctur", "Turma", "obter(id)"),
            volta("Turma", "ctur", "turma ou vazio"),
            alt(
                ("[não é a coordenação nem o professor da turma (RN07, RN24)]", [
                    volta("ctur", "turma", "404 Turma não encontrada (não revela quem está nela)"),
                    volta("turma", "professor", "Exibe o aviso"),
                ]),
                ("[coordenação ou professor da turma]", [
                    chama("ctur", "MatriculaTurma", "listar alunos e situação"),
                    chama("ctur", "Tcc", "TCC de cada aluno, com o orientador"),
                    volta("ctur", "turma", "200 {turma, alunos, TCCs}"),
                    volta("turma", "professor", "Exibe os alunos com situação, TCC e orientação; o título leva "
                          "ao acompanhamento do TCC (TEL06)"),
                ]),
            ),
        ]),
    Diagrama(
        "DS-FL11-D", "Encerrar turma", "SCRUM-46 RBN08.05 · previsto",
        "ainda não há tela para isto. O \"Arquivar turma\" do protótipo é outra ação (a coordenação tira da lista uma "
        "turma sem alunos). Sequência prevista: o professor responsável abre a turma, clica em Encerrar turma e "
        "confirma",
        ["professor", "turma", "ctur", "Turma", "MatriculaTurma", "LogAuditoria"],
        [
            acao("professor", "turma", "Abrir a turma e clicar em Encerrar turma"),
            volta("turma", "professor", "Pede confirmação"),
            acao("professor", "turma", "Confirmar"),
            chama("turma", "ctur", "POST /turmas/{id}/encerramento"),
            chama("ctur", "Turma", "obter(id)"),
            volta("Turma", "ctur", "turma, professor responsável, encerrada_em"),
            alt(
                ("[turma inexistente ou de outro professor (RN07, RN24)]", [
                    volta("ctur", "turma", "404 Turma não encontrada"),
                    volta("turma", "professor", "Exibe o aviso"),
                ]),
                ("[já encerrada]", [
                    volta("ctur", "turma", "409 Turma já encerrada"),
                    volta("turma", "professor", "Exibe o aviso"),
                ]),
                ("[turma do professor, em aberto]", [
                    chama("ctur", "MatriculaTurma", "alunos ainda Matriculado"),
                    volta("MatriculaTurma", "ctur", "lista"),
                    alt(
                        ("[há alunos Matriculado]", [
                            volta("ctur", "turma", "422 {pendentes}"),
                            volta("turma", "professor", "Bloqueia e lista os alunos pendentes"),
                        ]),
                        ("[todos Aprovado, Reprovado ou Desistente]", [
                            chama("ctur", "Turma", "encerrar: encerrada_em = agora"),
                            chama("ctur", "LogAuditoria", "registrar(encerrar_turma)"),
                            volta("ctur", "turma", "200 {turma encerrada}"),
                            volta("turma", "professor", "Mostra a turma como Encerrada"),
                        ]),
                    ),
                ]),
            ),
        ], fonte="previsto"),
], situacao="DS-FL11-D (encerrar turma) ainda não tem rota nem tela, nem no protótipo: sequência prevista.")


# =====================================================================================
# FL01 · Cadastrar e submeter o TCC
# =====================================================================================
FL01 = Fluxo("FL01", "Cadastrar e submeter TCC", "SCRUM-10 RAN03 · SCRUM-12 RAN06 · TEL04, TEL05", [
    Diagrama(
        "DS-FL01-A", "Abrir o cadastro de TCC", "SCRUM-10 RAN03 · RN05 · RBN08.04 · TEL04 → TEL05",
        "menu \"TCCs\" → TEL04 Meu TCC (/tccs) → botão \"Cadastrar TCC\" (ou \"Continuar cadastro\", se já "
        "houver rascunho) → TEL05 Cadastro de TCC (/tccs/cadastro), passo 1 Trabalho",
        ["aluno", "tel04", "tel05", "ctcc", "MatriculaTurma", "Tcc", "Usuario", "AreaInteresse"],
        [
            acao("aluno", "tel04", "Clicar em \"TCCs\" no menu"),
            *sessao_da_tela("tel04", "aluno"),
            chama("tel04", "ctcc", "GET /tccs"),
            volta("ctcc", "tel04", "TCCs do aluno"),
            chama("tel04", "ctcc", "GET /tccs/formulario (para saber se pode cadastrar)"),
            volta("ctcc", "tel04", "200 ou 403 sem matrícula"),
            alt(
                ("[sem matrícula ativa (RN05)]", [
                    volta("tel04", "aluno", "Exibe \"Seu cadastro de TCC está bloqueado\" e o motivo"),
                ]),
                ("[matriculado]", [
                    volta("tel04", "aluno", "Exibe o botão \"Cadastrar TCC\" (ou \"Continuar cadastro\")"),
                    acao("aluno", "tel04", "Clicar em \"Cadastrar TCC\""),
                    chama("tel04", "tel05", "ir para /tccs/cadastro"),
                    chama("tel05", "ctcc", "GET /tccs/formulario"),
                    chama("ctcc", "MatriculaTurma", "obter matrícula vigente(idAluno)"),
                    volta("MatriculaTurma", "ctcc", "turma, disciplina, período e situação"),
                    chama("ctcc", "Tcc", "obter do aluno no período"),
                    volta("Tcc", "ctcc", "rascunho/devolvido ou vazio"),
                    opt("[sem TCC no período e disciplina TCC2 (RBN08.04)]", [
                        chama("ctcc", "Tcc", "obter o TCC1 do aluno"),
                        volta("Tcc", "ctcc", "título, área, modalidade e orientador aceito"),
                    ]),
                    chama("ctcc", "Usuario", "orientadores e coorientadores elegíveis (docentes ativos com perfil)"),
                    volta("Usuario", "ctcc", "orientadores[], coorientadores[]"),
                    chama("ctcc", "AreaInteresse", "listar"),
                    volta("AreaInteresse", "ctcc", "áreas[]"),
                    volta("ctcc", "tel05", "200 {turma, tcc ou origem, orientadores, áreas}"),
                    volta("tel05", "aluno", "Exibe o passo 1 Trabalho (preenchido se já houver rascunho)"),
                ]),
            ),
        ]),
    Diagrama(
        "DS-FL01-B", "Preencher e salvar o rascunho (passos 1 e 2)",
        "SCRUM-10 RAN03 · RBN03.01, RBN03.02 · RN04 · RBN06.01, RBN06.02 · TEL05",
        "TEL05 passo 1 Trabalho (título, subtítulo, resumo, palavras-chave, área, modalidade e, se artigo, os "
        "dados do artigo) → botão Continuar (salva) → passo 2 Orientação (orientador e coorientador) → botão "
        "Continuar (salva) → passo 3 Revisar e enviar. \"Salvar rascunho\" salva sem mudar de passo.",
        ["aluno", "tel05", "ctcc", "MatriculaTurma", "Tcc", "Usuario", "AreaInteresse", "HistoricoSituacao",
         "PublicacaoArtigo", "Orientacao", "LogAuditoria", "NotificacaoEmail", "iemail", "smtp"],
        [
            ref("DS-FL01-A: o aluno está no passo 1 do TEL05", "aluno", "ctcc"),
            acao("aluno", "tel05", "Preencher o passo 1 e clicar em Continuar"),
            proprio("tel05", "validar na tela: título, área e modalidade; resumo até 500 palavras"),
            alt(
                ("[falta campo obrigatório]", [
                    volta("tel05", "aluno", "Marca os campos e fica no passo 1"),
                ]),
                ("[passo 1 completo]", [
                    chama("tel05", "ctcc", "POST /tccs {dados} (primeira vez) ou PUT /tccs/{id}"),
                    chama("ctcc", "MatriculaTurma", "obter matrícula vigente(idAluno)"),
                    volta("MatriculaTurma", "ctcc", "turma e situação"),
                    alt(
                        ("[sem matrícula ativa (RN05)]", [
                            volta("ctcc", "tel05", "403 Precisa estar matriculado"),
                            volta("tel05", "aluno", "Exibe o erro"),
                        ]),
                        ("[POST e já existe cadastro no período (RN04)]", [
                            volta("ctcc", "tel05", "409 Já tem cadastro neste período"),
                            volta("tel05", "aluno", "Exibe o erro"),
                        ]),
                        ("[dados aceitos]", [
                            chama("ctcc", "AreaInteresse", "conferir área"),
                            chama("ctcc", "Tcc", "criar(RASCUNHO, sem protocolo) ou atualizar"),
                            chama("ctcc", "HistoricoSituacao", "registrar(→ RASCUNHO) — só na criação"),
                            chama("ctcc", "LogAuditoria", "registrar(criar_tcc / editar_tcc por campo)"),
                            opt("[modalidade Artigo com veículo informado]", [
                                chama("ctcc", "PublicacaoArtigo", "salvar(veículo, situação editorial, DOI)"),
                            ]),
                            volta("ctcc", "tel05", "201/200 {tcc, pendências}"),
                            volta("tel05", "aluno", "Mostra \"Rascunho salvo às HH:MM\" e o passo 2 Orientação"),
                        ]),
                    ),
                ]),
            ),
            acao("aluno", "tel05", "Escolher orientador (e coorientador, opcional) e clicar em Continuar"),
            chama("tel05", "ctcc", "PUT /tccs/{id} {dados, orientador_id, coorientador_id}"),
            chama("ctcc", "Tcc", "obter do aluno (RN07)"),
            volta("Tcc", "ctcc", "TCC (situação)"),
            chama("ctcc", "Usuario", "orientador e coorientador elegíveis e diferentes?"),
            volta("Usuario", "ctcc", "sim / não"),
            alt(
                ("[TCC fora de RASCUNHO/DEVOLVIDO]", [
                    volta("ctcc", "tel05", "409 Não pode ser editado nesta situação"),
                    volta("tel05", "aluno", "Exibe o erro"),
                ]),
                ("[orientador ou coorientador não elegível (E2)]", [
                    volta("ctcc", "tel05", "422 {orientador_id ou coorientador_id}"),
                    volta("tel05", "aluno", "Marca o campo"),
                ]),
                ("[orientador já aceitou e foi trocado]", [
                    volta("ctcc", "tel05", "409 A troca agora é feita pela coordenação"),
                    volta("tel05", "aluno", "Exibe o aviso"),
                ]),
                ("[indicação válida]", [
                    chama("ctcc", "Tcc", "atualizar campos alterados"),
                    chama("ctcc", "Orientacao", "outro pendente do mesmo papel → SUBSTITUIDA"),
                    chama("ctcc", "Orientacao", "registrar vínculo(professor, papel) → PENDENTE"),
                    chama("ctcc", "LogAuditoria", "registrar(indicar_orientacao)"),
                    *enfileirar("ctcc", "VINCULO_ORIENTACAO"),
                    volta("ctcc", "tel05", "200 {tcc com o vínculo PENDENTE e as pendências}"),
                    volta("tel05", "aluno", "Mostra o passo 3 Revisar e enviar com \"Aguarde o orientador aceitar\""),
                    *email_depois("ctcc", "o orientador indicado", "pedido de orientação (link /orientacoes)"),
                ]),
            ),
            nota("O orientador responde em TEL08 (DS-FL03-A e DS-FL03).", "aluno", "ctcc"),
        ]),
    Diagrama(
        "DS-FL01", "Enviar o cadastro para análise", "SCRUM-10 RAN03 · RBN03.03, RBN03.04, RBN03.05 · RNF06 · TEL05",
        "TEL05 passo 3 Revisar e enviar (sem pendências) → botão \"Enviar para análise\" → janela de confirmação "
        "→ botão \"Enviar para análise\" → \"Cadastro enviado para análise\" com o protocolo → botão "
        "\"Acompanhar meu TCC\" → TEL06",
        ["aluno", "tel05", "tel06", "ctcc", "Tcc", "MatriculaTurma", "Orientacao", "HistoricoSituacao",
         "LogAuditoria", "NotificacaoEmail", "iemail", "smtp"],
        [
            ref("DS-FL01-A e DS-FL01-B: o aluno chega ao passo 3; o orientador já aceitou (DS-FL03)", "aluno", "ctcc"),
            alt(
                ("[há pendências: orientador não indicado, recusou ou ainda não aceitou]", [
                    volta("tel05", "aluno", "Mostra \"Antes de enviar:\" com a lista; o botão fica desativado"),
                ]),
                ("[sem pendências]", [
                    volta("tel05", "aluno", "Mostra \"Tudo certo\" e libera \"Enviar para análise\""),
                ]),
            ),
            acao("aluno", "tel05", "Clicar em \"Enviar para análise\""),
            volta("tel05", "aluno", "Abre a janela \"Enviar cadastro para análise?\""),
            acao("aluno", "tel05", "Confirmar em \"Enviar para análise\""),
            chama("tel05", "ctcc", "POST /tccs/{id}/submissao"),
            chama("ctcc", "Tcc", "obter do aluno, com trava da linha (RN07, RNF06)"),
            volta("Tcc", "ctcc", "TCC (situação, protocolo) ou vazio"),
            alt(
                ("[TCC inexistente ou de outro aluno]", [
                    volta("ctcc", "tel05", "404 Cadastro não encontrado"),
                    volta("tel05", "aluno", "Exibe o erro"),
                ]),
                ("[já EM_ANALISE: clique repetido]", [
                    volta("ctcc", "tel05", "200 {mesmo protocolo}; nada é criado"),
                    volta("tel05", "aluno", "Mostra o protocolo"),
                ]),
                ("[situação fora de RASCUNHO/DEVOLVIDO]", [
                    volta("ctcc", "tel05", "409 Não pode ser submetido nesta situação"),
                    volta("tel05", "aluno", "Exibe o erro"),
                ]),
                ("[RASCUNHO ou DEVOLVIDO]", [
                    chama("ctcc", "MatriculaTurma", "obter matrícula vigente (RN05)"),
                    volta("MatriculaTurma", "ctcc", "situação"),
                    chama("ctcc", "Orientacao", "vínculo do orientador (para as pendências)"),
                    volta("Orientacao", "ctcc", "ACEITA, PENDENTE, RECUSADA ou vazio"),
                    alt(
                        ("[sem matrícula ativa]", [
                            volta("ctcc", "tel05", "403"),
                            volta("tel05", "aluno", "Exibe o erro"),
                        ]),
                        ("[ainda há pendências (E1, RBN03.03)]", [
                            volta("ctcc", "tel05", "422 {campos_pendentes}"),
                            volta("tel05", "aluno", "Exibe \"Ainda falta: ...\""),
                        ]),
                        ("[cadastro completo]", [
                            chama("ctcc", "Tcc", "situação EM_ANALISE, submetido_em"),
                            opt("[primeira submissão]", [
                                proprio("ctcc", "gerarProtocolo() → TCC-AAAA-nnnnn (RBN03.04)"),
                                chama("ctcc", "Tcc", "gravar protocolo"),
                            ]),
                            chama("ctcc", "HistoricoSituacao", "registrar(anterior → EM_ANALISE)"),
                            chama("ctcc", "LogAuditoria", "registrar(submeter_tcc, gerar_protocolo)"),
                            *enfileirar("ctcc", "CADASTRO_SUBMETIDO"),
                            nota("Situação, protocolo, histórico e aviso são gravados juntos (uma transação). "
                                 "No reenvio de um DEVOLVIDO o protocolo é mantido (RBN03.05).", "ctcc", "LogAuditoria"),
                            volta("ctcc", "tel05", "200 {protocolo, situação EM_ANALISE}"),
                            volta("tel05", "aluno", "Exibe \"Cadastro enviado para análise\" com o protocolo"),
                            *email_depois("ctcc", "o orientador", "cadastro submetido (protocolo)"),
                        ]),
                    ),
                ]),
            ),
            acao("aluno", "tel05", "Clicar em \"Acompanhar meu TCC\""),
            chama("tel05", "tel06", "ir para /tccs/{id}"),
            chama("tel06", "ctcc", "GET /tccs/{id}"),
            volta("ctcc", "tel06", "200 {TCC, orientação, histórico}"),
            volta("tel06", "aluno", "Exibe a situação Em análise, o protocolo e o histórico"),
        ]),
])


# =====================================================================================
# FL03 · Orientação
# =====================================================================================
FL03 = Fluxo("FL03", "Regularizar orientação", "SCRUM-12 RAN06 · SCRUM-41 RBN03.06 · SCRUM-47, SCRUM-48 · TEL05, TEL08", [
    Diagrama(
        "DS-FL03-A", "Abrir as solicitações de orientação", "SCRUM-12 RAN06 · RN07 · TEL08",
        "e-mail \"pedido de orientação\" (link) ou menu \"Orientações\" → TEL08 (/orientacoes), aba \"Aguardando resposta\": "
        "cada pedido já mostra aluno, título, resumo, área e modalidade, com Recusar e Aceitar orientação",
        ["orientador", "tel08", "tel06", "ctcc", "deps", "Orientacao", "Tcc"],
        [
            acao("orientador", "tel08", "Clicar em \"Orientações\" no menu (ou no link do e-mail)"),
            *sessao_da_tela("tel08", "orientador"),
            chama("tel08", "ctcc", "GET /orientacoes?status=PENDENTE"),
            chama("ctcc", "deps", "exigir_perfil(orientador ou professor da disciplina)"),
            volta("deps", "ctcc", "ok (senão 403)"),
            chama("ctcc", "Orientacao", "listar do orientador (status PENDENTE, não encerrados)"),
            volta("Orientacao", "ctcc", "vínculos com papel, status e data"),
            chama("ctcc", "Tcc", "dados de cada TCC: aluno, título, resumo, área, modalidade"),
            volta("ctcc", "tel08", "200 {solicitações}"),
            volta("tel08", "orientador", "Exibe os pedidos pendentes, cada um com Recusar e Aceitar orientação"),
            opt("[ver o cadastro completo]", [
                acao("orientador", "tel08", "Clicar em \"Ver cadastro\" no pedido"),
                chama("tel08", "tel06", "ir para /tccs/{id}"),
                chama("tel06", "ctcc", "GET /tccs/{id}"),
                volta("ctcc", "tel06", "200 (quem foi indicado pode ver, RN07)"),
                volta("tel06", "orientador", "Exibe os dados do trabalho e a orientação"),
            ]),
            opt("[ver os já respondidos]", [
                acao("orientador", "tel08", "Clicar na aba \"Respondidas\""),
                chama("tel08", "ctcc", "GET /orientacoes"),
                volta("ctcc", "tel08", "todos os vínculos"),
                volta("tel08", "orientador", "Exibe os aceitos e recusados"),
            ]),
        ]),
    Diagrama(
        "DS-FL03", "Orientador aceita ou recusa", "SCRUM-12 RAN06 · RBN06.03 · RBN03.06 · TEL08",
        "TEL08 Orientações, aba \"Aguardando resposta\" → botão \"Aceitar orientação\"; ou botão \"Recusar\" → janela "
        "Recusar orientação com o Motivo → botão \"Recusar pedido\" → aviso de sucesso e o pedido sai da lista",
        ["orientador", "tel08", "ctcc", "Orientacao", "Tcc", "LogAuditoria", "NotificacaoEmail", "iemail", "smtp"],
        [
            ref("DS-FL03-A: o orientador está em TEL08 com os pedidos pendentes", "orientador", "ctcc"),
            alt(
                ("[aceitar]", [
                    acao("orientador", "tel08", "Clicar em \"Aceitar orientação\""),
                    chama("tel08", "ctcc", "POST /orientacoes/{id}/resposta {decisao: ACEITAR}"),
                ]),
                ("[recusar]", [
                    acao("orientador", "tel08", "Clicar em \"Recusar\""),
                    volta("tel08", "orientador", "Abre a janela Recusar orientação"),
                    acao("orientador", "tel08", "Escrever o motivo e clicar em \"Recusar pedido\""),
                    proprio("tel08", "motivo em branco? pede o motivo e não envia"),
                    chama("tel08", "ctcc", "POST /orientacoes/{id}/resposta {decisao: RECUSAR, motivo}"),
                ]),
            ),
            chama("ctcc", "Orientacao", "obter(id)"),
            volta("Orientacao", "ctcc", "vínculo (professor, status) ou vazio"),
            alt(
                ("[inexistente ou de outro professor (RN07)]", [
                    volta("ctcc", "tel08", "404 Solicitação não encontrada"),
                    volta("tel08", "orientador", "Exibe o erro"),
                ]),
                ("[já respondida]", [
                    volta("ctcc", "tel08", "409 Esta solicitação já foi respondida"),
                    volta("tel08", "orientador", "Exibe o erro"),
                ]),
                ("[recusa sem motivo]", [
                    volta("ctcc", "tel08", "400 {motivo}"),
                    volta("tel08", "orientador", "Marca o campo Motivo na janela"),
                ]),
                ("[resposta válida]", [
                    chama("ctcc", "Orientacao", "status ACEITA ou RECUSADA (com motivo), respondido_em"),
                    chama("ctcc", "LogAuditoria", "registrar(responder_orientacao)"),
                    chama("ctcc", "Tcc", "obter o aluno do TCC"),
                    volta("Tcc", "ctcc", "aluno (nome, e-mail)"),
                    *enfileirar("ctcc", "ORIENTACAO_ACEITA ou ORIENTACAO_RECUSADA"),
                    volta("ctcc", "tel08", "200 {status}"),
                    chama("tel08", "ctcc", "GET /orientacoes?status=PENDENTE"),
                    volta("ctcc", "tel08", "pendentes restantes"),
                    volta("tel08", "orientador", "Exibe \"Orientação aceita\" ou \"Solicitação recusada\"; o pedido sai "
                          "da lista"),
                    *email_depois("ctcc", "o aluno", "orientação aceita / recusada com o motivo"),
                ]),
            ),
            nota("Com a recusa, o aluno indica outro orientador (DS-FL03-B). Com o aceite, o aluno pode enviar "
                 "o cadastro (DS-FL01).", "orientador", "ctcc"),
        ]),
    Diagrama(
        "DS-FL03-B", "Aluno indica outro orientador depois da recusa",
        "SCRUM-47 RBN06.01 · SCRUM-48 RBN06.02 · TEL04, TEL05",
        "e-mail \"orientação recusada\" → menu \"TCCs\" → TEL04 Meu TCC (selo Recusada) → botão \"Continuar "
        "cadastro\" → TEL05 passo 1 → Continuar → passo 2 Orientação (mostra o motivo da recusa) → escolher "
        "outro orientador → Continuar",
        ["aluno", "tel04", "tel05", "ctcc", "Tcc", "Usuario", "Orientacao", "LogAuditoria", "NotificacaoEmail",
         "iemail", "smtp"],
        [
            acao("aluno", "tel04", "Clicar em \"TCCs\" no menu"),
            chama("tel04", "ctcc", "GET /tccs e GET /tccs/formulario"),
            volta("ctcc", "tel04", "TCC em RASCUNHO com o orientador RECUSADA"),
            volta("tel04", "aluno", "Exibe o TCC com os selos Rascunho e Recusada e o botão \"Continuar cadastro\""),
            acao("aluno", "tel04", "Clicar em \"Continuar cadastro\""),
            ref("DS-FL01-A: TEL05 abre com o rascunho no passo 1", "aluno", "ctcc"),
            acao("aluno", "tel05", "Clicar em Continuar no passo 1"),
            chama("tel05", "ctcc", "PUT /tccs/{id} (salva o passo 1)"),
            volta("ctcc", "tel05", "200"),
            volta("tel05", "aluno", "Exibe o passo 2 com o orientador anterior, o selo Recusada e o motivo"),
            acao("aluno", "tel05", "Escolher outro orientador (ou o coorientador) e clicar em Continuar"),
            chama("tel05", "ctcc", "PUT /tccs/{id} {orientador_id, coorientador_id}"),
            chama("ctcc", "Tcc", "obter do aluno (RN07)"),
            chama("ctcc", "Usuario", "elegível e diferente do outro vínculo? (E1, RBN06.02)"),
            volta("Usuario", "ctcc", "sim / não"),
            alt(
                ("[não elegível ou igual ao outro vínculo]", [
                    volta("ctcc", "tel05", "422 {orientador_id ou coorientador_id}"),
                    volta("tel05", "aluno", "Marca o campo"),
                ]),
                ("[indicação válida]", [
                    chama("ctcc", "Orientacao", "registrar vínculo(professor, papel) → PENDENTE (RN16)"),
                    chama("ctcc", "LogAuditoria", "registrar(indicar_orientacao)"),
                    *enfileirar("ctcc", "VINCULO_ORIENTACAO"),
                    volta("ctcc", "tel05", "200 {tcc com o novo vínculo PENDENTE}"),
                    volta("tel05", "aluno", "Exibe o passo 3 com \"Aguarde o orientador aceitar\""),
                    *email_depois("ctcc", "o novo orientador", "pedido de orientação"),
                ]),
            ),
            nota("A rota POST /tccs/{id}/orientacoes também registra a indicação, mas nenhuma tela a usa: "
                 "a tela de cadastro indica o orientador pelo PUT /tccs/{id}.", "tel05", "Orientacao"),
        ]),
    Diagrama(
        "DS-FL03-C", "Coordenação substitui o orientador", "RN16 · previsto",
        "ainda não há tela para isto, nem no sistema nem no protótipo. Sequência prevista: a coordenação abre o "
        "acompanhamento do TCC (TEL06), escolhe o novo orientador, escreve a justificativa e confirma",
        ["coord", "tel06", "ctcc", "Tcc", "Usuario", "Orientacao", "LogAuditoria", "NotificacaoEmail", "iemail",
         "smtp"],
        [
            acao("coord", "tel06", "Abrir o TCC e clicar em \"Substituir orientador\""),
            volta("tel06", "coord", "Abre a janela com os orientadores elegíveis e a justificativa"),
            acao("coord", "tel06", "Escolher o novo orientador, escrever a justificativa e confirmar"),
            chama("tel06", "ctcc", "POST /tccs/{id}/orientacoes/substituicao {professor_id, justificativa}"),
            chama("ctcc", "Tcc", "obter(id)"),
            chama("ctcc", "Orientacao", "vínculo ativo do orientador"),
            chama("ctcc", "Usuario", "novo orientador elegível?"),
            alt(
                ("[justificativa em branco]", [
                    volta("ctcc", "tel06", "400 {justificativa}"),
                    volta("tel06", "coord", "Marca o campo"),
                ]),
                ("[não elegível ou igual ao atual]", [
                    volta("ctcc", "tel06", "422 {professor_id}"),
                    volta("tel06", "coord", "Marca o campo"),
                ]),
                ("[troca válida]", [
                    chama("ctcc", "Orientacao", "encerrar o atual → SUBSTITUIDA, com a justificativa"),
                    chama("ctcc", "Orientacao", "registrar o novo → PENDENTE"),
                    chama("ctcc", "LogAuditoria", "registrar(substituir_orientador)"),
                    loop("[aluno, orientador anterior e novo orientador]", enfileirar("ctcc", "SUBSTITUICAO_ORIENTADOR")),
                    volta("ctcc", "tel06", "200 {novo vínculo PENDENTE}"),
                    volta("tel06", "coord", "Mostra a troca; o vínculo anterior fica no histórico"),
                    *email_depois("ctcc", "os três envolvidos", "substituição de orientador"),
                ]),
            ),
        ], fonte="previsto"),
], situacao="DS-FL03-C (substituir orientador) ainda não tem rota nem tela, nem no protótipo: sequência prevista.")


# =====================================================================================
# Daqui para baixo: ainda não implementado. A sequência segue as telas do protótipo
# (docs/prototipos/SIGA UEA — Protótipo.html); as rotas da API e as entidades são as planejadas na análise
# e no modelo lógico (página Planejado do diagrama de classes).
# =====================================================================================


def abrir_tcc(ator: str) -> list:
    """Entrar no espaço do TCC (TEL04 e TEL06 já existem no sistema)."""
    return [ref("menu \"TCCs\" (TEL04) → abrir o TCC → espaço do TCC (TEL06): capa, próximo passo e abas",
                ator, "tel06")]


def aba(ator: str, tela: str, nome: str) -> list:
    return [acao(ator, "tel06", f"Clicar na aba {nome}"), chama("tel06", tela, f"abrir {nome}")]


# =====================================================================================
# FL02 · Análise do cadastro pela coordenação
# =====================================================================================
FL02 = Fluxo("FL02", "Analisar cadastro", "SCRUM-2 RAN04 · SCRUM-3 RBN04.01 · SCRUM-7 RBN04.05 · SCRUM-40 RBN03.05 · TEL07", [
    Diagrama(
        "DS-FL02-A", "Abrir a fila e examinar um cadastro", "SCRUM-3 RBN04.01 · RN07 · TEL07",
        "menu \"Análise de cadastros\" (com o número dos que aguardam) → TEL07, aba \"Aguardando análise\", do mais "
        "antigo para o mais recente → filtro Curso → clicar num cadastro → painel com os dados, \"Abrir PDF\", "
        "Parecer e os botões Aprovar cadastro, Devolver para correção e Reprovar",
        ["coord", "tel07", "cana", "Tcc", "DocumentoTcc", "AnaliseCadastro"],
        [
            acao("coord", "tel07", "Clicar em \"Análise de cadastros\" no menu"),
            chama("tel07", "cana", "GET /cadastros?situacao=EM_ANALISE"),
            chama("cana", "Tcc", "listar EM_ANALISE dos cursos da coordenação (RN07), mais antigo primeiro"),
            volta("Tcc", "cana", "protocolo, aluno, curso, etapa, enviado em"),
            volta("cana", "tel07", "200 {fila}"),
            alt(
                ("[fila vazia]", [volta("tel07", "coord", "Exibe \"Nenhum cadastro aguardando análise\"")]),
                ("[há cadastros]", [volta("tel07", "coord", "Exibe a fila com há quantos dias cada um aguarda")]),
            ),
            opt("[filtrar por curso]", [
                acao("coord", "tel07", "Escolher o curso no filtro"),
                chama("tel07", "cana", "GET /cadastros?situacao=EM_ANALISE&curso={curso}"),
                volta("cana", "tel07", "200 {fila do curso}"),
                volta("tel07", "coord", "Exibe a fila filtrada"),
            ]),
            acao("coord", "tel07", "Clicar num cadastro da fila"),
            chama("tel07", "cana", "GET /cadastros/{idTcc}"),
            chama("cana", "Tcc", "obter(idTcc)"),
            volta("Tcc", "cana", "dados, situação e protocolo"),
            chama("cana", "DocumentoTcc", "versão preliminar vigente"),
            volta("DocumentoTcc", "cana", "PDF ou vazio"),
            alt(
                ("[já decidido por outra pessoa]", [
                    chama("cana", "AnaliseCadastro", "última decisão"),
                    volta("AnaliseCadastro", "cana", "resultado, parecer, quem e quando"),
                    volta("cana", "tel07", "200 {dados, decisão registrada}"),
                    volta("tel07", "coord", "Exibe a decisão registrada, sem os botões"),
                ]),
                ("[EM_ANALISE]", [
                    volta("cana", "tel07", "200 {dados, PDF}"),
                    volta("tel07", "coord", "Exibe autor, curso, modalidade, orientador, resumo, o PDF, o campo Parecer e "
                          "os botões Aprovar cadastro, Devolver para correção e Reprovar"),
                ]),
            ),
            opt("[ler o PDF]", [
                acao("coord", "tel07", "Clicar em \"Abrir PDF\""),
                chama("tel07", "cana", "GET /cadastros/{idTcc}/documento"),
                volta("cana", "tel07", "arquivo PDF"),
            ]),
            opt("[ver os já analisados]", [
                acao("coord", "tel07", "Clicar na aba \"Já analisados\""),
                chama("tel07", "cana", "GET /cadastros?situacao=APROVADO,DEVOLVIDO,REPROVADO"),
                volta("cana", "tel07", "200 {cadastros com resultado e parecer}"),
                volta("tel07", "coord", "Exibe a tabela com protocolo, trabalho e resultado"),
            ]),
        ], fonte="prototipo"),
    Diagrama(
        "DS-FL02", "Aprovar, devolver ou reprovar o cadastro", "SCRUM-2 RAN04 · RBN04.02 a RBN04.05 · TEL07",
        "TEL07, cadastro aberto → escrever o Parecer (obrigatório para devolver ou reprovar) → botão Aprovar cadastro, "
        "Devolver para correção ou Reprovar → janela de confirmação → o próximo da fila abre sozinho",
        ["coord", "tel07", "cana", "Tcc", "AnaliseCadastro", "HistoricoSituacao", "Orientacao", "LogAuditoria",
         "NotificacaoEmail", "iemail", "smtp"],
        [
            ref("DS-FL02-A: o cadastro está aberto em TEL07", "coord", "cana"),
            acao("coord", "tel07", "Escrever o parecer e clicar em Aprovar cadastro, Devolver para correção ou Reprovar"),
            proprio("tel07", "devolver ou reprovar com parecer de menos de 10 caracteres?"),
            alt(
                ("[falta o parecer]", [volta("tel07", "coord", "Marca o campo Parecer e não continua")]),
                ("[pode continuar]", [volta("tel07", "coord", "Abre a janela \"Aprovar este cadastro?\", \"Devolver para "
                                            "correção?\" ou \"Reprovar este cadastro?\"")]),
            ),
            acao("coord", "tel07", "Confirmar na janela"),
            chama("tel07", "cana", "POST /cadastros/{idTcc}/decisao {resultado, parecer}"),
            chama("cana", "Tcc", "obter(idTcc) com trava da linha"),
            volta("Tcc", "cana", "situação"),
            alt(
                ("[usuário sem perfil Coordenação (RN06)]", [
                    volta("cana", "tel07", "403"),
                    volta("tel07", "coord", "Exibe o erro"),
                ]),
                ("[já não está EM_ANALISE: outra pessoa decidiu (E2)]", [
                    chama("cana", "AnaliseCadastro", "última decisão"),
                    volta("cana", "tel07", "409 {decisão já registrada}"),
                    volta("tel07", "coord", "Exibe a decisão existente e atualiza a fila"),
                ]),
                ("[devolver ou reprovar sem parecer (E1)]", [
                    volta("cana", "tel07", "422 {parecer}"),
                    volta("tel07", "coord", "Marca o campo Parecer"),
                ]),
                ("[decisão válida]", [
                    chama("cana", "AnaliseCadastro", "registrar(resultado, parecer, coordenação, data)"),
                    chama("cana", "Tcc", "situação APROVADO, DEVOLVIDO ou REPROVADO; protocolo mantido"),
                    chama("cana", "HistoricoSituacao", "registrar(EM_ANALISE → nova situação)"),
                    chama("cana", "LogAuditoria", "registrar(decidir_cadastro)"),
                    chama("cana", "Orientacao", "orientador do TCC"),
                    volta("Orientacao", "cana", "orientador"),
                    loop("[aluno e orientador (RBN04.05)]", enfileirar("cana", "RESULTADO_ANALISE")),
                    volta("cana", "tel07", "200 {resultado, parecer, data}"),
                    volta("tel07", "coord", "Mostra \"Cadastro aprovado/devolvido/reprovado. Próximo da fila: ...\" e abre "
                          "o próximo"),
                    *email_depois("cana", "o aluno e o orientador", "resultado da análise com o parecer"),
                ]),
            ),
            nota("Aprovar o cadastro não aprova a defesa nem o artigo (aviso na própria tela).", "coord", "cana"),
        ], fonte="prototipo"),
    Diagrama(
        "DS-FL02-B", "Aluno lê o parecer e, se devolvido, corrige e reenvia",
        "SCRUM-7 RBN04.05 · SCRUM-40 RBN03.05 · TEL04, TEL06, TEL05",
        "e-mail com o resultado ou menu \"TCCs\" → TEL04 Meu TCC → abrir o TCC → TEL06 mostra o aviso \"Parecer da "
        "Coordenação\" e o próximo passo → botão \"Corrigir cadastro\" → TEL05 com \"Cadastro devolvido para "
        "correção\" → passos 1 a 3 → Enviar para análise",
        ["aluno", "tel04", "tel06", "tel05", "ctcc", "Tcc", "AnaliseCadastro", "HistoricoSituacao"],
        [
            acao("aluno", "tel04", "Clicar em \"TCCs\" no menu"),
            chama("tel04", "ctcc", "GET /tccs"),
            volta("ctcc", "tel04", "TCC com a situação nova"),
            volta("tel04", "aluno", "Exibe o TCC com o selo Devolvido, Aprovado ou Reprovado"),
            acao("aluno", "tel04", "Clicar no TCC"),
            chama("tel04", "tel06", "ir para /tccs/{id}"),
            chama("tel06", "ctcc", "GET /tccs/{id}"),
            chama("ctcc", "Tcc", "obter do aluno (RN07)"),
            chama("ctcc", "AnaliseCadastro", "decisões com o parecer"),
            chama("ctcc", "HistoricoSituacao", "tramitação em ordem (RBN05.04)"),
            volta("ctcc", "tel06", "200 {TCC, parecer, histórico}"),
            alt(
                ("[DEVOLVIDO]", [
                    volta("tel06", "aluno", "Exibe o aviso \"Parecer da Coordenação\" e o próximo passo com o botão "
                          "\"Corrigir cadastro\""),
                    acao("aluno", "tel06", "Clicar em \"Corrigir cadastro\""),
                    chama("tel06", "tel05", "ir para /tccs/cadastro"),
                    ref("DS-FL01-A, DS-FL01-B e DS-FL01: TEL05 mostra \"Cadastro devolvido para correção\"; ao reenviar, "
                        "o protocolo é mantido e a situação volta a EM_ANALISE (RBN03.05)", "aluno", "ctcc"),
                ]),
                ("[APROVADO]", [
                    volta("tel06", "aluno", "Exibe \"Cadastro aprovado. O orientador vai compor a banca e agendar a defesa\""),
                ]),
                ("[REPROVADO]", [
                    volta("tel06", "aluno", "Exibe o parecer e \"Procure a Coordenação\""),
                ]),
            ),
        ], fonte="prototipo"),
], situacao="Ainda não implementado: segue as telas do protótipo (TEL07). TEL04, TEL05 e TEL06 já existem no sistema.")


# =====================================================================================
# FL04 · Banca e agendamento da defesa
# =====================================================================================
FL04 = Fluxo("FL04", "Compor a banca e agendar a defesa",
             "SCRUM-15 RAN09 · SCRUM-59 a SCRUM-63 · SCRUM-32 RBN01.12 · RN14 · TEL10, TEL11", [
    Diagrama(
        "DS-FL04-A", "Compor a banca", "SCRUM-59 RBN09.01 · SCRUM-60 RBN09.02 · RN12, RN14, RN20 · TEL10",
        "TCCs → abrir o TCC → aba Banca → vagas Avaliador 1, Avaliador 2, Orientador (já preenchido), Coorientador e "
        "Suplente → botão \"Adicionar\" na vaga → Docente da UEA ou Convidado externo → \"Adicionar à banca\" → com os "
        "3 obrigatórios, aparece \"Banca completa\" e o botão \"Agendar defesa\"",
        ["orientador", "tel06", "tel10", "cagd", "Tcc", "Usuario", "BancaMembro", "LogAuditoria"],
        [
            *abrir_tcc("orientador"),
            *aba("orientador", "tel10", "\"Banca\""),
            chama("tel10", "cagd", "GET /tccs/{idTcc}/banca"),
            chama("cagd", "Tcc", "situação e curso"),
            chama("cagd", "BancaMembro", "membros já incluídos"),
            volta("cagd", "tel10", "200 {vagas, membros, pode editar}"),
            alt(
                ("[cadastro ainda não aprovado]", [
                    volta("tel10", "orientador", "Exibe \"Etapa ainda não liberada\" (a aba fica com cadeado)"),
                ]),
                ("[neste curso quem compõe é outro perfil (RN14)]", [
                    volta("tel10", "orientador", "Exibe as vagas em somente leitura"),
                ]),
                ("[pode compor]", [
                    volta("tel10", "orientador", "Exibe as vagas e \"x de 3 membros obrigatórios\""),
                ]),
            ),
            acao("orientador", "tel10", "Clicar em \"Adicionar\" numa vaga"),
            volta("tel10", "orientador", "Abre o formulário na vaga: Docente da UEA ou Convidado externo"),
            alt(
                ("[Docente da UEA]", [
                    acao("orientador", "tel10", "Escolher o docente na lista e clicar em \"Adicionar à banca\""),
                    chama("tel10", "cagd", "POST /tccs/{idTcc}/banca {papel, idDocente}"),
                    chama("cagd", "Usuario", "docente ativo?"),
                ]),
                ("[Convidado externo]", [
                    ref("DS-FL04-B: nome, e-mail e instituição do convidado externo", "orientador", "cagd"),
                ]),
            ),
            chama("cagd", "BancaMembro", "a pessoa já está na banca?"),
            volta("BancaMembro", "cagd", "sim / não"),
            alt(
                ("[pessoa repetida (RBN09.02)]", [
                    volta("cagd", "tel10", "422 {esta pessoa já faz parte da banca}"),
                    volta("tel10", "orientador", "Marca o campo na vaga"),
                ]),
                ("[membro válido]", [
                    chama("cagd", "BancaMembro", "incluir(papel, convite não enviado)"),
                    chama("cagd", "LogAuditoria", "registrar(incluir_membro_banca)"),
                    volta("cagd", "tel10", "201 {membro}"),
                    volta("tel10", "orientador", "Mostra o membro na vaga com \"Convite não enviado\" e atualiza a contagem"),
                ]),
            ),
            opt("[remover um membro]", [
                acao("orientador", "tel10", "Clicar em \"Remover\" na vaga"),
                chama("tel10", "cagd", "DELETE /tccs/{idTcc}/banca/{idMembro}"),
                chama("cagd", "BancaMembro", "remover"),
                volta("cagd", "tel10", "200"),
                volta("tel10", "orientador", "Esvazia a vaga, com \"Desfazer\""),
            ]),
            opt("[2 avaliadores e o orientador preenchidos (RN12)]", [
                volta("tel10", "orientador", "Mostra \"Banca completa\" e o botão \"Agendar defesa\" (DS-FL04)"),
            ]),
            nota("Os convites só saem quando a defesa é confirmada (DS-FL04). O suplente não conta para o quórum (RN20).",
                 "orientador", "cagd"),
        ], fonte="prototipo"),
    Diagrama(
        "DS-FL04-B", "Adicionar convidado externo à banca", "SCRUM-59 RBN09.01 · SCRUM-32 RBN01.12 · TEL10",
        "TEL10 Banca → \"Adicionar\" na vaga → opção \"Convidado externo\" → nome, e-mail e instituição → "
        "\"Adicionar à banca\" (a tela avisa que será criada uma conta limitada a esta defesa)",
        ["orientador", "tel10", "cagd", "UsuarioExterno", "Usuario", "AcessoLimitado", "BancaMembro"],
        [
            acao("orientador", "tel10", "Escolher \"Convidado externo\""),
            volta("tel10", "orientador", "Mostra Nome, E-mail e Instituição e o aviso da conta limitada"),
            acao("orientador", "tel10", "Informar nome, e-mail e instituição e clicar em \"Adicionar à banca\""),
            proprio("tel10", "nome, e-mail válido e instituição preenchidos?"),
            alt(
                ("[campo faltando ou e-mail inválido]", [volta("tel10", "orientador", "Marca os campos")]),
                ("[campos ok]", [
                    chama("tel10", "cagd", "POST /tccs/{idTcc}/banca {papel, nome, email, instituicao}"),
                    chama("cagd", "Usuario", "já existe conta com este e-mail?"),
                    volta("Usuario", "cagd", "usuário ou vazio"),
                    opt("[e-mail novo]", [
                        chama("cagd", "Usuario", "criar(sem senha) — conta limitada"),
                        chama("cagd", "UsuarioExterno", "criar(instituição)"),
                    ]),
                    chama("cagd", "AcessoLimitado", "criar(BANCA, idTcc, vale até a defesa)"),
                    chama("cagd", "BancaMembro", "incluir(papel, externo, convite não enviado)"),
                    volta("cagd", "tel10", "201 {membro externo}"),
                    volta("tel10", "orientador", "Mostra o convidado na vaga, como externo e com a instituição"),
                ]),
            ),
            nota("O link de acesso vai junto com o convite, quando a defesa for confirmada (DS-FL04).",
                 "orientador", "cagd"),
        ], fonte="prototipo"),
    Diagrama(
        "DS-FL04", "Agendar a defesa", "SCRUM-61 a SCRUM-63 · RBN09.03 a RBN09.05 · RN14, RN19 · TEL11",
        "TEL10 → botão \"Agendar defesa\" → aba Defesa › Agendamento → \"Condições para agendar\" → passo 1 Quando "
        "(data, início, término) → Continuar → passo 2 Onde (presencial, remoto ou híbrido; local e/ou link) → "
        "Continuar → passo 3 Conferir (conflitos) → \"Confirmar defesa\" → janela → \"Confirmar e enviar convites\"",
        ["orientador", "tel10", "tel11", "cagd", "Tcc", "DocumentoTcc", "BancaMembro", "Defesa", "LocalDefesa",
         "HistoricoDefesa", "LogAuditoria", "NotificacaoEmail", "iemail", "smtp"],
        [
            ref("DS-FL04-A: banca completa em TEL10", "orientador", "cagd"),
            acao("orientador", "tel10", "Clicar em \"Agendar defesa\""),
            chama("tel10", "tel11", "abrir Defesa › Agendamento"),
            chama("tel11", "cagd", "GET /tccs/{idTcc}/defesa"),
            chama("cagd", "Tcc", "cadastro aprovado?"),
            chama("cagd", "DocumentoTcc", "versão para banca enviada?"),
            chama("cagd", "BancaMembro", "banca completa?"),
            volta("cagd", "tel11", "200 {condições, defesa atual}"),
            alt(
                ("[condição pendente]", [
                    volta("tel11", "orientador", "Mostra \"Condições para agendar\" com o que falta e os botões \"Compor "
                          "banca\" ou \"Ver documentos\"; o formulário fica bloqueado"),
                ]),
                ("[condições atendidas]", [
                    volta("tel11", "orientador", "Mostra o passo 1 \"Quando será a defesa?\" e a duração prevista"),
                ]),
            ),
            acao("orientador", "tel11", "Informar data, início e término e clicar em Continuar"),
            proprio("tel11", "data não passada e término depois do início?"),
            volta("tel11", "orientador", "Mostra o passo 2 \"Onde será a defesa?\""),
            acao("orientador", "tel11", "Escolher o formato, informar local e/ou link e clicar em Continuar"),
            proprio("tel11", "local para presencial/híbrido; link https:// para remoto/híbrido?"),
            chama("tel11", "cagd", "GET /defesas/conflitos?data&inicio&fim&local&idTcc"),
            chama("cagd", "LocalDefesa", "local ocupado no horário?"),
            chama("cagd", "Defesa", "membros da banca em outra defesa no horário?"),
            volta("cagd", "tel11", "200 {conflitos[]}"),
            alt(
                ("[há conflito (RBN09.04)]", [
                    volta("tel11", "orientador", "Mostra o passo 3 com \"Há conflito neste horário\"; Confirmar desativado"),
                ]),
                ("[sem conflito]", [
                    volta("tel11", "orientador", "Mostra o passo 3 \"Confira e confirme\" e \"Nenhum conflito conhecido\""),
                ]),
            ),
            acao("orientador", "tel11", "Clicar em \"Confirmar defesa\""),
            volta("tel11", "orientador", "Abre a janela \"Confirmar a defesa?\""),
            acao("orientador", "tel11", "Clicar em \"Confirmar e enviar convites\""),
            chama("tel11", "cagd", "POST /tccs/{idTcc}/defesa {formato, data, inicio, fim, local, link}"),
            chama("cagd", "Tcc", "obter e conferir quem agenda neste curso (RN14)"),
            alt(
                ("[sem permissão (RN14)]", [
                    volta("cagd", "tel11", "403"),
                    volta("tel11", "orientador", "Exibe o erro"),
                ]),
                ("[surgiu conflito ou condição deixou de valer]", [
                    volta("cagd", "tel11", "409 {conflitos[] ou condição}"),
                    volta("tel11", "orientador", "Volta ao passo 3 com o conflito"),
                ]),
                ("[agendamento válido]", [
                    chama("cagd", "Defesa", "criar(CONFIRMADA, não publicada, instrumento vigente RN19)"),
                    chama("cagd", "HistoricoDefesa", "registrar(AGENDAMENTO)"),
                    chama("cagd", "BancaMembro", "convites → pendente"),
                    chama("cagd", "LogAuditoria", "registrar(agendar_defesa)"),
                    loop("[cada membro da banca (RBN09.05)]", enfileirar("cagd", "CONVITE_BANCA")),
                    volta("cagd", "tel11", "201 {defesa}"),
                    volta("tel11", "orientador", "Mostra \"Defesa confirmada\": data, formato, local, \"Não publicada\" e "
                          "os botões Remarcar e Cancelar defesa"),
                    *email_depois("cagd", "cada membro da banca", "convite com data, local ou link"),
                ]),
            ),
        ], fonte="prototipo"),
], situacao="Ainda não implementado: segue as telas do protótipo (aba Banca e aba Defesa › Agendamento).")


# =====================================================================================
# FL05 · Agenda e mudanças na defesa
# =====================================================================================
FL05 = Fluxo("FL05", "Agenda e mudanças na defesa", "SCRUM-64 a SCRUM-68 · RBN09.06 a RBN09.09 · RBN14.01 a RBN14.03 · TEL11, TEL17, TEL18", [
    Diagrama(
        "DS-FL05", "Publicar a defesa na agenda", "RN09 · RBN14.01 · TEL18",
        "TCCs → abrir o TCC → aba Defesa › \"Divulgação na agenda\" → \"Condições para publicar\" e \"Como aparece na "
        "agenda\" → botão \"Publicar na agenda\" → janela → \"Publicar\"; depois, \"Retirar da agenda\"",
        ["orientador", "tel06", "tel18", "cage", "Defesa", "Tcc", "HistoricoDefesa", "LogAuditoria"],
        [
            *abrir_tcc("orientador"),
            *aba("orientador", "tel18", "Defesa › \"Divulgação na agenda\""),
            chama("tel18", "cage", "GET /defesas/{idDefesa}/divulgacao"),
            chama("cage", "Defesa", "obter: situação, data, local, link, autorização do aluno"),
            chama("cage", "Tcc", "título, aluno, curso, etapa"),
            volta("cage", "tel18", "200 {condições, prévia, publicada}"),
            alt(
                ("[defesa cancelada]", [volta("tel18", "orientador", "Exibe \"Esta defesa foi cancelada\"")]),
                ("[não é o responsável nem a coordenação]", [volta("tel18", "orientador", "Exibe somente leitura")]),
                ("[pode publicar]", [volta("tel18", "orientador", "Exibe as condições, a prévia sem dados pessoais e o botão "
                                           "Publicar na agenda (liberado com todas atendidas)")]),
            ),
            acao("orientador", "tel18", "Clicar em \"Publicar na agenda\""),
            volta("tel18", "orientador", "Abre a janela \"Publicar na agenda?\""),
            acao("orientador", "tel18", "Clicar em \"Publicar\""),
            chama("tel18", "cage", "POST /defesas/{idDefesa}/publicacao"),
            alt(
                ("[condição pendente (RN09)]", [
                    volta("cage", "tel18", "422 {pendências}"),
                    volta("tel18", "orientador", "Exibe o que falta"),
                ]),
                ("[pode publicar]", [
                    chama("cage", "Defesa", "publicada = sim"),
                    chama("cage", "HistoricoDefesa", "registrar(PUBLICACAO)"),
                    chama("cage", "LogAuditoria", "registrar(publicar_agenda)"),
                    volta("cage", "tel18", "200 {publicada}"),
                    volta("tel18", "orientador", "Mostra \"Publicada\" e o botão \"Retirar da agenda\""),
                ]),
            ),
            opt("[retirar da agenda]", [
                acao("orientador", "tel18", "Clicar em \"Retirar da agenda\""),
                volta("tel18", "orientador", "Abre a janela: \"A defesa continua marcada\""),
                acao("orientador", "tel18", "Confirmar"),
                chama("tel18", "cage", "POST /defesas/{idDefesa}/retirada"),
                chama("cage", "Defesa", "publicada = não"),
                chama("cage", "HistoricoDefesa", "registrar(RETIRADA)"),
                volta("cage", "tel18", "200"),
                volta("tel18", "orientador", "Mostra \"Não publicada\"; a defesa continua marcada"),
            ]),
        ], fonte="prototipo"),
    Diagrama(
        "DS-FL05-A", "Consultar a agenda de apresentações", "RBN14.01, RBN14.02 · TEL17",
        "menu \"Agenda\" → TEL17 com as próximas apresentações, por dia → filtros Curso e Período (Próximas, "
        "Próximos 7 dias, Todas)",
        ["todos", "tel17", "cage", "Defesa", "Tcc"],
        [
            acao("todos", "tel17", "Clicar em \"Agenda\" no menu"),
            chama("tel17", "cage", "GET /agenda?periodo=proximos"),
            chama("cage", "Defesa", "publicadas no período"),
            chama("cage", "Tcc", "título, aluno, curso, etapa (sem notas, matrícula ou e-mail)"),
            volta("cage", "tel17", "200 {apresentações[]}"),
            alt(
                ("[nenhuma apresentação]", [volta("tel17", "todos", "Exibe \"Nenhuma apresentação encontrada\" e \"Limpar filtros\"")]),
                ("[há apresentações]", [volta("tel17", "todos", "Exibe por dia: horário, título, aluno, curso, formato, local "
                                              "ou link; as canceladas aparecem marcadas")]),
            ),
            acao("todos", "tel17", "Escolher Curso e Período"),
            chama("tel17", "cage", "GET /agenda?curso&periodo"),
            volta("cage", "tel17", "200 {apresentações[]}"),
            volta("tel17", "todos", "Exibe a agenda filtrada"),
            nota("A exportação da agenda em PDF (RBN14.03) não aparece no protótipo.", "todos", "cage"),
        ], fonte="prototipo"),
    Diagrama(
        "DS-FL05-B", "Remarcar a defesa", "RBN09.07 · RN14 · TEL11",
        "aba Defesa › Agendamento, defesa confirmada → botão \"Remarcar\" → o assistente abre com os dados atuais → "
        "passos 1 e 2 → passo 3 com \"Motivo da remarcação\" → \"Confirmar remarcação\" → janela → confirmar",
        ["orientador", "tel11", "cagd", "Defesa", "LocalDefesa", "BancaMembro", "HistoricoDefesa", "LogAuditoria",
         "NotificacaoEmail", "iemail", "smtp"],
        [
            ref("DS-FL04: a defesa está confirmada em Defesa › Agendamento", "orientador", "cagd"),
            acao("orientador", "tel11", "Clicar em \"Remarcar\""),
            volta("tel11", "orientador", "Abre \"Remarcar defesa\" com data, horário e local atuais"),
            acao("orientador", "tel11", "Mudar a data ou o horário e clicar em Continuar"),
            acao("orientador", "tel11", "Mudar formato, local ou link e clicar em Continuar"),
            chama("tel11", "cagd", "GET /defesas/conflitos?data&inicio&fim&local&idTcc"),
            chama("cagd", "LocalDefesa", "local ocupado?"),
            chama("cagd", "Defesa", "banca ocupada?"),
            volta("cagd", "tel11", "200 {conflitos[]}"),
            volta("tel11", "orientador", "Mostra o passo 3 com os conflitos e o campo Motivo da remarcação"),
            acao("orientador", "tel11", "Escrever o motivo e clicar em \"Confirmar remarcação\""),
            proprio("tel11", "motivo com menos de 5 caracteres? pede o motivo"),
            volta("tel11", "orientador", "Abre a janela \"Confirmar remarcação?\""),
            acao("orientador", "tel11", "Confirmar"),
            chama("tel11", "cagd", "POST /defesas/{idDefesa}/remarcacao {data, inicio, fim, formato, local, link, motivo}"),
            alt(
                ("[sem permissão (RN14)]", [volta("cagd", "tel11", "403"), volta("tel11", "orientador", "Exibe o erro")]),
                ("[defesa cancelada ou realizada]", [volta("cagd", "tel11", "409"), volta("tel11", "orientador", "Exibe o erro")]),
                ("[conflito (RBN09.04)]", [volta("cagd", "tel11", "409 {conflitos[]}"),
                                           volta("tel11", "orientador", "Volta ao passo 3 com o conflito")]),
                ("[remarcação válida]", [
                    chama("cagd", "HistoricoDefesa", "registrar(REMARCACAO, dados anteriores, motivo)"),
                    chama("cagd", "Defesa", "atualizar data, horário e local; a divulgação acompanha"),
                    chama("cagd", "LogAuditoria", "registrar(remarcar_defesa)"),
                    chama("cagd", "BancaMembro", "participantes"),
                    loop("[banca, aluno e orientador]", enfileirar("cagd", "DEFESA_REMARCADA")),
                    volta("cagd", "tel11", "200 {defesa remarcada}"),
                    volta("tel11", "orientador", "Mostra a nova data e o histórico com o motivo"),
                    *email_depois("cagd", "cada participante", "nova data da defesa"),
                ]),
            ),
        ], fonte="prototipo"),
    Diagrama(
        "DS-FL05-C", "Cancelar a defesa", "RBN09.08 · RN14 · TEL11",
        "aba Defesa › Agendamento, defesa confirmada → botão \"Cancelar defesa\" → janela com \"Motivo do "
        "cancelamento\" → \"Cancelar defesa\"",
        ["orientador", "tel11", "cagd", "Defesa", "BancaMembro", "HistoricoDefesa", "LogAuditoria",
         "NotificacaoEmail", "iemail", "smtp"],
        [
            ref("DS-FL04: a defesa está confirmada em Defesa › Agendamento", "orientador", "cagd"),
            acao("orientador", "tel11", "Clicar em \"Cancelar defesa\""),
            volta("tel11", "orientador", "Abre a janela \"Cancelar esta defesa?\" com o Motivo do cancelamento"),
            acao("orientador", "tel11", "Escrever o motivo e clicar em \"Cancelar defesa\""),
            chama("tel11", "cagd", "POST /defesas/{idDefesa}/cancelamento {justificativa}"),
            alt(
                ("[sem permissão (RN14)]", [volta("cagd", "tel11", "403"), volta("tel11", "orientador", "Exibe o erro")]),
                ("[já cancelada ou realizada]", [volta("cagd", "tel11", "409"), volta("tel11", "orientador", "Exibe o erro")]),
                ("[motivo em branco (RBN09.08)]", [volta("cagd", "tel11", "422 {justificativa}"),
                                                    volta("tel11", "orientador", "Marca o campo")]),
                ("[cancelamento válido]", [
                    chama("cagd", "Defesa", "situação CANCELADA; se publicada, aparece como Cancelada na agenda"),
                    chama("cagd", "HistoricoDefesa", "registrar(CANCELAMENTO, motivo)"),
                    chama("cagd", "LogAuditoria", "registrar(cancelar_defesa)"),
                    chama("cagd", "BancaMembro", "participantes"),
                    loop("[banca, aluno e orientador]", enfileirar("cagd", "DEFESA_CANCELADA")),
                    volta("cagd", "tel11", "200 {defesa cancelada}"),
                    volta("tel11", "orientador", "Mostra \"Defesa cancelada. Você pode agendar uma nova.\""),
                    *email_depois("cagd", "cada participante", "defesa cancelada com o motivo"),
                ]),
            ),
        ], fonte="prototipo"),
    Diagrama(
        "DS-FL05-D", "Lembrete na véspera da defesa", "RBN09.06 · tarefa automática",
        "não há tela: o agendador do servidor roda uma vez por dia e avisa os participantes das defesas do dia seguinte",
        ["relogio", "clem", "Defesa", "BancaMembro", "NotificacaoEmail", "iemail", "smtp"],
        [
            chama("relogio", "clem", "verificar defesas de amanhã (uma vez por dia)"),
            chama("clem", "Defesa", "listar CONFIRMADAS com data = amanhã"),
            volta("Defesa", "clem", "defesas[]"),
            loop("[para cada defesa de amanhã]", [
                chama("clem", "BancaMembro", "participantes: banca, aluno e orientador"),
                volta("BancaMembro", "clem", "participantes[]"),
                loop("[para cada participante]", enfileirar("clem", "LEMBRETE_DEFESA")),
            ]),
            *email_depois("clem", "cada participante", "lembrete com data, horário e local ou link"),
        ], fonte="previsto"),
    Diagrama(
        "DS-FL05-E", "Convocar o suplente", "RBN09.09 · RN20 · previsto em TEL10",
        "ainda não há tela: o protótipo diz que mudar a banca depois de confirmada é a convocação do suplente, fora da "
        "aba Banca. Sequência prevista: a coordenação ou o orientador escolhe o titular ausente, informa o motivo e "
        "convoca o suplente",
        ["orientador", "tel10", "cagd", "Defesa", "BancaMembro", "HistoricoDefesa", "LogAuditoria",
         "NotificacaoEmail", "iemail", "smtp"],
        [
            acao("orientador", "tel10", "Escolher o titular ausente, informar o motivo e convocar o suplente"),
            chama("tel10", "cagd", "POST /defesas/{idDefesa}/suplente {idMembroTitular, motivo}"),
            chama("cagd", "Defesa", "obter(situação)"),
            chama("cagd", "BancaMembro", "titular e suplente"),
            alt(
                ("[não é a coordenação nem o orientador]", [volta("cagd", "tel10", "403"), volta("tel10", "orientador", "Exibe o erro")]),
                ("[defesa cancelada ou realizada]", [volta("cagd", "tel10", "409"), volta("tel10", "orientador", "Exibe o erro")]),
                ("[banca sem suplente (RN20)]", [volta("cagd", "tel10", "409 {sem suplente}"),
                                                 volta("tel10", "orientador", "Exibe o aviso")]),
                ("[motivo em branco]", [volta("cagd", "tel10", "422 {motivo}"), volta("tel10", "orientador", "Marca o campo")]),
                ("[convocação válida]", [
                    chama("cagd", "BancaMembro", "titular → substituído; suplente → titular (passa a avaliar)"),
                    chama("cagd", "HistoricoDefesa", "registrar(SUPLENTE, motivo)"),
                    chama("cagd", "LogAuditoria", "registrar(convocar_suplente)"),
                    loop("[suplente, titular e aluno]", enfileirar("cagd", "SUPLENTE_CONVOCADO")),
                    volta("cagd", "tel10", "200 {banca atualizada}"),
                    volta("tel10", "orientador", "Mostra o suplente no lugar do titular"),
                    *email_depois("cagd", "o suplente e o titular", "convocação do suplente"),
                ]),
            ),
        ], fonte="previsto"),
], situacao="Ainda não implementado: segue o protótipo (TEL11, TEL17, TEL18). FL05-D e FL05-E não têm tela no protótipo.")


# =====================================================================================
# FL06 · Avaliação, resultado e documentos da defesa
# =====================================================================================
FL06 = Fluxo("FL06", "Avaliar a defesa e registrar o resultado",
             "SCRUM-16 RAN10 · RBN09.12 a RBN09.17 · RBN10.01 a RBN10.05 · RN13, RN15, RN19, RN21 · TEL12, TEL13", [
    Diagrama(
        "DS-FL06-A", "Avaliador lança a avaliação", "RBN10.01 a RBN10.05 · RN19, RN20 · TEL12",
        "TCCs → abrir o TCC → aba Resultado › Avaliação → \"Avaliações da banca: x de y enviadas\" → assistente com um "
        "passo por critério (conceito e nota dentro da faixa) → Parecer → Revisar → \"Salvar rascunho\" ou \"Enviar "
        "avaliação\" → janela → \"Enviar avaliação\"",
        ["banca", "tel06", "tel12", "cava", "Defesa", "BancaMembro", "InstrumentoAvaliacao", "Avaliacao",
         "AvaliacaoCriterio"],
        [
            *abrir_tcc("banca"),
            *aba("banca", "tel12", "Resultado › \"Avaliação\""),
            chama("tel12", "cava", "GET /defesas/{idDefesa}/avaliacao"),
            chama("cava", "Defesa", "situação (realizada?)"),
            chama("cava", "BancaMembro", "sou avaliador ou orientador desta defesa?"),
            chama("cava", "InstrumentoAvaliacao", "instrumento da defesa: critérios, pesos e conceitos (RN19)"),
            chama("cava", "Avaliacao", "minha avaliação: rascunho ou enviada; quantas já foram enviadas"),
            volta("cava", "tel12", "200 {instrumento, minha avaliação, envios}"),
            alt(
                ("[defesa ainda não realizada]", [volta("tel12", "banca", "Exibe \"A defesa ainda não foi realizada\"")]),
                ("[não avalia esta defesa]", [volta("tel12", "banca", "Exibe \"Você não avalia esta defesa\"")]),
                ("[avaliação já enviada]", [volta("tel12", "banca", "Exibe a avaliação enviada, sem edição")]),
                ("[avaliação aberta]", [volta("tel12", "banca", "Exibe os envios da banca e o passo 1 (primeiro critério)")]),
            ),
            loop("[para cada um dos 4 critérios do instrumento]", [
                acao("banca", "tel12", "Escolher o conceito e ajustar a nota dentro da faixa dele; clicar em Continuar"),
                proprio("tel12", "conceito escolhido e nota dentro da faixa? mostra nota × peso e a nota parcial"),
            ]),
            acao("banca", "tel12", "Escrever o parecer (mínimo de 20 caracteres) e clicar em Continuar"),
            volta("tel12", "banca", "Mostra \"Revisar e enviar\" com a tabela e a nota ponderada"),
            opt("[salvar sem enviar]", [
                acao("banca", "tel12", "Clicar em \"Salvar rascunho\""),
                chama("tel12", "cava", "PUT /defesas/{idDefesa}/avaliacao {conceitos, notas, parecer}"),
                chama("cava", "Avaliacao", "salvar rascunho"),
                chama("cava", "AvaliacaoCriterio", "salvar conceito e nota por critério"),
                volta("cava", "tel12", "200"),
                volta("tel12", "banca", "Exibe \"Rascunho da avaliação salvo\""),
            ]),
            acao("banca", "tel12", "Clicar em \"Enviar avaliação\""),
            volta("tel12", "banca", "Abre a janela \"Enviar a avaliação?\" com a nota ponderada"),
            acao("banca", "tel12", "Confirmar \"Enviar avaliação\""),
            chama("tel12", "cava", "POST /defesas/{idDefesa}/avaliacao/envio {critérios[], parecer}"),
            alt(
                ("[critério sem conceito ou nota fora da faixa (RBN10.03, RBN10.05)]", [
                    volta("cava", "tel12", "422 {critério}"),
                    volta("tel12", "banca", "Volta ao passo do critério"),
                ]),
                ("[já enviada]", [volta("cava", "tel12", "409"), volta("tel12", "banca", "Exibe a avaliação enviada")]),
                ("[avaliação completa]", [
                    chama("cava", "AvaliacaoCriterio", "gravar conceito, nota e ponderada (2 casas)"),
                    chama("cava", "Avaliacao", "ENVIADA, nota total, enviada_em"),
                    volta("cava", "tel12", "200 {nota total, ENVIADA}"),
                    volta("tel12", "banca", "Exibe \"Avaliação enviada\"; ela não pode mais ser editada"),
                ]),
            ),
        ], fonte="prototipo"),
    Diagrama(
        "DS-FL06-B", "Consolidar a nota final", "RN21 · TEL12, seção Consolidar resultado",
        "calculado quando o orientador abre a aba Resultado e todas as avaliações foram enviadas: a tela mostra a nota "
        "de cada avaliador, a média, a regra de exceção e a nota final",
        ["cava", "cnota", "Avaliacao", "Tcc", "PublicacaoArtigo"],
        [
            chama("cava", "cnota", "calcularNotaFinal(idDefesa)"),
            chama("cnota", "Avaliacao", "notas totais enviadas"),
            volta("Avaliacao", "cnota", "notas[]"),
            proprio("cnota", "média das notas"),
            chama("cnota", "Tcc", "modalidade"),
            volta("Tcc", "cnota", "ARTIGO ou MONOGRAFIA"),
            alt(
                ("[ARTIGO]", [
                    chama("cnota", "PublicacaoArtigo", "situação editorial atual e Qualis"),
                    volta("PublicacaoArtigo", "cnota", "situação e Qualis"),
                    alt(
                        ("[aceito ou publicado em Qualis A ou B (RN21)]", [
                            proprio("cnota", "nota final = maior entre 6,00 e a média"),
                        ]),
                        ("[demais casos]", [proprio("cnota", "nota final = média")]),
                    ),
                ]),
                ("[MONOGRAFIA]", [proprio("cnota", "nota final = média")]),
            ),
            volta("cnota", "cava", "{média, nota final, regra aplicada e o porquê}"),
        ], fonte="prototipo"),
    Diagrama(
        "DS-FL06", "Orientador confirma o resultado", "RBN09.12 · RN13 · TEL12",
        "aba Resultado › Avaliação → seção \"Consolidar resultado\" (com todas as avaliações enviadas) → escolher "
        "Aprovado, Aprovado com correções ou Reprovado → \"Confirmar resultado\" → janela → confirmar",
        ["orientador", "tel06", "tel12", "cava", "cnota", "Avaliacao", "ResultadoDefesa", "LogAuditoria",
         "NotificacaoEmail", "iemail", "smtp"],
        [
            *abrir_tcc("orientador"),
            *aba("orientador", "tel12", "Resultado › \"Avaliação\""),
            chama("tel12", "cava", "GET /defesas/{idDefesa}/resultado"),
            chama("cava", "Avaliacao", "quem já enviou"),
            volta("Avaliacao", "cava", "enviadas e pendentes"),
            alt(
                ("[falta avaliação]", [
                    volta("cava", "tel12", "200 {pendentes[]}"),
                    volta("tel12", "orientador", "Exibe \"Aguardando avaliações. Faltam: ...\""),
                ]),
                ("[resultado já confirmado (RN13)]", [
                    volta("cava", "tel12", "200 {resultado}"),
                    volta("tel12", "orientador", "Exibe o resultado, \"Retificar resultado\" e \"Ata e certificados\""),
                ]),
                ("[todas enviadas]", [
                    ref("DS-FL06-B: consolidar a nota final", "cava", "cnota"),
                    volta("cava", "tel12", "200 {notas, média, regra de exceção, nota final}"),
                    volta("tel12", "orientador", "Exibe \"Consolidar resultado\" com as opções Aprovado, Aprovado com "
                          "correções e Reprovado"),
                ]),
            ),
            acao("orientador", "tel12", "Escolher o resultado e clicar em \"Confirmar resultado\""),
            proprio("tel12", "nenhum resultado escolhido? pede a escolha"),
            volta("tel12", "orientador", "Abre a janela \"Confirmar o resultado?\" com a nota final"),
            acao("orientador", "tel12", "Confirmar"),
            chama("tel12", "cava", "POST /defesas/{idDefesa}/resultado {resultado}"),
            alt(
                ("[não é o orientador da defesa (RBN09.12)]", [volta("cava", "tel12", "403"), volta("tel12", "orientador", "Exibe o erro")]),
                ("[já confirmado (RN13)]", [volta("cava", "tel12", "409"), volta("tel12", "orientador", "Exibe o resultado vigente")]),
                ("[resultado válido]", [
                    chama("cava", "cnota", "recalcular a nota final"),
                    chama("cava", "ResultadoDefesa", "registrar(resultado, média, nota final, quem, quando)"),
                    chama("cava", "LogAuditoria", "registrar(confirmar_resultado)"),
                    loop("[aluno e banca]", enfileirar("cava", "RESULTADO_DEFESA")),
                    volta("cava", "tel12", "200 {resultado, nota final}"),
                    volta("tel12", "orientador", "Exibe \"Resultado da defesa\" e os botões \"Retificar resultado\" e \"Ata e "
                          "certificados\"; se Aprovado com correções, lembra de registrar as correções"),
                    *email_depois("cava", "o aluno e a banca", "resultado da defesa"),
                ]),
            ),
        ], fonte="prototipo"),
    Diagrama(
        "DS-FL06-C", "Gerar a ata e a Folha de Aprovação", "RBN09.14, RBN09.15 · TEL13",
        "aba Resultado › \"Ata e certificados\" → seção Ata da defesa → \"Gerar ata da defesa\" (ou \"Gerar nova "
        "versão\") → \"Baixar PDF\"; seção Folha de Aprovação (TCC2 ou artigo) → \"Gerar folha de aprovação\"",
        ["orientador", "tel06", "tel13", "cdocd", "ResultadoDefesa", "Defesa", "BancaMembro", "Correcao",
         "DocumentoOficial", "LogAuditoria"],
        [
            *abrir_tcc("orientador"),
            *aba("orientador", "tel13", "Resultado › \"Ata e certificados\""),
            chama("tel13", "cdocd", "GET /defesas/{idDefesa}/documentos"),
            chama("cdocd", "DocumentoOficial", "versões da ata, da folha e certificados"),
            volta("cdocd", "tel13", "200 {ata[], folha[], certificados}"),
            volta("tel13", "orientador", "Exibe as seções Ata, Folha de Aprovação e Certificados, cada uma com o que falta"),
            acao("orientador", "tel13", "Clicar em \"Gerar ata da defesa\""),
            chama("tel13", "cdocd", "POST /defesas/{idDefesa}/documentos/ata"),
            chama("cdocd", "ResultadoDefesa", "resultado confirmado?"),
            chama("cdocd", "Defesa", "data, local e banca presente"),
            alt(
                ("[resultado ainda não confirmado (RBN09.14)]", [
                    volta("cdocd", "tel13", "409"),
                    volta("tel13", "orientador", "Exibe \"Indisponível por enquanto\""),
                ]),
                ("[falha ao gerar]", [
                    volta("cdocd", "tel13", "500"),
                    volta("tel13", "orientador", "Exibe \"Não foi possível gerar o documento\" e \"Tentar de novo\"; nada muda"),
                ]),
                ("[dados completos]", [
                    proprio("cdocd", "gerar PDF pelo modelo da ata"),
                    chama("cdocd", "DocumentoOficial", "versões anteriores → substituída; nova → vigente"),
                    chama("cdocd", "LogAuditoria", "registrar(gerar_ata)"),
                    volta("cdocd", "tel13", "200 {ata vigente}"),
                    volta("tel13", "orientador", "Mostra a ata gerada com \"Baixar PDF\""),
                ]),
            ),
            opt("[TCC2 ou modalidade artigo (RBN09.15)]", [
                acao("orientador", "tel13", "Clicar em \"Gerar folha de aprovação\""),
                chama("tel13", "cdocd", "POST /defesas/{idDefesa}/documentos/folha"),
                chama("cdocd", "Correcao", "aprovado com correções: o aluno já deu a anuência?"),
                alt(
                    ("[reprovado ou anuência pendente]", [
                        volta("cdocd", "tel13", "409 {motivo}"),
                        volta("tel13", "orientador", "Exibe por que a folha ainda não pode ser gerada"),
                    ]),
                    ("[liberada]", [
                        chama("cdocd", "DocumentoOficial", "nova versão vigente da folha"),
                        volta("cdocd", "tel13", "200 {folha vigente}"),
                        volta("tel13", "orientador", "Mostra a folha com \"Baixar PDF\""),
                    ]),
                ),
            ]),
        ], fonte="prototipo"),
    Diagrama(
        "DS-FL06-D", "Retificar o resultado", "RN13 · RBN09.12 · TEL12",
        "aba Resultado › Avaliação, resultado confirmado → \"Retificar resultado\" → janela com \"Novo resultado\" e "
        "\"Motivo da retificação\" → \"Registrar retificação\"",
        ["orientador", "tel12", "cava", "ResultadoDefesa", "DocumentoOficial", "LogAuditoria", "NotificacaoEmail",
         "iemail", "smtp"],
        [
            ref("DS-FL06: o resultado está confirmado em TEL12", "orientador", "cava"),
            acao("orientador", "tel12", "Clicar em \"Retificar resultado\""),
            volta("tel12", "orientador", "Abre a janela com o Novo resultado e o Motivo da retificação"),
            acao("orientador", "tel12", "Escolher o novo resultado, escrever o motivo e clicar em \"Registrar retificação\""),
            proprio("tel12", "mesmo resultado de antes? avisa que nada mudou"),
            chama("tel12", "cava", "POST /defesas/{idDefesa}/resultado/retificacao {resultado, motivo}"),
            alt(
                ("[não é o orientador da defesa]", [volta("cava", "tel12", "403"), volta("tel12", "orientador", "Exibe o erro")]),
                ("[motivo em branco (RN13)]", [volta("cava", "tel12", "422 {motivo}"), volta("tel12", "orientador", "Marca o campo")]),
                ("[retificação válida]", [
                    chama("cava", "ResultadoDefesa", "nova versão; a anterior fica registrada (de, para, quem, quando, motivo)"),
                    chama("cava", "DocumentoOficial", "ata vigente → desatualizada"),
                    chama("cava", "LogAuditoria", "registrar(retificar_resultado)"),
                    loop("[aluno e banca]", enfileirar("cava", "RESULTADO_RETIFICADO")),
                    volta("cava", "tel12", "200 {resultado retificado}"),
                    volta("tel12", "orientador", "Mostra a retificação na lista; em Ata e certificados aparece \"O resultado "
                          "foi retificado\" para gerar nova ata"),
                    *email_depois("cava", "o aluno e a banca", "resultado retificado"),
                ]),
            ),
        ], fonte="prototipo"),
    Diagrama(
        "DS-FL06-E", "Aluno consulta o resultado e a ata", "RBN09.16 · RN07 · TEL06, TEL13",
        "menu \"TCCs\" → abrir o TCC → a capa mostra o selo \"Resultado da defesa\" → aba Resultado › \"Ata e "
        "certificados\" → \"Baixar PDF\" da versão vigente",
        ["aluno", "tel06", "tel13", "cava", "cdocd", "ResultadoDefesa", "DocumentoOficial"],
        [
            *abrir_tcc("aluno"),
            chama("tel06", "cava", "GET /defesas/{idDefesa}/resultado"),
            chama("cava", "ResultadoDefesa", "resultado vigente"),
            volta("cava", "tel06", "200 {resultado, nota final} ou aguardando"),
            alt(
                ("[resultado ainda não confirmado]", [volta("tel06", "aluno", "Exibe \"Defesa realizada. Aguarde as avaliações e o resultado\"")]),
                ("[resultado confirmado]", [volta("tel06", "aluno", "Exibe o selo do resultado na capa e o próximo passo")]),
            ),
            *aba("aluno", "tel13", "Resultado › \"Ata e certificados\""),
            chama("tel13", "cdocd", "GET /defesas/{idDefesa}/documentos"),
            chama("cdocd", "DocumentoOficial", "ata e folha: vigente e substituídas"),
            volta("cdocd", "tel13", "200 {versões}"),
            volta("tel13", "aluno", "Exibe as versões com Vigente ou Substituída e \"Baixar PDF\""),
            acao("aluno", "tel13", "Clicar em \"Baixar PDF\""),
            chama("tel13", "cdocd", "GET /documentos/{id}/arquivo"),
            volta("cdocd", "tel13", "arquivo PDF"),
        ], fonte="prototipo"),
    Diagrama(
        "DS-FL06-F", "Emitir os certificados de participação", "RBN09.17 · RN15 · TEL13",
        "aba Resultado › \"Ata e certificados\" → seção Certificados de participação → \"Emitir\" na linha do "
        "participante (ou \"Emitir todos\") → \"Baixar\"",
        ["orientador", "tel13", "cdocd", "Defesa", "BancaMembro", "DocumentoOficial", "NotificacaoEmail", "iemail",
         "smtp"],
        [
            ref("DS-FL06-C: o orientador está em Ata e certificados", "orientador", "cdocd"),
            acao("orientador", "tel13", "Clicar em \"Emitir\" na linha do participante (ou \"Emitir todos\")"),
            chama("tel13", "cdocd", "POST /defesas/{idDefesa}/documentos/certificados {idsMembro[]}"),
            chama("cdocd", "Defesa", "realizada?"),
            chama("cdocd", "BancaMembro", "participantes (o suplente não convocado fica de fora)"),
            alt(
                ("[defesa não realizada (RN15)]", [volta("cdocd", "tel13", "409"), volta("tel13", "orientador", "Exibe o aviso")]),
                ("[defesa realizada]", [
                    loop("[para cada participante escolhido]", [
                        chama("cdocd", "DocumentoOficial", "criar(CERTIFICADO, membro)"),
                        *enfileirar("cdocd", "CERTIFICADO"),
                    ]),
                    volta("cdocd", "tel13", "200 {certificados[]}"),
                    volta("tel13", "orientador", "Mostra \"Emitido\" e o botão \"Baixar\" em cada linha"),
                    *email_depois("cdocd", "cada participante", "certificado de participação"),
                ]),
            ),
        ], fonte="prototipo"),
], situacao="Ainda não implementado: segue o protótipo (aba Resultado: Avaliação e Ata e certificados).")


# =====================================================================================
# FL07 · Correções e encerramento
# =====================================================================================
FL07 = Fluxo("FL07", "Corrigir e encerrar o TCC", "SCRUM-17 RAN11 · RBN09.15 · RBN11.01 a RBN11.04 · RN17, RN24 · TEL14, TEL09", [
    Diagrama(
        "DS-FL07-A", "Registrar as correções exigidas", "RBN11.01 · RN17 · TEL14",
        "TCCs → abrir o TCC → aba Correções → seção \"Registrar nova exigência\" (o que precisa ser corrigido e "
        "prazo) → \"Adicionar exigência\"",
        ["banca", "tel06", "tel14", "ccor", "BancaMembro", "Correcao", "LogAuditoria", "NotificacaoEmail", "iemail",
         "smtp"],
        [
            *abrir_tcc("banca"),
            *aba("banca", "tel14", "\"Correções\""),
            chama("tel14", "ccor", "GET /tccs/{idTcc}/correcoes"),
            volta("ccor", "tel14", "200 {condições, correções[]}"),
            volta("tel14", "banca", "Exibe \"Condições para concluir\", a tabela de correções e \"Registrar nova exigência\""),
            acao("banca", "tel14", "Descrever a correção, escolher o prazo e clicar em \"Adicionar exigência\""),
            proprio("tel14", "descrição com 10 caracteres ou mais e prazo não passado?"),
            chama("tel14", "ccor", "POST /tccs/{idTcc}/correcoes {descricao, prazo}"),
            chama("ccor", "BancaMembro", "é avaliador ou orientador da defesa?"),
            alt(
                ("[sem vínculo com a defesa]", [volta("ccor", "tel14", "403"), volta("tel14", "banca", "Exibe o erro")]),
                ("[exigência válida]", [
                    chama("ccor", "Correcao", "criar(PENDENTE, avaliador, prazo)"),
                    chama("ccor", "LogAuditoria", "registrar(registrar_correcao)"),
                    *enfileirar("ccor", "CORRECAO_EXIGIDA"),
                    volta("ccor", "tel14", "201 {correção}"),
                    volta("tel14", "banca", "Mostra a correção na tabela e \"Exigência registrada. O aluno foi avisado.\""),
                    *email_depois("ccor", "o aluno", "nova correção exigida, com o prazo"),
                ]),
            ),
        ], fonte="prototipo"),
    Diagrama(
        "DS-FL07", "Aluno atende as correções e envia a versão final", "RBN09.15 · RBN11.02 · TEL14, TEL09",
        "aba Correções → (aprovado com correções) marcar \"Li as correções...\" e \"Dar anuência\" → em cada correção, "
        "\"Marcar como atendida\" → \"Enviar versão final\" → aba Documentos: Finalidade \"Versão final\", escolher o "
        "PDF e \"Enviar documento\"",
        ["aluno", "tel06", "tel14", "tel09", "ccor", "Correcao", "ResultadoDefesa", "DocumentoTcc", "LogAuditoria"],
        [
            *abrir_tcc("aluno"),
            *aba("aluno", "tel14", "\"Correções\""),
            chama("tel14", "ccor", "GET /tccs/{idTcc}/correcoes"),
            chama("ccor", "Correcao", "correções com prazo e situação"),
            chama("ccor", "ResultadoDefesa", "resultado confirmado?"),
            volta("ccor", "tel14", "200 {condições, correções[], anuência}"),
            volta("tel14", "aluno", "Exibe as condições, as correções com o prazo e, se for o caso, \"Anuência às correções\""),
            opt("[Aprovado com correções e anuência ainda não dada (RBN09.15)]", [
                acao("aluno", "tel14", "Marcar \"Li as correções exigidas e estou de acordo\" e clicar em \"Dar anuência\""),
                chama("tel14", "ccor", "POST /tccs/{idTcc}/correcoes/anuencia"),
                chama("ccor", "LogAuditoria", "registrar(anuencia)"),
                volta("ccor", "tel14", "200"),
                volta("tel14", "aluno", "Exibe \"Anuência registrada. Folha de Aprovação liberada\""),
            ]),
            loop("[para cada correção pendente ou devolvida]", [
                acao("aluno", "tel14", "Clicar em \"Marcar como atendida\""),
                chama("tel14", "ccor", "POST /correcoes/{idCorrecao}/atendida"),
                chama("ccor", "Correcao", "situação ATENDIDA"),
                volta("ccor", "tel14", "200"),
                volta("tel14", "aluno", "Mostra \"Atendida pelo aluno\"; aguarda aprovação"),
            ]),
            acao("aluno", "tel14", "Clicar em \"Enviar versão final\""),
            chama("tel14", "tel09", "abrir a aba Documentos"),
            volta("tel09", "aluno", "Exibe \"Enviar novo documento\" e as versões enviadas"),
            acao("aluno", "tel09", "Escolher a finalidade \"Versão final\" e o arquivo PDF"),
            proprio("tel09", "é PDF e tem até 20 MB?"),
            alt(
                ("[não é PDF ou passa de 20 MB]", [volta("tel09", "aluno", "Exibe o motivo; a versão vigente é mantida")]),
                ("[arquivo válido]", [
                    volta("tel09", "aluno", "Mostra \"Arquivo válido\" e \"Será criada a versão final vN\""),
                    acao("aluno", "tel09", "Clicar em \"Enviar documento\""),
                    chama("tel09", "ccor", "POST /tccs/{idTcc}/documentos {PDF, finalidade FINAL}"),
                    chama("ccor", "DocumentoTcc", "versão anterior → substituída; nova → vigente"),
                    opt("[depois do prazo (RBN11.02)]", [
                        chama("ccor", "DocumentoTcc", "marcar entregue com atraso"),
                    ]),
                    chama("ccor", "LogAuditoria", "registrar(enviar_versao_final)"),
                    ref("DS-FL07-C: o sistema confere se o TCC pode ser concluído", "tel09", "ccor"),
                    volta("ccor", "tel09", "201 {versão, concluído?}"),
                    volta("tel09", "aluno", "Exibe \"Documento enviado. A nova versão é a vigente\" (ou \"TCC concluído\")"),
                ]),
            ),
        ], fonte="prototipo"),
    Diagrama(
        "DS-FL07-B", "Aprovar ou devolver a correção", "RBN11.03 · RN24 · TEL14",
        "aba Correções → na correção \"Atendida pelo aluno\": \"Aprovar\", ou \"Devolver\" → janela com \"O que falta "
        "corrigir\" → \"Devolver\" (TCC1: professor da disciplina; TCC2: orientador)",
        ["orientador", "tel06", "tel14", "ccor", "Correcao", "LogAuditoria", "NotificacaoEmail", "iemail", "smtp"],
        [
            *abrir_tcc("orientador"),
            *aba("orientador", "tel14", "\"Correções\""),
            chama("tel14", "ccor", "GET /tccs/{idTcc}/correcoes"),
            volta("ccor", "tel14", "200 {correções[]}"),
            volta("tel14", "orientador", "Exibe Aprovar e Devolver nas correções atendidas"),
            alt(
                ("[aprovar]", [
                    acao("orientador", "tel14", "Clicar em \"Aprovar\""),
                    chama("tel14", "ccor", "POST /correcoes/{idCorrecao}/decisao {APROVADA}"),
                ]),
                ("[devolver]", [
                    acao("orientador", "tel14", "Clicar em \"Devolver\""),
                    volta("tel14", "orientador", "Abre a janela com \"O que falta corrigir\""),
                    acao("orientador", "tel14", "Escrever o que falta e clicar em \"Devolver\""),
                    chama("tel14", "ccor", "POST /correcoes/{idCorrecao}/decisao {DEVOLVIDA, justificativa}"),
                ]),
            ),
            chama("ccor", "Correcao", "obter: situação ATENDIDA?"),
            alt(
                ("[não é o responsável pela turma (RN24)]", [volta("ccor", "tel14", "403"), volta("tel14", "orientador", "Exibe o erro")]),
                ("[correção não está ATENDIDA]", [volta("ccor", "tel14", "409"), volta("tel14", "orientador", "Exibe o erro")]),
                ("[devolução sem justificativa (RBN11.03)]", [volta("ccor", "tel14", "422"), volta("tel14", "orientador", "Marca o campo")]),
                ("[decisão válida]", [
                    chama("ccor", "Correcao", "APROVADA, ou DEVOLVIDA com a observação"),
                    chama("ccor", "LogAuditoria", "registrar(decidir_correcao)"),
                    opt("[aprovada]", [ref("DS-FL07-C: conferir se o TCC pode ser concluído", "ccor", "Correcao")]),
                    opt("[devolvida]", enfileirar("ccor", "CORRECAO_DEVOLVIDA")),
                    volta("ccor", "tel14", "200 {correção, concluído?}"),
                    volta("tel14", "orientador", "Mostra \"Aprovada\" ou \"Devolvida ao aluno\" (ou \"TCC concluído\")"),
                ]),
            ),
        ], fonte="prototipo"),
    Diagrama(
        "DS-FL07-C", "Concluir o TCC", "RBN11.04 · conclusão automática",
        "não há botão: depois de aprovar uma correção ou de enviar a versão final, o sistema confere as três "
        "condições mostradas em \"Condições para concluir o TCC\" e conclui sozinho",
        ["ccor", "ResultadoDefesa", "Correcao", "DocumentoTcc", "Tcc", "HistoricoSituacao", "LogAuditoria",
         "NotificacaoEmail"],
        [
            chama("ccor", "ResultadoDefesa", "resultado confirmado e diferente de reprovado?"),
            chama("ccor", "Correcao", "todas APROVADAS?"),
            chama("ccor", "DocumentoTcc", "versão final vigente?"),
            alt(
                ("[alguma condição pendente]", [proprio("ccor", "nada muda; a tela mostra a condição pendente")]),
                ("[as três condições atendidas]", [
                    chama("ccor", "Tcc", "situação CONCLUIDO, concluido_em"),
                    chama("ccor", "HistoricoSituacao", "registrar(→ CONCLUIDO, Sistema)"),
                    chama("ccor", "LogAuditoria", "registrar(concluir_tcc)"),
                    *enfileirar("ccor", "TCC_CONCLUIDO"),
                    nota("O acesso do aluno continua por 7 dias após a aprovação oficial.", "ccor", "Tcc"),
                ]),
            ),
        ], fonte="previsto"),
    Diagrama(
        "DS-FL07-D", "Decidir atraso e alterar o prazo", "RBN11.01, RBN11.02 · RN24 · previsto em TEL14",
        "ainda não há tela: o protótipo só mostra \"Vencido há N dias\" na correção. Sequência prevista: o professor "
        "responsável aceita ou não a entrega com atraso, ou muda o prazo com um motivo",
        ["professor", "tel14", "ccor", "DocumentoTcc", "PeriodoLetivo", "LogAuditoria"],
        [
            alt(
                ("[decidir a entrega com atraso]", [
                    acao("professor", "tel14", "Aceitar ou recusar a entrega com atraso"),
                    chama("tel14", "ccor", "POST /tccs/{idTcc}/correcoes/atraso {aceita}"),
                    chama("ccor", "DocumentoTcc", "versão final marcada com atraso?"),
                    alt(
                        ("[sem atraso a decidir]", [volta("ccor", "tel14", "409"), volta("tel14", "professor", "Exibe o aviso")]),
                        ("[entrega com atraso]", [
                            chama("ccor", "DocumentoTcc", "registrar a decisão sobre o atraso"),
                            chama("ccor", "LogAuditoria", "registrar(decidir_atraso)"),
                            volta("ccor", "tel14", "200"),
                            volta("tel14", "professor", "Mostra a decisão"),
                        ]),
                    ),
                ]),
                ("[alterar o prazo]", [
                    acao("professor", "tel14", "Informar o novo prazo e o motivo"),
                    chama("tel14", "ccor", "POST /tccs/{idTcc}/correcoes/prazo {prazo, motivo}"),
                    alt(
                        ("[motivo em branco]", [volta("ccor", "tel14", "422"), volta("tel14", "professor", "Marca o campo")]),
                        ("[prazo e motivo informados]", [
                            chama("ccor", "PeriodoLetivo", "prazo da versão final"),
                            chama("ccor", "LogAuditoria", "registrar(alterar_prazo, anterior, novo, motivo)"),
                            volta("ccor", "tel14", "200 {prazo}"),
                            volta("tel14", "professor", "Mostra o novo prazo"),
                        ]),
                    ),
                ]),
            ),
        ], fonte="previsto"),
], situacao="Ainda não implementado: segue o protótipo (aba Correções e aba Documentos). FL07-D não tem tela no protótipo.")


# =====================================================================================
# FL08 · Publicação do artigo e indicadores
# =====================================================================================
FL08 = Fluxo("FL08", "Acompanhar a publicação do artigo", "SCRUM-18 RAN12 · RBN03.02 · RBN12.01 a RBN12.03 · RBN13.01 · TEL15, TEL16", [
    Diagrama(
        "DS-FL08", "Registrar a submissão e a situação do artigo", "RBN03.02 · RBN12.01 · TEL15",
        "TCCs → abrir o TCC (modalidade artigo) → aba Artigo → \"Situação atual do artigo\" → seção \"Registrar nova "
        "situação\" (veículo, Qualis, situação editorial, endereço) → \"Adicionar ao histórico\"",
        ["aluno", "tel06", "tel15", "cpub", "cnot", "Tcc", "PublicacaoArtigo", "HistoricoPublicacao", "LogAuditoria"],
        [
            *abrir_tcc("aluno"),
            *aba("aluno", "tel15", "\"Artigo\" (só aparece na modalidade artigo)"),
            chama("tel15", "cpub", "GET /tccs/{idTcc}/publicacao"),
            chama("cpub", "PublicacaoArtigo", "situação atual"),
            chama("cpub", "HistoricoPublicacao", "registros anteriores"),
            volta("cpub", "tel15", "200 {situação atual, histórico[]}"),
            volta("tel15", "aluno", "Exibe a situação atual, o formulário e o histórico"),
            acao("aluno", "tel15", "Informar veículo, Qualis, situação editorial e endereço e clicar em \"Adicionar ao histórico\""),
            proprio("tel15", "veículo preenchido? endereço começa com https://?"),
            chama("tel15", "cpub", "POST /tccs/{idTcc}/publicacao {veiculo, qualis, situacao, link}"),
            chama("cpub", "Tcc", "autor ou orientador? modalidade ARTIGO?"),
            alt(
                ("[sem vínculo ou não é artigo]", [volta("cpub", "tel15", "403 ou 409"), volta("tel15", "aluno", "Exibe o erro")]),
                ("[campo inválido ou situação fora do vocabulário (E1)]", [volta("cpub", "tel15", "422"),
                                                                           volta("tel15", "aluno", "Marca o campo")]),
                ("[dados válidos]", [
                    chama("cpub", "PublicacaoArtigo", "atualizar situação atual, veículo e Qualis"),
                    chama("cpub", "HistoricoPublicacao", "registrar(situação, data, quem); os anteriores ficam"),
                    chama("cpub", "LogAuditoria", "registrar(registrar_publicacao)"),
                    ref("DS-FL08-A: avisar o orientador e o autor", "cpub", "cnot"),
                    volta("cpub", "tel15", "201 {situação atual}"),
                    volta("tel15", "aluno", "Mostra o registro no histórico e \"Registro adicionado ao histórico\""),
                ]),
            ),
            nota("Aceito ou publicado em Qualis A ou B pode mudar a nota final da defesa (DS-FL06-B).", "aluno", "cpub"),
        ], fonte="prototipo"),
    Diagrama(
        "DS-FL08-A", "Avisar por e-mail a mudança de situação", "RBN12.03 · aviso automático",
        "não há tela: acontece logo depois do registro em DS-FL08",
        ["cpub", "cnot", "Orientacao", "NotificacaoEmail", "iemail", "smtp"],
        [
            chama("cpub", "cnot", "notificarSituacao(idTcc, situação)"),
            chama("cnot", "Orientacao", "orientador do TCC"),
            volta("Orientacao", "cnot", "orientador"),
            loop("[orientador e cada autor]", enfileirar("cnot", "SITUACAO_ARTIGO")),
            *email_depois("cnot", "o orientador e o autor", "nova situação do artigo"),
        ], fonte="previsto"),
    Diagrama(
        "DS-FL08-B", "Atualizar a situação pelo DOI", "RBN12.02 · tarefa automática",
        "não há tela: o agendador confere, de tempos em tempos, os artigos com DOI que ainda não estão publicados",
        ["relogio", "cpub", "PublicacaoArtigo", "doi", "HistoricoPublicacao"],
        [
            chama("relogio", "cpub", "verificar artigos com DOI"),
            chama("cpub", "PublicacaoArtigo", "com DOI e situação ≠ PUBLICADO"),
            volta("PublicacaoArtigo", "cpub", "publicações[]"),
            loop("[para cada publicação]", [
                chama("cpub", "doi", "consultar o DOI"),
                alt(
                    ("[DOI encontrado e artigo publicado]", [
                        volta("doi", "cpub", "metadados (publicado em)"),
                        chama("cpub", "PublicacaoArtigo", "situação PUBLICADO"),
                        chama("cpub", "HistoricoPublicacao", "registrar(PUBLICADO, Sistema)"),
                    ]),
                    ("[DOI não encontrado ou base fora do ar]", [
                        volta("doi", "cpub", "não encontrado / erro"),
                        proprio("cpub", "mantém a situação; tenta na próxima rodada"),
                    ]),
                ),
            ]),
        ], fonte="previsto"),
    Diagrama(
        "DS-FL08-C", "Consultar o histórico do artigo", "RBN12.01 · TEL15",
        "TCCs → abrir o TCC → aba Artigo → seção Histórico, do mais recente para o mais antigo",
        ["orientador", "tel06", "tel15", "cpub", "PublicacaoArtigo", "HistoricoPublicacao"],
        [
            *abrir_tcc("orientador"),
            *aba("orientador", "tel15", "\"Artigo\""),
            chama("tel15", "cpub", "GET /tccs/{idTcc}/publicacoes/historico"),
            chama("cpub", "HistoricoPublicacao", "listar do mais recente para o mais antigo"),
            volta("cpub", "tel15", "200 {histórico[]}"),
            alt(
                ("[nenhum registro]", [volta("tel15", "orientador", "Exibe \"Nenhuma submissão registrada\"")]),
                ("[há registros]", [volta("tel15", "orientador", "Exibe cada registro com a situação, o veículo, o Qualis, a data e o endereço")]),
            ),
        ], fonte="prototipo"),
    Diagrama(
        "DS-FL08-D", "Indicadores de produção científica", "RBN13.01 · RN07 · TEL16",
        "menu \"Indicadores\" → TEL16 com o escopo do perfil → filtros Período letivo e Curso → números da situação "
        "acadêmica, da produção científica e das participações em banca → \"Gerar relatório em PDF\"",
        ["coord", "tel16", "cind", "Tcc", "PublicacaoArtigo", "BancaMembro"],
        [
            acao("coord", "tel16", "Clicar em \"Indicadores\" no menu"),
            chama("tel16", "cind", "GET /indicadores?periodo&curso"),
            proprio("cind", "escopo pelos perfis: coordenação vê o núcleo; professor, as turmas; orientador, os orientandos"),
            chama("cind", "Tcc", "contar por situação acadêmica (cada TCC uma vez)"),
            chama("cind", "PublicacaoArtigo", "contar por situação editorial"),
            chama("cind", "BancaMembro", "participações em banca por docente"),
            volta("cind", "tel16", "200 {totais, situação acadêmica, produção, bancas}"),
            alt(
                ("[sem dados no filtro]", [volta("tel16", "coord", "Exibe \"Sem dados para este filtro\" e \"Limpar filtros\"")]),
                ("[há dados]", [volta("tel16", "coord", "Exibe os totais, as barras e a tabela de bancas, sem nomes de alunos")]),
            ),
            opt("[mudar os filtros]", [
                acao("coord", "tel16", "Escolher período letivo e curso"),
                chama("tel16", "cind", "GET /indicadores?periodo&curso"),
                volta("cind", "tel16", "200"),
                volta("tel16", "coord", "Atualiza os números"),
            ]),
            acao("coord", "tel16", "Clicar em \"Gerar relatório em PDF\""),
            chama("tel16", "cind", "POST /indicadores/relatorio {filtros}"),
            proprio("cind", "gerar PDF com os mesmos números e filtros"),
            volta("cind", "tel16", "200 {PDF}"),
            volta("tel16", "coord", "Baixa o relatório"),
        ], fonte="prototipo"),
], situacao="Ainda não implementado: segue o protótipo (aba Artigo e menu Indicadores). FL08-A e FL08-B são automáticos.")


# =====================================================================================
# FL09 · Ocorrências, ouvintes e declarações
# =====================================================================================
FL09 = Fluxo("FL09", "Registrar ocorrências e ouvintes", "SCRUM-19 RAN15 · RN07, RN15 · TEL19", [
    Diagrama(
        "DS-FL09", "Registrar ocorrências e ouvintes da defesa", "RAN15 · RN07 · TEL19",
        "TCCs → abrir o TCC → aba Defesa › \"Presença e ocorrências\" (liberada depois da defesa realizada) → "
        "\"Registrar ocorrência\" → \"Adicionar ouvinte\" (nome e matrícula) ou \"Colar uma lista\"",
        ["orientador", "tel06", "tel19", "coco", "Defesa", "OcorrenciaDefesa", "OuvinteDefesa", "LogAuditoria"],
        [
            *abrir_tcc("orientador"),
            *aba("orientador", "tel19", "Defesa › \"Presença e ocorrências\""),
            chama("tel19", "coco", "GET /defesas/{idDefesa}/ocorrencias"),
            chama("coco", "Defesa", "situação e vínculo (RN07)"),
            chama("coco", "OcorrenciaDefesa", "ocorrências"),
            chama("coco", "OuvinteDefesa", "ouvintes"),
            volta("coco", "tel19", "200 {ocorrências[], ouvintes[]}"),
            alt(
                ("[defesa ainda não realizada]", [volta("tel19", "orientador", "Exibe \"Etapa ainda não liberada\"")]),
                ("[defesa realizada]", [volta("tel19", "orientador", "Exibe as ocorrências e os ouvintes, com \"x prontos para declaração\"")]),
            ),
            acao("orientador", "tel19", "Escrever a ocorrência e clicar em \"Registrar ocorrência\""),
            proprio("tel19", "texto com 5 caracteres ou mais?"),
            chama("tel19", "coco", "POST /defesas/{idDefesa}/ocorrencias {texto}"),
            alt(
                ("[sem vínculo ou defesa cancelada (E2)]", [volta("coco", "tel19", "403 ou 409"), volta("tel19", "orientador", "Exibe o erro")]),
                ("[ocorrência válida]", [
                    chama("coco", "OcorrenciaDefesa", "criar(texto, quem, quando)"),
                    chama("coco", "LogAuditoria", "registrar(registrar_ocorrencia)"),
                    volta("coco", "tel19", "201 {ocorrência}"),
                    volta("tel19", "orientador", "Mostra a ocorrência na lista"),
                ]),
            ),
            acao("orientador", "tel19", "Informar nome e matrícula e clicar em \"Adicionar ouvinte\""),
            proprio("tel19", "nome com 3 letras ou mais; matrícula com 7 dígitos e sem repetir?"),
            chama("tel19", "coco", "POST /defesas/{idDefesa}/ouvintes {nome, matricula}"),
            alt(
                ("[matrícula repetida ou dado inválido (E1)]", [volta("coco", "tel19", "422"), volta("tel19", "orientador", "Marca o campo")]),
                ("[ouvinte válido]", [
                    chama("coco", "OuvinteDefesa", "criar(nome, matrícula)"),
                    volta("coco", "tel19", "201 {ouvinte}"),
                    volta("tel19", "orientador", "Mostra o ouvinte como \"Pronto para emitir\""),
                ]),
            ),
            opt("[colar uma lista]", [
                acao("orientador", "tel19", "Abrir \"Colar uma lista\", colar \"nome; matrícula\" por linha e clicar em \"Adicionar da lista\""),
                chama("tel19", "coco", "POST /defesas/{idDefesa}/ouvintes/lote {linhas[]}"),
                chama("coco", "OuvinteDefesa", "criar os válidos"),
                volta("coco", "tel19", "200 {adicionados, linhas com problema[]}"),
                volta("tel19", "orientador", "Mostra quantos entraram e as linhas que não entraram"),
            ]),
        ], fonte="prototipo"),
    Diagrama(
        "DS-FL09-A", "Corrigir uma ocorrência ou um ouvinte", "RAN15 · RNF03 · TEL19",
        "TEL19 → \"Corrigir\" na ocorrência → editar → \"Salvar correção\"; ou \"Corrigir matrícula\" no ouvinte → "
        "\"Salvar\"; ou \"Remover\" o ouvinte",
        ["orientador", "tel19", "coco", "OcorrenciaDefesa", "OuvinteDefesa", "LogAuditoria"],
        [
            ref("DS-FL09: o orientador está em Presença e ocorrências", "orientador", "coco"),
            alt(
                ("[corrigir ocorrência]", [
                    acao("orientador", "tel19", "Clicar em \"Corrigir\", editar o texto e clicar em \"Salvar correção\""),
                    chama("tel19", "coco", "PUT /defesas/{idDefesa}/ocorrencias/{id} {texto}"),
                    chama("coco", "OcorrenciaDefesa", "atualizar texto, alterada_em"),
                    chama("coco", "LogAuditoria", "registrar(corrigir_ocorrencia, anterior, novo)"),
                    volta("coco", "tel19", "200"),
                    volta("tel19", "orientador", "Mostra o texto com \"corrigido em ...\""),
                ]),
                ("[corrigir matrícula]", [
                    acao("orientador", "tel19", "Clicar em \"Corrigir matrícula\", digitar e clicar em \"Salvar\""),
                    proprio("tel19", "7 dígitos?"),
                    chama("tel19", "coco", "PUT /defesas/{idDefesa}/ouvintes/{id} {matricula}"),
                    chama("coco", "OuvinteDefesa", "atualizar matrícula"),
                    chama("coco", "LogAuditoria", "registrar(corrigir_ouvinte)"),
                    volta("coco", "tel19", "200"),
                    volta("tel19", "orientador", "Mostra a matrícula corrigida e \"Pronto para emitir\""),
                ]),
                ("[remover ouvinte]", [
                    acao("orientador", "tel19", "Clicar em \"Remover\""),
                    chama("tel19", "coco", "DELETE /defesas/{idDefesa}/ouvintes/{id}"),
                    chama("coco", "OuvinteDefesa", "remover"),
                    volta("coco", "tel19", "200"),
                    volta("tel19", "orientador", "Tira da lista, com \"Desfazer\""),
                ]),
            ),
        ], fonte="prototipo"),
    Diagrama(
        "DS-FL09-B", "Emitir a declaração de horas do ouvinte", "RAN15 · RN15 · TEL19",
        "TEL19 → na linha do ouvinte com matrícula válida, \"Emitir declaração\"",
        ["orientador", "tel19", "coco", "Defesa", "OuvinteDefesa", "DocumentoOficial"],
        [
            ref("DS-FL09: o orientador está em Presença e ocorrências", "orientador", "coco"),
            acao("orientador", "tel19", "Clicar em \"Emitir declaração\" na linha do ouvinte"),
            chama("tel19", "coco", "POST /defesas/{idDefesa}/declaracoes {idOuvinte}"),
            chama("coco", "Defesa", "realizada?"),
            chama("coco", "OuvinteDefesa", "matrícula válida?"),
            alt(
                ("[defesa não realizada (RN15)]", [volta("coco", "tel19", "409"), volta("tel19", "orientador", "Exibe o aviso")]),
                ("[matrícula incompleta]", [volta("coco", "tel19", "422 {matrícula}"),
                                            volta("tel19", "orientador", "Pede para corrigir a matrícula (DS-FL09-A)")]),
                ("[pode emitir]", [
                    chama("coco", "DocumentoOficial", "criar(DECLARACAO_HORAS, ouvinte)"),
                    volta("coco", "tel19", "200 {declaração}"),
                    volta("tel19", "orientador", "Mostra \"Emitida\" na linha do ouvinte"),
                ]),
            ),
        ], fonte="prototipo"),
], situacao="Ainda não implementado: segue o protótipo (aba Defesa › Presença e ocorrências).")


FLUXOS = [FL01, FL02, FL03, FL04, FL05, FL06, FL07, FL08, FL09, FL10, FL11]
