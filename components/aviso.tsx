import type { ReactNode } from "react";
import { Icone, type NomeIcone } from "./icone";

const TIPOS: Record<string, { estilo: string; icone: NomeIcone }> = {
  info: { estilo: "bg-azul-claro text-azul-escuro border-azul-borda", icone: "info" },
  sucesso: { estilo: "bg-verde-claro text-verde border-verde/25", icone: "certo" },
  alerta: { estilo: "bg-ambar-claro text-ambar border-ambar/25", icone: "alerta" },
  erro: { estilo: "bg-vermelho-claro text-vermelho border-vermelho/25", icone: "alerta" },
};

export type TipoAviso = "info" | "sucesso" | "alerta" | "erro";

export function Aviso({ tipo = "info", children }: { tipo?: TipoAviso; children: ReactNode }) {
  const { estilo, icone } = TIPOS[tipo];
  return (
    <div
      role={tipo === "erro" ? "alert" : "status"}
      className={`flex gap-2.5 rounded-lg border px-3.5 py-3 text-sm ${estilo}`}
    >
      <Icone nome={icone} className="mt-0.5 size-4" />
      <div className="min-w-0">{children}</div>
    </div>
  );
}

const SELOS = {
  azul: "bg-azul-claro text-azul-escuro",
  verde: "bg-verde-claro text-verde",
  ambar: "bg-ambar-claro text-ambar",
  cinza: "bg-fundo text-suave ring-1 ring-inset ring-borda",
  vermelho: "bg-vermelho-claro text-vermelho",
};

export function Selo({ cor = "azul", children }: { cor?: keyof typeof SELOS; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap ${SELOS[cor]}`}
    >
      {children}
    </span>
  );
}
