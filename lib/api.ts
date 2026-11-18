// Único ponto de contato com a API. As telas chamam api("/caminho") e recebem
// os dados prontos ou um ErroApi com a mensagem para mostrar.
//
// O endereço é relativo (/api/v1/...): o Next repassa para o FastAPI (ver
// rewrites em next.config.ts), então o cookie de sessão vai junto sozinho.

import type { CriterioSenha } from "./senha";

export class ErroApi extends Error {
  status: number;
  campo?: string; // 409: qual campo está duplicado
  campos?: Record<string, string>; // 400: mensagem por campo
  criterios?: CriterioSenha[]; // 422: critérios de senha que faltam
  // link que não vale mais; ou o motivo de uma recusa do cadastro de TCC (sem matrícula, duplicado...)
  motivo?: "invalido" | "expirado" | "usado" | "sem_matricula" | "duplicado" | "nao_editavel" | string;
  campos_pendentes?: string[]; // 422 na submissão do TCC: o que ainda falta
  pendentes?: { matricula_id: number; aluno: string; matricula: string }[]; // 422 ao encerrar a turma

  constructor(status: number, corpo: Record<string, unknown>) {
    super(
      typeof corpo.detail === "string"
        ? corpo.detail
        : "Não foi possível concluir. Tente novamente.",
    );
    this.status = status;
    Object.assign(this, corpo);
  }
}

type Opcoes = {
  metodo?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  // Objeto vira JSON; FormData (upload de arquivo) vai como está.
  corpo?: unknown;
  // Rotas de login e de link público: um 401 aqui é resposta normal, não sessão expirada.
  publica?: boolean;
};

export async function api<T>(caminho: string, opcoes: Opcoes = {}): Promise<T> {
  let resposta: Response;
  try {
    const arquivo = opcoes.corpo instanceof FormData;
    resposta = await fetch(`/api/v1${caminho}`, {
      method: opcoes.metodo ?? "GET",
      headers: opcoes.corpo && !arquivo ? { "Content-Type": "application/json" } : undefined,
      body: arquivo ? (opcoes.corpo as FormData) : opcoes.corpo ? JSON.stringify(opcoes.corpo) : undefined,
    });
  } catch {
    throw new ErroApi(0, { detail: "Sem conexão com o servidor." });
  }

  // Interceptor: sessão expirada (60 min sem uso) ou encerrada leva ao login.
  if (resposta.status === 401 && !opcoes.publica) {
    // Recarga completa de propósito: descarta da memória do navegador os dados da sessão encerrada.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.assign("/entrar?motivo=sessao");
    return new Promise<T>(() => {}); // a página está saindo; ninguém espera a resposta
  }

  if (resposta.status === 204) return undefined as T; // sucesso sem corpo (ex.: exclusão)

  const corpo = await resposta.json().catch(() => null);
  if (!resposta.ok || corpo === null) {
    throw new ErroApi(
      resposta.status,
      corpo ?? { detail: "O servidor não respondeu. A API está no ar?" },
    );
  }
  return corpo as T;
}

// Baixa um PDF gerado na hora (agenda e relatório dos indicadores): salva com o nome que a API manda ou o padrão.
// Com corpo, vai como POST em JSON. Erro da API vira ErroApi, como em api().
export async function baixarPdf(caminho: string, nomePadrao: string, corpo?: unknown): Promise<void> {
  let resposta: Response;
  try {
    resposta = await fetch(
      `/api/v1${caminho}`,
      corpo === undefined
        ? undefined
        : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo) },
    );
  } catch {
    throw new ErroApi(0, { detail: "Sem conexão com o servidor." });
  }
  if (resposta.status === 401) {
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.assign("/entrar?motivo=sessao");
    return;
  }
  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => null);
    throw new ErroApi(resposta.status, corpo ?? { detail: "Não foi possível gerar o PDF." });
  }
  const nome = /filename="([^"]+)"/.exec(resposta.headers.get("content-disposition") ?? "")?.[1] ?? nomePadrao;
  const url = URL.createObjectURL(await resposta.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = nome;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
