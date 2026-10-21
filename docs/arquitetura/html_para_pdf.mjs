// Gera o PDF de um HTML com o Chrome instalado.
//
//   npm i --no-save playwright-core@1.48.2     (uma vez)
//   node docs/arquitetura/html_para_pdf.mjs <arquivo.html>          A4, cabeçalho com o título e "página x de y"
//   node docs/arquitetura/html_para_pdf.mjs <arquivo.html> --siga   formato dos documentos do grupo: margens do
//                                                                   próprio HTML (@page) e só o número da página
//                                                                   no rodapé, à direita (usado por formato_siga.py)

import { chromium } from "playwright-core";
import path from "node:path";
import { pathToFileURL } from "node:url";

const entrada = path.resolve(process.argv[2]);
const siga = process.argv.includes("--siga");
const saida = entrada.replace(/\.html$/, ".pdf");
const navegador = await chromium.launch({ channel: "chrome", headless: true });
const pagina = await navegador.newPage();
await pagina.goto(pathToFileURL(entrada).href, { waitUntil: "load" });
const titulo = await pagina.title();
await pagina.pdf(
  siga
    ? {
        path: saida,
        preferCSSPageSize: true,
        displayHeaderFooter: true,
        headerTemplate: "<span></span>",
        footerTemplate:
          '<div style="font:9pt Arial;color:#000;width:100%;padding:0 20mm 0 30mm;text-align:right">' +
          '<span class="pageNumber"></span></div>',
        printBackground: true,
      }
    : {
        path: saida,
        format: "A4",
        margin: { top: "18mm", bottom: "16mm", left: "14mm", right: "14mm" },
        displayHeaderFooter: true,
        headerTemplate: `<div style="font:8px Arial;color:#777;width:100%;padding:0 14mm">${titulo}</div>`,
        footerTemplate:
          '<div style="font:8px Arial;color:#777;width:100%;padding:0 14mm;text-align:right">' +
          'página <span class="pageNumber"></span> de <span class="totalPages"></span></div>',
        printBackground: true,
      },
);
await navegador.close();
console.log(saida);
