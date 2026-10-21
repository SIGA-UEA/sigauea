# Preenchimento das seções "específico do doc" das fichas SCRUM-22, SCRUM-29 e SCRUM-30

Conteúdo para colar nas seções que estavam "A preencher" no documento de Histórias de Usuário (itens 1 a 4). Descreve o que já está implementado no repositório.

## SCRUM-22 · RBN01.02 · Gerenciar áreas de interesse

**Fluxo principal**
1. O Coordenador abre a TEL02 e clica na aba Áreas de interesse.
2. A lista mostra cada área e quantos docentes a usam.
3. Para criar, clica em Nova área, informa o nome e confirma.
4. Para renomear, clica em Renomear na linha, altera o nome e salva.
5. Para excluir, clica em Excluir; a confirmação informa quantos docentes perdem a área; o Coordenador confirma.
6. O sistema grava a alteração e registra a auditoria.

**Alternativos e exceções**
- A1. Nome já existente, mesmo com maiúsculas diferentes ("IA" e "ia"): o sistema recusa e informa a duplicidade.
- A2. Nome vazio ou com menos de 2 caracteres: o sistema destaca o campo e não salva.
- A3. Área em uso: a exclusão remove os vínculos com os docentes (sem vínculos órfãos) e o log guarda quais docentes foram desvinculados.
- E1. Usuário que não é Coordenador: a aba não aparece e a API responde 403.

**Como implementamos**

| Parte | O que foi feito |
|---|---|
| Banco | Tabela `area_interesse` (nome UNIQUE) e `docente_area` (vínculo docente × área). A exclusão apaga primeiro os vínculos e depois a área, na mesma transação. |
| API | `GET /api/v1/areas/gestao` (lista com a quantidade de docentes), `POST /api/v1/areas`, `PUT /api/v1/areas/{id}`, `DELETE /api/v1/areas/{id}`. Respostas: 201, 200, 204, 400, 403, 404 e 409 (nome repetido). A lista simples `GET /api/v1/areas` continua aberta aos usuários logados, para os formulários. |
| Tela | TEL02, aba Áreas de interesse: lista com contagem de docentes, botões Renomear e Excluir por linha, janela de confirmação com o impacto da exclusão. |

**Testes:** `backend/tests/test_perfil.py`, funções `test_rbn0102_*`.

## SCRUM-29 · RBN01.09 · Editar o próprio perfil (aluno)

**Fluxo principal**
1. O Aluno clica em Meu perfil no menu (ou na própria foto, no topo).
2. A tela mostra nome, e-mail, matrícula e curso somente para leitura.
3. O Aluno altera o telefone e clica em Salvar alterações.
4. Para a foto, clica em Adicionar foto (ou Trocar foto) e escolhe a imagem; o envio é imediato.
5. O sistema grava, registra a auditoria e atualiza a foto no topo da tela.

**Alternativos e exceções**
- A1. Remover foto: o botão Remover apaga a foto e volta para as iniciais.
- E1. Arquivo que não é JPG, PNG ou WebP (o conteúdo é conferido, não só a extensão) ou maior que 5 MB: o sistema recusa, informa o motivo e mantém a foto anterior.
- E2. Tentativa de alterar nome, e-mail, matrícula ou curso pela API: recusada (400 ou 403).
- E3. Não existe exclusão da própria conta nem edição do perfil de outra pessoa (403).

**Como implementamos**

| Parte | O que foi feito |
|---|---|
| Banco | `usuario.telefone`; tabela `foto_usuario` (bytes da imagem, tipo e SHA-256), uma por usuário (migração 0002). |
| API | `GET /api/v1/usuarios/me`, `PUT /api/v1/usuarios/me` (aceita só os campos permitidos), `PUT` e `DELETE /api/v1/usuarios/me/foto`, `GET /api/v1/usuarios/{id}/foto`. Respostas: 200, 400, 403, 413 (acima de 5 MB) e 415 (não é imagem). |
| Tela | Meu perfil (`/perfil`), abas Perfil e Senha. Também permite trocar a própria senha (regra do RBN01.04). |

**Testes:** `test_rbn0109_*`, `test_foto_*` e `test_ct_01_09_*` em `backend/tests/test_perfil.py`.

## SCRUM-30 · RBN01.10 · Editar o próprio perfil (docentes e membro da banca)

**Fluxo principal**
1. O docente clica em Meu perfil.
2. Altera telefone e foto; professor, orientador e membro da banca também alteram o curso.
3. Professor da disciplina e orientador marcam as áreas de interesse entre as cadastradas pela coordenação.
4. Clica em Salvar alterações; o sistema grava e registra a auditoria de cada campo alterado.

**Alternativos e exceções**
- A1. Coordenador: o campo curso não é oferecido, porque ele acessa todos os cursos do núcleo; a API recusa a alteração (403).
- A2. Membro da banca ou coordenador sem perfil de professor ou orientador: o campo áreas não é oferecido e a API recusa (403).
- E1. Tentativa de alterar nome ou e-mail pela API: recusada (400).
- E2. Edição do perfil de outra pessoa: recusada (403).

**Como implementamos**

| Parte | O que foi feito |
|---|---|
| Banco | `usuario.telefone`, `docente.curso_id`, `docente_area` e `foto_usuario`. |
| API | As mesmas rotas da SCRUM-29. `PUT /api/v1/usuarios/me` aceita `telefone`, `curso_id` (exceto coordenador) e `areas` (só professor da disciplina e orientador). |
| Tela | Meu perfil (`/perfil`), com o seletor de curso e os botões de áreas de interesse quando o perfil permite. |

**Testes:** `test_rbn0110_*` e `test_scrum30_*` em `backend/tests/test_perfil.py`.

O caso de teste CT-01.10-06 (proposta direcionada à área aparece para o professor) depende do módulo de ideias (RBN02.01), que ainda não existe.
