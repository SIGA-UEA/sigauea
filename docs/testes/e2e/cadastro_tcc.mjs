// Roteiro de ponta a ponta da S03: aluno cadastra TCC -> orientador aceita -> aluno envia -> protocolo.
import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";

const [, , pasta] = process.argv;
const BASE = process.env.BASE ?? "http://localhost:3000";
const SENHA = "Siga@2026";
const shots = path.join(pasta, "telas");
fs.mkdirSync(shots, { recursive: true });

const ok = (m) => console.log("OK  ", m);
const falha = (m) => {
  console.log("FALHA", m);
  process.exitCode = 1;
};
const checar = (c, m) => (c ? ok(m) : falha(m));

async function entrar(page, email) {
  await page.goto(`${BASE}/entrar`);
  await page.getByLabel("E-mail").fill(email);
  await page.locator('input[autocomplete="current-password"]').fill(SENHA);
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.waitForURL(/inicio/);
}

const browser = await chromium.launch({ channel: "chrome", headless: true });
const erros = [];
const nova = async (w = 1280) => {
  const ctx = await browser.newContext({ viewport: { width: w, height: 900 } });
  const p = await ctx.newPage();
  p.on("pageerror", (e) => erros.push(e.message));
  return p;
};

try {
  // ---------- aluno: rascunho ----------
  const aluno = await nova();
  await entrar(aluno, "aluno@exemplo.com");
  await aluno.getByRole("link", { name: "TCCs" }).first().click();
  await aluno.waitForURL(/\/tccs$/);
  await aluno.getByText("Já pode cadastrar o seu TCC").waitFor();
  ok("aluno matriculado vê o convite para cadastrar (RBN08.01)");
  await aluno.getByRole("link", { name: "Cadastrar TCC" }).click();
  await aluno.waitForURL(/\/tccs\/cadastro/);

  // validação na tela: sem título/área/modalidade
  await aluno.getByRole("button", { name: "Continuar" }).click();
  checar(await aluno.getByText("Informe o título.").isVisible(), "passo 1 valida campos obrigatórios");

  await aluno.getByLabel(/^Título do trabalho/).fill("Detecção de falhas em redes elétricas com aprendizado de máquina");
  await aluno.getByLabel(/^Resumo/).fill("Este trabalho investiga métodos de aprendizado de máquina para detectar falhas.");
  for (const p of ["aprendizado de máquina", "redes elétricas", "detecção de falhas"]) {
    await aluno.getByLabel("Nova palavra-chave").fill(p);
    await aluno.getByLabel("Nova palavra-chave").press("Enter");
  }
  checar(await aluno.getByText("(3 de 10)").isVisible(), "palavras-chave incluídas como chips");
  await aluno.getByLabel(/^Área de interesse/).selectOption({ index: 1 });
  await aluno.getByLabel(/Monografia/).check();
  checar((await aluno.getByText("Informe o título.").count()) === 0, "erro some ao corrigir o campo");
  await aluno.screenshot({ path: path.join(shots, "cadastro-1-trabalho.png"), fullPage: true });
  await aluno.getByRole("button", { name: "Continuar" }).click();
  await aluno.getByRole("heading", { name: "2. Orientação" }).waitFor();
  checar(await aluno.getByText(/Rascunho salvo às/).isVisible(), "rascunho salvo ao continuar (DS-FL01-B)");

  const orientador = aluno.getByLabel(/^Orientador/);
  const opcoes = await orientador.locator("option").allTextContents();
  const alvo = opcoes.find((o) => /orientador/i.test(o)) ?? opcoes[1];
  await orientador.selectOption({ label: alvo });
  await aluno.getByRole("button", { name: "Continuar" }).click();
  await aluno.getByRole("heading", { name: "3. Revisar e enviar" }).waitFor();
  checar(await aluno.getByText("Antes de enviar:").isVisible(), "pendência: orientador ainda não aceitou (RBN03.03)");
  checar(
    await aluno.getByRole("button", { name: "Enviar para análise" }).isDisabled(),
    "envio bloqueado enquanto há pendências",
  );
  await aluno.screenshot({ path: path.join(shots, "cadastro-3-revisar-pendente.png"), fullPage: true });

  // ---------- orientador: aceite (DS-FL03-A) ----------
  const ori = await nova();
  await entrar(ori, "orientador@exemplo.com");
  await ori.goto(`${BASE}/orientacoes`);
  await ori.getByText("Detecção de falhas em redes elétricas").waitFor();
  ok("orientador vê o pedido pendente (DS-FL03)");
  await ori.screenshot({ path: path.join(shots, "cadastro-4-orientacoes.png"), fullPage: true });
  await ori.getByRole("button", { name: "Aceitar orientação" }).click();
  await ori.getByText(/aceita\. O aluno foi avisado/).waitFor();
  ok("orientador aceitou a orientação");

  // ---------- aluno: envio e protocolo (DS-FL01) ----------
  await aluno.goto(`${BASE}/tccs/cadastro`);
  await aluno.getByRole("button", { name: "Continuar" }).click();
  await aluno.getByRole("heading", { name: "2. Orientação" }).waitFor();
  checar(await aluno.getByText("Aceita", { exact: true }).isVisible(), "aluno vê o vínculo aceito");
  await aluno.getByRole("button", { name: "Continuar" }).click();
  await aluno.getByText("Tudo certo.").waitFor();
  await aluno.getByRole("button", { name: "Enviar para análise" }).click();
  await aluno.getByRole("dialog").getByRole("button", { name: "Enviar para análise" }).click();
  await aluno.getByRole("heading", { name: "Cadastro enviado para análise" }).waitFor();
  const texto = await aluno.locator("strong.font-mono").textContent();
  checar(/^TCC-2026-\d{5}$/.test(texto ?? ""), `protocolo único gerado: ${texto} (RBN03.04)`);
  await aluno.screenshot({ path: path.join(shots, "cadastro-5-protocolo.png"), fullPage: true });

  await aluno.getByRole("button", { name: "Acompanhar meu TCC" }).click();
  await aluno.getByRole("heading", { name: "Histórico" }).waitFor();
  checar(await aluno.getByText("Rascunho → Em análise").isVisible(), "histórico registra a submissão (RNF03)");
  await aluno.screenshot({ path: path.join(shots, "cadastro-6-acompanhamento.png"), fullPage: true });

  await aluno.goto(`${BASE}/tccs/cadastro`);
  await aluno.getByText("está em análise pela coordenação").waitFor();
  ok("cadastro em análise não é editável");
  checar(
    (await aluno.goto(`${BASE}/tccs`), await aluno.getByRole("link", { name: /Cadastrar TCC|Continuar cadastro/ }).count()) === 0,
    "sem botão de novo cadastro: um TCC por período (RN04)",
  );

  // ---------- coordenação: turmas ----------
  const coord = await nova(360);
  await entrar(coord, "coordenador@exemplo.com");
  await coord.goto(`${BASE}/turmas`);
  await coord.getByText("TCC1-EC-2026/2-1").click();
  await coord.getByText("aluno@exemplo.com").or(coord.getByRole("combobox", { name: /Situação de/ })).first().waitFor();
  ok("coordenação vê a turma com o aluno");
  const largura = await coord.evaluate(() => document.documentElement.scrollWidth);
  checar(largura <= 360, `turmas sem rolagem horizontal em 360 px (${largura})`);
  await coord.screenshot({ path: path.join(shots, "cadastro-7-turmas-360.png"), fullPage: true });
  await coord.goto(`${BASE}/tccs`);
  await coord.getByText(texto).waitFor();
  ok("coordenação vê o TCC enviado na lista");
} catch (e) {
  falha("exceção: " + e.message);
} finally {
  checar(erros.length === 0, "sem erros de JavaScript nas páginas " + erros.join(" | "));
  await browser.close();
}
