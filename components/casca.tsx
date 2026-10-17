"use client";

// Moldura das telas internas: barra superior fixa + menu lateral.
// No celular o menu vira uma gaveta aberta pelo botão ☰.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useSessao } from "@/lib/sessao";
import { NOME_PERFIL, urlFoto, type Perfil } from "@/lib/tipos";
import { Avatar } from "./avatar";
import { Icone, type NomeIcone } from "./icone";
import { Marca } from "./marca";

type Item = { href: string; rotulo: string; icone: NomeIcone; perfis?: Perfil[] };

// Cada tela nova entra aqui. "perfis" limita quem vê o item no menu;
// a API confere a permissão de novo em cada rota.
const MENU: Item[] = [
  { href: "/inicio", rotulo: "Início", icone: "inicio" },
  { href: "/tccs", rotulo: "TCCs", icone: "documento" },
  { href: "/orientacoes", rotulo: "Orientações", icone: "certo", perfis: ["orientador", "professor_disciplina"] },
  { href: "/turmas", rotulo: "Turmas", icone: "turma", perfis: ["coordenador"] },
  { href: "/usuarios", rotulo: "Usuários e perfis", icone: "pessoas", perfis: ["coordenador"] },
  { href: "/perfil", rotulo: "Meu perfil", icone: "perfil" },
];

export function Casca({ children }: { children: React.ReactNode }) {
  const { usuario, sair } = useSessao();
  const caminho = usePathname();
  const [menuAberto, setMenuAberto] = useState(false);
  const itens = MENU.filter((i) => !i.perfis || i.perfis.some((p) => usuario.perfis.includes(p)));

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-30 flex h-16 items-center gap-2 border-b border-borda bg-superficie px-3 sm:px-5">
        <button
          type="button"
          onClick={() => setMenuAberto(!menuAberto)}
          aria-label="Abrir menu"
          aria-expanded={menuAberto}
          className="flex size-10 items-center justify-center rounded-full text-suave hover:bg-fundo lg:hidden"
        >
          <Icone nome="menu" />
        </button>
        <Link href="/inicio" className="rounded-lg">
          <Marca />
        </Link>

        <div className="ml-auto flex items-center gap-2 sm:gap-3">
          <div className="hidden text-right leading-tight sm:block">
            <p className="text-sm font-medium">{usuario.nome}</p>
            <p className="text-xs text-suave">{usuario.perfis.map((p) => NOME_PERFIL[p]).join(" · ")}</p>
          </div>
          <Link href="/perfil" aria-label="Meu perfil" className="rounded-full">
            <Avatar nome={usuario.nome} foto={urlFoto(usuario)} />
          </Link>
          <button
            type="button"
            onClick={sair}
            className="flex h-10 items-center gap-2 rounded-full px-3 text-sm font-medium text-suave hover:bg-fundo hover:text-texto"
          >
            <Icone nome="sair" />
            <span className="hidden sm:inline">Sair</span>
            <span className="sr-only sm:hidden">Sair</span>
          </button>
        </div>
      </header>

      {menuAberto && (
        <button
          type="button"
          aria-label="Fechar menu"
          onClick={() => setMenuAberto(false)}
          className="fixed inset-0 top-16 z-10 bg-texto/40 lg:hidden"
        />
      )}

      <nav
        aria-label="Menu do sistema"
        className={`fixed top-16 bottom-0 left-0 z-20 w-64 overflow-y-auto border-r border-borda bg-superficie py-3 pr-3 transition-transform lg:translate-x-0 ${
          menuAberto ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <ul className="flex flex-col gap-1">
          {itens.map((item) => {
            const atual = caminho === item.href || caminho.startsWith(item.href + "/");
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  onClick={() => setMenuAberto(false)}
                  aria-current={atual ? "page" : undefined}
                  className={`flex h-11 items-center gap-4 rounded-r-full pr-4 pl-6 text-sm font-medium ${
                    atual ? "bg-azul-claro text-azul-escuro" : "text-texto hover:bg-fundo"
                  }`}
                >
                  <Icone nome={item.icone} className={`size-5 ${atual ? "text-azul" : "text-suave"}`} />
                  {item.rotulo}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      <main className="lg:pl-64">
        <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 sm:py-8">{children}</div>
      </main>
    </div>
  );
}
