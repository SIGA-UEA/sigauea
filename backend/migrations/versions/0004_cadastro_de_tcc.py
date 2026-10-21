"""Cadastro de TCC (Sprint S03): período letivo, turma, matrícula na turma, TCC,
palavras-chave, histórico de situação, orientação e informações do artigo
(RBN03.01 a RBN03.05, RBN06.01 a RBN06.03, RBN08.01 a RBN08.03, RN04, RN05, RN10, RN16).

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, Sequence[str], None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "periodo_letivo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=6), nullable=False),
        sa.Column("inicio", sa.Date(), nullable=False),
        sa.Column("fim", sa.Date(), nullable=False),
        sa.Column("prazo_versao_final", sa.Date(), nullable=True),
        sa.CheckConstraint("fim > inicio", name="ck_periodo_letivo_datas"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo"),
    )
    op.create_table(
        "turma",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=30), nullable=False),
        sa.Column("disciplina", sa.String(length=4), nullable=False),
        sa.Column("curso_id", sa.Integer(), nullable=False),
        sa.Column("periodo_id", sa.Integer(), nullable=False),
        sa.Column("professor_id", sa.Integer(), nullable=False),
        sa.Column("encerrada_em", sa.DateTime(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.CheckConstraint("disciplina IN ('TCC1', 'TCC2')", name="ck_turma_disciplina"),
        sa.ForeignKeyConstraint(["curso_id"], ["curso.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["periodo_id"], ["periodo_letivo.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["professor_id"], ["docente.usuario_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo"),
        sa.UniqueConstraint(
            "curso_id", "disciplina", "periodo_id", "professor_id", name="uq_turma"
        ),
    )
    op.create_table(
        "matricula_turma",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("turma_id", sa.Integer(), nullable=False),
        sa.Column("aluno_id", sa.Integer(), nullable=False),
        sa.Column("situacao", sa.String(length=12), nullable=False),
        sa.Column("nota_final", sa.Numeric(precision=3, scale=1), nullable=True),
        sa.Column("incluido_por", sa.Integer(), nullable=False),
        sa.Column("incluido_em", sa.DateTime(), nullable=False),
        sa.Column("situacao_alterada_em", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "situacao IN ('MATRICULADO', 'DESISTENTE', 'APROVADO', 'REPROVADO')",
            name="ck_matricula_turma_situacao",
        ),
        sa.CheckConstraint(
            "nota_final IS NULL OR nota_final BETWEEN 0 AND 10", name="ck_matricula_turma_nota"
        ),
        sa.ForeignKeyConstraint(["aluno_id"], ["aluno.usuario_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["incluido_por"], ["usuario.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["turma_id"], ["turma.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("turma_id", "aluno_id", name="uq_matricula_turma"),
    )
    with op.batch_alter_table("matricula_turma", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_matricula_turma_aluno_id"), ["aluno_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_matricula_turma_turma_id"), ["turma_id"], unique=False)

    op.create_table(
        "tcc",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("aluno_id", sa.Integer(), nullable=False),
        sa.Column("turma_id", sa.Integer(), nullable=False),
        sa.Column("periodo_id", sa.Integer(), nullable=False),
        sa.Column("etapa", sa.String(length=4), nullable=False),
        sa.Column("modalidade", sa.String(length=10), nullable=False),
        sa.Column("titulo", sa.String(length=300), nullable=False),
        sa.Column("subtitulo", sa.String(length=300), nullable=True),
        sa.Column("resumo", sa.Text(), nullable=False),
        sa.Column("area_id", sa.Integer(), nullable=False),
        sa.Column("situacao", sa.String(length=12), nullable=False),
        sa.Column("protocolo", sa.String(length=20), nullable=True),
        sa.Column("submetido_em", sa.DateTime(), nullable=True),
        sa.Column("concluido_em", sa.DateTime(), nullable=True),
        sa.Column("desistencia_motivo", sa.Text(), nullable=True),
        sa.Column("tcc_origem_id", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(), nullable=False),
        sa.CheckConstraint("etapa IN ('TCC1', 'TCC2')", name="ck_tcc_etapa"),
        sa.CheckConstraint("modalidade IN ('ARTIGO', 'MONOGRAFIA')", name="ck_tcc_modalidade"),
        sa.CheckConstraint(
            "situacao IN ('RASCUNHO', 'EM_ANALISE', 'APROVADO', 'DEVOLVIDO', 'REPROVADO', 'CONCLUIDO', 'DESISTENCIA')",
            name="ck_tcc_situacao",
        ),
        sa.ForeignKeyConstraint(["aluno_id"], ["aluno.usuario_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["area_id"], ["area_interesse.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["periodo_id"], ["periodo_letivo.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tcc_origem_id"], ["tcc.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["turma_id"], ["turma.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("aluno_id", "periodo_id", name="uq_tcc_aluno_periodo"),
        sa.UniqueConstraint("protocolo"),
    )
    with op.batch_alter_table("tcc", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_tcc_aluno_id"), ["aluno_id"], unique=False)

    op.create_table(
        "historico_situacao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tcc_id", sa.Integer(), nullable=False),
        sa.Column("situacao_anterior", sa.String(length=12), nullable=True),
        sa.Column("situacao_nova", sa.String(length=12), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("registrado_em", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tcc_id"], ["tcc.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("historico_situacao", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_historico_situacao_tcc_id"), ["tcc_id"], unique=False)

    op.create_table(
        "orientacao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tcc_id", sa.Integer(), nullable=False),
        sa.Column("professor_id", sa.Integer(), nullable=False),
        sa.Column("papel", sa.String(length=12), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False),
        sa.Column("solicitado_em", sa.DateTime(), nullable=False),
        sa.Column("respondido_em", sa.DateTime(), nullable=True),
        sa.Column("motivo_recusa", sa.Text(), nullable=True),
        sa.Column("encerrado_em", sa.DateTime(), nullable=True),
        sa.Column("justificativa_encerramento", sa.Text(), nullable=True),
        sa.CheckConstraint("papel IN ('ORIENTADOR', 'COORIENTADOR')", name="ck_orientacao_papel"),
        sa.CheckConstraint(
            "status IN ('PENDENTE', 'ACEITA', 'RECUSADA', 'SUBSTITUIDA')",
            name="ck_orientacao_status",
        ),
        sa.ForeignKeyConstraint(["professor_id"], ["usuario.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tcc_id"], ["tcc.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("orientacao", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_orientacao_professor_id"), ["professor_id"], unique=False
        )
        batch_op.create_index(batch_op.f("ix_orientacao_tcc_id"), ["tcc_id"], unique=False)

    op.create_table(
        "publicacao_artigo",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tcc_id", sa.Integer(), nullable=False),
        sa.Column("tipo_veiculo", sa.String(length=10), nullable=False),
        sa.Column("veiculo", sa.String(length=200), nullable=False),
        sa.Column("qualis", sa.String(length=2), nullable=True),
        sa.Column("doi", sa.String(length=200), nullable=True),
        sa.Column("situacao_atual", sa.String(length=12), nullable=False),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "situacao_atual <> 'PUBLICADO' OR doi IS NOT NULL", name="ck_publicacao_artigo_doi"
        ),
        sa.CheckConstraint(
            "situacao_atual IN ('SUBMETIDO', 'EM_REVISAO', 'ACEITO', 'RECUSADO', 'PUBLICADO')",
            name="ck_publicacao_artigo_situacao_atual",
        ),
        sa.CheckConstraint(
            "tipo_veiculo IN ('PERIODICO', 'CONGRESSO')", name="ck_publicacao_artigo_tipo_veiculo"
        ),
        sa.ForeignKeyConstraint(["tcc_id"], ["tcc.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("publicacao_artigo", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_publicacao_artigo_tcc_id"), ["tcc_id"], unique=False)

    op.create_table(
        "tcc_palavra_chave",
        sa.Column("tcc_id", sa.Integer(), nullable=False),
        sa.Column("ordem", sa.SmallInteger(), nullable=False),
        sa.Column("palavra", sa.String(length=60), nullable=False),
        sa.CheckConstraint("ordem BETWEEN 1 AND 10", name="ck_tcc_palavra_chave_ordem"),
        sa.ForeignKeyConstraint(["tcc_id"], ["tcc.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("tcc_id", "ordem"),
    )
    op.create_table(
        "historico_publicacao",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("publicacao_id", sa.Integer(), nullable=False),
        sa.Column("situacao", sa.String(length=12), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("registrado_em", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "situacao IN ('SUBMETIDO', 'EM_REVISAO', 'ACEITO', 'RECUSADO', 'PUBLICADO')",
            name="ck_historico_publicacao_situacao",
        ),
        sa.ForeignKeyConstraint(["publicacao_id"], ["publicacao_artigo.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("historico_publicacao", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_historico_publicacao_publicacao_id"), ["publicacao_id"], unique=False
        )

    with op.batch_alter_table("notificacao_email", schema=None) as batch_op:
        batch_op.add_column(sa.Column("entidade", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("entidade_id", sa.Integer(), nullable=True))
        # tipos novos (ORIENTACAO_RECUSADA, ...) passam de 20 caracteres
        batch_op.alter_column("tipo", existing_type=sa.String(length=20), type_=sa.String(length=30))


def downgrade() -> None:
    with op.batch_alter_table("notificacao_email", schema=None) as batch_op:
        batch_op.alter_column("tipo", existing_type=sa.String(length=30), type_=sa.String(length=20))
        batch_op.drop_column("entidade_id")
        batch_op.drop_column("entidade")

    with op.batch_alter_table("historico_publicacao", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_historico_publicacao_publicacao_id"))

    op.drop_table("historico_publicacao")
    op.drop_table("tcc_palavra_chave")
    with op.batch_alter_table("publicacao_artigo", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_publicacao_artigo_tcc_id"))

    op.drop_table("publicacao_artigo")
    with op.batch_alter_table("orientacao", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_orientacao_tcc_id"))
        batch_op.drop_index(batch_op.f("ix_orientacao_professor_id"))

    op.drop_table("orientacao")
    with op.batch_alter_table("historico_situacao", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_historico_situacao_tcc_id"))

    op.drop_table("historico_situacao")
    with op.batch_alter_table("tcc", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_tcc_aluno_id"))

    op.drop_table("tcc")
    with op.batch_alter_table("matricula_turma", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_matricula_turma_turma_id"))
        batch_op.drop_index(batch_op.f("ix_matricula_turma_aluno_id"))

    op.drop_table("matricula_turma")
    op.drop_table("turma")
    op.drop_table("periodo_letivo")
