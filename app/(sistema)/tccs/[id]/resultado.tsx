"use client";

// TEL12 · seção "Consolidar resultado" (DS-FL06 e DS-FL06-B · RBN09.11, RN21), na página do TCC (TEL06).
//   GET /defesas/{id}/resultado   {pendentes[]} enquanto falta avaliação; com todas enviadas,
//                                 {notas, média, regra de exceção, nota final}
// Só o orientador do TCC vê esta seção: para os demais a API responde 403 e nada aparece aqui.
// A nota final é sempre calculada no servidor; a tela só mostra, com duas casas (CA-06).
// A escolha e a confirmação do resultado (Aprovado, Aprovado com correções, Reprovado) entram no SCRUM-70.

import { useEffect, useState } from "react";
import { Aviso, Selo } from "@/components/aviso";
import { api, ErroApi } from "@/lib/api";
import {
  type Banca,
  type ConsultaResultado,
  type PapelAvaliador,
} from "@/lib/tipos";

const NOME_PAPEL: Record<PapelAvaliador, string> = {
  ORIENTADOR: "Orientador(a)",
  AVALIADOR: "Avaliador(a)",
  SUPLENTE: "Suplente convocado(a)",
};

// Mesma precisão em tela, ata e relatórios (CA-06): duas casas, vírgula decimal.
const nota = (n: number) => n.toFixed(2).replace(".", ",");

export function SecaoResultado({ tccId }: { tccId: string }) {
  const [dados, setDados] = useState<ConsultaResultado | null>(null);
  const [oculta, setOculta] = useState(false);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<Banca>(`/tccs/${tccId}/banca`)
      .then((b) => {
        if (!b.defesa) return setOculta(true);
        return api<ConsultaResultado>(`/defesas/${b.defesa.id}/resultado`).then(
          setDados,
        );
      })
      .catch((e: ErroApi) =>
        // 403: não é o orientador; 404: sem acesso ao TCC; 409: defesa cancelada
        e.status === 403 || e.status === 404 || e.status === 409
          ? setOculta(true)
          : setErro(e.message),
      );
  }, [tccId]);

  if (oculta) return null;

  return (
    <section
      className="rounded-xl border border-borda bg-superficie p-5"
      aria-labelledby="titulo-resultado"
    >
      <h2 id="titulo-resultado" className="mb-1 font-semibold">
        Consolidar resultado
      </h2>
      <p className="mb-4 text-[13px] text-suave">
        A nota final é a média das notas do orientador e dos dois avaliadores,
        calculada pelo sistema a partir das avaliações enviadas.
      </p>
      {erro ? (
        <Aviso tipo="erro">{erro}</Aviso>
      ) : !dados ? (
        <p role="status" className="text-sm text-suave">
          Carregando…
        </p>
      ) : !dados.consolidacao ? (
        // DS-FL06, [falta avaliação]: "Aguardando avaliações. Faltam: ..." (RBN10.05)
        <Aviso tipo="info">
          <span className="font-medium">Aguardando avaliações.</span> Faltam:{" "}
          {dados.pendentes.map((p, i) => (
            <span key={p.membro_id}>
              {i > 0 && ", "}
              <span className="font-medium">{p.pessoa.nome}</span> (
              {NOME_PAPEL[p.papel].toLowerCase()})
            </span>
          ))}
          . A nota final aparece quando todos enviarem.
        </Aviso>
      ) : (
        <Consolidacao c={dados.consolidacao} />
      )}
    </section>
  );
}

function Consolidacao({
  c,
}: {
  c: NonNullable<ConsultaResultado["consolidacao"]>;
}) {
  return (
    <div className="flex flex-col gap-4">
      <ul
        className="divide-y divide-borda rounded-lg border border-borda text-sm"
        aria-label="Notas da banca"
      >
        {c.notas.map((n) => (
          <li
            key={n.membro_id}
            className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 p-3"
          >
            <span className="min-w-0 break-words">
              <span className="font-medium">{n.pessoa.nome}</span>{" "}
              <span className="text-suave">· {NOME_PAPEL[n.papel]}</span>
            </span>
            <span className="tabular-nums">{nota(n.nota)}</span>
          </li>
        ))}
      </ul>

      <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-[max-content_1fr]">
        <dt className="text-suave">Média</dt>
        <dd className="tabular-nums">{nota(c.media)}</dd>
        <dt className="text-suave">Regra de exceção</dt>
        <dd className="flex flex-col gap-1">
          <span>
            <Selo cor={c.regra.aplicada ? "verde" : "cinza"}>
              {c.regra.aplicada ? "Aplicada" : "Não aplicada"}
            </Selo>
          </span>
          {/* H10: a regra do artigo Qualis A ou B (RN21) é explicada na própria consolidação */}
          <span className="text-suave">{c.regra.porque}</span>
        </dd>
        <dt className="text-suave">Nota final</dt>
        <dd>
          <span
            className="text-2xl font-semibold tabular-nums"
            aria-live="polite"
          >
            {nota(c.nota_final)}
          </span>
        </dd>
      </dl>
    </div>
  );
}
