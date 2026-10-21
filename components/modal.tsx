"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { Icone } from "./icone";

type Props = {
  titulo: string;
  aoFechar: () => void;
  children: ReactNode;
  largo?: boolean;
};

/** Janela sobre a página. Usa o <dialog> do navegador, que já cuida do foco e da tecla Esc. */
export function Modal({ titulo, aoFechar, children, largo }: Props) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialogo = ref.current;
    dialogo?.showModal();
    return () => dialogo?.close();
  }, []);

  return (
    <dialog
      ref={ref}
      onCancel={(e) => {
        e.preventDefault();
        aoFechar();
      }}
      aria-label={titulo}
      className={`m-auto w-[calc(100vw-1.5rem)] rounded-2xl bg-superficie p-0 text-texto shadow-xl ${
        largo ? "max-w-2xl" : "max-w-md"
      }`}
    >
      <header className="flex items-center justify-between gap-4 border-b border-borda py-3 pr-3 pl-5">
        <h2 className="text-lg font-semibold">{titulo}</h2>
        <button
          type="button"
          onClick={aoFechar}
          aria-label="Fechar"
          className="flex size-9 items-center justify-center rounded-full text-suave hover:bg-fundo"
        >
          <Icone nome="fechar" />
        </button>
      </header>
      <div className="p-5">{children}</div>
    </dialog>
  );
}
