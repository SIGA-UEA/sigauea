// Casos de teste que a matriz marca como Manual ou Parcial por dependerem da tela.
// Cada checagem cita o CT entre colchetes; o relatório de execução usa essa marca.
//
//   node complementares.mjs <BASE> <log-da-api> <pasta-de-evidencias>
//
// Precisa do banco de demonstração (python -m app.seed --demo) e da API sem SMTP
// (o link de ativação da aluna nova sai no log da API).
import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";

const [, , BASE, apiLog, pasta] = process.argv;
const API = `${BASE}/api/v1`;
const telas = path.join(pasta, "telas");
fs.mkdirSync(telas, { recursive: true });
const ok = (m) => console.log("OK  ", m);
const falha = (m) => {
  console.log("FALHA", m);
  process.exitCode = 1;
};
const checar = (c, m) => (c ? ok(m) : falha(m));
const SENHA = "Siga@2026";

const browser = await chromium.launch({ channel: "chrome", headless: true });
const erros = [];

async function pagina(largura = 1280) {
  const ctx = await browser.newContext({ viewport: { width: largura, height: 900 } });
  const p = await ctx.newPage();
  p.on("pageerror", (e) => erros.push(e.message));
  return p;
}
async function entrar(p, email, senha = SENHA) {
  await p.goto(`${BASE}/entrar`);
  await p.getByLabel("E-mail").fill(email);
  await p.locator('input[autocomplete="current-password"]').fill(senha);
  await p.getByRole("button", { name: "Entrar" }).click();
  await p.waitForURL(/inicio/);
}
const larguraDoc = (p) => p.evaluate(() => document.documentElement.scrollWidth);
async function semRolagem(p, largura, ct, tela, arquivo) {
  await p.setViewportSize({ width: largura, height: 900 });
  await p.waitForTimeout(300);
  const w = await larguraDoc(p);
  checar(w <= largura, `[${ct}] ${tela} em ${largura} px sem rolagem horizontal (largura ${w})`);
  if (arquivo) await p.screenshot({ path: path.join(telas, `${arquivo}-${largura}.png`), fullPage: true });
}

try {
  // ---------- TEL01 · login (CT-01.06-09, CT-01.06-06)
  const vis = await pagina(360);
  await vis.goto(`${BASE}/entrar`);
  await semRolagem(vis, 360, "CT-01.06-09", "login", "complementar-login");
  await semRolagem(vis, 768, "CT-01.06-09", "login", "complementar-login");
  await vis.getByRole("button", { name: "Entrar" }).click();
  await vis.waitForTimeout(500);
  const vazio = await vis.getByLabel("E-mail").evaluate((el) => el.validity.valueMissing && el.matches(":invalid"));
  checar(vazio && vis.url().includes("/entrar"),
    "[CT-01.06-06] login com campos vazios não é enviado e a tela marca o campo obrigatório");

  // ---------- TEL02 · usuários e áreas (CT-01.01-08, CT-01.02-01)
  const coord = await pagina(1280);
  await entrar(coord, "coordenador@exemplo.com");
  await coord.goto(`${BASE}/usuarios`);
  await coord.getByRole("tab", { name: "Áreas de interesse" }).click();
  await coord.getByRole("button", { name: "Nova área" }).click();
  await coord.getByLabel(/^Nome da área/).fill("Computação Quântica");
  await coord.getByRole("button", { name: "Criar área" }).click();
  await coord.getByText("Computação Quântica").first().waitFor();
  ok("[CT-01.02-01] coordenação cria a área \"Computação Quântica\" pela tela");
  await coord.getByRole("tab", { name: "Docentes" }).click();
  await coord.getByRole("button", { name: "Novo docente" }).click();
  const selecionavel = coord.getByRole("dialog").getByRole("button", { name: "Computação Quântica" });
  await selecionavel.waitFor();
  await selecionavel.click();
  checar((await selecionavel.getAttribute("aria-pressed")) === "true",
    "[CT-01.02-01] a área nova aparece e pode ser selecionada no cadastro de docente");
  await semRolagem(coord, 360, "CT-01.01-08", "formulário de docente", "complementar-docente");
  await semRolagem(coord, 768, "CT-01.01-08", "formulário de docente", "complementar-docente");

  // ---------- Meu perfil (CT-01.09-06, CT-01.10-03)
  const aluno = await pagina(1280);
  await entrar(aluno, "aluno@exemplo.com");
  await aluno.goto(`${BASE}/perfil`);
  await aluno.getByRole("button", { name: /Salvar alterações/ }).waitFor();
  await semRolagem(aluno, 360, "CT-01.09-06", "perfil do aluno", "complementar-perfil-aluno");
  await semRolagem(aluno, 768, "CT-01.09-06", "perfil do aluno", "complementar-perfil-aluno");
  const banca = await pagina(1280);
  await entrar(banca, "banca@exemplo.com");
  await banca.goto(`${BASE}/perfil`);
  await banca.getByRole("button", { name: /Salvar alterações/ }).waitFor();
  checar((await banca.getByText("Áreas de interesse").count()) === 0,
    "[CT-01.10-03] o perfil do membro da banca não oferece o campo de áreas de interesse");
  await banca.screenshot({ path: path.join(telas, "complementar-perfil-banca.png"), fullPage: true });

  // ---------- TEL05 · cadastro em celular e tablet, campos do artigo
  // (CT-03.01-01, CT-03.01-07, CT-03.02-01, CT-03.02-02, CT-03.02-07)
  const cursos = await (await coord.request.get(`${API}/cursos`)).json();
  const ec = cursos.find((c) => c.sigla === "EC");
  const email = `celular${Date.now()}@exemplo.com`;
  const nova = await (await coord.request.post(`${API}/alunos`, {
    data: { nome: "Clara Celular", email, matricula: String(Date.now()).slice(-10), curso_id: ec.id },
  })).json();
  const turmas = await (await coord.request.get(`${API}/turmas`)).json();
  await coord.request.post(`${API}/turmas/${turmas[0].id}/alunos`, { data: { aluno_id: nova.id } });
  let token;
  for (let i = 0; i < 20 && !token; i++) {
    const bloco = fs.readFileSync(apiLog, "utf8").split("--- E-mail para ").filter((b) => b.startsWith(email)).at(-1);
    token = bloco?.match(/token=([\w-]+)/)?.[1];
    if (!token) await new Promise((r) => setTimeout(r, 500));
  }
  const cel = await pagina(360);
  await cel.goto(`${BASE}/ativar?token=${token}`);
  const campos = cel.locator('input[autocomplete="new-password"]');
  await campos.nth(0).fill("Clara@2026x");
  await campos.nth(1).fill("Clara@2026x");
  await cel.getByRole("button", { name: "Ativar conta" }).click();
  await cel.waitForURL(/entrar/);
  await entrar(cel, email, "Clara@2026x");
  await cel.goto(`${BASE}/tccs/cadastro`);
  await cel.getByRole("heading", { name: "1. Trabalho" }).waitFor();
  checar(await cel.getByText(/TCC1-EC-2026\/2-1 · TCC1 · 2026\/2/).isVisible(),
    "[CT-03.01-01] o cadastro mostra turma, etapa e período vindos da turma da aluna");
  await cel.getByLabel(/^Título do trabalho/).fill("Aplicativo móvel para monitorar a qualidade do ar");
  await cel.getByLabel(/^Área de interesse/).selectOption({ index: 1 });
  checar((await cel.getByText("Informações do artigo").count()) === 0,
    "[CT-03.02-02] sem modalidade artigo, os campos editoriais não aparecem");
  await cel.getByLabel(/Artigo/).check();
  await cel.getByText("Informações do artigo").waitFor();
  const editoriais = await Promise.all(
    [/^Veículo/, /^Tipo de veículo/, /^Situação editorial/, /^DOI/].map((r) => cel.getByLabel(r).isVisible()),
  );
  checar(editoriais.every(Boolean),
    "[CT-03.02-01] com modalidade artigo aparecem veículo, tipo de veículo, situação editorial e DOI");
  await cel.getByLabel(/^Veículo/).fill("Revista Brasileira de Computação Aplicada");
  await cel.getByRole("button", { name: "Salvar rascunho" }).click();
  await cel.getByText(/Rascunho salvo às/).waitFor();
  await semRolagem(cel, 360, "CT-03.01-07", "cadastro de TCC (artigo)", "complementar-cadastro-artigo");
  const salvoArtigo = (await (await cel.request.get(`${API}/tccs`)).json())[0];
  checar(salvoArtigo.artigo?.veiculo === "Revista Brasileira de Computação Aplicada",
    "[CT-03.02-01] o rascunho de artigo guarda os dados editoriais");
  await cel.getByLabel(/Monografia/).check();
  checar((await cel.getByText("Informações do artigo").count()) === 0,
    "[CT-03.02-07] ao trocar para monografia, os campos editoriais somem da tela");
  await cel.getByRole("button", { name: "Salvar rascunho" }).click();
  await cel.waitForTimeout(800);
  const salvoMono = (await (await cel.request.get(`${API}/tccs`)).json())[0];
  checar(salvoMono.modalidade === "MONOGRAFIA" && salvoMono.artigo === null,
    "[CT-03.02-07] depois da troca, o cadastro é monografia e não traz mais os dados do artigo");
  await semRolagem(cel, 360, "CT-03.01-07", "cadastro de TCC (monografia)", "complementar-cadastro-monografia");
  await semRolagem(cel, 768, "CT-03.01-07", "cadastro de TCC", "complementar-cadastro");
} catch (e) {
  falha("exceção: " + e.message);
} finally {
  checar(erros.length === 0, "sem erros de JavaScript nas páginas " + erros.join(" | "));
  await browser.close();
}
