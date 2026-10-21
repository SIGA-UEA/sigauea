// Gera o PDF de um HTML desta pasta com o Chrome instalado (A4, com cabeçalho e número de página).
//
//   npm i --no-save playwright-core@1.48.2     (uma vez)
//   node docs/arquitetura/html_para_pdf.mjs docs/arquitetura/contrato-api-siga-uea.html

import { chromium } from "playwright-core";
import path from "node:path";
import { pathToFileURL } from "node:url";

const entrada = path.resolve(process.argv[2]);
const saida = entrada.replace(/\.html$/, ".pdf");
const navegador = await chromium.launch({ channel: "chrome", headless: true });
const pagina = await navegador.newPage();
await pagina.goto(pathToFileURL(entrada).href, { waitUntil: "load" });
const titulo = await pagina.title();
await pagina.pdf({
  path: saida,
  format: "A4",
  margin: { top: "18mm", bottom: "16mm", left: "14mm", right: "14mm" },
  displayHeaderFooter: true,
  headerTemplate: `<div style="font:8px Arial;color:#777;width:100%;padding:0 14mm">${titulo}</div>`,
  footerTemplate:
    '<div style="font:8px Arial;color:#777;width:100%;padding:0 14mm;text-align:right">' +
    'página <span class="pageNumber"></span> de <span class="totalPages"></span></div>',
  printBackground: true,
});
await navegador.close();
console.log(saida);
