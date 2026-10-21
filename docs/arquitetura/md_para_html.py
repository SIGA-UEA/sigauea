"""Converte um documento Markdown da pasta docs/arquitetura em HTML com o visual do contrato da API.

    pip install markdown
    python docs/arquitetura/md_para_html.py docs/modelagem/modelo-logico-siga-uea.md
    node docs/arquitetura/html_para_pdf.mjs docs/modelagem/modelo-logico-siga-uea.html
"""

import sys
from pathlib import Path

import markdown

ESTILO = """
body{font-family:Arial,Helvetica,sans-serif;color:#1b2432;margin:32px auto;max-width:980px;line-height:1.5;font-size:13px}
h1{font-size:24px;margin:0 0 6px} h2{font-size:17px;margin:26px 0 8px;border-bottom:2px solid #1a73e8;padding-bottom:4px}
code{font-family:Consolas,monospace;font-size:12px;background:#f1f5fb;padding:0 3px;border-radius:3px}
pre{background:#f6f9fe;border:1px solid #dde4ee;border-radius:6px;padding:10px;overflow-x:auto;font-size:12px}
pre code{background:none;padding:0}
table{border-collapse:collapse;width:100%;margin:6px 0 10px;page-break-inside:avoid}
th,td{border:1px solid #dde4ee;padding:5px 7px;text-align:left;vertical-align:top} th{background:#f1f5fb}
li{margin:2px 0} @media print{body{margin:0;max-width:none}}
"""


def main(origem: str) -> None:
    md = Path(origem)
    texto = md.read_text(encoding="utf8")
    titulo = texto.splitlines()[0].lstrip("# ").strip()
    corpo = markdown.markdown(texto, extensions=["tables", "fenced_code"])
    saida = md.with_suffix(".html")
    saida.write_text(f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>{titulo}</title>'
                     f"<style>{ESTILO}</style></head><body>{corpo}</body></html>", encoding="utf8")
    print(saida)


if __name__ == "__main__":
    main(sys.argv[1])
