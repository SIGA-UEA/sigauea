# Matriz CT × teste (RBN01.01 a RBN01.10, RBN03.01 a RBN03.04 e RBN06.01)

Gerada a partir dos casos de teste das fichas do JIRA e dos testes em `backend/tests`. O ID do CT está no nome de cada teste (`test_ct_01_06_04_...`); os que cobrem mais de um CT listam todos na docstring.

**Resumo:** 79 cobertos, 12 parciais, 9 manuais (tela, carga), 2 pendentes (dependem de funcionalidade que não existe) — total 102.

Para rodar: `cd backend && pytest -v` (SQLite temporário) ou `TEST_DATABASE_URL=... pytest` (PostgreSQL).

Situações: **Coberto** = teste automatizado confere o resultado esperado; **Parcial** = confere via API ou com tempo simulado (ver observação); **Manual** = precisa da tela ou de ambiente de carga; **Pendente** = a funcionalidade ainda não existe.


## RBN01.01

| CT | Tipo | Passos | Situação | Teste | Observação |
| --- | --- | --- | --- | --- | --- |
| CT-01.01-01 | Funcional | Cadastrar "Maria Silva", e-mail institucional, cargo Orientador, curso EC | Parcial | test_usuarios.py::test_ct_01_01_01_docente_nasce_inativo_e_sem_senha | Cria e confere o estado; o e-mail é conferido em CT-01.05-01. |
| CT-01.01-02 | Negativo | Enviar sem e-mail | Coberto | test_usuarios.py::test_ct_01_01_02_campo_obrigatorio_vazio_responde_400 | — |
| CT-01.01-03 | Negativo | Cadastrar com o mesmo e-mail | Coberto | test_usuarios.py::test_ct_01_01_03_email_duplicado_ignora_maiusculas | — |
| CT-01.01-04 | Funcional | Atribuir também perfil coordenador | Coberto | test_cts_complementares.py::test_ct_01_01_04_docente_recebe_tambem_o_perfil_de_coordenador | — |
| CT-01.01-05 | Funcional | Cadastrar cargo Coordenador sem curso | Coberto | test_usuarios.py::test_ct_01_01_05_coordenador_nao_exige_curso | — |
| CT-01.01-06 | Segurança | POST de cadastro de docente | Coberto | test_usuarios.py::test_ct_01_01_06_quem_nao_e_coordenador_recebe_403 | — |
| CT-01.01-07 | Auditoria | Consultar log | Coberto | test_usuarios.py::test_ct_01_01_07_criacao_fica_no_log | — |
| CT-01.01-08 | Não funcional | Preencher formulário | Manual | — | Manual: abrir a tela em 360 px (e 768 px) e conferir que não há rolagem horizontal. |

## RBN01.02

| CT | Tipo | Passos | Situação | Teste | Observação |
| --- | --- | --- | --- | --- | --- |
| CT-01.02-01 | Funcional | Adicionar "Computação Quântica" | Parcial | test_perfil.py::test_ct_01_02_01_e_01_02_07_coordenador_cria_renomeia_e_exclui_area | Via API; a seleção na tela é manual. |
| CT-01.02-02 | Negativo | Adicionar "IA" novamente | Coberto | test_perfil.py::test_ct_01_02_02_nome_repetido_ignora_maiusculas | — |
| CT-01.02-03 | Negativo | Adicionar nome vazio | Coberto | test_cts_complementares.py::test_ct_01_02_03_area_com_nome_vazio_e_recusada | — |
| CT-01.02-04 | Funcional | Renomear | Coberto | test_cts_complementares.py::test_ct_01_02_04_renomear_area_vale_para_os_docentes_vinculados | — |
| CT-01.02-05 | Funcional | Excluir e confirmar/cancelar | Coberto | test_perfil.py::test_ct_01_02_05_excluir_area_em_uso_desvincula_docentes | — |
| CT-01.02-06 | Segurança | Chamar endpoint de exclusão | Coberto | test_perfil.py::test_ct_01_02_06_so_coordenador_gerencia_areas | — |
| CT-01.02-07 | Auditoria | Consultar log | Coberto | test_perfil.py::test_ct_01_02_01_e_01_02_07_coordenador_cria_renomeia_e_exclui_area | — |

## RBN01.03

| CT | Tipo | Passos | Situação | Teste | Observação |
| --- | --- | --- | --- | --- | --- |
| CT-01.03-01 | Funcional | Cadastrar aluno completo | Parcial | test_usuarios.py::test_ct_01_03_01_aluno_nasce_sem_senha_com_perfil_aluno | Cria e ativa; a inclusão na turma é outro passo (RBN08.02). |
| CT-01.03-02 | Negativo | Omitir matrícula | Coberto | test_cts_complementares.py::test_ct_01_03_02_aluno_sem_matricula_e_recusado | — |
| CT-01.03-03 | Negativo | Repetir matrícula | Coberto | test_usuarios.py::test_ct_01_03_03_indica_o_campo_duplicado | — |
| CT-01.03-04 | Funcional | Cadastrar aluno de SI | Coberto | test_tcc.py::test_ct_01_03_04_aluno_de_outro_curso_entra_e_mantem_o_curso | — |
| CT-01.03-05 | Segurança | Chamar endpoint | Coberto | test_cts_complementares.py::test_ct_01_03_05_aluno_nao_cadastra_aluno | — |
| CT-01.03-06 | Auditoria | Consultar log | Coberto | test_usuarios.py::test_ct_01_03_06_e_01_05_01_enfileira_ativacao_e_audita | — |

## RBN01.04

| CT | Tipo | Passos | Situação | Teste | Observação |
| --- | --- | --- | --- | --- | --- |
| CT-01.04-01 | Funcional | Definir "Siga@2026" | Coberto | test_acesso.py::test_ct_01_04_01_e_01_04_06_senha_gravada_com_bcrypt_e_nunca_devolvida | — |
| CT-01.04-02 | Negativo | Definir "siga2026" (sem maiúscula/especial) | Coberto | test_acesso.py::test_ct_01_04_02_a_01_04_04_criterios_da_senha | — |
| CT-01.04-03 | Limite | Definir "Aa1!aaa" (7 caracteres) | Coberto | test_acesso.py::test_ct_01_04_02_a_01_04_04_criterios_da_senha | — |
| CT-01.04-04 | Limite | Definir "Aa1!aaaa" (8 caracteres) | Coberto | test_acesso.py::test_ct_01_04_02_a_01_04_04_criterios_da_senha | — |
| CT-01.04-05 | Segurança | POST direto com senha fraca | Coberto | test_acesso.py::test_ct_01_04_05_ativacao_recusa_senha_fraca_e_lista_criterios | — |
| CT-01.04-06 | Segurança | Inspecionar coluna de senha e logs | Coberto | test_acesso.py::test_ct_01_04_01_e_01_04_06_senha_gravada_com_bcrypt_e_nunca_devolvida | — |

## RBN01.05

| CT | Tipo | Passos | Situação | Teste | Observação |
| --- | --- | --- | --- | --- | --- |
| CT-01.05-01 | Integração | Cadastrar docente | Coberto | test_usuarios.py::test_ct_01_03_06_e_01_05_01_enfileira_ativacao_e_audita | — |
| CT-01.05-02 | Funcional | Definir senha válida | Coberto | test_acesso.py::test_ct_01_05_02_e_01_05_04_link_ativa_a_conta_e_vale_uma_vez | — |
| CT-01.05-03 | Limite | Acessar link | Parcial | test_acesso.py::test_ct_01_05_03_link_expirado | Tempo simulado: a expiração é antecipada no banco. |
| CT-01.05-04 | Negativo | Acessar novamente | Coberto | test_acesso.py::test_ct_01_05_02_e_01_05_04_link_ativa_a_conta_e_vale_uma_vez | — |
| CT-01.05-05 | Segurança | Tentar login | Coberto | test_acesso.py::test_ct_01_05_05_conta_nao_ativada_recebe_a_mesma_mensagem | — |
| CT-01.05-06 | Resiliência | Cadastrar e reenviar | Coberto | test_acesso.py::test_ct_01_05_06_falha_de_email_nao_desfaz_cadastro_e_permite_reenvio | — |

## RBN01.06

| CT | Tipo | Passos | Situação | Teste | Observação |
| --- | --- | --- | --- | --- | --- |
| CT-01.06-01 | Funcional | Login correto | Coberto | test_acesso.py::test_ct_01_06_01_login_devolve_usuario_e_cookie_httponly | — |
| CT-01.06-02 | Negativo | Senha errada | Coberto | test_acesso.py::test_ct_01_06_02_e_01_06_03_mesma_mensagem_para_email_ou_senha_errados | — |
| CT-01.06-03 | Negativo | E-mail inexistente | Coberto | test_acesso.py::test_ct_01_06_02_e_01_06_03_mesma_mensagem_para_email_ou_senha_errados | — |
| CT-01.06-04 | Limite | 3 falhas + 1 tentativa correta | Coberto | test_acesso.py::test_ct_01_06_04_e_01_06_05_bloqueio_apos_3_falhas_mesmo_com_senha_correta | — |
| CT-01.06-05 | Limite | Aguardar 15 min e tentar | Parcial | test_acesso.py::test_ct_01_06_04_e_01_06_05_bloqueio_apos_3_falhas_mesmo_com_senha_correta | Tempo simulado: o bloqueio é antecipado no banco. |
| CT-01.06-06 | Negativo | Enviar com campos vazios | Parcial | test_cts_complementares.py::test_ct_01_06_06_login_com_campos_vazios_e_recusado | A API recusa; o destaque do campo na tela é manual. |
| CT-01.06-07 | Funcional | Ficar 60 min inativo; abrir página restrita | Parcial | test_acesso.py::test_ct_01_06_07_sessao_expira_por_inatividade_e_renova_com_uso | Tempo simulado: a expiração da sessão é antecipada no banco. |
| CT-01.06-08 | Segurança | Tentar login | Coberto | test_usuarios.py::test_ct_01_08_03_e_01_08_04_inativado_nao_entra_e_reativado_volta | — |
| CT-01.06-09 | Não funcional | Usar a tela de login | Manual | — | Manual: abrir a tela em 360 px (e 768 px) e conferir que não há rolagem horizontal. |

## RBN01.07

| CT | Tipo | Passos | Situação | Teste | Observação |
| --- | --- | --- | --- | --- | --- |
| CT-01.07-01 | Integração | Solicitar recuperação | Coberto | test_acesso.py::test_ct_01_07_01_e_01_07_02_resposta_igual_e_email_so_para_cadastrado | — |
| CT-01.07-02 | Segurança | Solicitar com e-mail inexistente | Coberto | test_acesso.py::test_ct_01_07_01_e_01_07_02_resposta_igual_e_email_so_para_cadastrado | — |
| CT-01.07-03 | Funcional | Definir "Nova@2026" | Coberto | test_acesso.py::test_ct_01_07_03_e_01_07_04_e_01_07_06_troca_a_senha_desbloqueia_e_link_nao_se_repete | — |
| CT-01.07-04 | Negativo | Reabrir link | Coberto | test_acesso.py::test_ct_01_07_03_e_01_07_04_e_01_07_06_troca_a_senha_desbloqueia_e_link_nao_se_repete | — |
| CT-01.07-05 | Limite | Acessar | Parcial | test_acesso.py::test_ct_01_07_05_link_de_recuperacao_vencido_e_recusado | Tempo simulado: a expiração é antecipada no banco. |
| CT-01.07-06 | Negativo | Definir "abc" | Coberto | test_acesso.py::test_ct_01_07_03_e_01_07_04_e_01_07_06_troca_a_senha_desbloqueia_e_link_nao_se_repete | — |

## RBN01.08

| CT | Tipo | Passos | Situação | Teste | Observação |
| --- | --- | --- | --- | --- | --- |
| CT-01.08-01 | Funcional | Alterar telefone e vínculo | Coberto | test_usuarios.py::test_ct_01_08_01_e_01_08_06_edicao_auditada_com_valor_anterior_e_novo | — |
| CT-01.08-02 | Negativo | Alterar e-mail para o do outro | Coberto | test_usuarios.py::test_ct_01_08_02_email_ou_matricula_de_outra_pessoa | — |
| CT-01.08-03 | Funcional | Inativar | Coberto | test_usuarios.py::test_ct_01_08_03_e_01_08_04_inativado_nao_entra_e_reativado_volta | — |
| CT-01.08-04 | Funcional | Reativar | Coberto | test_usuarios.py::test_ct_01_08_03_e_01_08_04_inativado_nao_entra_e_reativado_volta | — |
| CT-01.08-05 | Segurança | Editar outro usuário | Coberto | test_cts_complementares.py::test_ct_01_08_05_aluno_nao_edita_outro_usuario | — |
| CT-01.08-06 | Auditoria | Consultar log | Coberto | test_usuarios.py::test_ct_01_08_01_e_01_08_06_edicao_auditada_com_valor_anterior_e_novo | — |

## RBN01.09

| CT | Tipo | Passos | Situação | Teste | Observação |
| --- | --- | --- | --- | --- | --- |
| CT-01.09-01 | Funcional | Alterar telefone e foto | Coberto | test_perfil.py::test_ct_01_09_01_e_01_09_02_aluno_edita_telefone_mas_nao_o_curso<br>test_perfil.py::test_ct_01_09_01_foto_aceita_jpg_png_webp_e_pode_ser_removida | — |
| CT-01.09-02 | Segurança | PUT com matrícula alterada | Coberto | test_perfil.py::test_ct_01_09_01_e_01_09_02_aluno_edita_telefone_mas_nao_o_curso | — |
| CT-01.09-03 | Negativo | Enviar arquivo .exe como foto | Coberto | test_perfil.py::test_ct_01_09_03_foto_recusa_arquivo_que_nao_e_imagem_mesmo_com_extensao_certa<br>test_perfil.py::test_ct_01_09_03_foto_recusada_mantem_a_anterior | — |
| CT-01.09-04 | Segurança | DELETE da própria conta | Coberto | test_perfil.py::test_ct_01_09_04_aluno_nao_exclui_a_propria_conta | — |
| CT-01.09-05 | Segurança | Editar perfil do aluno B | Coberto | test_perfil.py::test_ct_01_09_05_e_01_10_05_ninguem_edita_o_perfil_de_outro | — |
| CT-01.09-06 | Não funcional | Editar perfil | Manual | — | Manual: abrir a tela em 360 px (e 768 px) e conferir que não há rolagem horizontal. |

## RBN01.10

| CT | Tipo | Passos | Situação | Teste | Observação |
| --- | --- | --- | --- | --- | --- |
| CT-01.10-01 | Funcional | Alterar telefone, foto e curso | Coberto | test_perfil.py::test_ct_01_10_01_e_01_10_02_docente_edita_telefone_curso_e_areas | — |
| CT-01.10-02 | Funcional | Selecionar "IA" e "Ciência de Dados" | Coberto | test_perfil.py::test_ct_01_10_01_e_01_10_02_docente_edita_telefone_curso_e_areas | — |
| CT-01.10-03 | Funcional | Abrir perfil | Parcial | test_perfil.py::test_ct_01_10_03_membro_da_banca_nao_escolhe_areas | A API recusa as áreas; a ausência do campo na tela é manual. |
| CT-01.10-04 | Segurança | PUT alterando e-mail | Coberto | test_perfil.py::test_ct_01_10_04_nome_e_email_so_a_coordenacao_altera | — |
| CT-01.10-05 | Segurança | Editar perfil do B | Coberto | test_perfil.py::test_ct_01_09_05_e_01_10_05_ninguem_edita_o_perfil_de_outro | — |
| CT-01.10-06 | Integração | Professor vinculado à IA consulta propostas | Pendente | test_cts_complementares.py::test_ct_01_10_06_professor_ve_as_propostas_da_sua_area | Pendente: depende do módulo de ideias e propostas (RBN02.01). |

## RBN03.01

| CT | Tipo | Passos | Situação | Teste | Observação |
| --- | --- | --- | --- | --- | --- |
| CT-03.01-01 | Funcional | Abrir TEL05 | Parcial | test_tcc.py::test_ct_03_01_01_formulario_traz_turma_orientadores_e_areas | A API devolve os dados; a exibição na tela é manual. |
| CT-03.01-02 | Limite | Resumo com 501 palavras | Coberto | test_tcc.py::test_ct_03_01_02_e_03_01_03_resumo_ate_500_palavras_e_ate_10_palavras_chave | — |
| CT-03.01-03 | Limite | 11 palavras-chave | Coberto | test_tcc.py::test_ct_03_01_02_e_03_01_03_resumo_ate_500_palavras_e_ate_10_palavras_chave | — |
| CT-03.01-04 | Funcional | Salvar com só o título | Coberto | test_tcc.py::test_ct_03_01_04_e_03_04_02_e_06_01_01_rascunho_sem_protocolo_e_vinculo_pendente | — |
| CT-03.01-05 | Funcional | Omitir subtítulo e coorientador | Coberto | test_tcc.py::test_ct_03_01_04_e_03_04_02_e_06_01_01_rascunho_sem_protocolo_e_vinculo_pendente | — |
| CT-03.01-06 | Integração | Salvar | Coberto | test_cts_complementares.py::test_ct_03_01_06_aluno_de_outro_curso_salva_o_cadastro_e_mantem_o_curso | — |
| CT-03.01-07 | Não funcional | Preencher e salvar | Manual | — | Manual: abrir a tela em 360 px (e 768 px) e conferir que não há rolagem horizontal. |
| CT-03.01-08 | Integração | Enviar formulário completo (monografia) | Parcial | test_tcc.py::test_ct_03_01_08_editar_rascunho_audita_cada_campo | Via API; o clique na tela é manual. |

## RBN03.02

| CT | Tipo | Passos | Situação | Teste | Observação |
| --- | --- | --- | --- | --- | --- |
| CT-03.02-01 | Funcional | Selecionar "artigo" | Manual | — | Manual: conferir na tela que os campos editoriais aparecem em artigo. |
| CT-03.02-02 | Funcional | Selecionar "monografia" | Manual | — | Manual: conferir na tela que os campos editoriais não aparecem em monografia. |
| CT-03.02-03 | Integração | Enviar cadastro | Coberto | test_tcc.py::test_ct_03_02_03_e_03_02_04_artigo_publicado_exige_doi | — |
| CT-03.02-04 | Negativo | Enviar sem DOI | Coberto | test_tcc.py::test_ct_03_02_03_e_03_02_04_artigo_publicado_exige_doi | — |
| CT-03.02-05 | Funcional | Enviar sem DOI | Coberto | test_cts_complementares.py::test_ct_03_02_05_artigo_submetido_nao_exige_doi | — |
| CT-03.02-06 | Segurança | POST com situação "xyz" | Coberto | test_cts_complementares.py::test_ct_03_02_06_situacao_editorial_fora_dos_valores_previstos_e_recusada | — |
| CT-03.02-07 | Funcional | Trocar para monografia | Manual | — | Manual: trocar para monografia na tela e conferir que os campos somem. |

## RBN03.03

| CT | Tipo | Passos | Situação | Teste | Observação |
| --- | --- | --- | --- | --- | --- |
| CT-03.03-01 | Funcional | Submeter | Coberto | test_tcc.py::test_ct_03_03_01_e_03_03_06_e_03_04_01_submissao_gera_protocolo_unico_e_repetir_nao_duplica | — |
| CT-03.03-02 | Negativo | Submeter | Coberto | test_tcc.py::test_ct_03_03_02_campos_obrigatorios | — |
| CT-03.03-03 | Negativo | Submeter | Coberto | test_tcc.py::test_ct_03_03_03_desistente_nao_submete | — |
| CT-03.03-04 | Funcional | Submeter novamente | Coberto | test_cts_complementares.py::test_ct_03_03_04_aluno_incluido_na_turma_passa_a_poder_submeter | — |
| CT-03.03-05 | Funcional | Submeter | Coberto | test_tcc.py::test_ct_03_03_01_e_03_03_06_e_03_04_01_submissao_gera_protocolo_unico_e_repetir_nao_duplica | — |
| CT-03.03-06 | Resiliência | Duplo clique em "Enviar" | Coberto | test_tcc.py::test_ct_03_03_01_e_03_03_06_e_03_04_01_submissao_gera_protocolo_unico_e_repetir_nao_duplica | — |
| CT-03.03-07 | Desempenho | Teste de carga | Manual | — | Manual: teste de carga com 30 usuários (p95 ≤ 3 s) em ambiente à parte. |
| CT-03.03-08 | Integração | Submeter | Parcial | test_tcc.py::test_ct_03_03_01_e_03_03_06_e_03_04_01_submissao_gera_protocolo_unico_e_repetir_nao_duplica | Via API; o clique na tela é manual. |

## RBN03.04

| CT | Tipo | Passos | Situação | Teste | Observação |
| --- | --- | --- | --- | --- | --- |
| CT-03.04-01 | Funcional | Submeter | Coberto | test_tcc.py::test_ct_03_03_01_e_03_03_06_e_03_04_01_submissao_gera_protocolo_unico_e_repetir_nao_duplica | — |
| CT-03.04-02 | Funcional | Consultar TCC | Coberto | test_tcc.py::test_ct_03_01_04_e_03_04_02_e_06_01_01_rascunho_sem_protocolo_e_vinculo_pendente | — |
| CT-03.04-03 | Resiliência | Reenviar a mesma requisição | Coberto | test_tcc.py::test_ct_03_03_01_e_03_03_06_e_03_04_01_submissao_gera_protocolo_unico_e_repetir_nao_duplica | — |
| CT-03.04-04 | Negativo | Nova submissão do mesmo aluno | Coberto | test_tcc.py::test_ct_03_04_04_um_cadastro_por_periodo | — |
| CT-03.04-05 | Concorrência | Submissões simultâneas | Coberto | test_cts_complementares.py::test_ct_03_04_05_submissoes_simultaneas_geram_protocolos_distintos | — |
| CT-03.04-06 | Auditoria | Consultar log | Coberto | test_tcc.py::test_ct_03_03_01_e_03_03_06_e_03_04_01_submissao_gera_protocolo_unico_e_repetir_nao_duplica | — |
| CT-03.04-07 | Integração | Submeter pela tela | Manual | — | Manual: submeter pela tela e conferir protocolo e dados. |

## RBN06.01

| CT | Tipo | Passos | Situação | Teste | Observação |
| --- | --- | --- | --- | --- | --- |
| CT-06.01-01 | Funcional | Selecionar no cadastro | Coberto | test_tcc.py::test_ct_03_01_04_e_03_04_02_e_06_01_01_rascunho_sem_protocolo_e_vinculo_pendente | — |
| CT-06.01-02 | Funcional | Abrir lista | Coberto | test_cts_complementares.py::test_ct_06_01_02_orientador_inativo_nao_aparece_na_lista | — |
| CT-06.01-03 | Negativo | Submeter | Coberto | test_cts_complementares.py::test_ct_06_01_03_nao_submete_sem_orientador | — |
| CT-06.01-04 | Funcional | Substituir orientador | Pendente | test_cts_complementares.py::test_ct_06_01_04_substituir_orientador_preserva_o_historico | Pendente: não existe rota nem tela para a coordenação trocar o orientador após o aceite. |
| CT-06.01-05 | Segurança | Alterar orientação do TCC do aluno A | Coberto | test_cts_complementares.py::test_ct_06_01_05_aluno_de_outro_cadastro_nao_altera_a_orientacao | — |
| CT-06.01-06 | Auditoria | Consultar log | Coberto | test_cts_complementares.py::test_ct_06_01_06_vinculo_de_orientacao_fica_no_log | — |
