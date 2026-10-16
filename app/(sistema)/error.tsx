"use client";

import { Aviso } from "@/components/aviso";
import { Botao } from "@/components/botao";

// Mostrado quando uma tela interna falha ao carregar (ex.: API fora do ar).
export default function ErroSistema({ retry }: { error: Error; retry: () => void }) {
  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col items-center justify-center gap-4 p-6">
      <Aviso tipo="erro">Não foi possível carregar esta tela. Confira se a API está no ar.</Aviso>
      <Botao variante="contorno" onClick={retry}>
        Tentar de novo
      </Botao>
    </div>
  );
}
