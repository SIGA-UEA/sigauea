// Minhas turmas: professor vê cartões e abre a turma; aluno vê a própria; coordenação mantém a gestão.
import { chromium } from "playwright-core";
import fs from "node:fs";
import path from "node:path";

const [, , pasta, BASE = "http://localhost:3002"] = process.argv;
const shots = path.join(pasta, "telas");
fs.mkdirSync(shots, { recursive: true });
const ok = (m) => console.log("OK  ", m);
const falha = (m) => {
  console.log("FALHA", m);
  process.exitCode = 1;
};
const checar = (c, m) => (c ? ok(m) : falha(m));

const browser = await chromium.launch({ channel: "chrome", headless: true });
const erros = [];
async function entrar(email, largura = 1280) {
  const ctx = await browser.newContext({ viewport: { width: largura, height: 900 } });
  const p = await ctx.newPage();
  p.on("pageerror", (e) => erros.push(e.message));
  await p.goto(`${BASE}/entrar`);
  await p.getByLabel("E-mail").fill(email);
  await p.locator('input[autocomplete="current-password"]').fill("Siga@2026");
  await p.getByRole("button", { name: "Entrar" }).click();
  await p.waitForURL(/inicio/);
  return p;
}

try {
  const prof = await entrar("professor@exemplo.com");
  await prof.getByRole("link", { name: "Minhas turmas" }).click();
  await prof.getByRole("heading", { name: "Minhas turmas" }).waitFor();
  await prof.getByRole("heading", { name: "Engenharia de Computação" }).waitFor();
  ok("professor vê Minhas turmas no menu e o cartão da turma");
  checar(await prof.getByText("com TCC").isVisible(), "cartão mostra alunos e quantos têm TCC");
  await prof.screenshot({ path: path.join(shots, "turmas-1-professor-cartoes.png") });
  await prof.getByRole("link", { name: "Abrir turma" }).click();
  await prof.getByRole("heading", { name: /^Alunos \(/ }).waitFor();
  checar(await prof.getByText("Ana Aluna").isVisible(), "turma aberta lista os alunos");
  checar((await prof.getByText(/TCC-2026-|Em análise/).count()) > 0, "turma mostra o TCC e a situação de cada aluno");
  await prof.screenshot({ path: path.join(shots, "turmas-2-professor-turma.png"), fullPage: false });

  const aluno = await entrar("aluno@exemplo.com");
  await aluno.getByRole("link", { name: "Minha turma" }).click();
  await aluno.getByRole("heading", { name: "Minha turma" }).waitFor();
  await aluno.getByRole("heading", { name: "Engenharia de Computação" }).waitFor();
  checar(await aluno.getByText("Professor responsável", { exact: true }).isVisible(), "aluno vê o professor responsável");
  checar(await aluno.getByText("Matriculado", { exact: true }).isVisible(), "aluno vê a situação da matrícula");
  checar(await aluno.getByRole("link", { name: "Ver meu TCC" }).isVisible(), "aluno tem atalho para o próprio TCC");
  await aluno.screenshot({ path: path.join(shots, "turmas-3-aluno.png") });
  const r = await aluno.goto(`${BASE}/turmas/1`);
  await aluno.getByText("Turma não encontrada.").waitFor();
  ok("aluno não abre a turma (não vê os colegas)");

  const coord = await entrar("coordenador@exemplo.com");
  checar((await coord.getByRole("link", { name: "Minhas turmas" }).count()) === 0, "coordenação não vê item duplicado");
  await coord.getByRole("link", { name: "Turmas", exact: true }).click();
  await coord.getByRole("heading", { name: "Turmas de TCC" }).waitFor();
  ok("coordenação continua com a gestão de turmas");

  const celular = await entrar("professor@exemplo.com", 360);
  await celular.goto(`${BASE}/turmas`);
  await celular.getByRole("link", { name: "Abrir turma" }).waitFor();
  const l1 = await celular.evaluate(() => document.documentElement.scrollWidth);
  await celular.getByRole("link", { name: "Abrir turma" }).click();
  await celular.getByRole("heading", { name: /^Alunos \(/ }).waitFor();
  const l2 = await celular.evaluate(() => document.documentElement.scrollWidth);
  checar(l1 <= 360 && l2 <= 360, `sem rolagem horizontal em 360 px (${l1}, ${l2})`);
  await celular.screenshot({ path: path.join(shots, "turmas-4-celular-turma.png") });
} catch (e) {
  falha("exceção: " + e.message);
} finally {
  checar(erros.length === 0, "sem erros de JavaScript " + erros.join(" | "));
  await browser.close();
}
