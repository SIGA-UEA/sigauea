import type { ButtonHTMLAttributes } from "react";

const VARIANTES = {
  primario: "bg-azul text-white hover:bg-azul-forte shadow-sm",
  contorno: "border border-borda bg-superficie text-azul-forte hover:bg-azul-claro",
  texto: "text-azul-forte hover:bg-azul-claro",
  perigo: "text-vermelho hover:bg-vermelho-claro",
  destrutivo: "bg-vermelho text-white hover:bg-vermelho/90 shadow-sm",
};

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variante?: keyof typeof VARIANTES;
  pequeno?: boolean;
  // Enquanto a requisição está em andamento: desabilita e evita clique duplicado.
  carregando?: boolean;
};

export function Botao({
  variante = "primario",
  pequeno,
  carregando,
  className = "",
  children,
  ...resto
}: Props) {
  return (
    <button
      type="button"
      {...resto}
      disabled={resto.disabled || carregando}
      className={`inline-flex items-center justify-center gap-2 rounded-full font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-55 ${
        pequeno ? "h-8 px-3 text-sm" : "h-10 px-5 text-sm"
      } ${VARIANTES[variante]} ${className}`}
    >
      {carregando ? "Aguarde…" : children}
    </button>
  );
}
