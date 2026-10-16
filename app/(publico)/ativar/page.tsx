// TEL01 · Ativar a conta pelo link do e-mail (HU01.05)

import type { Metadata } from "next";
import { Suspense } from "react";
import { DefinirSenha } from "@/components/definir-senha";

export const metadata: Metadata = { title: "Ativar conta" };

export default function PaginaAtivar() {
  return (
    <Suspense>
      <DefinirSenha tipo="ativacao" />
    </Suspense>
  );
}
