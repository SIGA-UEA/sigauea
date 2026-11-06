"""Documentos oficiais em PDF (DocumentoOficial): geração, gravação e leitura conferida.

O banco guarda o caminho relativo à pasta ARQUIVOS_DIR e o SHA-256 do arquivo (documento_oficial,
RNF06). A gravação escreve num arquivo temporário e só então troca pelo definitivo, para uma falha no
meio não deixar um PDF pela metade. A leitura confere o SHA-256 antes de entregar.

Por ora gera a declaração de horas complementares do ouvinte (DS-FL09-B, RBN09.10, RN23). Ata, Folha
de Aprovação e certificados (RBN09.14 a RBN09.17) usam a mesma gravação.
"""

import hashlib
import os
from datetime import datetime, timedelta
from pathlib import Path

from fpdf import FPDF

from app import config
from app.erros import ErroAPI

FUSO_MANAUS = timedelta(hours=-4)  # America/Manaus não tem horário de verão (RNF03)
NOME_FORMATO = {"PRESENCIAL": "presencial", "REMOTO": "remota", "HIBRIDO": "híbrida"}
CABECALHO = (
    "UNIVERSIDADE DO ESTADO DO AMAZONAS",
    "ESCOLA SUPERIOR DE TECNOLOGIA",
    "NÚCLEO DE COMPUTAÇÃO (NUCOMP)",
)


# =================================================================== gravação e leitura


def _destino(caminho: str) -> Path:
    return Path(config.ARQUIVOS_DIR) / caminho


def gravar(caminho: str, conteudo: bytes) -> str:
    """Grava o arquivo em ARQUIVOS_DIR/caminho e devolve o SHA-256 do conteúdo."""
    destino = _destino(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(destino.suffix + ".tmp")
    temporario.write_bytes(conteudo)
    os.replace(temporario, destino)
    return hashlib.sha256(conteudo).hexdigest()


def ler(caminho: str, sha256: str) -> bytes:
    """Lê o arquivo e confere o SHA-256 gravado no banco (RNF06)."""
    destino = _destino(caminho)
    if not destino.is_file():
        raise ErroAPI(404, "O arquivo deste documento não foi encontrado.")
    conteudo = destino.read_bytes()
    if hashlib.sha256(conteudo).hexdigest() != sha256:
        raise ErroAPI(409, "O arquivo deste documento não confere com o registrado e não pode ser entregue.")
    return conteudo


def apagar(caminho: str) -> None:
    """Desfaz uma gravação cuja transação falhou."""
    _destino(caminho).unlink(missing_ok=True)


# =================================================================== declaração de horas (DS-FL09-B)
# Mesmo layout das declarações da UEA (Secretaria Acadêmica): brasão no topo, "DECLARAÇÃO" centralizado,
# texto "DECLARAMOS, para fins de direito..." com os dados em negrito, bloco de emissão no rodapé do texto
# e o endereço da universidade embaixo. O brasão e o logo entram se os arquivos oficiais estiverem em
# app/assets (brasao_amazonas.png e logo_uea.png); sem eles, o cabeçalho sai só em texto.

ASSETS = Path(__file__).resolve().parent.parent / "assets"
MESES = ("Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro",
         "Novembro", "Dezembro")
EMISSOR = ("NÚCLEO DE COMPUTAÇÃO (NUCOMP) DA ESCOLA SUPERIOR DE TECNOLOGIA DA UNIVERSIDADE DO ESTADO DO "
           "AMAZONAS.")
ENDERECO = ("Universidade do Estado do Amazonas", "Av. Djalma Batista, 3578 - Flores", "CEP 69050-010 - Manaus/AM",
            "www.uea.edu.br")


def _data(d) -> str:
    return d.strftime("%d/%m/%Y")


def _hora(h) -> str:
    return h.strftime("%H:%M")


def _negrito(texto: str) -> str:
    """Trecho em negrito no texto com marcação do FPDF, sem deixar o dado quebrar a marcação."""
    return "**" + texto.replace("*", "").replace("__", "_").replace("--", "-") + "**"


def carga_horaria(inicio, fim) -> str:
    """Duração da sessão, que é a carga horária da declaração: "1 h", "1 h 30 min" ou "20 min"."""
    minutos = (datetime.combine(datetime.min, fim) - datetime.combine(datetime.min, inicio)).seconds // 60
    horas, resto = divmod(minutos, 60)
    if horas and resto:
        return f"{horas} h {resto} min"
    return f"{horas} h" if horas else f"{resto} min"


def declaracao_horas(*, numero: int, ouvinte, defesa, tcc, gerado_em: datetime) -> bytes:
    """PDF da declaração de horas complementares de um ouvinte da defesa (RN23)."""
    pdf = FPDF(format="A4")
    pdf.set_margins(22, 18, 22)
    pdf.set_auto_page_break(False)
    pdf.set_title("Declaração de horas complementares")
    pdf.set_author("SIGA UEA")
    pdf.add_page()

    # cabeçalho: brasão do Governo do Estado do Amazonas
    brasao = ASSETS / "brasao_amazonas.png"  # já traz o nome "Governo do Estado do Amazonas"
    if brasao.is_file():
        pdf.image(str(brasao), x=(210 - 90) / 2, y=14, w=90)  # imagem sem bordas brancas
    else:
        pdf.set_y(24)
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(0, 5, "GOVERNO DO ESTADO DO AMAZONAS", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(62)
    pdf.set_font("Times", "B", 22)
    pdf.cell(0, 10, "DECLARAÇÃO", align="C", new_x="LMARGIN", new_y="NEXT")

    local = f", em {defesa.local.nome}" if defesa.local else ""
    texto = (
        f"{_negrito('DECLARAMOS')}, para fins de direito e todos os efeitos, que {_negrito(ouvinte.nome)}, "
        f"nº {_negrito(ouvinte.matricula)}, assistiu como ouvinte à sessão pública de defesa do Trabalho de "
        f"Conclusão de Curso ({_negrito(tcc.etapa)}) intitulado {_negrito(tcc.titulo)}, de autoria de "
        f"{tcc.aluno.usuario.nome}, do curso de {_negrito(tcc.aluno.curso.nome)}, vinculado à "
        f"{_negrito('EST - Escola Superior de Tecnologia')}, realizada de forma {NOME_FORMATO[defesa.formato]}"
        f"{local}, em {_negrito(_data(defesa.data))}, das {_hora(defesa.inicio)} às {_hora(defesa.fim)}, "
        f"totalizando {_negrito(carga_horaria(defesa.inicio, defesa.fim))} de atividade complementar."
    )
    pdf.set_y(84)
    pdf.set_font("Times", "", 13)
    pdf.multi_cell(0, 8, texto, align="J", markdown=True, new_x="LMARGIN", new_y="NEXT")

    # bloco de emissão, como o da Secretaria Acadêmica
    emitido = gerado_em + FUSO_MANAUS
    pdf.set_y(224)
    pdf.set_font("Times", "", 10)
    pdf.multi_cell(0, 5, EMISSOR, align="L", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.cell(0, 5, f"Documento emitido às {emitido.strftime('%H:%M:%S')} do dia {emitido.day} / "
                   f"{MESES[emitido.month - 1]} / {emitido.year}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Times", "B", 10)
    pdf.cell(0, 5, f"Matrícula: {ouvinte.matricula}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Declaração Nº: {numero}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Times", "", 10)
    pdf.cell(0, 5, "Emitida pelo SIGA UEA a partir da lista de ouvintes registrada na defesa.",
             new_x="LMARGIN", new_y="NEXT")

    # rodapé: linha e endereço da universidade, com o logo da UEA à direita
    pdf.set_draw_color(0, 0, 0)
    pdf.line(15, 262, 195, 262)
    pdf.set_y(266)
    pdf.set_font("Times", "", 9.5)
    for linha in ENDERECO:
        pdf.cell(0, 4.5, linha, new_x="LMARGIN", new_y="NEXT")
    logo = ASSETS / "logo_uea.png"
    if logo.is_file():
        pdf.image(str(logo), x=172, y=265, w=20)
    return bytes(pdf.output())
