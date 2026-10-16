// TEL01 · Criar nova senha pelo link de recuperação (HU01.07)

import type { Metadata } from "next";
import { Suspense } from "react";
import { DefinirSenha } from "@/components/definir-senha";

export const metadata: Metadata = { title: "Nova senha" };

export default function PaginaRedefinirSenha() {
  return (
    <Suspense>
      <DefinirSenha tipo="recuperacao" />
    </Suspense>
  );
}
