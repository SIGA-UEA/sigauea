"""Correções e versão final: RBN11.01 a RBN11.04, RN11, RN17 (DS-FL07).

Do modelo físico entregue:
- tabela correcao: cada correção exigida pela banca, com a situação (pendente, atendida, aprovada ou devolvida),
  a justificativa da devolução e quem decidiu; tem também criada_em e atendida_em, que o SQL físico não tem;
- tabela documento_tcc: as versões do PDF do TCC; nesta entrega só a versão final a usa (RBN11.02);
- em resultado_defesa, as colunas do prazo da versão final, da versão final enviada e da entrega com atraso,
  que a 0011 deixou para as histórias das correções.

Revision ID: 0015
Revises: 0014
Create Date: 2026-11-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0015'
down_revision: Union[str, Sequence[str], None] = '0014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('documento_tcc',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tcc_id', sa.Integer(), nullable=False),
    sa.Column('versao', sa.Integer(), nullable=False),
    sa.Column('finalidade', sa.String(length=12), nullable=False),
    sa.Column('nome_arquivo', sa.String(length=255), nullable=False),
    sa.Column('tamanho_bytes', sa.Integer(), nullable=False),
    sa.Column('sha256', sa.String(length=64), nullable=False),
    sa.Column('caminho', sa.String(length=500), nullable=False),
    sa.Column('enviado_por', sa.Integer(), nullable=False),
    sa.Column('enviado_em', sa.DateTime(), nullable=False),
    sa.CheckConstraint("finalidade IN ('PRELIMINAR', 'BANCA', 'FINAL')", name='ck_documento_tcc_finalidade'),
    sa.CheckConstraint('tamanho_bytes BETWEEN 1 AND 20971520', name='ck_documento_tcc_tamanho'),
    sa.ForeignKeyConstraint(['enviado_por'], ['usuario.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['tcc_id'], ['tcc.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tcc_id', 'versao', name='uq_documento_tcc_tcc_versao')
    )
    with op.batch_alter_table('documento_tcc', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_documento_tcc_enviado_por'), ['enviado_por'], unique=False)
        batch_op.create_index(batch_op.f('ix_documento_tcc_tcc_id'), ['tcc_id'], unique=False)

    op.create_table('correcao',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('resultado_id', sa.Integer(), nullable=False),
    sa.Column('descricao', sa.Text(), nullable=False),
    sa.Column('avaliador_id', sa.Integer(), nullable=False),
    sa.Column('situacao', sa.String(length=10), nullable=False),
    sa.Column('justificativa', sa.Text(), nullable=True),
    sa.Column('criada_em', sa.DateTime(), nullable=False),
    sa.Column('atendida_em', sa.DateTime(), nullable=True),
    sa.Column('decidida_por', sa.Integer(), nullable=True),
    sa.Column('decidida_em', sa.DateTime(), nullable=True),
    sa.CheckConstraint("situacao <> 'DEVOLVIDA' OR length(trim(justificativa)) > 0", name='ck_correcao_justificativa'),
    sa.CheckConstraint("situacao IN ('PENDENTE', 'ATENDIDA', 'APROVADA', 'DEVOLVIDA')", name='ck_correcao_situacao'),
    sa.CheckConstraint('length(trim(descricao)) > 0', name='ck_correcao_descricao'),
    sa.ForeignKeyConstraint(['avaliador_id'], ['banca_membro.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['decidida_por'], ['usuario.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['resultado_id'], ['resultado_defesa.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('correcao', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_correcao_avaliador_id'), ['avaliador_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_correcao_decidida_por'), ['decidida_por'], unique=False)
        batch_op.create_index(batch_op.f('ix_correcao_resultado_id'), ['resultado_id'], unique=False)

    with op.batch_alter_table('resultado_defesa', schema=None) as batch_op:
        batch_op.add_column(sa.Column('prazo_versao_final', sa.Date(), nullable=True))
        batch_op.add_column(sa.Column('prazo_motivo', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('versao_final_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('entregue_com_atraso', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('atraso_aceito', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('atraso_decidido_por', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('atraso_decidido_em', sa.DateTime(), nullable=True))
        batch_op.create_index(batch_op.f('ix_resultado_defesa_atraso_decidido_por'), ['atraso_decidido_por'], unique=False)
        batch_op.create_index(batch_op.f('ix_resultado_defesa_versao_final_id'), ['versao_final_id'], unique=False)
        batch_op.create_foreign_key('fk_resultado_defesa_versao_final_id', 'documento_tcc', ['versao_final_id'], ['id'], ondelete='RESTRICT')
        batch_op.create_foreign_key('fk_resultado_defesa_atraso_decidido_por', 'usuario', ['atraso_decidido_por'], ['id'], ondelete='RESTRICT')



def downgrade() -> None:
    with op.batch_alter_table('resultado_defesa', schema=None) as batch_op:
        batch_op.drop_constraint('fk_resultado_defesa_atraso_decidido_por', type_='foreignkey')
        batch_op.drop_constraint('fk_resultado_defesa_versao_final_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_resultado_defesa_versao_final_id'))
        batch_op.drop_index(batch_op.f('ix_resultado_defesa_atraso_decidido_por'))
        batch_op.drop_column('atraso_decidido_em')
        batch_op.drop_column('atraso_decidido_por')
        batch_op.drop_column('atraso_aceito')
        batch_op.drop_column('entregue_com_atraso')
        batch_op.drop_column('versao_final_id')
        batch_op.drop_column('prazo_motivo')
        batch_op.drop_column('prazo_versao_final')

    with op.batch_alter_table('correcao', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_correcao_resultado_id'))
        batch_op.drop_index(batch_op.f('ix_correcao_decidida_por'))
        batch_op.drop_index(batch_op.f('ix_correcao_avaliador_id'))

    op.drop_table('correcao')
    with op.batch_alter_table('documento_tcc', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_documento_tcc_tcc_id'))
        batch_op.drop_index(batch_op.f('ix_documento_tcc_enviado_por'))

    op.drop_table('documento_tcc')
