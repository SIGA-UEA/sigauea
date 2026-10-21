// "Salvar rascunho" (RBN03.01): salva e mantém a aluna em TEL05, com "Rascunho salvo às HH:MM".
// A aluna é criada pela API como a coordenação faria; o link de ativação sai no log da API (sem SMTP).
import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";

const [, , BASE, apiLog, pasta] = process.argv;
fs.mkdirSync(path.join(pasta, "telas"), { recursive: true });
const API = `${BASE}/api/v1`;
const ok = (m) => console.log("OK  ", m);
const falha = (m) => {
  console.log("FALHA", m);
  process.exitCode = 1;
};
const checar = (c, m) => (c ? ok(m) : falha(m));

const browser = await chromium.launch({ channel: "chrome", headless: true });
const erros = [];
try {
  const coord = await browser.newContext();
  const r0 = await coord.request.post(`${API}/auth/login`, { data: { email: "coordenador@exemplo.com", senha: "Siga@2026" } });
  checar(r0.ok(), "coordenação entra pela API");
  const cursos = await (await coord.request.get(`${API}/cursos`)).json();
  const ec = cursos.find((c) => c.sigla === "EC");
  const email = `rascunho${Date.now()}@exemplo.com`;
  const nova = await coord.request.post(`${API}/alunos`, {
    data: { nome: "Rita Rascunho", email, matricula: String(Date.now()).slice(-10), curso_id: ec.id },
  });
  checar(nova.status() === 201, "coordenação cadastra a aluna (RBN01.03)");
  const aluna = await nova.json();
  const turmas = await (await coord.request.get(`${API}/turmas`)).json();
  const inc = await coord.request.post(`${API}/turmas/${turmas[0].id}/alunos`, { data: { aluno_id: aluna.id } });
  checar(inc.status() === 201, "coordenação inclui a aluna na turma (RBN08.02)");

  // link de ativação no log da API
  let token;
  for (let i = 0; i < 20 && !token; i++) {
    const bloco = fs.readFileSync(apiLog, "utf8").split("--- E-mail para ").filter((b) => b.startsWith(email)).at(-1);
    token = bloco?.match(/token=([\w-]+)/)?.[1];
    if (!token) await new Promise((r) => setTimeout(r, 500));
  }
  checar(!!token, "link de ativação gerado (RBN01.05)");

  const p = await (await browser.newContext({ viewport: { width: 1280, height: 900 } })).newPage();
  p.on("pageerror", (e) => erros.push(e.message));
  await p.goto(`${BASE}/ativar?token=${token}`);
  const campos = p.locator('input[autocomplete="new-password"]');
  await campos.nth(0).fill("Rita@2026x");
  await campos.nth(1).fill("Rita@2026x");
  await p.getByRole("button", { name: "Ativar conta" }).click();
  await p.waitForURL(/entrar/);
  ok("aluna ativa a conta e volta para o login");
  await p.getByLabel("E-mail").fill(email);
  await p.locator('input[autocomplete="current-password"]').fill("Rita@2026x");
  await p.getByRole("button", { name: "Entrar" }).click();
  await p.waitForURL(/inicio/);

  await p.goto(`${BASE}/tccs/cadastro`);
  await p.getByLabel(/^Título do trabalho/).fill("Rascunho de teste do botão salvar");
  await p.getByLabel(/^Área de interesse/).selectOption({ index: 1 });
  await p.getByLabel(/Monografia/).check();
  await p.getByRole("button", { name: "Salvar rascunho" }).click();
  await p.getByText(/Rascunho salvo às \d\d:\d\d/).waitFor();
  checar(p.url().endsWith("/tccs/cadastro"), "Salvar rascunho mantém a aluna no cadastro (RBN03.01)");
  checar(await p.getByRole("heading", { name: "1. Trabalho" }).isVisible(), "continua no mesmo passo");
  await p.screenshot({ path: path.join(pasta, "telas", "rascunho-1-salvo-sem-sair.png"), fullPage: true });

  await p.goto(`${BASE}/tccs`);
  await p.getByText("Rascunho de teste do botão salvar").waitFor();
  checar(await p.getByText("sem protocolo").isVisible(), "rascunho aparece na lista, sem protocolo (CA-03)");
} catch (e) {
  falha("exceção: " + e.message);
} finally {
  checar(erros.length === 0, "sem erros de JavaScript " + erros.join(" | "));
  await browser.close();
}
