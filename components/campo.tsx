import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";

export const ESTILO_ENTRADA =
  "h-11 w-full min-w-0 rounded-lg border bg-superficie px-3 text-[15px] text-texto placeholder:text-suave/70 disabled:bg-fundo disabled:text-suave";

const borda = (erro?: string) => (erro ? "border-vermelho" : "border-borda");

type PropsCampo = {
  rotulo: string;
  obrigatorio?: boolean;
  dica?: string;
  erro?: string;
  className?: string;
  children: ReactNode;
};

/** Rótulo + controle + mensagem de erro. O controle vai como filho. */
export function Campo({ rotulo, obrigatorio, dica, erro, className = "", children }: PropsCampo) {
  return (
    <label className={`flex min-w-0 flex-col gap-1.5 text-sm ${className}`}>
      <span className="font-medium text-texto">
        {rotulo}
        {obrigatorio ? (
          <span className="text-vermelho" title="Obrigatório">
            {" "}
            *
          </span>
        ) : (
          dica && <span className="font-normal text-suave"> ({dica})</span>
        )}
      </span>
      {children}
      {erro && (
        <span role="alert" className="text-[13px] font-medium text-vermelho">
          {erro}
        </span>
      )}
    </label>
  );
}

export function Entrada({
  erro,
  className = "",
  ...resto
}: InputHTMLAttributes<HTMLInputElement> & { erro?: string }) {
  return (
    <input
      {...resto}
      aria-invalid={erro ? true : undefined}
      className={`${ESTILO_ENTRADA} ${borda(erro)} ${className}`}
    />
  );
}

export function Selecao({
  erro,
  className = "",
  children,
  ...resto
}: SelectHTMLAttributes<HTMLSelectElement> & { erro?: string }) {
  return (
    <select
      {...resto}
      aria-invalid={erro ? true : undefined}
      className={`${ESTILO_ENTRADA} ${borda(erro)} ${className}`}
    >
      {children}
    </select>
  );
}
