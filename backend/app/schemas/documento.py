"""Formato dos documentos da defesa: ata, Folha de Aprovação e certificados (RBN09.14 a RBN09.17).

Rotas dos diagramas DS-FL06-C (GET /defesas/{id}/documentos, POST .../documentos/ata e .../documentos/folha),
DS-FL06-E (GET /documentos/{id}/arquivo) e DS-FL06-F (POST .../documentos/certificados {idsMembro[]}).
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.tcc import PessoaOut
from app.schemas.usuario import DataHora

SituacaoEnvio = Literal["NAO_ENVIADO", "PENDENTE", "ENVIADO", "FALHA"]


class VersaoDocumentoOut(BaseModel):
    """Uma versão da ata ou da folha: a vigente e as substituídas ficam na lista (RBN09.16 CA-02)."""

    id: int
    versao: int
    vigente: bool
    gerado_em: DataHora
    substituido_em: DataHora | None


class DocumentoDefesaOut(BaseModel):
    """Seção "Ata da defesa" ou "Folha de Aprovação" da TEL13, com o que falta para gerar."""

    aplica: bool  # a folha só existe para TCC2 ou artigo (RBN09.15 CA-02); a ata sempre
    disponivel: bool  # pode gerar agora
    motivo: str | None  # por que ainda não pode ("Indisponível por enquanto", E1 e E3)
    faltas: list[str]  # dados obrigatórios ausentes (RBN09.14 CA-03, RBN09.15 CA-04)
    desatualizada: bool  # o resultado foi retificado ou a presença mudou depois da versão vigente (RN15)
    presenca_mudou: bool = False  # a causa foi a presença da banca, e não a retificação
    versoes: list[VersaoDocumentoOut]  # da mais nova para a mais antiga


class CertificadoOut(BaseModel):
    """Linha da seção Certificados de participação (DS-FL06-F)."""

    membro_id: int
    papel: str
    pessoa: PessoaOut
    presente: bool | None
    pode_emitir: bool  # presente na defesa realizada (CA-01, CA-03 e CA-04)
    motivo: str | None  # por que não recebe certificado
    certificado_id: int | None
    emitido_em: DataHora | None
    envio: SituacaoEnvio  # último e-mail do certificado (CA-02 e CA-05)


class DocumentosOut(BaseModel):
    """DS-FL06-C mensagens 2 a 4 e DS-FL06-E mensagens 4 a 6: as seções da TEL13 para quem consulta."""

    defesa_id: int
    pode_gerar: bool  # coordenação ou orientador do TCC geram e emitem
    resultado_confirmado: bool
    ata: DocumentoDefesaOut
    folha: DocumentoDefesaOut
    certificados: list[CertificadoOut]  # só para quem gera
    meus_certificados: list[VersaoDocumentoOut]  # o certificado do próprio membro da banca, para baixar


class CertificadosEntrada(BaseModel):
    ids_membro: list[int] = Field(min_length=1, max_length=20)


class FaltasOut(BaseModel):
    detail: str
    faltas: list[str]
