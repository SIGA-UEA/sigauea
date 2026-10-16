"use client";

// Disponibiliza o usuário logado para as telas internas.
// O usuário chega pronto do servidor (ver app/(sistema)/layout.tsx).

import { createContext, useContext } from "react";
import { api } from "./api";
import type { Perfil, Usuario } from "./tipos";

type Sessao = {
  usuario: Usuario;
  tem: (perfil: Perfil) => boolean;
  sair: () => Promise<void>;
};

const Contexto = createContext<Sessao | null>(null);

export function useSessao(): Sessao {
  const sessao = useContext(Contexto);
  if (!sessao) throw new Error("useSessao só funciona dentro de ProvedorSessao");
  return sessao;
}

export function ProvedorSessao({ usuario, children }: { usuario: Usuario; children: React.ReactNode }) {
  const sessao: Sessao = {
    usuario,
    tem: (perfil) => usuario.perfis.includes(perfil),
    sair: async () => {
      await api("/auth/logout", { metodo: "POST", publica: true }).catch(() => {});
      // Recarga completa de propósito: descarta da memória do navegador os dados da sessão encerrada.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.assign("/entrar?motivo=saiu");
    },
  };

  return <Contexto value={sessao}>{children}</Contexto>;
}
