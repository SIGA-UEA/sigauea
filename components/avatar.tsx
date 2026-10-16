// Foto da pessoa ou, sem foto, um círculo com as iniciais. A cor é escolhida
// pelo nome, então a mesma pessoa aparece sempre com a mesma cor.

import Image from "next/image";

const CORES = ["bg-azul", "bg-[#0b8043]", "bg-[#8430ce]", "bg-[#c2410c]", "bg-[#0e7490]", "bg-[#be185d]"];

const TAMANHOS = {
  normal: { classe: "size-9 text-[13px]", px: 36 },
  grande: { classe: "size-12 text-base", px: 48 },
  perfil: { classe: "size-24 text-3xl", px: 96 },
};

export function iniciais(nome: string) {
  const partes = nome.trim().split(/\s+/);
  const letras = partes.length > 1 ? partes[0][0] + partes[partes.length - 1][0] : partes[0].slice(0, 2);
  return letras.toUpperCase();
}

type Props = {
  nome: string;
  foto?: string | null; // ver urlFoto em lib/tipos.ts
  tamanho?: keyof typeof TAMANHOS;
};

export function Avatar({ nome, foto, tamanho = "normal" }: Props) {
  const { classe, px } = TAMANHOS[tamanho];

  if (foto) {
    return (
      <Image
        src={foto}
        alt=""
        width={px}
        height={px}
        // A foto exige o cookie de sessão; o otimizador de imagens do Next não repassa cookies.
        unoptimized
        className={`shrink-0 rounded-full bg-fundo object-cover ${classe}`}
      />
    );
  }

  const soma = [...nome].reduce((total, letra) => total + letra.charCodeAt(0), 0);
  return (
    <span
      aria-hidden="true"
      className={`flex shrink-0 items-center justify-center rounded-full font-semibold text-white ${
        CORES[soma % CORES.length]
      } ${classe}`}
    >
      {iniciais(nome)}
    </span>
  );
}
