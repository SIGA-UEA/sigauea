# SIGA UEA: API

API do **SIGA UEA**, sistema de gestão de Trabalhos de Conclusão de Curso (TCC) do NUCOMP, na Universidade do Estado do Amazonas (UEA). Foi desenvolvida na disciplina de Engenharia de Software e centraliza o ciclo de vida do TCC: turma, cadastro, orientação, documentos, defesa, avaliação, correções, publicação e divulgação da agenda.

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

## Stack e execução

- **Linguagem/framework:** Python com FastAPI (backend) e Next.js (frontend).
- **Banco de dados:** a definir.
- **Autenticação:** a definir.
- **Armazenamento de arquivos:** a definir.
- **E-mail:** a definir.

Para iniciar o backend no Windows usando PowerShell:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

A API fica disponível em `http://127.0.0.1:8000`; a documentação interativa fica em `http://127.0.0.1:8000/docs`.

## Documentação

Os requisitos completos (módulos, RAN, RBN, regras de negócio e RNF) ficam na planilha **Requisitos_SIGA_UEA**, na pasta SIGA-NUCOMP. Os identificadores dos requisitos podem mudar durante a reorganização, então consulte sempre a versão vigente.

## Equipe

Davih Taumaturgo Soares · Igor Leite de Almeida · Igor Meireles de Lima Taveira · Matheus Maia Braga · Samuel Ogino Barbosa

Disciplina de Engenharia de Software · Escola Superior de Tecnologia (EST) · UEA, Manaus/AM


This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
