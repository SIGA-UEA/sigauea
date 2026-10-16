-- SIGA UEA: esquema do banco no PostgreSQL (módulo de usuários e acesso, MOD01).
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

COMMIT;

