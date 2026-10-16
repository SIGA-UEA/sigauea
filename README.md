# SIGA UEA

O **SIGA UEA** é o sistema de gestão de Trabalhos de Conclusão de Curso (TCC) do NUCOMP, na Universidade do Estado do Amazonas (UEA). Foi desenvolvido na disciplina de Engenharia de Software e centraliza o ciclo de vida do TCC: turma, cadastro, orientação, documentos, defesa, avaliação, correções, publicação e divulgação da agenda.

## Visão geral

O sistema substitui o controle disperso (planilhas, e-mails e documentos soltos) por um fluxo único, auditável e com acesso por perfil. Cursos contemplados: Engenharia de Computação, Licenciatura em Computação e Sistemas de Informação. Etapas: TCC1 e TCC2, nas modalidades artigo e monografia.

## Perfis de acesso

| Perfil | Atuação principal |
|---|---|
| Aluno | Cadastra e corrige o TCC, envia documentos, acompanha o andamento |
| Orientador | Aceita a orientação, acompanha o aluno, participa da banca |
| Professor da disciplina | Gerencia a turma e os alunos, agenda a banca (Sistemas de Informação) |
| Coordenador(a) / Secretaria | Analisa cadastros, gerencia contas e acompanha indicadores (mesmas permissões, muda só o rótulo) |
| Membro da banca | Registra nota, parecer e conceitos da defesa (inclui externos com conta limitada) |

## Módulos

1. **Usuários e acesso:** cadastro feito por perfil autorizado (sem autocadastro), conta criada sem senha com link de ativação válido por 48 h, login, redefinição de senha, autorização por perfil e vínculo, edição do próprio perfil e revogação de acesso do aluno 7 dias após a aprovação em TCC2. Contas limitadas para banca externa e coorientador externo.
2. **Interação e compartilhamento de ideias:** propostas de TCC de alunos e professores, direcionadas por professor ou área de interesse, com moderação.
3. **Gestão e acompanhamento dos TCCs:** turmas (TCC1 e TCC2), cadastro com protocolo único e rascunho, validação pela coordenação (aprovar, devolver, reprovar), vínculos de orientação, versionamento de documentos PDF e histórico cronológico.
4. **Gestão da defesa:** composição da banca (2 membros, orientador obrigatório, coorientador e suplente opcionais), agendamento com verificação de conflitos, avaliação por instrumento ponderado e versionado, ata e folha de aprovação em PDF, certificados, correções e encerramento.
5. **Gestão da publicação:** acompanhamento de submissão e publicação de artigos, com edição dos campos e histórico de alterações.
6. **Dashboard gerencial:** indicadores por situação, orientador, publicação, desistências e participação em banca, com exportação de relatório em PDF.
7. **Agenda e divulgação:** agenda pública de defesas autorizadas, sem expor PDFs, contatos, matrícula ou notas.

## Regras de destaque

- Senha com no mínimo 8 caracteres, com maiúscula, número e caractere especial.
- Bloqueio da conta por 15 minutos após 3 tentativas inválidas; sessão expira após 60 minutos de inatividade.
- Nota ponderada por critério = (nota × peso) ÷ 10; o avaliador escolhe o conceito (Exemplar, Competente, Necessita de Trabalho) e a nota fica restrita à faixa do conceito.
- Alterar o instrumento de avaliação gera nova versão e não afeta defesas já avaliadas.
- Falha de upload nunca remove a versão anterior válida do documento.
- Auditoria de alterações relevantes, com retenção mínima de 5 anos após a conclusão.

## Requisitos não funcionais

| Atributo | Meta |
|---|---|
| Desempenho | Cadastro de TCC em até 3 s (p95) com 30 submissões simultâneas; ata em PDF em até 5 s (p95) |
| Disponibilidade | 99% nos períodos de pico, com recuperação em até 30 min |
| Segurança | Senhas com hash e salt (bcrypt), HTTPS/TLS 1.2+, conformidade com a LGPD |
| Integridade | Sem protocolos duplicados; checksum SHA-256 dos arquivos |
| Responsividade | Telas a partir de 360 px, nas duas versões mais recentes do Chrome e do Safari mobile |

## Recursos previstos da API (sugestão)

| Área | Exemplos de recursos |
|---|---|
| Autenticação | `/auth/login`, `/auth/logout`, `/auth/ativar`, `/auth/redefinir-senha` |
| Usuários | `/usuarios`, `/usuarios/{id}`, `/usuarios/me` |
| Turmas | `/turmas`, `/turmas/{id}/alunos` |
| TCCs | `/tccs`, `/tccs/{id}`, `/tccs/{id}/submissao`, `/tccs/{id}/historico` |
| Orientação | `/tccs/{id}/orientacao`, `/tccs/{id}/coorientacao` |
| Documentos | `/tccs/{id}/documentos`, `/tccs/{id}/documentos/{versao}` |
| Defesas | `/defesas`, `/defesas/{id}/banca`, `/defesas/{id}/avaliacoes`, `/defesas/{id}/ata` |
| Publicação | `/tccs/{id}/publicacao`, `/tccs/{id}/publicacao/historico` |
| Indicadores | `/indicadores`, `/indicadores/relatorio` |
| Agenda | `/agenda` |

## Stack

- **Backend:** Python com FastAPI e SQLAlchemy, em `backend/`.
- **Frontend:** Next.js 16 (App Router) com Tailwind CSS, na raiz do repositório.
- **Banco de dados:** PostgreSQL em produção. Em desenvolvimento, sem configurar nada, a API usa um arquivo SQLite (`backend/siga_dev.db`). Troque pela variável `DATABASE_URL`.
- **Autenticação:** sessão guardada no banco, com token em cookie `httpOnly` e expiração de 60 minutos de inatividade. Senhas com bcrypt.
- **E-mail:** SMTP (variáveis `SMTP_*`). Sem SMTP configurado, o e-mail é impresso no terminal da API.

## Como rodar

São dois terminais: um para a API e um para o site.

**1. API** (PowerShell):

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```

O `python -m app.seed` aplica as migrações do banco (Alembic), depois cria os cursos, as áreas, os perfis e o primeiro coordenador (`coordenacao@uea.edu.br`). Ele imprime um **link de ativação**: abra esse link com o site no ar para definir a senha do coordenador. Para usar outro nome ou e-mail, defina `SEED_COORDENADOR_NOME` e `SEED_COORDENADOR_EMAIL` antes de rodar.

A API fica em `http://127.0.0.1:8000` e a documentação interativa em `http://127.0.0.1:8000/docs`.

**2. Site:**

```powershell
npm install
npm run dev
```

Abra `http://localhost:3000`. O site repassa tudo que começa com `/api/v1` para a API (ver `next.config.ts`).

Quando a coordenação cadastra alguém, o link de ativação dessa pessoa aparece no terminal da API (enquanto não houver SMTP configurado).

**Contas de demonstração:** para testar ou apresentar com todos os perfis sem esperar link de ativação, rode `python -m app.seed --demo`. Ele cria uma conta já ativa por perfil, todas com a senha `Siga@2026`:

| E-mail | Perfil |
|---|---|
| `coordenador@exemplo.com` | Coordenador |
| `professor@exemplo.com` | Professor da disciplina |
| `orientador@exemplo.com` | Orientador |
| `banca@exemplo.com` | Membro da banca |
| `aluno@exemplo.com` | Aluno |

Não use `--demo` no servidor de produção.

**Testes da API:**

```powershell
cd backend
python -m pytest
```

Os testes têm o nome da história e do critério de aceite que conferem, por exemplo `test_hu0106_ca3_bloqueio_apos_3_falhas_mesmo_com_senha_correta`.

Por padrão os testes usam um SQLite temporário. Para rodar a mesma suíte contra o PostgreSQL, aponte `TEST_DATABASE_URL` para um banco vazio (ele é apagado a cada teste):

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://usuario:senha@localhost:5432/siga_teste"
python -m pytest
```

**Banco de dados (migrações):**

O esquema do banco vem das migrações em `backend/migrations/versions/`, e não de `create_all`, para o PostgreSQL de produção e o SQLite de desenvolvimento terem as mesmas tabelas. Quem já tinha um `siga_dev.db` antigo não precisa apagar: o seed reconhece e atualiza.

```powershell
cd backend
alembic upgrade head                                  # aplica o que falta
alembic revision --autogenerate -m "o que mudou"      # depois de mudar app/models.py
```

O teste `test_migracoes_batem_com_os_modelos` falha se alguém mudar `models.py` sem criar a migração.

### Com Docker (PostgreSQL + API + site)

```powershell
docker compose up --build -d
docker compose run --rm api python -m app.seed
docker compose logs -f api
```

O seed imprime o link de ativação do primeiro coordenador. Site em `http://localhost:3000`, API em `http://localhost:8000/docs`. Em produção, defina `POSTGRES_PASSWORD`, `FRONTEND_URL`, `COOKIE_SEGURO=1` e as variáveis de SMTP, e coloque HTTPS na frente do site (RNF02).

### Variáveis de ambiente

| Variável | Onde | Padrão | Para que serve |
|---|---|---|---|
| `DATABASE_URL` | API | SQLite local | Banco. Ex.: `postgresql+psycopg://usuario:senha@host:5432/siga` |
| `FRONTEND_URL` | API | `http://localhost:3000` | Endereço usado nos links dos e-mails |
| `COOKIE_SEGURO` | API | `0` | Use `1` em produção (HTTPS) |
| `SMTP_HOST`, `SMTP_PORTA`, `SMTP_USUARIO`, `SMTP_SENHA`, `EMAIL_REMETENTE` | API | vazio | Envio real de e-mail |
| `API_URL` | Site | `http://127.0.0.1:8000` | Endereço da API |

## Onde fica cada coisa

```
backend/app/
  main.py            monta a API e registra as rotas em /api/v1
  config.py          configurações e regras numéricas (60 min, 48 h, 3 tentativas...)
  models.py          tabelas
  migracoes.py       aplica as migrações (usado pelo seed e pelos testes)
  schemas/           formato de entrada e saída de cada rota
  routes/            rotas: recebem a requisição e chamam um serviço
  services/          regras de negócio (usuários, perfil, áreas, autenticação, tokens, e-mail, auditoria)
  security.py        senha (bcrypt, regra de complexidade) e tokens
  deps.py            quem está logado e qual perfil a rota exige
  seed.py            carga inicial de desenvolvimento
backend/migrations/  migrações do banco (Alembic): 0001 esquema inicial, 0002 foto
backend/tests/       um teste por critério de aceite
docs/                modelo de dados (diagrama ER), script SQL do PostgreSQL e contrato da API

app/(publico)/       telas sem login: entrar, ativar, esqueci-senha, redefinir-senha (TEL01)
app/(sistema)/       telas com login: inicio, usuarios e perfil (TEL02)
components/          peças de interface reutilizadas (botão, campo, modal, casca...)
lib/                 api.ts (chamadas à API), sessao (usuário logado), tipos, regra de senha
proxy.ts             manda para o login quem abre tela interna sem cookie de sessão
```

## O que já está implementado

Sprint S02, épico EP01 (usuários e acesso):

| História | O que faz |
|---|---|
| HU01.01 | Cadastrar docentes e atribuir perfis |
| HU01.03 | Cadastrar alunos manualmente |
| HU01.04 | Regra de complexidade da senha, com lista de critérios na tela |
| HU01.05 | Ativação da conta por link de 48 horas, com reenvio |
| HU01.06 | Entrar e sair, bloqueio após 3 tentativas, sessão de 60 minutos |
| HU01.07 | Recuperação de senha por link |
| HU01.08 | Editar e inativar usuários, com auditoria |
| RBN01.01 | Foto do docente (opcional), incluída pela coordenação |
| RBN01.02 | Adicionar, renomear e excluir áreas de interesse (aba em Usuários e perfis) |
| RBN01.09 | Aluno edita telefone e foto em Meu perfil |
| RBN01.10 | Docente edita telefone, foto, curso e, se orienta ou dá a disciplina, as áreas de interesse |
| RBN01.04 | Troca de senha pelo próprio usuário, com a mesma regra de complexidade |
| RBN01.07 | Link de recuperação válido por 10 minutos |

Banco: PostgreSQL com migrações Alembic; a suíte inteira de testes passa também no PostgreSQL 16. Modelo de dados e contrato da API em [`docs/modelo-de-dados.md`](docs/modelo-de-dados.md). O DER completo do sistema (todos os módulos, 45 tabelas) está em [`docs/der/`](docs/der/der-siga-uea.md); as tabelas dos próximos módulos ganham migração quando cada módulo for implementado.

Ficam para os módulos seguintes, porque dependem deles: revogação do acesso do aluno 7 dias após a aprovação em TCC2 (RBN01.11), conta limitada de membro externo da banca (RBN01.12) e de coorientador externo (RBN01.13).

## Documentação

Os requisitos completos (módulos, RAN, RBN, regras de negócio e RNF) ficam na planilha **Requisitos_SIGA_UEA**, na pasta SIGA-NUCOMP. Os identificadores dos requisitos podem mudar durante a reorganização, então consulte sempre a versão vigente.

## Equipe

Davih Taumaturgo Soares · Igor Leite de Almeida · Igor Meireles de Lima Taveira · Matheus Maia Braga · Samuel Ogino Barbosa

Disciplina de Engenharia de Software · Escola Superior de Tecnologia (EST) · UEA, Manaus/AM
