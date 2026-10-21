"""Dicionário de Dados no formato dos documentos do grupo (.docx e .pdf).

    python docs/modelagem/dicionario_dados.py

Gera docs/modelagem/Dicionario_de_Dados_SIGA_UEA.{docx,pdf} a partir do modelo lógico
(modelo_logico.py): as mesmas 46 tabelas do DER, com a descrição de cada coluna.
"""

from __future__ import annotations

import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI.parent / "arquitetura"))
import modelo_logico as ml  # noqa: E402
from documentos import CLIENTE, DATA, INSTITUICAO, PROJETO, REF_PLANO, REF_REQ, finais  # noqa: E402
from formato_siga import EQUIPE, Doc, gerar  # noqa: E402

# ---------------------------------------------------------------- descrição das colunas
# Por nome de coluna; "tabela.coluna" vale só para aquela tabela.
DESC = {
    "id": "Identificador do registro, gerado pelo banco.",
    "criado_em": "Data e hora em que o registro foi criado.",
    "atualizado_em": "Data e hora da última alteração.",
    "registrado_em": "Data e hora do registro.",
    "nome": "Nome.",
    "sigla": "Sigla.",
    "titulo": "Título.",
    "subtitulo": "Subtítulo (opcional).",
    "descricao": "Descrição.",
    "texto": "Texto escrito pelo autor.",
    "motivo": "Motivo informado.",
    "justificativa": "Justificativa da decisão.",
    "parecer": "Parecer escrito.",
    "observacao": "Observação sobre a mudança.",
    "ordem": "Posição na lista.",
    "versao": "Número da versão; aumenta a cada nova versão.",
    "vigente": "Indica a versão que vale hoje; as anteriores ficam como histórico.",
    "sha256": "Resumo SHA-256 do arquivo, conferido no envio e na leitura (RNF06).",
    "caminho": "Local onde o arquivo está guardado.",
    "expira_em": "Data e hora em que deixa de valer.",
    "usado_em": "Data e hora em que o link foi usado; o link vale uma única vez.",
    "revogado_em": "Data e hora em que o acesso foi revogado antes do prazo.",
    "token_hash": "Resumo do token; o valor do link não é guardado.",
    "entidade": "Tipo do registro relacionado.",
    "entidade_id": "Identificador do registro relacionado.",
    "campo": "Campo alterado.",
    "acao": "Ação realizada (ex.: criar, editar, entrar).",
    "valor_anterior": "Valor antes da alteração.",
    "valor_novo": "Valor depois da alteração.",
    "tentativas": "Quantas vezes o envio foi tentado.",
    "erro": "Mensagem do último erro de envio.",
    "destinatario": "Endereço de e-mail de destino.",
    "enviado_em": "Data e hora do envio.",
    "decidido_em": "Data e hora da decisão.",
    "decidida_em": "Data e hora da decisão.",
    "confirmado_em": "Data e hora da confirmação.",
    "respondido_em": "Data e hora da resposta.",
    "solicitado_em": "Data e hora do pedido.",
    "encerrado_em": "Data e hora do encerramento do vínculo.",
    "encerrada_em": "Data e hora do encerramento.",
    "gerado_em": "Data e hora da geração do documento.",
    "substituido_em": "Data e hora em que foi substituído por uma nova versão.",
    "alterada_em": "Data e hora da última correção.",
    "publicada_em": "Data e hora da publicação na agenda.",
    "enviada_em": "Data e hora do envio.",
    "entregue_em": "Data e hora da entrega.",
    "incluido_em": "Data e hora da inclusão.",
    "atribuido_em": "Data e hora da atribuição.",
    "inativado_em": "Data e hora da inativação; vazio enquanto a conta está ativa.",
    "oculta_em": "Data e hora em que a coordenação ocultou a proposta (moderação).",
    "oculto_em": "Data e hora em que a coordenação ocultou o comentário (moderação).",
    "matricula": "Matrícula do aluno na UEA.",
    "telefone": "Telefone de contato (opcional).",
    "ativo": "Indica se a conta pode entrar no sistema.",
    "tentativas_falhas": "Tentativas de login erradas seguidas; a 3ª bloqueia a conta.",
    "bloqueado_ate": "Fim do bloqueio de 15 minutos após 3 tentativas erradas.",
    "instituicao": "Instituição de origem da pessoa externa.",
    "cargo": "Cargo do docente.",
    "palavra": "Palavra-chave.",
    "conteudo": "Conteúdo do arquivo da imagem.",
    "nome_arquivo": "Nome original do arquivo enviado.",
    "inicio": "Início.",
    "fim": "Fim.",
    "data": "Data.",
    "link": "Endereço da sala virtual.",
    "prazo": "Data limite.",
    "nota": "Nota de 0 a 10.",
    "nota_final": "Nota final de 0 a 10.",
    "nota_total": "Soma das notas ponderadas do avaliador.",
    "media": "Média das notas dos avaliadores.",
    "peso": "Peso do critério na nota.",
    "pontos": "Pontos máximos da parte.",
    "qualis": "Estrato Qualis do veículo (ex.: A1, B2).",
    "doi": "DOI do artigo; obrigatório quando publicado.",
    "veiculo": "Nome do periódico ou do congresso.",
    "interno": "Indica se o membro é da UEA.",
    "divulgar_link": "Indica se o link da sala virtual aparece na agenda pública.",
    "texto_exemplar": "Descrição do conceito Exemplar no critério.",
    "texto_competente": "Descrição do conceito Competente no critério.",
    "texto_necessita": "Descrição do conceito Necessita melhorar no critério.",
    "motivo_recusa": "Motivo da recusa da orientação.",
    "justificativa_encerramento": "Por que o vínculo foi encerrado ou substituído.",
    "motivo_convocacao": "Por que o suplente foi chamado.",
    "motivo_retificacao": "Por que o resultado foi retificado.",
    "prazo_versao_final": "Data limite para entregar a versão final corrigida.",
    "prazo_motivo": "Por que o prazo da versão final foi diferente do padrão.",
    "anuencia_em": "Data e hora em que o aluno concordou com as correções exigidas.",
    "entregue_com_atraso": "Indica se a versão final foi entregue depois do prazo.",
    "atraso_aceito": "Decisão sobre a entrega com atraso.",
    "atraso_decidido_em": "Data e hora da decisão sobre o atraso.",
    "convite_enviado_em": "Data e hora do envio do convite para a banca.",
    "situacao_alterada_em": "Data e hora da última mudança de situação.",
    "situacao_anterior": "Situação antes da mudança.",
    "situacao_nova": "Situação depois da mudança.",
    "submetido_em": "Data e hora da última submissão do cadastro.",
    "concluido_em": "Data e hora da conclusão do TCC.",
    "desistencia_motivo": "Motivo da desistência.",
    "valores_anteriores": "Data, horário, local e banca antes da mudança.",
    "codigo": "Código.",
    "tipo": "Tipo.",
    "situacao": "Situação.",
    "status": "Situação.",
    # por tabela
    "nucleo.sigla": "Sigla do núcleo (ex.: NUCOMP).",
    "curso.sigla": "Sigla do curso.",
    "perfil.codigo": "Código do perfil, usado nas permissões.",
    "periodo_letivo.codigo": "Período no formato AAAA/N.",
    "periodo_letivo.inicio": "Primeiro dia do período.",
    "periodo_letivo.fim": "Último dia do período.",
    "turma.codigo": "Código da turma, formado por curso, disciplina e período.",
    "turma.disciplina": "Etapa da turma.",
    "usuario.email": "E-mail de acesso; único, sem diferenciar maiúsculas.",
    "usuario.senha_hash": "Senha guardada com bcrypt; a senha em si nunca é guardada.",
    "foto_usuario.tipo": "Formato da imagem, conferido pelo conteúdo do arquivo.",
    "token_usuario.tipo": "Finalidade do link.",
    "notificacao_email.tipo": "Assunto do aviso (ex.: ativação, orientação).",
    "documento_oficial.tipo": "Tipo do documento gerado.",
    "defesa.data": "Dia da defesa.",
    "defesa.inicio": "Horário de início.",
    "historico_publicacao.data": "Data em que a situação editorial mudou.",
    "componente_avaliacao.nome": "Nome da parte da avaliação.",
    "criterio_avaliacao.nome": "Nome do critério.",
    "local_defesa.descricao": "Detalhes do local (bloco, andar).",
    "tarefa_tcc.descricao": "O que deve ser entregue.",
    "correcao.descricao": "Correção exigida pela banca.",
    "correcao.justificativa": "Justificativa ao devolver a correção.",
    "ouvinte_defesa.nome": "Nome do ouvinte.",
    "ouvinte_defesa.matricula": "Matrícula do ouvinte, se for aluno da UEA.",
    "tcc.protocolo": "Protocolo único do cadastro.",
    "tcc.resumo": "Resumo do trabalho.",
    "tcc.etapa": "Etapa do TCC.",
    "tcc.modalidade": "Modalidade do trabalho.",
    "proposta.destino": "Para quem a proposta é mostrada.",
    "acesso_limitado.escopo": "O que a conta limitada pode acessar.",
    "orientacao.papel": "Papel do docente no TCC.",
    "banca_membro.papel": "Papel na banca.",
    "banca_membro.presente": "Presença na defesa.",
    "avaliacao_criterio.conceito": "Conceito dado no critério.",
    "avaliacao_criterio.nota_ponderada": "Nota do critério multiplicada pelo peso.",
    "resultado_defesa.resultado": "Resultado da defesa.",
    "resultado_defesa.regra_qualis": "Indica se valeu a regra do artigo com Qualis (RN21).",
    "historico_defesa.evento": "O que aconteceu com a defesa.",
    "documento_tcc.finalidade": "Para que a versão foi enviada.",
    "documento_tcc.tamanho_bytes": "Tamanho do arquivo em bytes.",
    "publicacao_artigo.tipo_veiculo": "Tipo do veículo.",
    "publicacao_artigo.situacao_atual": "Situação editorial atual.",
    "denuncia.situacao": "Situação da denúncia.",
    "defesa.formato": "Como a defesa acontece.",
    "defesa.situacao": "Situação do agendamento.",
    "defesa.publicada": "Indica se a defesa aparece na agenda pública.",
    "defesa.revisao_banca": "Indica que a banca precisa ser revista porque o orientador mudou.",
    "defesa.lembrete_enviado_em": "Data e hora do lembrete enviado na véspera.",
    "instrumento_avaliacao.versao": "Número da versão do instrumento.",
    "aluno.acesso_ate": "Último dia de acesso do aluno.",
}

# Como a referência a outra tabela aparece no texto.
NOME_TABELA = {
    "usuario": "a pessoa (usuario)", "docente": "o docente (docente)", "aluno": "o aluno (aluno)",
    "curso": "o curso", "nucleo": "o núcleo", "area_interesse": "a área de interesse", "perfil": "o perfil",
    "tcc": "o TCC", "turma": "a turma", "periodo_letivo": "o período letivo", "proposta": "a proposta",
    "comentario_proposta": "o comentário", "defesa": "a defesa", "local_defesa": "o local",
    "banca_membro": "o membro da banca", "instrumento_avaliacao": "o instrumento de avaliação",
    "componente_avaliacao": "a parte da avaliação", "criterio_avaliacao": "o critério",
    "avaliacao": "a avaliação", "resultado_defesa": "o resultado", "documento_tcc": "a versão do PDF",
    "ouvinte_defesa": "o ouvinte", "publicacao_artigo": "a publicação",
}

# Quem é a pessoa apontada, quando o nome da coluna diz mais que a tabela.
PAPEL_FK = {
    "autor_id": "Autor", "atribuido_por": "Quem atribuiu", "incluido_por": "Quem incluiu",
    "enviado_por": "Quem enviou", "cadastrada_por": "Quem cadastrou", "criado_por": "Quem criou",
    "confirmado_por": "Quem confirmou", "decidida_por": "Quem decidiu", "atraso_decidido_por": "Quem decidiu",
    "denunciante_id": "Quem denunciou", "moderador_id": "Coordenador que decidiu", "coordenador_id": "Coordenador",
    "professor_id": "Docente", "responsavel_id": "Docente responsável", "avaliador_id": "Avaliador que pediu",
    "tcc_origem_id": "TCC de origem", "substitui_membro_id": "Membro substituído", "membro_id": "Membro",
    "versao_final_id": "Versão final entregue", "ouvinte_id": "Ouvinte",
}


def descricao(t: ml.Tabela, col: ml.Col) -> str:
    texto = DESC.get(f"{t.nome}.{col.nome}") or DESC.get(col.nome)
    if col.fk and not texto:
        alvo = NOME_TABELA.get(col.fk, col.fk)
        texto = f"{PAPEL_FK[col.nome]}; aponta para {alvo}." if col.nome in PAPEL_FK else f"Aponta para {alvo}."
    partes = [texto or ""]
    if col.nota:
        partes.append(col.nota[0].upper() + col.nota[1:] + ".")
    if col.valores:
        partes.append("Valores: " + ", ".join(col.valores) + ".")
    if col.novo:
        partes.append("Coluna planejada.")
    return " ".join(p for p in partes if p)


def chave(col: ml.Col) -> str:
    out = []
    if col.pk:
        out.append("PK")
    if col.fk:
        out.append(f"FK → {col.fk}")
    if col.uk:
        out.append("UK")
    return ", ".join(out) or "—"


# As regras de integridade (CHECK) em português, como a coordenação lê.
CHECK = {
    "(escopo = 'BANCA' AND defesa_id IS NOT NULL) OR (escopo = 'COORIENTACAO' AND tcc_id IS NOT NULL)":
        "Conta de banca aponta para uma defesa; conta de coorientação aponta para um TCC.",
    "destino <> 'AREA' OR area_id IS NOT NULL": "Proposta destinada a uma área precisa informar a área.",
    "length(trim(texto)) > 0": "O texto não pode ficar em branco.",
    "(proposta_id IS NULL) <> (comentario_id IS NULL)":
        "A denúncia é de uma proposta ou de um comentário, nunca dos dois nem de nenhum.",
    "length(trim(motivo)) > 0": "O motivo não pode ficar em branco.",
    "situacao = 'PENDENTE' OR (moderador_id IS NOT NULL AND length(trim(justificativa)) > 0 "
    "AND decidida_em IS NOT NULL)": "Denúncia decidida precisa do coordenador, da justificativa e da data.",
    "fim > inicio": "O fim vem depois do início.",
    "nota_final IS NULL OR nota_final BETWEEN 0 AND 10": "A nota final, quando houver, fica entre 0 e 10.",
    "ordem BETWEEN 1 AND 10": "No máximo 10 palavras-chave.",
    "resultado = 'APROVADO' OR length(trim(parecer)) > 0": "Devolução e reprovação exigem parecer.",
    "tamanho_bytes BETWEEN 1 AND 20971520": "O arquivo não pode estar vazio nem passar de 20 MB.",
    "(formato = 'PRESENCIAL' AND local_id IS NOT NULL) OR (formato = 'REMOTO' AND link IS NOT NULL) "
    "OR (formato = 'HIBRIDO' AND local_id IS NOT NULL AND link IS NOT NULL)":
        "Defesa presencial exige local; remota exige link; híbrida exige os dois.",
    "(conceito = 'EXEMPLAR' AND nota BETWEEN 8 AND 10) OR (conceito = 'COMPETENTE' AND nota BETWEEN 6 AND 7.9) "
    "OR (conceito = 'NECESSITA' AND nota BETWEEN 0 AND 5.9)":
        "A nota acompanha o conceito: Exemplar de 8 a 10, Competente de 6 a 7,9 e Necessita melhorar de 0 a 5,9.",
    "situacao_atual <> 'PUBLICADO' OR doi IS NOT NULL": "Artigo publicado precisa do DOI.",
}


def restricoes(t: ml.Tabela) -> list[str]:
    out = [f"Não se repete a combinação de {', '.join(u)}." for u in t.unicos]
    out += [CHECK[ch] for ch in t.checks]
    if t.nome == "log_auditoria":
        out.append("O banco recusa alterar ou apagar registros desta tabela (RNF03).")
    return out


DESC_TABELA = {
    "log_auditoria": "Registro de cada alteração feita no sistema, com quem, quando e o valor anterior e o novo.",
}

MODULO_TEXTO = {
    "MOD01": "Pessoas, perfis de acesso, sessões, links de ativação e recuperação, fila de e-mails e auditoria.",
    "MOD02": "Propostas de TCC dos alunos, comentários dos professores e denúncias para moderação.",
    "MOD03": "Períodos, turmas, matrícula, cadastro do TCC, análise da coordenação, orientação, documentos e "
             "tarefas.",
    "MOD04": "Agendamento da defesa, banca, avaliação, resultado, correções, ata, certificados e ouvintes.",
    "MOD05": "Submissão do artigo e histórico da situação editorial.",
}


# ---------------------------------------------------------------- documento
def dicionario() -> Doc:
    d = Doc("DICIONÁRIO DE DADOS", [
        ("Nome do Projeto:", PROJETO), ("Instituição:", INSTITUICAO), ("Patrocinadora / Cliente:", CLIENTE),
        ("Equipe / Gerentes do Projeto:", EQUIPE),
        ("Documento de referência:", "Plano de Integração do Projeto, versão 2.3; história HT02 (SCRUM-107)"),
        ("Data:", "21/10/2026"), ("Versão:", "1.0")])
    criadas = [t for t in ml.T if t.implementada]

    d.h1("1. INTRODUÇÃO")
    d.p("Este documento descreve os dados do SIGA UEA – Sistema de Gestão de TCC do NUCOMP-UEA: cada tabela do "
        "banco, o que guarda, suas colunas, chaves e regras de integridade, e os requisitos que atende. É o "
        "complemento textual do DER em notação pé de galinha e atende à história HT02 (Modelagem de dados).")
    d.h2("1.1 Objetivo")
    d.p("Dar à equipe e à coordenação uma referência única do significado de cada dado, para que o banco, a API "
        "e as telas usem os mesmos nomes e as mesmas regras.")
    d.h2("1.2 Escopo")
    d.p(f"As {len(ml.T)} tabelas do sistema completo, nos cinco módulos. {len(criadas)} já existem no banco "
        f"(usuários e acesso, turmas e cadastro de TCC, sprints S02 e S03); as outras {len(ml.T) - len(criadas)} "
        "estão modeladas para os próximos marcos. Os indicadores (MOD06) e a agenda pública (MOD07) não têm "
        "tabelas próprias: são consultas sobre as tabelas descritas aqui.")
    d.h2("1.3 Documentos de referência")
    d.lista([
        "Requisitos_SIGA_UEA.xlsx: requisitos, regras de negócio e requisitos não funcionais.",
        "DER do SIGA UEA em notação pé de galinha (D05, pasta 05_Modelo_de_Dados): visão geral, sistema completo "
        "e tabelas já implementadas.",
        "DER conceitual do SIGA UEA, no estilo brModelo, uma página por módulo.",
        "Esquema físico do banco (SIGA_UEA_modelo_fisico_PostgreSQL.sql), gerado das migrações.",
        "Documento de Arquitetura do Sistema e Contrato da API.",
    ], numerada=False)
    d.h2("1.4 Siglas")
    d.tabela(["Sigla", "Significado"], [
        ["PK", "Chave primária: identifica o registro na tabela."],
        ["FK", "Chave estrangeira: aponta para o registro de outra tabela."],
        ["UK", "Chave única: o valor não se repete na tabela."],
        ["DER", "Diagrama Entidade-Relacionamento."],
        ["SGBD", "Sistema Gerenciador de Banco de Dados (aqui, PostgreSQL 16)."],
        ["RBN, RN, RNF", "Requisito de baixo nível, regra de negócio e requisito não funcional da planilha."],
    ], [3.5, 12.5])

    d.h1("2. VISÃO GERAL")
    d.tabela(["Módulo", "Conteúdo", "Tabelas", "Já no banco"], [
        [ml.MODULOS[m].split(" (")[0], MODULO_TEXTO[m], str(sum(t.modulo == m for t in ml.T)),
         str(sum(t.modulo == m and t.implementada for t in ml.T))] for m in ml.MODULOS
    ] + [["Total", "", str(len(ml.T)), str(len(criadas))]], [4.4, 8.0, 1.8, 1.8])
    d.figura(AQUI / "der-pe-de-galinha-1-visao-geral.png",
             f"Figura 1 – DER em notação pé de galinha, visão geral das {len(ml.T)} entidades. "
             "Fonte: elaborado pelos autores (2026).")

    d.h1("3. CONVENÇÕES")
    d.tabela(None, [
        ["Nomes", "Tabelas e colunas em minúsculas, sem acento, com sublinhado (ex.: periodo_letivo). Chave "
         "estrangeira termina em _id ou diz o papel da pessoa (ex.: enviado_por)."],
        ["Tipos", "Tipos do PostgreSQL: SERIAL (número gerado), INTEGER, VARCHAR(n) (texto de até n caracteres), "
         "TEXT, DATE, TIME, TIMESTAMP (data e hora), BOOLEAN (sim ou não), NUMERIC(p,e), BYTEA (arquivo), "
         "CHAR(64) (resumo SHA-256) e JSONB (dados estruturados)."],
        ["Datas", "Data e hora gravadas em UTC; a tela mostra no fuso de Manaus."],
        ["Nulo", "\"Não\" quer dizer campo obrigatório. \"Sim\" quer dizer que o campo pode ficar vazio."],
        ["Valores", "Quando a coluna tem uma lista de valores permitidos, o banco recusa qualquer outro."],
        ["Histórico", "Nada que tenha valor de registro é apagado: mudanças viram linhas novas ou versões, como "
         "mostra a tabela abaixo."],
    ], [3.0, 13.0], rotulo=True)
    d.tabela(["O que muda", "Onde fica o histórico"], [
        ["Situação acadêmica do TCC", "historico_situacao: cada transição, com quem e quando."],
        ["Parecer da coordenação", "analise_cadastro: uma linha por decisão; o protocolo não muda."],
        ["Orientador substituído", "orientacao com status SUBSTITUIDA, data e justificativa; o novo vínculo é "
         "outra linha (RN16)."],
        ["Versões do PDF", "documento_tcc: versão nova a cada envio; a anterior permanece."],
        ["Remarcação, cancelamento e suplência", "historico_defesa, com os valores anteriores."],
        ["Retificação do resultado", "resultado_defesa com versao e vigente; ata e folha antigas ficam em "
         "documento_oficial com substituido_em."],
        ["Instrumento de avaliação", "instrumento_avaliacao versionado; cada avaliação aponta para a versão "
         "usada (RN19)."],
        ["Situação editorial", "historico_publicacao; outro veículo é outra publicacao_artigo."],
        ["Qualquer alteração", "log_auditoria, que o banco não deixa alterar nem apagar (RNF03)."],
    ], [5.0, 11.0])

    n = 4
    for mod, titulo in ml.MODULOS.items():
        d.h1(f"{n}. {titulo.split(' (')[0].upper()}")
        d.p(MODULO_TEXTO[mod])
        for i, t in enumerate([t for t in ml.T if t.modulo == mod], 1):
            d.h2(f"{n}.{i} {t.nome}")
            estado = "já existe no banco" if t.implementada else "planejada para os próximos marcos"
            texto = DESC_TABELA.get(t.nome, t.descricao)
            d.p(f"{texto} Situação: {estado}. Requisitos: {t.requisitos or '—'}.")
            d.tabela(["Coluna", "Tipo", "Chave", "Nulo", "Descrição"],
                     [[c.nome, c.tipo, chave(c), "Sim" if c.nulo else "Não", descricao(t, c)] for c in t.cols],
                     [3.4, 3.1, 2.9, 1.2, 5.4])
            regras = restricoes(t)
            if regras:
                d.lista(regras, numerada=False)
        n += 1

    d.h1(f"{n}. COBERTURA DOS REQUISITOS")
    d.p("Toda RBN e RN da planilha de requisitos (113 itens) está citada em alguma tabela deste documento ou na "
        "lista abaixo, que traz os requisitos sem tabela própria e o motivo. A conferência é feita contra a "
        "planilha a cada mudança no modelo.")
    d.tabela(["Requisito", "Por quê"], [[r, m] for r, m in ml.SEM_TABELA.items()], [4.0, 12.0])
    n += 1

    finais(d, n, "Versão inicial: as 46 tabelas do sistema, com colunas, chaves, restrições e requisitos.", [
        REF_PLANO, REF_REQ,
        "SIGA UEA. DER do SIGA UEA em notação pé de galinha. Manaus: NUCOMP – EST/UEA, 2026.",
        "HEUSER, Carlos Alberto. Projeto de banco de dados. 6. ed. Porto Alegre: Bookman, 2009.",
    ])
    return d


def main():
    paginas, faltando = gerar(dicionario(), AQUI / "Dicionario_de_Dados_SIGA_UEA")
    print(f"Dicionario_de_Dados_SIGA_UEA: {paginas} páginas no PDF; títulos sem página no sumário: "
          f"{faltando or 'nenhum'}")


if __name__ == "__main__":
    main()
