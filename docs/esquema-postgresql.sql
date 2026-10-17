-- SIGA UEA: esquema do banco no PostgreSQL (MOD01 e cadastro de TCC da S03).
-- Gerado a partir das migrações: cd backend; alembic upgrade head --sql
-- Não edite à mão: mude app/models.py, crie uma migração e gere de novo.

BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 0001

CREATE TABLE nucleo (
    id SERIAL NOT NULL, 
    sigla VARCHAR(20) NOT NULL, 
    nome VARCHAR(150) NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (sigla)
);

CREATE TABLE curso (
    id SERIAL NOT NULL, 
    sigla VARCHAR(10) NOT NULL, 
    nome VARCHAR(100) NOT NULL, 
    nucleo_id INTEGER NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(nucleo_id) REFERENCES nucleo (id) ON DELETE RESTRICT, 
    UNIQUE (sigla), 
    UNIQUE (nome)
);

CREATE TABLE area_interesse (
    id SERIAL NOT NULL, 
    nome VARCHAR(100) NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (nome)
);

CREATE TABLE perfil (
    id SERIAL NOT NULL, 
    codigo VARCHAR(30) NOT NULL, 
    nome VARCHAR(50) NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (codigo)
);

CREATE TABLE usuario (
    id SERIAL NOT NULL, 
    nome VARCHAR(150) NOT NULL, 
    email VARCHAR(254) NOT NULL, 
    telefone VARCHAR(20), 
    senha_hash VARCHAR(60), 
    ativo BOOLEAN NOT NULL, 
    inativado_em TIMESTAMP WITHOUT TIME ZONE, 
    tentativas_falhas INTEGER NOT NULL, 
    bloqueado_ate TIMESTAMP WITHOUT TIME ZONE, 
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX uq_usuario_email_lower ON usuario (lower(email));

CREATE TABLE usuario_perfil (
    usuario_id INTEGER NOT NULL, 
    perfil_id INTEGER NOT NULL, 
    atribuido_por INTEGER, 
    atribuido_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (usuario_id, perfil_id), 
    FOREIGN KEY(usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT, 
    FOREIGN KEY(perfil_id) REFERENCES perfil (id) ON DELETE RESTRICT, 
    FOREIGN KEY(atribuido_por) REFERENCES usuario (id) ON DELETE RESTRICT
);

CREATE TABLE docente (
    usuario_id INTEGER NOT NULL, 
    cargo VARCHAR(20) NOT NULL, 
    nucleo_id INTEGER NOT NULL, 
    curso_id INTEGER, 
    PRIMARY KEY (usuario_id), 
    FOREIGN KEY(usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT, 
    FOREIGN KEY(nucleo_id) REFERENCES nucleo (id) ON DELETE RESTRICT, 
    FOREIGN KEY(curso_id) REFERENCES curso (id) ON DELETE RESTRICT
);

CREATE TABLE docente_area (
    docente_id INTEGER NOT NULL, 
    area_id INTEGER NOT NULL, 
    PRIMARY KEY (docente_id, area_id), 
    FOREIGN KEY(docente_id) REFERENCES docente (usuario_id) ON DELETE RESTRICT, 
    FOREIGN KEY(area_id) REFERENCES area_interesse (id) ON DELETE RESTRICT
);

CREATE TABLE aluno (
    usuario_id INTEGER NOT NULL, 
    matricula VARCHAR(20) NOT NULL, 
    curso_id INTEGER NOT NULL, 
    PRIMARY KEY (usuario_id), 
    FOREIGN KEY(usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT, 
    FOREIGN KEY(curso_id) REFERENCES curso (id) ON DELETE RESTRICT, 
    UNIQUE (matricula)
);

CREATE TABLE token_usuario (
    id SERIAL NOT NULL, 
    usuario_id INTEGER NOT NULL, 
    tipo VARCHAR(20) NOT NULL, 
    token_hash CHAR(64) NOT NULL, 
    expira_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    usado_em TIMESTAMP WITHOUT TIME ZONE, 
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT, 
    UNIQUE (token_hash)
);

CREATE INDEX ix_token_usuario_usuario_id ON token_usuario (usuario_id);

CREATE TABLE sessao (
    id SERIAL NOT NULL, 
    usuario_id INTEGER NOT NULL, 
    token_hash CHAR(64) NOT NULL, 
    expira_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT, 
    UNIQUE (token_hash)
);

CREATE INDEX ix_sessao_usuario_id ON sessao (usuario_id);

CREATE TABLE notificacao_email (
    id SERIAL NOT NULL, 
    usuario_id INTEGER NOT NULL, 
    tipo VARCHAR(20) NOT NULL, 
    destinatario VARCHAR(254) NOT NULL, 
    status VARCHAR(10) NOT NULL, 
    tentativas INTEGER NOT NULL, 
    erro TEXT, 
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    enviado_em TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT
);

CREATE INDEX ix_notificacao_email_usuario_id ON notificacao_email (usuario_id);

CREATE TABLE log_auditoria (
    id SERIAL NOT NULL, 
    usuario_id INTEGER, 
    acao VARCHAR(40) NOT NULL, 
    entidade VARCHAR(40) NOT NULL, 
    entidade_id INTEGER, 
    campo VARCHAR(40), 
    valor_anterior TEXT, 
    valor_novo TEXT, 
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT
);

CREATE INDEX ix_log_auditoria_usuario_id ON log_auditoria (usuario_id);

CREATE INDEX ix_log_auditoria_criado_em ON log_auditoria (criado_em);

INSERT INTO alembic_version (version_num) VALUES ('0001') RETURNING alembic_version.version_num;

-- Running upgrade 0001 -> 0002

CREATE TABLE foto_usuario (
    usuario_id INTEGER NOT NULL, 
    tipo VARCHAR(20) NOT NULL, 
    conteudo BYTEA NOT NULL, 
    sha256 CHAR(64) NOT NULL, 
    atualizado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (usuario_id), 
    FOREIGN KEY(usuario_id) REFERENCES usuario (id) ON DELETE CASCADE
);

UPDATE alembic_version SET version_num='0002' WHERE alembic_version.version_num = '0001';

-- Running upgrade 0002 -> 0003

CREATE FUNCTION log_auditoria_somente_insercao() RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'log_auditoria nao pode ser alterado nem apagado (RNF03)';
            END;
            $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_log_auditoria_imutavel BEFORE UPDATE OR DELETE ON log_auditoria FOR EACH ROW EXECUTE FUNCTION log_auditoria_somente_insercao();

UPDATE alembic_version SET version_num='0003' WHERE alembic_version.version_num = '0002';

-- Running upgrade 0003 -> 0004

CREATE TABLE periodo_letivo (
    id SERIAL NOT NULL, 
    codigo VARCHAR(6) NOT NULL, 
    inicio DATE NOT NULL, 
    fim DATE NOT NULL, 
    prazo_versao_final DATE, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_periodo_letivo_datas CHECK (fim > inicio), 
    UNIQUE (codigo)
);

CREATE TABLE turma (
    id SERIAL NOT NULL, 
    codigo VARCHAR(30) NOT NULL, 
    disciplina VARCHAR(4) NOT NULL, 
    curso_id INTEGER NOT NULL, 
    periodo_id INTEGER NOT NULL, 
    professor_id INTEGER NOT NULL, 
    encerrada_em TIMESTAMP WITHOUT TIME ZONE, 
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_turma_disciplina CHECK (disciplina IN ('TCC1', 'TCC2')), 
    FOREIGN KEY(curso_id) REFERENCES curso (id) ON DELETE RESTRICT, 
    FOREIGN KEY(periodo_id) REFERENCES periodo_letivo (id) ON DELETE RESTRICT, 
    FOREIGN KEY(professor_id) REFERENCES docente (usuario_id) ON DELETE RESTRICT, 
    UNIQUE (codigo), 
    CONSTRAINT uq_turma UNIQUE (curso_id, disciplina, periodo_id, professor_id)
);

CREATE TABLE matricula_turma (
    id SERIAL NOT NULL, 
    turma_id INTEGER NOT NULL, 
    aluno_id INTEGER NOT NULL, 
    situacao VARCHAR(12) NOT NULL, 
    nota_final NUMERIC(3, 1), 
    incluido_por INTEGER NOT NULL, 
    incluido_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    situacao_alterada_em TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_matricula_turma_situacao CHECK (situacao IN ('MATRICULADO', 'DESISTENTE', 'APROVADO', 'REPROVADO')), 
    CONSTRAINT ck_matricula_turma_nota CHECK (nota_final IS NULL OR nota_final BETWEEN 0 AND 10), 
    FOREIGN KEY(aluno_id) REFERENCES aluno (usuario_id) ON DELETE RESTRICT, 
    FOREIGN KEY(incluido_por) REFERENCES usuario (id) ON DELETE RESTRICT, 
    FOREIGN KEY(turma_id) REFERENCES turma (id) ON DELETE RESTRICT, 
    CONSTRAINT uq_matricula_turma UNIQUE (turma_id, aluno_id)
);

CREATE INDEX ix_matricula_turma_aluno_id ON matricula_turma (aluno_id);

CREATE INDEX ix_matricula_turma_turma_id ON matricula_turma (turma_id);

CREATE TABLE tcc (
    id SERIAL NOT NULL, 
    aluno_id INTEGER NOT NULL, 
    turma_id INTEGER NOT NULL, 
    periodo_id INTEGER NOT NULL, 
    etapa VARCHAR(4) NOT NULL, 
    modalidade VARCHAR(10) NOT NULL, 
    titulo VARCHAR(300) NOT NULL, 
    subtitulo VARCHAR(300), 
    resumo TEXT NOT NULL, 
    area_id INTEGER NOT NULL, 
    situacao VARCHAR(12) NOT NULL, 
    protocolo VARCHAR(20), 
    submetido_em TIMESTAMP WITHOUT TIME ZONE, 
    concluido_em TIMESTAMP WITHOUT TIME ZONE, 
    desistencia_motivo TEXT, 
    tcc_origem_id INTEGER, 
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    atualizado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_tcc_etapa CHECK (etapa IN ('TCC1', 'TCC2')), 
    CONSTRAINT ck_tcc_modalidade CHECK (modalidade IN ('ARTIGO', 'MONOGRAFIA')), 
    CONSTRAINT ck_tcc_situacao CHECK (situacao IN ('RASCUNHO', 'EM_ANALISE', 'APROVADO', 'DEVOLVIDO', 'REPROVADO', 'CONCLUIDO', 'DESISTENCIA')), 
    FOREIGN KEY(aluno_id) REFERENCES aluno (usuario_id) ON DELETE RESTRICT, 
    FOREIGN KEY(area_id) REFERENCES area_interesse (id) ON DELETE RESTRICT, 
    FOREIGN KEY(periodo_id) REFERENCES periodo_letivo (id) ON DELETE RESTRICT, 
    FOREIGN KEY(tcc_origem_id) REFERENCES tcc (id) ON DELETE RESTRICT, 
    FOREIGN KEY(turma_id) REFERENCES turma (id) ON DELETE RESTRICT, 
    CONSTRAINT uq_tcc_aluno_periodo UNIQUE (aluno_id, periodo_id), 
    UNIQUE (protocolo)
);

CREATE INDEX ix_tcc_aluno_id ON tcc (aluno_id);

CREATE TABLE historico_situacao (
    id SERIAL NOT NULL, 
    tcc_id INTEGER NOT NULL, 
    situacao_anterior VARCHAR(12), 
    situacao_nova VARCHAR(12) NOT NULL, 
    usuario_id INTEGER NOT NULL, 
    observacao TEXT, 
    registrado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(tcc_id) REFERENCES tcc (id) ON DELETE RESTRICT, 
    FOREIGN KEY(usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT
);

CREATE INDEX ix_historico_situacao_tcc_id ON historico_situacao (tcc_id);

CREATE TABLE orientacao (
    id SERIAL NOT NULL, 
    tcc_id INTEGER NOT NULL, 
    professor_id INTEGER NOT NULL, 
    papel VARCHAR(12) NOT NULL, 
    status VARCHAR(12) NOT NULL, 
    solicitado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    respondido_em TIMESTAMP WITHOUT TIME ZONE, 
    motivo_recusa TEXT, 
    encerrado_em TIMESTAMP WITHOUT TIME ZONE, 
    justificativa_encerramento TEXT, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_orientacao_papel CHECK (papel IN ('ORIENTADOR', 'COORIENTADOR')), 
    CONSTRAINT ck_orientacao_status CHECK (status IN ('PENDENTE', 'ACEITA', 'RECUSADA', 'SUBSTITUIDA')), 
    FOREIGN KEY(professor_id) REFERENCES usuario (id) ON DELETE RESTRICT, 
    FOREIGN KEY(tcc_id) REFERENCES tcc (id) ON DELETE RESTRICT
);

CREATE INDEX ix_orientacao_professor_id ON orientacao (professor_id);

CREATE INDEX ix_orientacao_tcc_id ON orientacao (tcc_id);

CREATE TABLE publicacao_artigo (
    id SERIAL NOT NULL, 
    tcc_id INTEGER NOT NULL, 
    tipo_veiculo VARCHAR(10) NOT NULL, 
    veiculo VARCHAR(200) NOT NULL, 
    qualis VARCHAR(2), 
    doi VARCHAR(200), 
    situacao_atual VARCHAR(12) NOT NULL, 
    criado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_publicacao_artigo_doi CHECK (situacao_atual <> 'PUBLICADO' OR doi IS NOT NULL), 
    CONSTRAINT ck_publicacao_artigo_situacao_atual CHECK (situacao_atual IN ('SUBMETIDO', 'EM_REVISAO', 'ACEITO', 'RECUSADO', 'PUBLICADO')), 
    CONSTRAINT ck_publicacao_artigo_tipo_veiculo CHECK (tipo_veiculo IN ('PERIODICO', 'CONGRESSO')), 
    FOREIGN KEY(tcc_id) REFERENCES tcc (id) ON DELETE RESTRICT
);

CREATE INDEX ix_publicacao_artigo_tcc_id ON publicacao_artigo (tcc_id);

CREATE TABLE tcc_palavra_chave (
    tcc_id INTEGER NOT NULL, 
    ordem SMALLINT NOT NULL, 
    palavra VARCHAR(60) NOT NULL, 
    PRIMARY KEY (tcc_id, ordem), 
    CONSTRAINT ck_tcc_palavra_chave_ordem CHECK (ordem BETWEEN 1 AND 10), 
    FOREIGN KEY(tcc_id) REFERENCES tcc (id) ON DELETE RESTRICT
);

CREATE TABLE historico_publicacao (
    id SERIAL NOT NULL, 
    publicacao_id INTEGER NOT NULL, 
    situacao VARCHAR(12) NOT NULL, 
    data DATE NOT NULL, 
    usuario_id INTEGER, 
    registrado_em TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT ck_historico_publicacao_situacao CHECK (situacao IN ('SUBMETIDO', 'EM_REVISAO', 'ACEITO', 'RECUSADO', 'PUBLICADO')), 
    FOREIGN KEY(publicacao_id) REFERENCES publicacao_artigo (id) ON DELETE RESTRICT, 
    FOREIGN KEY(usuario_id) REFERENCES usuario (id) ON DELETE RESTRICT
);

CREATE INDEX ix_historico_publicacao_publicacao_id ON historico_publicacao (publicacao_id);

ALTER TABLE notificacao_email ADD COLUMN entidade VARCHAR(40);

ALTER TABLE notificacao_email ADD COLUMN entidade_id INTEGER;

ALTER TABLE notificacao_email ALTER COLUMN tipo TYPE VARCHAR(30);

UPDATE alembic_version SET version_num='0004' WHERE alembic_version.version_num = '0003';

COMMIT;

