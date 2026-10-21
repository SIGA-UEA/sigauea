// Marca do sistema. O quadrado é um espaço reservado para o logotipo oficial da UEA.

export function Marca({ clara }: { clara?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <span
        aria-hidden="true"
        className={`flex size-9 items-center justify-center rounded-lg text-[13px] font-bold tracking-tight ${
          clara ? "bg-white text-azul" : "bg-azul text-white"
        }`}
      >
        UEA
      </span>
      <span className={`text-lg font-semibold tracking-tight ${clara ? "text-white" : "text-texto"}`}>
        SIGA <span className={clara ? "text-white/80" : "text-azul"}>UEA</span>
      </span>
    </span>
  );
}
