"""DER completo do SIGA UEA (HT02 / SCRUM-107): fonte única do modelo lógico.

Gera, a partir da especificação abaixo:
  docs/der/der-siga-uea.drawio     uma página por módulo (draw.io)
  docs/der/der-siga-uea.md         diagrama ER (Mermaid) e dicionário de dados
  docs/der/der-siga-uea.sql        DDL PostgreSQL do modelo completo

    python docs/der/modelo.py

Tabelas marcadas como implementadas já existem nas migrações (backend/migrations).
As demais são o modelo aprovado para os próximos marcos; a migração de cada uma é
criada quando o módulo for implementado (HT05). Nomes de entidades e situações
seguem os diagramas de sequência FL01 a FL10 (ex.: MatriculaTurma -> matricula_turma).
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import quoteattr

AQUI = Path(__file__).resolve().parent


@dataclass
class Col:
    nome: str
    tipo: str
    pk: bool = False
    fk: str | None = None  # "tabela" (sempre para a coluna id/usuario_id da tabela alvo)
    uk: bool = False
    nulo: bool = False
    valores: tuple[str, ...] = ()  # domínio (vira CHECK no SQL)
    nota: str = ""
    novo: bool = False  # coluna planejada em tabela que já existe


@dataclass
class Tabela:
    nome: str
    modulo: str
    descricao: str
    cols: list[Col]
    implementada: bool = False
    unicos: list[tuple[str, ...]] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)
    requisitos: str = ""


def c(nome, tipo, **kw) -> Col:
    return Col(nome, tipo, **kw)


def id_() -> Col:
    return c("id", "SERIAL", pk=True)


def criado() -> Col:
    return c("criado_em", "TIMESTAMP")


SIM_NAO = "BOOLEAN"

T: list[Tabela] = [
    # ======================= MOD01 · Usuários e acesso =======================
    Tabela("nucleo", "MOD01", "Núcleo acadêmico (NUCOMP).", [
        id_(), c("sigla", "VARCHAR(20)", uk=True), c("nome", "VARCHAR(150)")],
        implementada=True, requisitos="RBN01.01"),
    Tabela("curso", "MOD01", "Cursos contemplados (RN01).", [
        id_(), c("sigla", "VARCHAR(10)", uk=True), c("nome", "VARCHAR(100)", uk=True),
        c("nucleo_id", "INTEGER", fk="nucleo")], implementada=True, requisitos="RN01"),
    Tabela("area_interesse", "MOD01", "Áreas de interesse mantidas pela coordenação.", [
        id_(), c("nome", "VARCHAR(100)", uk=True)], implementada=True, requisitos="RBN01.02, RN25"),
    Tabela("perfil", "MOD01", "Os cinco perfis de acesso (RN07).", [
        id_(), c("codigo", "VARCHAR(30)", uk=True), c("nome", "VARCHAR(50)")],
        implementada=True, requisitos="RN07"),
    Tabela("usuario", "MOD01", "Toda pessoa que acessa o sistema.", [
        id_(), c("nome", "VARCHAR(150)"),
        c("email", "VARCHAR(254)", uk=True, nota="único em lower(email)"),
        c("telefone", "VARCHAR(20)", nulo=True), c("senha_hash", "VARCHAR(60)", nulo=True, nota="bcrypt; nulo até ativar"),
        c("ativo", SIM_NAO), c("inativado_em", "TIMESTAMP", nulo=True),
        c("tentativas_falhas", "INTEGER"), c("bloqueado_ate", "TIMESTAMP", nulo=True), criado()],
        implementada=True, requisitos="RBN01.01 a RBN01.08"),
    Tabela("usuario_perfil", "MOD01", "Perfis de cada pessoa e quem os atribuiu.", [
        c("usuario_id", "INTEGER", pk=True, fk="usuario"), c("perfil_id", "INTEGER", pk=True, fk="perfil"),
        c("atribuido_por", "INTEGER", fk="usuario", nulo=True), c("atribuido_em", "TIMESTAMP")],
        implementada=True, requisitos="RN07"),
    Tabela("docente", "MOD01", "Dados de quem é docente (coordenador, professor, orientador).", [
        c("usuario_id", "INTEGER", pk=True, fk="usuario"),
        c("cargo", "VARCHAR(20)", valores=("coordenador", "professor", "orientador")),
        c("nucleo_id", "INTEGER", fk="nucleo"),
        c("curso_id", "INTEGER", fk="curso", nulo=True, nota="nulo = coordenador")],
        implementada=True, requisitos="RBN01.01"),
    Tabela("docente_area", "MOD01", "Áreas de interesse de cada docente (RN25).", [
        c("docente_id", "INTEGER", pk=True, fk="docente"), c("area_id", "INTEGER", pk=True, fk="area_interesse")],
        implementada=True, requisitos="RN25, RBN01.10"),
    Tabela("aluno", "MOD01", "Dados de quem é aluno.", [
        c("usuario_id", "INTEGER", pk=True, fk="usuario"), c("matricula", "VARCHAR(20)", uk=True),
        c("curso_id", "INTEGER", fk="curso"),
        c("acesso_ate", "DATE", nulo=True, novo=True, nota="aprovação em TCC2 + 7 dias (RN27)")],
        implementada=True, requisitos="RBN01.03, RBN01.11"),
    Tabela("foto_usuario", "MOD01", "Foto de perfil (opcional).", [
        c("usuario_id", "INTEGER", pk=True, fk="usuario"), c("tipo", "VARCHAR(20)"),
        c("conteudo", "BYTEA"), c("sha256", "CHAR(64)"), c("atualizado_em", "TIMESTAMP")],
        implementada=True, requisitos="RBN01.09, RBN01.10"),
    Tabela("usuario_externo", "MOD01", "Membro de banca ou coorientador de fora da UEA (AcessoLimitado).", [
        c("usuario_id", "INTEGER", pk=True, fk="usuario"), c("instituicao", "VARCHAR(150)")],
        requisitos="RBN01.12, RBN01.13, RN12"),
    Tabela("acesso_limitado", "MOD01", "Conta restrita a uma defesa ou a um TCC, com validade.", [
        id_(), c("usuario_id", "INTEGER", fk="usuario"),
        c("escopo", "VARCHAR(20)", valores=("BANCA", "COORIENTACAO")),
        c("defesa_id", "INTEGER", fk="defesa", nulo=True), c("tcc_id", "INTEGER", fk="tcc", nulo=True),
        c("expira_em", "TIMESTAMP", nulo=True, nota="7 dias após o resultado"), c("revogado_em", "TIMESTAMP", nulo=True), criado()],
        checks=["(escopo = 'BANCA' AND defesa_id IS NOT NULL) OR (escopo = 'COORIENTACAO' AND tcc_id IS NOT NULL)"],
        requisitos="RBN01.12, RBN01.13"),
    Tabela("token_usuario", "MOD01", "Links de ativação e recuperação (só o hash).", [
        id_(), c("usuario_id", "INTEGER", fk="usuario"), c("tipo", "VARCHAR(20)", valores=("ativacao", "recuperacao")),
        c("token_hash", "CHAR(64)", uk=True), c("expira_em", "TIMESTAMP"), c("usado_em", "TIMESTAMP", nulo=True), criado()],
        implementada=True, requisitos="RBN01.05, RBN01.07"),
    Tabela("sessao", "MOD01", "Sessões de login (60 min de inatividade).", [
        id_(), c("usuario_id", "INTEGER", fk="usuario"), c("token_hash", "CHAR(64)", uk=True),
        c("expira_em", "TIMESTAMP"), criado()], implementada=True, requisitos="RBN01.06"),
    Tabela("notificacao_email", "MOD01", "Fila de e-mails de todos os módulos (NotificacaoEmail).", [
        id_(), c("usuario_id", "INTEGER", fk="usuario"), c("tipo", "VARCHAR(30)"), c("destinatario", "VARCHAR(254)"),
        c("status", "VARCHAR(10)", valores=("pendente", "enviado", "falha")), c("tentativas", "INTEGER"),
        c("erro", "TEXT", nulo=True),
        c("entidade", "VARCHAR(40)", nulo=True, novo=True, nota="ex.: tcc, defesa"),
        c("entidade_id", "INTEGER", nulo=True, novo=True), criado(), c("enviado_em", "TIMESTAMP", nulo=True)],
        implementada=True, requisitos="RBN03.06, RBN04.05, RBN09.05, RBN12.03"),
    Tabela("log_auditoria", "MOD01", "Log imutável de alterações (RNF03); trigger recusa UPDATE/DELETE.", [
        id_(), c("usuario_id", "INTEGER", fk="usuario", nulo=True), c("acao", "VARCHAR(40)"),
        c("entidade", "VARCHAR(40)"), c("entidade_id", "INTEGER", nulo=True), c("campo", "VARCHAR(40)", nulo=True),
        c("valor_anterior", "TEXT", nulo=True), c("valor_novo", "TEXT", nulo=True), criado()],
        implementada=True, requisitos="RNF03"),

    # ======================= MOD02 · Ideias de TCC =======================
    Tabela("proposta", "MOD02", "Proposta de TCC de um aluno, direcionada a área ou a professores.", [
        id_(), c("autor_id", "INTEGER", fk="usuario"), c("titulo", "VARCHAR(200)"), c("descricao", "TEXT"),
        c("destino", "VARCHAR(12)", valores=("AREA", "PROFESSORES")),
        c("area_id", "INTEGER", fk="area_interesse", nulo=True, nota="obrigatória se destino = AREA"),
        c("oculta_em", "TIMESTAMP", nulo=True), criado()],
        checks=["destino <> 'AREA' OR area_id IS NOT NULL"], requisitos="RBN02.01, RN25"),
    Tabela("proposta_destinatario", "MOD02", "Professores escolhidos quando destino = PROFESSORES.", [
        c("proposta_id", "INTEGER", pk=True, fk="proposta"), c("professor_id", "INTEGER", pk=True, fk="docente")],
        requisitos="RBN02.01"),
    Tabela("comentario_proposta", "MOD02", "Comentários de professores nas propostas.", [
        id_(), c("proposta_id", "INTEGER", fk="proposta"), c("autor_id", "INTEGER", fk="usuario"),
        c("texto", "TEXT"), c("oculto_em", "TIMESTAMP", nulo=True), criado()],
        checks=["length(trim(texto)) > 0"], requisitos="RBN02.02"),

    # ======================= MOD03 · Gestão e acompanhamento =======================
    Tabela("periodo_letivo", "MOD03", "Período letivo AAAA/N e prazo da versão final (PeriodoLetivo).", [
        id_(), c("codigo", "VARCHAR(6)", uk=True, nota="ex.: 2026/2"), c("inicio", "DATE"), c("fim", "DATE"),
        c("prazo_versao_final", "DATE", nulo=True)],
        checks=["fim > inicio"], requisitos="RBN08.01, RBN11.01"),
    Tabela("turma", "MOD03", "Turma de TCC1 (disciplina) ou TCC2 (orientador).", [
        id_(), c("codigo", "VARCHAR(30)", uk=True), c("disciplina", "VARCHAR(4)", valores=("TCC1", "TCC2")),
        c("curso_id", "INTEGER", fk="curso"), c("periodo_id", "INTEGER", fk="periodo_letivo"),
        c("professor_id", "INTEGER", fk="docente", nota="responsável (RN24, RN26)"),
        c("encerrada_em", "TIMESTAMP", nulo=True), criado()],
        unicos=[("curso_id", "disciplina", "periodo_id", "professor_id")], requisitos="RBN08.01, RBN08.05, RN24, RN26"),
    Tabela("matricula_turma", "MOD03", "Aluno na turma e sua situação (MatriculaTurma).", [
        id_(), c("turma_id", "INTEGER", fk="turma"), c("aluno_id", "INTEGER", fk="aluno"),
        c("situacao", "VARCHAR(12)", valores=("MATRICULADO", "DESISTENTE", "APROVADO", "REPROVADO")),
        c("nota_final", "NUMERIC(3,1)", nulo=True), c("incluido_por", "INTEGER", fk="usuario"),
        c("incluido_em", "TIMESTAMP"), c("situacao_alterada_em", "TIMESTAMP", nulo=True)],
        unicos=[("turma_id", "aluno_id")], checks=["nota_final IS NULL OR nota_final BETWEEN 0 AND 10"],
        requisitos="RBN08.02, RBN08.03, RN05"),
    Tabela("tcc", "MOD03", "O trabalho: cadastro, protocolo e situação acadêmica (TCC).", [
        id_(), c("aluno_id", "INTEGER", fk="aluno"), c("turma_id", "INTEGER", fk="turma"),
        c("periodo_id", "INTEGER", fk="periodo_letivo"),
        c("etapa", "VARCHAR(4)", valores=("TCC1", "TCC2")),
        c("modalidade", "VARCHAR(10)", valores=("ARTIGO", "MONOGRAFIA")),
        c("titulo", "VARCHAR(300)"), c("subtitulo", "VARCHAR(300)", nulo=True),
        c("resumo", "TEXT", nota="até 500 palavras"), c("area_id", "INTEGER", fk="area_interesse"),
        c("situacao", "VARCHAR(12)", valores=("RASCUNHO", "EM_ANALISE", "APROVADO", "DEVOLVIDO", "REPROVADO", "CONCLUIDO", "DESISTENCIA")),
        c("protocolo", "VARCHAR(20)", uk=True, nulo=True, nota="gerado na 1ª submissão"),
        c("submetido_em", "TIMESTAMP", nulo=True), c("concluido_em", "TIMESTAMP", nulo=True),
        c("desistencia_motivo", "TEXT", nulo=True),
        c("tcc_origem_id", "INTEGER", fk="tcc", nulo=True, nota="TCC1 que originou o TCC2"),
        criado(), c("atualizado_em", "TIMESTAMP")],
        unicos=[("aluno_id", "periodo_id")], requisitos="RBN03.01 a RBN03.05, RBN08.04, RN04, RN10"),
    Tabela("tcc_palavra_chave", "MOD03", "Palavras-chave do TCC (no máximo 10).", [
        c("tcc_id", "INTEGER", pk=True, fk="tcc"), c("ordem", "SMALLINT", pk=True), c("palavra", "VARCHAR(60)")],
        checks=["ordem BETWEEN 1 AND 10"], requisitos="RBN03.01"),
    Tabela("historico_situacao", "MOD03", "Cada mudança de situação do TCC (HistoricoSituacao).", [
        id_(), c("tcc_id", "INTEGER", fk="tcc"), c("situacao_anterior", "VARCHAR(12)", nulo=True),
        c("situacao_nova", "VARCHAR(12)"), c("usuario_id", "INTEGER", fk="usuario"),
        c("observacao", "TEXT", nulo=True), c("registrado_em", "TIMESTAMP")],
        requisitos="RBN05.04, RN10"),
    Tabela("analise_cadastro", "MOD03", "Decisões da coordenação sobre o cadastro (AnaliseCadastro).", [
        id_(), c("tcc_id", "INTEGER", fk="tcc"), c("coordenador_id", "INTEGER", fk="docente"),
        c("resultado", "VARCHAR(10)", valores=("APROVADO", "DEVOLVIDO", "REPROVADO")),
        c("parecer", "TEXT", nota="obrigatório em DEVOLVIDO/REPROVADO"), c("decidido_em", "TIMESTAMP")],
        checks=["resultado = 'APROVADO' OR length(trim(parecer)) > 0"], requisitos="RBN04.01 a RBN04.05, RN06"),
    Tabela("orientacao", "MOD03", "Vínculos de orientação e coorientação, com histórico (Orientacao).", [
        id_(), c("tcc_id", "INTEGER", fk="tcc"), c("professor_id", "INTEGER", fk="usuario", nota="pode ser externo"),
        c("papel", "VARCHAR(12)", valores=("ORIENTADOR", "COORIENTADOR")),
        c("status", "VARCHAR(12)", valores=("PENDENTE", "ACEITA", "RECUSADA", "SUBSTITUIDA")),
        c("solicitado_em", "TIMESTAMP"), c("respondido_em", "TIMESTAMP", nulo=True),
        c("motivo_recusa", "TEXT", nulo=True), c("encerrado_em", "TIMESTAMP", nulo=True),
        c("justificativa_encerramento", "TEXT", nulo=True)],
        requisitos="RBN06.01 a RBN06.03, RN16"),
    Tabela("documento_tcc", "MOD03", "Versões do PDF do TCC (DocumentoTCC).", [
        id_(), c("tcc_id", "INTEGER", fk="tcc"), c("versao", "INTEGER"),
        c("finalidade", "VARCHAR(12)", valores=("PRELIMINAR", "BANCA", "FINAL")),
        c("nome_arquivo", "VARCHAR(255)"), c("tamanho_bytes", "INTEGER", nota="até 20 MB"),
        c("sha256", "CHAR(64)"), c("caminho", "VARCHAR(500)"),
        c("enviado_por", "INTEGER", fk="usuario"), c("enviado_em", "TIMESTAMP")],
        unicos=[("tcc_id", "versao")], checks=["tamanho_bytes BETWEEN 1 AND 20971520"],
        requisitos="RBN07.01 a RBN07.04, RN11, RNF06"),
    Tabela("tarefa_tcc", "MOD03", "Tarefas/entregáveis definidos para um TCC aprovado.", [
        id_(), c("tcc_id", "INTEGER", fk="tcc"), c("descricao", "TEXT"), c("prazo", "DATE"),
        c("cadastrada_por", "INTEGER", fk="usuario"), c("entregue_em", "TIMESTAMP", nulo=True),
        c("status", "VARCHAR(10)", valores=("PENDENTE", "ENTREGUE", "ATRASADA")), criado()],
        requisitos="RBN05.05"),

    # ======================= MOD04 · Gestão da defesa =======================
    Tabela("local_defesa", "MOD04", "Salas e locais físicos de defesa (LocalDefesa).", [
        id_(), c("nome", "VARCHAR(100)", uk=True), c("descricao", "VARCHAR(200)", nulo=True)],
        requisitos="RBN09.03, RBN09.04"),
    Tabela("defesa", "MOD04", "Agendamento da defesa e divulgação na agenda (Defesa).", [
        id_(), c("tcc_id", "INTEGER", fk="tcc"),
        c("formato", "VARCHAR(10)", valores=("PRESENCIAL", "REMOTO", "HIBRIDO")),
        c("data", "DATE"), c("inicio", "TIME"), c("fim", "TIME"),
        c("local_id", "INTEGER", fk="local_defesa", nulo=True), c("link", "VARCHAR(500)", nulo=True),
        c("situacao", "VARCHAR(10)", valores=("CONFIRMADA", "REMARCADA", "CANCELADA", "REALIZADA")),
        c("responsavel_id", "INTEGER", fk="docente", nota="RN14"),
        c("publicada", SIM_NAO, nota="agenda (RAN14)"), c("publicada_em", "TIMESTAMP", nulo=True),
        c("divulgar_link", SIM_NAO), c("revisao_banca", SIM_NAO, nota="orientador substituído"), criado()],
        checks=["fim > inicio",
                "(formato = 'PRESENCIAL' AND local_id IS NOT NULL) OR (formato = 'REMOTO' AND link IS NOT NULL) "
                "OR (formato = 'HIBRIDO' AND local_id IS NOT NULL AND link IS NOT NULL)"],
        requisitos="RBN09.01, RBN09.03, RBN09.07, RBN09.08, RBN14.01 a RBN14.04, RN09, RN14"),
    Tabela("historico_defesa", "MOD04", "Agendamento, remarcação, cancelamento e suplência (HistoricoDefesa).", [
        id_(), c("defesa_id", "INTEGER", fk="defesa"),
        c("evento", "VARCHAR(20)", valores=("AGENDAMENTO", "REMARCACAO", "CANCELAMENTO", "SUPLENTE_CONVOCADO")),
        c("motivo", "TEXT", nulo=True), c("valores_anteriores", "JSONB", nulo=True),
        c("usuario_id", "INTEGER", fk="usuario"), c("registrado_em", "TIMESTAMP")],
        requisitos="RBN09.07 a RBN09.09"),
    Tabela("banca_membro", "MOD04", "Membros da banca de uma defesa (BancaMembro).", [
        id_(), c("defesa_id", "INTEGER", fk="defesa"), c("usuario_id", "INTEGER", fk="usuario"),
        c("papel", "VARCHAR(12)", valores=("AVALIADOR", "ORIENTADOR", "COORIENTADOR", "SUPLENTE")),
        c("interno", SIM_NAO), c("convite_enviado_em", "TIMESTAMP", nulo=True),
        c("presente", SIM_NAO, nulo=True, nota="para certificado"),
        c("convocado_em", "TIMESTAMP", nulo=True, nota="suplente chamado"),
        c("substitui_membro_id", "INTEGER", fk="banca_membro", nulo=True),
        c("motivo_convocacao", "TEXT", nulo=True)],
        unicos=[("defesa_id", "usuario_id")], requisitos="RBN09.01, RBN09.02, RBN09.05, RBN09.09, RN12, RN20"),
    Tabela("instrumento_avaliacao", "MOD04", "Versões do instrumento de avaliação (InstrumentoAvaliacao).", [
        id_(), c("versao", "INTEGER", uk=True), c("vigente", SIM_NAO),
        c("criado_por", "INTEGER", fk="usuario"), criado()],
        requisitos="RBN10.01, RN19"),
    Tabela("componente_avaliacao", "MOD04", "Parte escrita (7,0) e oral (3,0).", [
        id_(), c("instrumento_id", "INTEGER", fk="instrumento_avaliacao"), c("nome", "VARCHAR(60)"),
        c("pontos", "NUMERIC(3,1)"), c("ordem", "SMALLINT")],
        requisitos="RBN10.01"),
    Tabela("criterio_avaliacao", "MOD04", "Critério com peso e texto dos três conceitos.", [
        id_(), c("componente_id", "INTEGER", fk="componente_avaliacao"), c("nome", "VARCHAR(120)"),
        c("peso", "NUMERIC(4,2)"), c("texto_exemplar", "TEXT"), c("texto_competente", "TEXT"),
        c("texto_necessita", "TEXT"), c("ordem", "SMALLINT")],
        requisitos="RBN10.01, RBN10.03, RN19"),
    Tabela("avaliacao", "MOD04", "Avaliação de um membro da banca (Avaliacao).", [
        id_(), c("defesa_id", "INTEGER", fk="defesa"), c("membro_id", "INTEGER", fk="banca_membro"),
        c("instrumento_id", "INTEGER", fk="instrumento_avaliacao"),
        c("status", "VARCHAR(10)", valores=("RASCUNHO", "ENVIADA")),
        c("parecer", "TEXT", nulo=True), c("nota_total", "NUMERIC(3,1)", nulo=True),
        c("enviada_em", "TIMESTAMP", nulo=True)],
        unicos=[("defesa_id", "membro_id")], requisitos="RBN10.02, RBN10.04, RBN10.05"),
    Tabela("avaliacao_criterio", "MOD04", "Conceito e nota por critério (AvaliacaoCriterio).", [
        c("avaliacao_id", "INTEGER", pk=True, fk="avaliacao"), c("criterio_id", "INTEGER", pk=True, fk="criterio_avaliacao"),
        c("conceito", "VARCHAR(12)", valores=("EXEMPLAR", "COMPETENTE", "NECESSITA")),
        c("nota", "NUMERIC(3,1)"), c("nota_ponderada", "NUMERIC(4,2)", nota="nota × peso ÷ 10")],
        checks=["(conceito = 'EXEMPLAR' AND nota BETWEEN 8 AND 10) OR (conceito = 'COMPETENTE' AND nota BETWEEN 6 AND 7.9) "
                "OR (conceito = 'NECESSITA' AND nota BETWEEN 0 AND 5.9)"],
        requisitos="RBN10.03, RBN10.04"),
    Tabela("resultado_defesa", "MOD04", "Resultado confirmado, versionado por retificação (ResultadoDefesa).", [
        id_(), c("defesa_id", "INTEGER", fk="defesa"), c("versao", "INTEGER"), c("vigente", SIM_NAO),
        c("media", "NUMERIC(3,1)"), c("nota_final", "NUMERIC(3,1)"), c("regra_qualis", SIM_NAO, nota="RN21"),
        c("resultado", "VARCHAR(24)", valores=("APROVADO", "APROVADO_COM_CORRECOES", "REPROVADO")),
        c("parecer", "TEXT"), c("confirmado_por", "INTEGER", fk="usuario"), c("confirmado_em", "TIMESTAMP"),
        c("motivo_retificacao", "TEXT", nulo=True), c("prazo_versao_final", "DATE", nulo=True),
        c("prazo_motivo", "TEXT", nulo=True), c("anuencia_em", "TIMESTAMP", nulo=True),
        c("versao_final_id", "INTEGER", fk="documento_tcc", nulo=True),
        c("entregue_com_atraso", SIM_NAO, nulo=True), c("atraso_aceito", SIM_NAO, nulo=True),
        c("atraso_decidido_por", "INTEGER", fk="usuario", nulo=True), c("atraso_decidido_em", "TIMESTAMP", nulo=True)],
        unicos=[("defesa_id", "versao")], requisitos="RBN09.11, RBN09.12, RBN11.01, RBN11.02, RN13, RN21"),
    Tabela("correcao", "MOD04", "Correções exigidas pela banca (Correcao).", [
        id_(), c("resultado_id", "INTEGER", fk="resultado_defesa"), c("descricao", "TEXT"),
        c("avaliador_id", "INTEGER", fk="banca_membro"),
        c("situacao", "VARCHAR(10)", valores=("PENDENTE", "ATENDIDA", "APROVADA", "DEVOLVIDA")),
        c("justificativa", "TEXT", nulo=True), c("decidida_por", "INTEGER", fk="usuario", nulo=True),
        c("decidida_em", "TIMESTAMP", nulo=True)],
        requisitos="RBN11.01 a RBN11.04, RN17"),
    Tabela("documento_oficial", "MOD04", "Ata, folha de aprovação, certificados e declarações (DocumentoOficial).", [
        id_(), c("defesa_id", "INTEGER", fk="defesa"),
        c("tipo", "VARCHAR(16)", valores=("ATA", "FOLHA_APROVACAO", "CERTIFICADO", "DECLARACAO_HORAS")),
        c("versao", "INTEGER"), c("vigente", SIM_NAO), c("sha256", "CHAR(64)"), c("caminho", "VARCHAR(500)"),
        c("membro_id", "INTEGER", fk="banca_membro", nulo=True, nota="certificado"),
        c("ouvinte_id", "INTEGER", fk="ouvinte_defesa", nulo=True, nota="declaração"),
        c("gerado_em", "TIMESTAMP"), c("substituido_em", "TIMESTAMP", nulo=True)],
        requisitos="RBN09.14 a RBN09.17, RN15, RN23"),
    Tabela("ocorrencia_defesa", "MOD04", "Ocorrências registradas na sessão (OcorrenciaDefesa).", [
        id_(), c("defesa_id", "INTEGER", fk="defesa"), c("texto", "TEXT"), c("autor_id", "INTEGER", fk="usuario"),
        criado(), c("alterada_em", "TIMESTAMP", nulo=True)],
        requisitos="RBN09.10, RN23"),
    Tabela("ouvinte_defesa", "MOD04", "Ouvintes presentes, para declaração de horas (OuvinteDefesa).", [
        id_(), c("defesa_id", "INTEGER", fk="defesa"), c("nome", "VARCHAR(150)"),
        c("matricula", "VARCHAR(20)", nulo=True), criado()],
        requisitos="RBN09.10, RN23"),

    # ======================= MOD05 · Publicação =======================
    Tabela("publicacao_artigo", "MOD05", "Submissão do artigo a um veículo (PublicacaoArtigo).", [
        id_(), c("tcc_id", "INTEGER", fk="tcc"),
        c("tipo_veiculo", "VARCHAR(10)", valores=("PERIODICO", "CONGRESSO")), c("veiculo", "VARCHAR(200)"),
        c("qualis", "VARCHAR(2)", nulo=True), c("doi", "VARCHAR(200)", nulo=True),
        c("situacao_atual", "VARCHAR(12)", valores=("SUBMETIDO", "EM_REVISAO", "ACEITO", "RECUSADO", "PUBLICADO")),
        criado()],
        checks=["situacao_atual <> 'PUBLICADO' OR doi IS NOT NULL"],
        requisitos="RBN03.02, RBN12.01, RN03, RN21"),
    Tabela("historico_publicacao", "MOD05", "Sequência de situações editoriais (HistoricoPublicacao).", [
        id_(), c("publicacao_id", "INTEGER", fk="publicacao_artigo"),
        c("situacao", "VARCHAR(12)", valores=("SUBMETIDO", "EM_REVISAO", "ACEITO", "RECUSADO", "PUBLICADO")),
        c("data", "DATE"), c("usuario_id", "INTEGER", fk="usuario", nulo=True, nota="nulo = sistema (DOI)"),
        c("registrado_em", "TIMESTAMP")],
        requisitos="RBN05.02, RBN12.01, RBN12.02"),
]

POR_NOME = {t.nome: t for t in T}

# O alvo de uma FK é sempre a chave primária simples da tabela de destino.
def pk_de(tabela: str) -> str:
    return [col.nome for col in POR_NOME[tabela].cols if col.pk][0]


MODULOS = {
    "MOD01": "MOD01 · Usuários e acesso",
    "MOD02": "MOD02 · Ideias de TCC",
    "MOD03": "MOD03 · Gestão e acompanhamento dos TCCs",
    "MOD04": "MOD04 · Gestão da defesa e agenda (MOD07)",
    "MOD05": "MOD05 · Publicação",
}

# Disposição de cada página: colunas de tabelas (as de outro módulo entram como referência).
PAGINAS = {
    "MOD01": [["nucleo", "curso", "aluno"], ["docente", "usuario"],
              ["docente_area", "usuario_perfil", "foto_usuario", "usuario_externo"],
              ["area_interesse", "perfil", "acesso_limitado", "tcc", "defesa"],
              ["token_usuario", "sessao", "notificacao_email", "log_auditoria"]],
    "MOD02": [["usuario", "area_interesse"], ["proposta", "comentario_proposta"],
              ["proposta_destinatario", "docente"]],
    "MOD03": [["curso", "periodo_letivo", "area_interesse"], ["turma", "matricula_turma", "aluno"],
              ["tcc", "tcc_palavra_chave"], ["historico_situacao", "analise_cadastro", "tarefa_tcc"],
              ["orientacao", "documento_tcc", "docente", "usuario"]],
    "MOD04": [["tcc", "local_defesa", "historico_defesa", "documento_tcc"],
              ["defesa", "ocorrencia_defesa", "ouvinte_defesa"],
              ["banca_membro", "usuario", "documento_oficial"],
              ["avaliacao", "avaliacao_criterio", "resultado_defesa"],
              ["instrumento_avaliacao", "componente_avaliacao", "criterio_avaliacao", "correcao", "docente"]],
    "MOD05": [["tcc"], ["publicacao_artigo"], ["historico_publicacao", "usuario"]],
}


# ---------------------------------------------------------------- validação
def validar() -> None:
    nomes_pagina = {n for cols in PAGINAS.values() for col in cols for n in col}
    for t in T:
        assert t.nome in nomes_pagina, f"{t.nome} fora das páginas"
        nomes = [col.nome for col in t.cols]
        assert len(nomes) == len(set(nomes)), f"coluna repetida em {t.nome}"
        for col in t.cols:
            if col.fk:
                assert col.fk in POR_NOME, f"{t.nome}.{col.nome} -> {col.fk} inexistente"
        for u in t.unicos:
            assert set(u) <= set(nomes), f"único inválido em {t.nome}"
    for n in nomes_pagina:
        assert n in POR_NOME, f"página cita {n} inexistente"


# ---------------------------------------------------------------- SQL
def sql() -> str:
    # Ordem topológica pelas FKs (autorreferência não conta).
    feitas: list[str] = []
    pendentes = [t.nome for t in T]
    while pendentes:
        for nome in pendentes:
            deps = {col.fk for col in POR_NOME[nome].cols if col.fk and col.fk != nome}
            if deps <= set(feitas):
                feitas.append(nome)
                pendentes.remove(nome)
                break
        else:
            raise SystemExit(f"ciclo de FK entre {pendentes}")
    # acesso_limitado depende de tcc/defesa; já entra na ordem certa pela topologia.
    linhas = [
        "-- SIGA UEA: DER completo em DDL PostgreSQL (HT02). Gerado por docs/der/modelo.py; não edite à mão.",
        "-- As tabelas do MOD01 já existem pelas migrações; as demais são o modelo dos próximos marcos.",
        "BEGIN;",
    ]
    for nome in feitas:
        t = POR_NOME[nome]
        defs = []
        for col in t.cols:
            d = f"    {col.nome} {col.tipo}"
            if not col.nulo and not col.tipo == "SERIAL":
                d += " NOT NULL"
            if col.valores:
                d += f" CHECK ({col.nome} IN ({', '.join(repr(v) for v in col.valores)}))"
            defs.append(d)
        pks = [col.nome for col in t.cols if col.pk]
        defs.append(f"    PRIMARY KEY ({', '.join(pks)})")
        for col in t.cols:
            if col.uk and col.nome != "email":
                defs.append(f"    UNIQUE ({col.nome})")
        for u in t.unicos:
            defs.append(f"    UNIQUE ({', '.join(u)})")
        for col in t.cols:
            if col.fk:
                acao = "CASCADE" if nome == "foto_usuario" else "RESTRICT"
                defs.append(f"    FOREIGN KEY ({col.nome}) REFERENCES {col.fk} ({pk_de(col.fk)}) ON DELETE {acao}")
        for ch in t.checks:
            defs.append(f"    CHECK ({ch})")
        linhas.append(f"\n-- {t.descricao}\nCREATE TABLE {nome} (\n" + ",\n".join(defs) + "\n);")
    linhas.append("\nCREATE UNIQUE INDEX uq_usuario_email_lower ON usuario (lower(email));")
    linhas.append("\nCOMMIT;\n")
    return "\n".join(linhas)


# ---------------------------------------------------------------- draw.io
W, CAB, LIN, GAP_X, GAP_Y = 290, 30, 20, 60, 40
CORES = {"MOD01": ("#dae8fc", "#6c8ebf"), "MOD02": ("#e1d5e7", "#9673a6"), "MOD03": ("#d5e8d4", "#82b366"),
         "MOD04": ("#fff2cc", "#d6b656"), "MOD05": ("#f8cecc", "#b85450")}


def rotulo_coluna(col: Col) -> str:
    chaves = " ".join(k for k, v in (("PK", col.pk), ("FK", bool(col.fk)), ("UK", col.uk)) if v)
    nome = f"<u>{col.nome}</u>" if col.pk else col.nome
    if col.novo:
        nome = f"<i>{nome}</i>"
    return (f'<span style="display:inline-block;width:46px;font-weight:bold;color:#555">{chaves}</span>'
            f"{nome}: {col.tipo}{'' if col.nulo else ' <b>NN</b>'}")


def pagina_drawio(mod: str, idx: int) -> str:
    cells, pos = [], {}
    titulo = html.escape(f"SIGA UEA · DER · {MODULOS[mod]}")
    cells.append(f'<mxCell id="p{idx}-t" value="{titulo}" style="text;html=1;fontSize=20;fontStyle=1;align=left;" '
                 f'vertex="1" parent="1"><mxGeometry x="40" y="10" width="1100" height="34" as="geometry"/></mxCell>')
    x = 40
    for coluna in PAGINAS[mod]:
        y = 70
        for nome in coluna:
            t = POR_NOME[nome]
            ref = t.modulo != mod
            cols = [col for col in t.cols if col.pk] if ref else t.cols
            h = CAB + LIN * len(cols)
            pos[nome] = (x, y, h)
            fill, stroke = ("#f5f5f5", "#999999") if ref else CORES[mod]
            tracejado = "dashed=1;" if (not t.implementada and not ref) else ""
            rotulo = f"{nome} ({t.modulo})" if ref else nome
            cid = f"p{idx}-{nome}"
            cells.append(
                f'<mxCell id="{cid}" value={quoteattr(rotulo)} style="swimlane;fontStyle=1;childLayout=stackLayout;'
                f"horizontal=1;startSize={CAB};horizontalStack=0;resizeParent=1;resizeParentMax=0;resizeLast=0;"
                f'collapsible=0;marginBottom=0;html=1;fillColor={fill};strokeColor={stroke};fontSize=12;rounded=1;arcSize=5;{tracejado}" '
                f'vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{W}" height="{h}" as="geometry"/></mxCell>')
            for i, col in enumerate(cols):
                cells.append(
                    f'<mxCell id="{cid}-{i}" value={quoteattr(rotulo_coluna(col))} style="text;strokeColor=none;fillColor=none;'
                    f'align=left;verticalAlign=middle;spacingLeft=6;overflow=hidden;html=1;fontSize=10;" vertex="1" '
                    f'parent="{cid}"><mxGeometry y="{CAB + i * LIN}" width="{W}" height="{LIN}" as="geometry"/></mxCell>')
            y += h + GAP_Y
        x += W + GAP_X
    # Relacionamentos: FKs das tabelas do módulo para tabelas presentes na página.
    n = 0
    for nome in pos:
        t = POR_NOME[nome]
        if t.modulo != mod:
            continue
        for col in t.cols:
            if not col.fk or col.fk not in pos:
                continue
            um_para_um = col.pk and len([k for k in t.cols if k.pk]) == 1 or col.uk
            ponta_pai = "ERzeroToOne" if col.nulo else "ERmandOne"
            ponta_filho = "ERzeroToOne" if um_para_um else "ERzeroToMany"
            loop = "" if col.fk != nome else "loop=1;"
            cells.append(
                f'<mxCell id="p{idx}-r{n}" value={quoteattr(col.nome)} style="edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;'
                f"startArrow={ponta_pai};endArrow={ponta_filho};startFill=0;endFill=0;startSize=9;endSize=9;fontSize=9;"
                f'fontColor=#666666;labelBackgroundColor=#ffffff;strokeColor=#555555;{loop}" edge="1" parent="1" '
                f'source="p{idx}-{col.fk}" target="p{idx}-{nome}"><mxGeometry relative="1" as="geometry"/></mxCell>')
            n += 1
    altura = max(y for _, y, _ in pos.values()) + 600
    legenda = ("<b>Legenda</b><br>PK chave primária (sublinhada) · FK estrangeira · UK única · NN NOT NULL<br>"
               "Borda contínua: tabela já criada por migração · borda tracejada: planejada<br>"
               "<i>Itálico</i>: coluna planejada em tabela existente · cinza: tabela de outro módulo (só a PK)<br>"
               "Pé de galinha: | um · o zero · &lt; muitos · rótulo da linha = coluna FK")
    cells.append(f'<mxCell id="p{idx}-leg" value={quoteattr(legenda)} style="text;html=1;align=left;verticalAlign=top;'
                 f'spacing=8;fillColor=#f5f5f5;strokeColor=#999999;rounded=1;fontSize=11;" vertex="1" parent="1">'
                 f'<mxGeometry x="{x}" y="70" width="380" height="110" as="geometry"/></mxCell>')
    nome_pag = html.escape(MODULOS[mod])
    return (f'<diagram name="{nome_pag}" id="der-{mod}"><mxGraphModel dx="1600" dy="1000" grid="1" gridSize="10" '
            f'guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{x + 420}" '
            f'pageHeight="{altura}" math="0" shadow="0"><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
            + "".join(cells) + "</root></mxGraphModel></diagram>")


def drawio() -> str:
    return ('<mxfile host="app.diagrams.net">'
            + "".join(pagina_drawio(m, i) for i, m in enumerate(PAGINAS)) + "</mxfile>")


# ---------------------------------------------------------------- Markdown
def mermaid() -> str:
    tipo = lambda s: re.sub(r"\W", "_", s.split("(")[0]).lower()  # noqa: E731
    linhas = ["erDiagram"]
    for t in T:
        for col in t.cols:
            if col.fk and col.fk != t.nome:
                um = (col.pk and len([k for k in t.cols if k.pk]) == 1) or col.uk
                pai = "|o" if col.nulo else "||"
                filho = "o|" if um else "o{"
                linhas.append(f'    {col.fk} {pai}--{filho} {t.nome} : "{col.nome}"')
    for t in T:
        linhas.append(f"    {t.nome} {{")
        for col in t.cols:
            chaves = ",".join(k for k, v in (("PK", col.pk), ("FK", bool(col.fk)), ("UK", col.uk)) if v)
            linhas.append(f"        {tipo(col.tipo)} {col.nome}{(' ' + chaves) if chaves else ''}")
        linhas.append("    }")
    return "\n".join(linhas)


def markdown() -> str:
    implementadas = [t for t in T if t.implementada]
    partes = [
        "# DER completo do SIGA UEA (HT02 · SCRUM-107)",
        "",
        "Gerado por [`modelo.py`](modelo.py); não edite à mão. O mesmo modelo gera o "
        "[`der-siga-uea.drawio`](der-siga-uea.drawio) (uma página por módulo) e o "
        "[`der-siga-uea.sql`](der-siga-uea.sql), que é executado num PostgreSQL para conferir chaves e restrições.",
        "",
        f"**{len(T)} tabelas**: {len(implementadas)} já criadas pelas migrações (MOD01) e "
        f"{len(T) - len(implementadas)} planejadas para os próximos marcos. Os nomes seguem as entidades dos "
        "diagramas de sequência FL01 a FL10 (`MatriculaTurma` → `matricula_turma`, `ResultadoDefesa` → `resultado_defesa`).",
        "",
        "## Histórico preservado (CA-02 da HT02)",
        "",
        "| O que muda | Onde fica o histórico |",
        "|---|---|",
        "| Situação acadêmica do TCC | `historico_situacao` (cada transição, quem e quando) |",
        "| Parecer da coordenação | `analise_cadastro` (uma linha por decisão; o protocolo não muda) |",
        "| Orientador substituído | `orientacao` com status `SUBSTITUIDA`, data e justificativa; o novo vínculo é outra linha (RN16) |",
        "| Versões do PDF | `documento_tcc` (versão nova a cada envio; a anterior permanece) |",
        "| Remarcação, cancelamento, suplência | `historico_defesa` com os valores anteriores |",
        "| Retificação do resultado | `resultado_defesa` com `versao` e `vigente`; ata e folha antigas ficam em `documento_oficial` com `substituido_em` |",
        "| Instrumento de avaliação | `instrumento_avaliacao` versionado; cada avaliação aponta para a versão usada (RN19) |",
        "| Situação editorial | `historico_publicacao`; outro veículo é outra `publicacao_artigo` |",
        "| Qualquer alteração | `log_auditoria`, que o banco não deixa alterar nem apagar (RNF03) |",
        "",
        "Indicadores (MOD06) e agenda (MOD07) não têm tabelas próprias: são consultas sobre `tcc`, `orientacao`, "
        "`banca_membro`, `publicacao_artigo` e `defesa` (`publicada`).",
        "",
        "## Diagrama",
        "",
        "```mermaid",
        mermaid(),
        "```",
        "",
        "## Dicionário de dados",
    ]
    for mod, titulo in MODULOS.items():
        partes += ["", f"### {titulo}"]
        for t in [t for t in T if t.modulo == mod]:
            estado = "criada" if t.implementada else "planejada"
            partes += ["", f"**`{t.nome}`** ({estado}) · {t.descricao} Requisitos: {t.requisitos or '—'}", "",
                       "| Coluna | Tipo | Chave | Nulo | Observação |", "|---|---|---|---|---|"]
            for col in t.cols:
                chave = " ".join(k for k, v in (("PK", col.pk), (f"FK → {col.fk}", bool(col.fk)), ("UK", col.uk)) if v)
                obs = col.nota
                if col.valores:
                    obs = (obs + "; " if obs else "") + "valores: " + ", ".join(col.valores)
                if col.novo:
                    obs = (obs + "; " if obs else "") + "coluna planejada"
                partes.append(f"| `{col.nome}` | {col.tipo} | {chave} | {'sim' if col.nulo else 'não'} | {obs} |")
            extras = [f"único ({', '.join(u)})" for u in t.unicos] + [f"CHECK {ch}" for ch in t.checks]
            if extras:
                partes += ["", "Restrições: " + " · ".join(f"`{e}`" for e in extras)]
    return "\n".join(partes) + "\n"


if __name__ == "__main__":
    validar()
    (AQUI / "der-siga-uea.sql").write_text(sql(), encoding="utf8")
    (AQUI / "der-siga-uea.drawio").write_text(drawio(), encoding="utf8")
    (AQUI / "der-siga-uea.md").write_text(markdown(), encoding="utf8")
    print(f"{len(T)} tabelas, {sum(1 for t in T if t.implementada)} criadas; arquivos em {AQUI}")
