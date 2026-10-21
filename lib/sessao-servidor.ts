import "server-only";

// Leitura da sessão no servidor do Next, antes de desenhar qualquer tela interna.
// Quem decide se a sessão vale é sempre a API: aqui só perguntamos "quem sou eu?".

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import type { Usuario } from "./tipos";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

export async function buscarUsuarioLogado(): Promise<Usuario> {
  const token = (await cookies()).get("siga_sessao")?.value;
  if (!token) redirect("/entrar");

  const resposta = await fetch(`${API_URL}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  // Sessão expirada (60 min sem uso), encerrada ou de conta inativada.
  if (resposta.status === 401) redirect("/entrar?motivo=sessao");
  if (!resposta.ok) throw new Error("A API não respondeu ao conferir a sessão.");
  return resposta.json();
}
