"use client";

// PasswordField (HU01.04): senha mascarada com botão de mostrar/ocultar e,
// quando pedido, a lista dos 4 critérios que vai sendo marcada durante a digitação.

import { useState } from "react";
import { avaliarSenha } from "@/lib/senha";
import { Campo, ESTILO_ENTRADA } from "./campo";
import { Icone } from "./icone";

type Props = {
  rotulo: string;
  valor: string;
  aoMudar: (valor: string) => void;
  erro?: string;
  // "new-password" na ativação e na redefinição; "current-password" no login.
  autoComplete: "current-password" | "new-password";
  mostrarCriterios?: boolean;
};

export function CampoSenha({ rotulo, valor, aoMudar, erro, autoComplete, mostrarCriterios }: Props) {
  const [visivel, setVisivel] = useState(false);

  return (
    <div className="flex flex-col gap-2">
      <Campo rotulo={rotulo} obrigatorio erro={erro}>
        <span className="relative">
          <input
            type={visivel ? "text" : "password"}
            value={valor}
            onChange={(e) => aoMudar(e.target.value)}
            autoComplete={autoComplete}
            required
            maxLength={128}
            aria-invalid={erro ? true : undefined}
            className={`${ESTILO_ENTRADA} pr-12 ${erro ? "border-vermelho" : "border-borda"}`}
          />
          <button
            type="button"
            onClick={() => setVisivel(!visivel)}
            aria-label={visivel ? "Ocultar senha" : "Mostrar senha"}
            aria-pressed={visivel}
            className="absolute inset-y-0 right-0 flex w-11 items-center justify-center rounded-lg text-suave hover:text-azul-forte"
          >
            <Icone nome={visivel ? "olho-fechado" : "olho"} />
          </button>
        </span>
      </Campo>

      {mostrarCriterios && (
        <ul className="flex flex-col gap-1 text-[13px]" aria-label="Critérios da senha">
          {avaliarSenha(valor).map((c) => (
            <li
              key={c.codigo}
              className={`flex items-center gap-2 ${c.ok ? "text-verde" : "text-suave"}`}
            >
              <Icone nome={c.ok ? "certo" : "ponto"} className="size-4" />
              {c.descricao}
              <span className="sr-only">{c.ok ? " (atendido)" : " (falta)"}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
