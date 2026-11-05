"use client";

// Agenda de apresentações (TEL17 · RBN14.01 e RBN14.04): as defesas vigentes por dia e horário.
// Canceladas não aparecem e uma remarcada mostra só o novo horário; tudo vem pronto da API.

import { useEffect, useState } from "react";
import { Aviso, Selo } from "@/components/aviso";
import { Icone } from "@/components/icone";
import { corDoCurso } from "@/components/turma";
import { api, ErroApi } from "@/lib/api";
import { NOME_FORMATO, type Apresentacao } from "@/lib/tipos";

const hora = (t: string) => t.slice(0, 5);

function diaPorExtenso(iso: string) {
  const [a, m, d] = iso.split("-").map(Number);
  return new Date(a, m - 1, d).toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long" });
}

function agruparPorDia(lista: Apresentacao[]) {
  const dias = new Map<string, Apresentacao[]>();
  for (const a of lista) dias.set(a.data, [...(dias.get(a.data) ?? []), a]);
  return [...dias.entries()];
}

function Local({ a }: { a: Apresentacao }) {
  if (a.link) {
    return (
      <a href={a.link} target="_blank" rel="noreferrer" className="text-azul-forte underline">
        Entrar na defesa
      </a>
    );
  }
  return <span>{a.local ?? (a.formato === "REMOTO" ? "Link enviado aos participantes" : "Local a confirmar")}</span>;
}

export default function PaginaAgenda() {
  const [lista, setLista] = useState<Apresentacao[] | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<Apresentacao[]>("/agenda").then(setLista).catch((e: ErroApi) => setErro(e.message));
  }, []);

  return (
    <div className="flex flex-col gap-5">
      <header>
        <p className="text-xs font-semibold tracking-widest text-suave uppercase">Defesas</p>
        <h1 className="text-2xl font-semibold">Agenda de apresentações</h1>
        <p className="mt-1 text-sm text-suave">As defesas programadas, em ordem de data e horário.</p>
      </header>

      {erro && <Aviso tipo="erro">{erro}</Aviso>}

      {!lista ? (
        !erro && (
          <p role="status" className="text-sm text-suave">
            Carregando…
          </p>
        )
      ) : lista.length === 0 ? (
        <div className="rounded-xl border border-borda bg-superficie p-6 text-sm">
          <p className="font-medium">Nenhuma apresentação programada</p>
          <p className="mt-1 text-suave">Quando uma defesa for agendada, ela aparece aqui.</p>
        </div>
      ) : (
        agruparPorDia(lista).map(([dia, itens]) => (
          <section key={dia} aria-labelledby={`dia-${dia}`} className="flex flex-col gap-3">
            <h2 id={`dia-${dia}`} className="text-sm font-semibold text-suave first-letter:uppercase">
              {diaPorExtenso(dia)}
            </h2>
            <ul className="flex flex-col gap-3">
              {itens.map((a) => (
                <li key={a.id} className="flex gap-4 rounded-xl border border-borda bg-superficie p-4">
                  <div className="flex w-16 shrink-0 flex-col items-center text-center">
                    <Icone nome="relogio" className="size-4 text-suave" />
                    <span className="mt-1 text-lg font-semibold">{hora(a.inicio)}</span>
                    <span className="text-xs text-suave">até {hora(a.fim)}</span>
                  </div>
                  <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                    <h3 className="font-medium">{a.titulo}</h3>
                    <p className="text-sm text-suave">
                      {a.autor}
                      {a.orientador && ` · Orientador(a): ${a.orientador}`}
                    </p>
                    <div className="flex flex-wrap items-center gap-2 text-sm">
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${corDoCurso(a.curso.sigla)}`}>
                        {a.curso.sigla}
                      </span>
                      <Selo cor="cinza">{NOME_FORMATO[a.formato]}</Selo>
                      {a.remarcada && <Selo cor="ambar">Remarcada</Selo>}
                      <Local a={a} />
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        ))
      )}
    </div>
  );
}
