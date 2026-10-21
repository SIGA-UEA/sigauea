import { Suspense } from "react";
import { Casca } from "@/components/casca";
import { ProvedorSessao } from "@/lib/sessao";
import { buscarUsuarioLogado } from "@/lib/sessao-servidor";

// Tudo que fica dentro de (sistema) exige login.
export default function LayoutSistema({ children }: { children: React.ReactNode }) {
  return (
    // Ler a sessão depende da requisição, então fica atrás de um Suspense:
    // o navegador mostra "Carregando…" enquanto a API confere quem está logado.
    <Suspense
      fallback={
        <div role="status" className="flex min-h-dvh items-center justify-center text-suave">
          Carregando…
        </div>
      }
    >
      <ComSessao>{children}</ComSessao>
    </Suspense>
  );
}

async function ComSessao({ children }: { children: React.ReactNode }) {
  const usuario = await buscarUsuarioLogado(); // sem sessão válida, leva ao login
  return (
    <ProvedorSessao usuario={usuario}>
      <Casca>{children}</Casca>
    </ProvedorSessao>
  );
}
