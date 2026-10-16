-- SIGA UEA: DER completo em DDL PostgreSQL (HT02). Gerado por docs/der/modelo.py; não edite à mão.
-- As tabelas do MOD01 já existem pelas migrações; as demais são o modelo dos próximos marcos.
BEGIN;

-- Núcleo acadêmico (NUCOMP).
CREATE TABLE nucleo (
    id SERIAL,
    sigla VARCHAR(20) NOT NULL,
    nome VARCHAR(150) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (sigla)
);

-- Cursos contemplados (RN01).
CREATE TABLE curso (
    id SERIAL,
    sigla VARCHAR(10) NOT NULL,
    nome VARCHAR(100) NOT NULL,
    nucleo_id INTEGER NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (sigla),
    UNIQUE (nome),
    FOREIGN KEY (nucleo_id) REFERENCES nucleo (id) ON DELETE RESTRICT
);

-- Áreas de interesse mantidas pela coordenação.
CREATE TABLE area_interesse (
    id SERIAL,
    nome VARCHAR(100) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (nome)
);

-- Os cinco perfis de acesso (RN07).
CREATE TABLE perfil (
    id SERIAL,
    codigo VARCHAR(30) NOT NULL,
    nome VARCHAR(50) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (codigo)
);

-- Toda pessoa que acessa o sistema.
CREATE TABLE usuario (
    id SERIAL,
    nome VARCHAR(150) NOT NULL,
    email VARCHAR(254) NOT NULL,
    telefone VARCHAR(20),
    senha_hash VARCHAR(60),
    ativo BOOLEAN NOT NULL,
    inativado_em TIMESTAMP,
    tentativas_falhas INTEGER NOT NULL,
    bloqueado_ate TIMESTAMP,
    criado_em TIMESTAMP NOT NULL,
    PRIMARY KEY (id)
);

-- Perfis de cada pessoa e quem os atribuiu.
CREATE TABLE usuario_perfil (
    usuario_id INTEGER NOT NULL,
    perfil_id INTEGER NOT NULL,
    atribuido_por INTEGER,
    atribuido_em TIMESTAMP NOT NULL,
    PRIMARY KEY (usuario_id, perfil_id),
    FOREIGN KEY (usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT,
    FOREIGN KEY (perfil_id) REFERENCES perfil (id) ON DELETE RESTRICT,
    FOREIGN KEY (atribuido_por) REFERENCES usuario (id) ON DELETE RESTRICT
);

-- Dados de quem é docente (coordenador, professor, orientador).
CREATE TABLE docente (
    usuario_id INTEGER NOT NULL,
    cargo VARCHAR(20) NOT NULL CHECK (cargo IN ('coordenador', 'professor', 'orientador')),
    nucleo_id INTEGER NOT NULL,
    curso_id INTEGER,
    PRIMARY KEY (usuario_id),
    FOREIGN KEY (usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT,
    FOREIGN KEY (nucleo_id) REFERENCES nucleo (id) ON DELETE RESTRICT,
    FOREIGN KEY (curso_id) REFERENCES curso (id) ON DELETE RESTRICT
);

-- Áreas de interesse de cada docente (RN25).
CREATE TABLE docente_area (
    docente_id INTEGER NOT NULL,
    area_id INTEGER NOT NULL,
    PRIMARY KEY (docente_id, area_id),
    FOREIGN KEY (docente_id) REFERENCES docente (usuario_id) ON DELETE RESTRICT,
    FOREIGN KEY (area_id) REFERENCES area_interesse (id) ON DELETE RESTRICT
);

-- Dados de quem é aluno.
CREATE TABLE aluno (
    usuario_id INTEGER NOT NULL,
    matricula VARCHAR(20) NOT NULL,
    curso_id INTEGER NOT NULL,
    acesso_ate DATE,
    PRIMARY KEY (usuario_id),
    UNIQUE (matricula),
    FOREIGN KEY (usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT,
    FOREIGN KEY (curso_id) REFERENCES curso (id) ON DELETE RESTRICT
);

-- Foto de perfil (opcional).
CREATE TABLE foto_usuario (
    usuario_id INTEGER NOT NULL,
    tipo VARCHAR(20) NOT NULL,
    conteudo BYTEA NOT NULL,
    sha256 CHAR(64) NOT NULL,
    atualizado_em TIMESTAMP NOT NULL,
    PRIMARY KEY (usuario_id),
    FOREIGN KEY (usuario_id) REFERENCES usuario (id) ON DELETE CASCADE
);

-- Membro de banca ou coorientador de fora da UEA (AcessoLimitado).
CREATE TABLE usuario_externo (
    usuario_id INTEGER NOT NULL,
    instituicao VARCHAR(150) NOT NULL,
    PRIMARY KEY (usuario_id),
    FOREIGN KEY (usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT
);

-- Links de ativação e recuperação (só o hash).
CREATE TABLE token_usuario (
    id SERIAL,
    usuario_id INTEGER NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('ativacao', 'recuperacao')),
    token_hash CHAR(64) NOT NULL,
    expira_em TIMESTAMP NOT NULL,
    usado_em TIMESTAMP,
    criado_em TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (token_hash),
    FOREIGN KEY (usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT
);

-- Sessões de login (60 min de inatividade).
CREATE TABLE sessao (
    id SERIAL,
    usuario_id INTEGER NOT NULL,
    token_hash CHAR(64) NOT NULL,
    expira_em TIMESTAMP NOT NULL,
    criado_em TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (token_hash),
    FOREIGN KEY (usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT
);

-- Fila de e-mails de todos os módulos (NotificacaoEmail).
CREATE TABLE notificacao_email (
    id SERIAL,
    usuario_id INTEGER NOT NULL,
    tipo VARCHAR(30) NOT NULL,
    destinatario VARCHAR(254) NOT NULL,
    status VARCHAR(10) NOT NULL CHECK (status IN ('pendente', 'enviado', 'falha')),
    tentativas INTEGER NOT NULL,
    erro TEXT,
    entidade VARCHAR(40),
    entidade_id INTEGER,
    criado_em TIMESTAMP NOT NULL,
    enviado_em TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT
);

-- Log imutável de alterações (RNF03); trigger recusa UPDATE/DELETE.
CREATE TABLE log_auditoria (
    id SERIAL,
    usuario_id INTEGER,
    acao VARCHAR(40) NOT NULL,
    entidade VARCHAR(40) NOT NULL,
    entidade_id INTEGER,
    campo VARCHAR(40),
    valor_anterior TEXT,
    valor_novo TEXT,
    criado_em TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT
);

-- Proposta de TCC de um aluno, direcionada a área ou a professores.
CREATE TABLE proposta (
    id SERIAL,
    autor_id INTEGER NOT NULL,
    titulo VARCHAR(200) NOT NULL,
    descricao TEXT NOT NULL,
    destino VARCHAR(12) NOT NULL CHECK (destino IN ('AREA', 'PROFESSORES')),
    area_id INTEGER,
    oculta_em TIMESTAMP,
    criado_em TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (autor_id) REFERENCES usuario (id) ON DELETE RESTRICT,
    FOREIGN KEY (area_id) REFERENCES area_interesse (id) ON DELETE RESTRICT,
    CHECK (destino <> 'AREA' OR area_id IS NOT NULL)
);

-- Professores escolhidos quando destino = PROFESSORES.
CREATE TABLE proposta_destinatario (
    proposta_id INTEGER NOT NULL,
    professor_id INTEGER NOT NULL,
    PRIMARY KEY (proposta_id, professor_id),
    FOREIGN KEY (proposta_id) REFERENCES proposta (id) ON DELETE RESTRICT,
    FOREIGN KEY (professor_id) REFERENCES docente (usuario_id) ON DELETE RESTRICT
);

-- Comentários de professores nas propostas.
CREATE TABLE comentario_proposta (
    id SERIAL,
    proposta_id INTEGER NOT NULL,
    autor_id INTEGER NOT NULL,
    texto TEXT NOT NULL,
    oculto_em TIMESTAMP,
    criado_em TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (proposta_id) REFERENCES proposta (id) ON DELETE RESTRICT,
    FOREIGN KEY (autor_id) REFERENCES usuario (id) ON DELETE RESTRICT,
    CHECK (length(trim(texto)) > 0)
);

-- Período letivo AAAA/N e prazo da versão final (PeriodoLetivo).
CREATE TABLE periodo_letivo (
    id SERIAL,
    codigo VARCHAR(6) NOT NULL,
    inicio DATE NOT NULL,
    fim DATE NOT NULL,
    prazo_versao_final DATE,
    PRIMARY KEY (id),
    UNIQUE (codigo),
    CHECK (fim > inicio)
);

-- Turma de TCC1 (disciplina) ou TCC2 (orientador).
CREATE TABLE turma (
    id SERIAL,
    codigo VARCHAR(30) NOT NULL,
    disciplina VARCHAR(4) NOT NULL CHECK (disciplina IN ('TCC1', 'TCC2')),
    curso_id INTEGER NOT NULL,
    periodo_id INTEGER NOT NULL,
    professor_id INTEGER NOT NULL,
    encerrada_em TIMESTAMP,
    criado_em TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (codigo),
    UNIQUE (curso_id, disciplina, periodo_id, professor_id),
    FOREIGN KEY (curso_id) REFERENCES curso (id) ON DELETE RESTRICT,
    FOREIGN KEY (periodo_id) REFERENCES periodo_letivo (id) ON DELETE RESTRICT,
    FOREIGN KEY (professor_id) REFERENCES docente (usuario_id) ON DELETE RESTRICT
);

-- Aluno na turma e sua situação (MatriculaTurma).
CREATE TABLE matricula_turma (
    id SERIAL,
    turma_id INTEGER NOT NULL,
    aluno_id INTEGER NOT NULL,
    situacao VARCHAR(12) NOT NULL CHECK (situacao IN ('MATRICULADO', 'DESISTENTE', 'APROVADO', 'REPROVADO')),
    nota_final NUMERIC(3,1),
    incluido_por INTEGER NOT NULL,
    incluido_em TIMESTAMP NOT NULL,
    situacao_alterada_em TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (turma_id, aluno_id),
    FOREIGN KEY (turma_id) REFERENCES turma (id) ON DELETE RESTRICT,
    FOREIGN KEY (aluno_id) REFERENCES aluno (usuario_id) ON DELETE RESTRICT,
    FOREIGN KEY (incluido_por) REFERENCES usuario (id) ON DELETE RESTRICT,
    CHECK (nota_final IS NULL OR nota_final BETWEEN 0 AND 10)
);

-- O trabalho: cadastro, protocolo e situação acadêmica (TCC).
CREATE TABLE tcc (
    id SERIAL,
    aluno_id INTEGER NOT NULL,
    turma_id INTEGER NOT NULL,
    periodo_id INTEGER NOT NULL,
    etapa VARCHAR(4) NOT NULL CHECK (etapa IN ('TCC1', 'TCC2')),
    modalidade VARCHAR(10) NOT NULL CHECK (modalidade IN ('ARTIGO', 'MONOGRAFIA')),
    titulo VARCHAR(300) NOT NULL,
    subtitulo VARCHAR(300),
    resumo TEXT NOT NULL,
    area_id INTEGER NOT NULL,
    situacao VARCHAR(12) NOT NULL CHECK (situacao IN ('RASCUNHO', 'EM_ANALISE', 'APROVADO', 'DEVOLVIDO', 'REPROVADO', 'CONCLUIDO', 'DESISTENCIA')),
    protocolo VARCHAR(20),
    submetido_em TIMESTAMP,
    concluido_em TIMESTAMP,
    desistencia_motivo TEXT,
    tcc_origem_id INTEGER,
    criado_em TIMESTAMP NOT NULL,
    atualizado_em TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (protocolo),
    UNIQUE (aluno_id, periodo_id),
    FOREIGN KEY (aluno_id) REFERENCES aluno (usuario_id) ON DELETE RESTRICT,
    FOREIGN KEY (turma_id) REFERENCES turma (id) ON DELETE RESTRICT,
    FOREIGN KEY (periodo_id) REFERENCES periodo_letivo (id) ON DELETE RESTRICT,
    FOREIGN KEY (area_id) REFERENCES area_interesse (id) ON DELETE RESTRICT,
    FOREIGN KEY (tcc_origem_id) REFERENCES tcc (id) ON DELETE RESTRICT
);

-- Palavras-chave do TCC (no máximo 10).
CREATE TABLE tcc_palavra_chave (
    tcc_id INTEGER NOT NULL,
    ordem SMALLINT NOT NULL,
    palavra VARCHAR(60) NOT NULL,
    PRIMARY KEY (tcc_id, ordem),
    FOREIGN KEY (tcc_id) REFERENCES tcc (id) ON DELETE RESTRICT,
    CHECK (ordem BETWEEN 1 AND 10)
);

-- Cada mudança de situação do TCC (HistoricoSituacao).
CREATE TABLE historico_situacao (
    id SERIAL,
    tcc_id INTEGER NOT NULL,
    situacao_anterior VARCHAR(12),
    situacao_nova VARCHAR(12) NOT NULL,
    usuario_id INTEGER NOT NULL,
    observacao TEXT,
    registrado_em TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (tcc_id) REFERENCES tcc (id) ON DELETE RESTRICT,
    FOREIGN KEY (usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT
);

-- Decisões da coordenação sobre o cadastro (AnaliseCadastro).
CREATE TABLE analise_cadastro (
    id SERIAL,
    tcc_id INTEGER NOT NULL,
    coordenador_id INTEGER NOT NULL,
    resultado VARCHAR(10) NOT NULL CHECK (resultado IN ('APROVADO', 'DEVOLVIDO', 'REPROVADO')),
    parecer TEXT NOT NULL,
    decidido_em TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (tcc_id) REFERENCES tcc (id) ON DELETE RESTRICT,
    FOREIGN KEY (coordenador_id) REFERENCES docente (usuario_id) ON DELETE RESTRICT,
    CHECK (resultado = 'APROVADO' OR length(trim(parecer)) > 0)
);

-- Vínculos de orientação e coorientação, com histórico (Orientacao).
CREATE TABLE orientacao (
    id SERIAL,
    tcc_id INTEGER NOT NULL,
    professor_id INTEGER NOT NULL,
    papel VARCHAR(12) NOT NULL CHECK (papel IN ('ORIENTADOR', 'COORIENTADOR')),
    status VARCHAR(12) NOT NULL CHECK (status IN ('PENDENTE', 'ACEITA', 'RECUSADA', 'SUBSTITUIDA')),
    solicitado_em TIMESTAMP NOT NULL,
    respondido_em TIMESTAMP,
    motivo_recusa TEXT,
    encerrado_em TIMESTAMP,
    justificativa_encerramento TEXT,
    PRIMARY KEY (id),
    FOREIGN KEY (tcc_id) REFERENCES tcc (id) ON DELETE RESTRICT,
    FOREIGN KEY (professor_id) REFERENCES usuario (id) ON DELETE RESTRICT
);

-- Versões do PDF do TCC (DocumentoTCC).
CREATE TABLE documento_tcc (
    id SERIAL,
    tcc_id INTEGER NOT NULL,
    versao INTEGER NOT NULL,
    finalidade VARCHAR(12) NOT NULL CHECK (finalidade IN ('PRELIMINAR', 'BANCA', 'FINAL')),
    nome_arquivo VARCHAR(255) NOT NULL,
    tamanho_bytes INTEGER NOT NULL,
    sha256 CHAR(64) NOT NULL,
    caminho VARCHAR(500) NOT NULL,
    enviado_por INTEGER NOT NULL,
    enviado_em TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (tcc_id, versao),
    FOREIGN KEY (tcc_id) REFERENCES tcc (id) ON DELETE RESTRICT,
    FOREIGN KEY (enviado_por) REFERENCES usuario (id) ON DELETE RESTRICT,
    CHECK (tamanho_bytes BETWEEN 1 AND 20971520)
);

-- Tarefas/entregáveis definidos para um TCC aprovado.
CREATE TABLE tarefa_tcc (
    id SERIAL,
    tcc_id INTEGER NOT NULL,
    descricao TEXT NOT NULL,
    prazo DATE NOT NULL,
    cadastrada_por INTEGER NOT NULL,
    entregue_em TIMESTAMP,
    status VARCHAR(10) NOT NULL CHECK (status IN ('PENDENTE', 'ENTREGUE', 'ATRASADA')),
    criado_em TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (tcc_id) REFERENCES tcc (id) ON DELETE RESTRICT,
    FOREIGN KEY (cadastrada_por) REFERENCES usuario (id) ON DELETE RESTRICT
);

-- Salas e locais físicos de defesa (LocalDefesa).
CREATE TABLE local_defesa (
    id SERIAL,
    nome VARCHAR(100) NOT NULL,
    descricao VARCHAR(200),
    PRIMARY KEY (id),
    UNIQUE (nome)
);

-- Agendamento da defesa e divulgação na agenda (Defesa).
CREATE TABLE defesa (
    id SERIAL,
    tcc_id INTEGER NOT NULL,
    formato VARCHAR(10) NOT NULL CHECK (formato IN ('PRESENCIAL', 'REMOTO', 'HIBRIDO')),
    data DATE NOT NULL,
    inicio TIME NOT NULL,
    fim TIME NOT NULL,
    local_id INTEGER,
    link VARCHAR(500),
    situacao VARCHAR(10) NOT NULL CHECK (situacao IN ('CONFIRMADA', 'REMARCADA', 'CANCELADA', 'REALIZADA')),
    responsavel_id INTEGER NOT NULL,
    publicada BOOLEAN NOT NULL,
    publicada_em TIMESTAMP,
    divulgar_link BOOLEAN NOT NULL,
    revisao_banca BOOLEAN NOT NULL,
    criado_em TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (tcc_id) REFERENCES tcc (id) ON DELETE RESTRICT,
    FOREIGN KEY (local_id) REFERENCES local_defesa (id) ON DELETE RESTRICT,
    FOREIGN KEY (responsavel_id) REFERENCES docente (usuario_id) ON DELETE RESTRICT,
    CHECK (fim > inicio),
    CHECK ((formato = 'PRESENCIAL' AND local_id IS NOT NULL) OR (formato = 'REMOTO' AND link IS NOT NULL) OR (formato = 'HIBRIDO' AND local_id IS NOT NULL AND link IS NOT NULL))
);

-- Conta restrita a uma defesa ou a um TCC, com validade.
CREATE TABLE acesso_limitado (
    id SERIAL,
    usuario_id INTEGER NOT NULL,
    escopo VARCHAR(20) NOT NULL CHECK (escopo IN ('BANCA', 'COORIENTACAO')),
    defesa_id INTEGER,
    tcc_id INTEGER,
    expira_em TIMESTAMP,
    revogado_em TIMESTAMP,
    criado_em TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT,
    FOREIGN KEY (defesa_id) REFERENCES defesa (id) ON DELETE RESTRICT,
    FOREIGN KEY (tcc_id) REFERENCES tcc (id) ON DELETE RESTRICT,
    CHECK ((escopo = 'BANCA' AND defesa_id IS NOT NULL) OR (escopo = 'COORIENTACAO' AND tcc_id IS NOT NULL))
);

-- Agendamento, remarcação, cancelamento e suplência (HistoricoDefesa).
CREATE TABLE historico_defesa (
    id SERIAL,
    defesa_id INTEGER NOT NULL,
    evento VARCHAR(20) NOT NULL CHECK (evento IN ('AGENDAMENTO', 'REMARCACAO', 'CANCELAMENTO', 'SUPLENTE_CONVOCADO')),
    motivo TEXT,
    valores_anteriores JSONB,
    usuario_id INTEGER NOT NULL,
    registrado_em TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (defesa_id) REFERENCES defesa (id) ON DELETE RESTRICT,
    FOREIGN KEY (usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT
);

-- Membros da banca de uma defesa (BancaMembro).
CREATE TABLE banca_membro (
    id SERIAL,
    defesa_id INTEGER NOT NULL,
    usuario_id INTEGER NOT NULL,
    papel VARCHAR(12) NOT NULL CHECK (papel IN ('AVALIADOR', 'ORIENTADOR', 'COORIENTADOR', 'SUPLENTE')),
    interno BOOLEAN NOT NULL,
    convite_enviado_em TIMESTAMP,
    presente BOOLEAN,
    convocado_em TIMESTAMP,
    substitui_membro_id INTEGER,
    motivo_convocacao TEXT,
    PRIMARY KEY (id),
    UNIQUE (defesa_id, usuario_id),
    FOREIGN KEY (defesa_id) REFERENCES defesa (id) ON DELETE RESTRICT,
    FOREIGN KEY (usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT,
    FOREIGN KEY (substitui_membro_id) REFERENCES banca_membro (id) ON DELETE RESTRICT
);

-- Versões do instrumento de avaliação (InstrumentoAvaliacao).
CREATE TABLE instrumento_avaliacao (
    id SERIAL,
    versao INTEGER NOT NULL,
    vigente BOOLEAN NOT NULL,
    criado_por INTEGER NOT NULL,
    criado_em TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (versao),
    FOREIGN KEY (criado_por) REFERENCES usuario (id) ON DELETE RESTRICT
);

-- Parte escrita (7,0) e oral (3,0).
CREATE TABLE componente_avaliacao (
    id SERIAL,
    instrumento_id INTEGER NOT NULL,
    nome VARCHAR(60) NOT NULL,
    pontos NUMERIC(3,1) NOT NULL,
    ordem SMALLINT NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (instrumento_id) REFERENCES instrumento_avaliacao (id) ON DELETE RESTRICT
);

-- Critério com peso e texto dos três conceitos.
CREATE TABLE criterio_avaliacao (
    id SERIAL,
    componente_id INTEGER NOT NULL,
    nome VARCHAR(120) NOT NULL,
    peso NUMERIC(4,2) NOT NULL,
    texto_exemplar TEXT NOT NULL,
    texto_competente TEXT NOT NULL,
    texto_necessita TEXT NOT NULL,
    ordem SMALLINT NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (componente_id) REFERENCES componente_avaliacao (id) ON DELETE RESTRICT
);

-- Avaliação de um membro da banca (Avaliacao).
CREATE TABLE avaliacao (
    id SERIAL,
    defesa_id INTEGER NOT NULL,
    membro_id INTEGER NOT NULL,
    instrumento_id INTEGER NOT NULL,
    status VARCHAR(10) NOT NULL CHECK (status IN ('RASCUNHO', 'ENVIADA')),
    parecer TEXT,
    nota_total NUMERIC(3,1),
    enviada_em TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (defesa_id, membro_id),
    FOREIGN KEY (defesa_id) REFERENCES defesa (id) ON DELETE RESTRICT,
    FOREIGN KEY (membro_id) REFERENCES banca_membro (id) ON DELETE RESTRICT,
    FOREIGN KEY (instrumento_id) REFERENCES instrumento_avaliacao (id) ON DELETE RESTRICT
);

-- Conceito e nota por critério (AvaliacaoCriterio).
CREATE TABLE avaliacao_criterio (
    avaliacao_id INTEGER NOT NULL,
    criterio_id INTEGER NOT NULL,
    conceito VARCHAR(12) NOT NULL CHECK (conceito IN ('EXEMPLAR', 'COMPETENTE', 'NECESSITA')),
    nota NUMERIC(3,1) NOT NULL,
    nota_ponderada NUMERIC(4,2) NOT NULL,
    PRIMARY KEY (avaliacao_id, criterio_id),
    FOREIGN KEY (avaliacao_id) REFERENCES avaliacao (id) ON DELETE RESTRICT,
    FOREIGN KEY (criterio_id) REFERENCES criterio_avaliacao (id) ON DELETE RESTRICT,
    CHECK ((conceito = 'EXEMPLAR' AND nota BETWEEN 8 AND 10) OR (conceito = 'COMPETENTE' AND nota BETWEEN 6 AND 7.9) OR (conceito = 'NECESSITA' AND nota BETWEEN 0 AND 5.9))
);

-- Resultado confirmado, versionado por retificação (ResultadoDefesa).
CREATE TABLE resultado_defesa (
    id SERIAL,
    defesa_id INTEGER NOT NULL,
    versao INTEGER NOT NULL,
    vigente BOOLEAN NOT NULL,
    media NUMERIC(3,1) NOT NULL,
    nota_final NUMERIC(3,1) NOT NULL,
    regra_qualis BOOLEAN NOT NULL,
    resultado VARCHAR(24) NOT NULL CHECK (resultado IN ('APROVADO', 'APROVADO_COM_CORRECOES', 'REPROVADO')),
    parecer TEXT NOT NULL,
    confirmado_por INTEGER NOT NULL,
    confirmado_em TIMESTAMP NOT NULL,
    motivo_retificacao TEXT,
    prazo_versao_final DATE,
    prazo_motivo TEXT,
    anuencia_em TIMESTAMP,
    versao_final_id INTEGER,
    entregue_com_atraso BOOLEAN,
    atraso_aceito BOOLEAN,
    atraso_decidido_por INTEGER,
    atraso_decidido_em TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE (defesa_id, versao),
    FOREIGN KEY (defesa_id) REFERENCES defesa (id) ON DELETE RESTRICT,
    FOREIGN KEY (confirmado_por) REFERENCES usuario (id) ON DELETE RESTRICT,
    FOREIGN KEY (versao_final_id) REFERENCES documento_tcc (id) ON DELETE RESTRICT,
    FOREIGN KEY (atraso_decidido_por) REFERENCES usuario (id) ON DELETE RESTRICT
);

-- Correções exigidas pela banca (Correcao).
CREATE TABLE correcao (
    id SERIAL,
    resultado_id INTEGER NOT NULL,
    descricao TEXT NOT NULL,
    avaliador_id INTEGER NOT NULL,
    situacao VARCHAR(10) NOT NULL CHECK (situacao IN ('PENDENTE', 'ATENDIDA', 'APROVADA', 'DEVOLVIDA')),
    justificativa TEXT,
    decidida_por INTEGER,
    decidida_em TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (resultado_id) REFERENCES resultado_defesa (id) ON DELETE RESTRICT,
    FOREIGN KEY (avaliador_id) REFERENCES banca_membro (id) ON DELETE RESTRICT,
    FOREIGN KEY (decidida_por) REFERENCES usuario (id) ON DELETE RESTRICT
);

-- Ocorrências registradas na sessão (OcorrenciaDefesa).
CREATE TABLE ocorrencia_defesa (
    id SERIAL,
    defesa_id INTEGER NOT NULL,
    texto TEXT NOT NULL,
    autor_id INTEGER NOT NULL,
    criado_em TIMESTAMP NOT NULL,
    alterada_em TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (defesa_id) REFERENCES defesa (id) ON DELETE RESTRICT,
    FOREIGN KEY (autor_id) REFERENCES usuario (id) ON DELETE RESTRICT
);

-- Ouvintes presentes, para declaração de horas (OuvinteDefesa).
CREATE TABLE ouvinte_defesa (
    id SERIAL,
    defesa_id INTEGER NOT NULL,
    nome VARCHAR(150) NOT NULL,
    matricula VARCHAR(20),
    criado_em TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (defesa_id) REFERENCES defesa (id) ON DELETE RESTRICT
);

-- Ata, folha de aprovação, certificados e declarações (DocumentoOficial).
CREATE TABLE documento_oficial (
    id SERIAL,
    defesa_id INTEGER NOT NULL,
    tipo VARCHAR(16) NOT NULL CHECK (tipo IN ('ATA', 'FOLHA_APROVACAO', 'CERTIFICADO', 'DECLARACAO_HORAS')),
    versao INTEGER NOT NULL,
    vigente BOOLEAN NOT NULL,
    sha256 CHAR(64) NOT NULL,
    caminho VARCHAR(500) NOT NULL,
    membro_id INTEGER,
    ouvinte_id INTEGER,
    gerado_em TIMESTAMP NOT NULL,
    substituido_em TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (defesa_id) REFERENCES defesa (id) ON DELETE RESTRICT,
    FOREIGN KEY (membro_id) REFERENCES banca_membro (id) ON DELETE RESTRICT,
    FOREIGN KEY (ouvinte_id) REFERENCES ouvinte_defesa (id) ON DELETE RESTRICT
);

-- Submissão do artigo a um veículo (PublicacaoArtigo).
CREATE TABLE publicacao_artigo (
    id SERIAL,
    tcc_id INTEGER NOT NULL,
    tipo_veiculo VARCHAR(10) NOT NULL CHECK (tipo_veiculo IN ('PERIODICO', 'CONGRESSO')),
    veiculo VARCHAR(200) NOT NULL,
    qualis VARCHAR(2),
    doi VARCHAR(200),
    situacao_atual VARCHAR(12) NOT NULL CHECK (situacao_atual IN ('SUBMETIDO', 'EM_REVISAO', 'ACEITO', 'RECUSADO', 'PUBLICADO')),
    criado_em TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (tcc_id) REFERENCES tcc (id) ON DELETE RESTRICT,
    CHECK (situacao_atual <> 'PUBLICADO' OR doi IS NOT NULL)
);

-- Sequência de situações editoriais (HistoricoPublicacao).
CREATE TABLE historico_publicacao (
    id SERIAL,
    publicacao_id INTEGER NOT NULL,
    situacao VARCHAR(12) NOT NULL CHECK (situacao IN ('SUBMETIDO', 'EM_REVISAO', 'ACEITO', 'RECUSADO', 'PUBLICADO')),
    data DATE NOT NULL,
    usuario_id INTEGER,
    registrado_em TIMESTAMP NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (publicacao_id) REFERENCES publicacao_artigo (id) ON DELETE RESTRICT,
    FOREIGN KEY (usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX uq_usuario_email_lower ON usuario (lower(email));

COMMIT;
