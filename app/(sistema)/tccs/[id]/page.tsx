"use client";

// TEL06 · Acompanhamento do TCC: dados do cadastro, vínculos de orientação e histórico
// de situações (RNF03). Quem pode ver é decidido pela API (403/404 para os demais).

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Aviso } from "@/components/aviso";
import { SeloOrientacao, SeloSituacao } from "@/components/situacao-tcc";
import { api, ErroApi } from "@/lib/api";
import { useSessao } from "@/lib/sessao";
import { dataHora, NOME_SITUACAO_EDITORIAL, NOME_SITUACAO_TCC, type SituacaoTcc, type Tcc } from "@/lib/tipos";

export default function PaginaTcc() {
  const { id } = useParams<{ id: string }>();
  const { tem } = useSessao();
  const [tcc, setTcc] = useState<Tcc | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<Tcc>(`/tccs/${id}`).then(setTcc).catch((e: ErroApi) => setErro(e.message));
  }, [id]);

  if (erro) return <Aviso tipo="erro">{erro}</Aviso>;
  if (!tcc)
    return (
      <p role="status" className="text-suave">
        Carregando…
      </p>
    );

  const editavel = tcc.situacao === "RASCUNHO" || tcc.situacao === "DEVOLVIDO";
  const nome = (s: string | null) => (s ? (NOME_SITUACAO_TCC[s as SituacaoTcc] ?? s) : "—");

  return (
    <div className="flex max-w-4xl flex-col gap-5">
      <Link href="/tccs" className="text-sm font-medium text-azul-forte hover:underline">
        ← Voltar para TCCs
      </Link>
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-mono text-sm text-suave">{tcc.protocolo ?? "Sem protocolo (rascunho)"}</p>
          <h1 className="text-2xl font-semibold break-words">{tcc.titulo}</h1>
          {tcc.subtitulo && <p className="text-suave">{tcc.subtitulo}</p>}
        </div>
        <SeloSituacao situacao={tcc.situacao} />
      </header>

      {tem("aluno") && editavel && (
        <Aviso tipo={tcc.situacao === "DEVOLVIDO" ? "alerta" : "info"}>
          {tcc.situacao === "DEVOLVIDO" ? "O cadastro foi devolvido para correção. " : "O cadastro ainda é um rascunho. "}
          <Link href="/tccs/cadastro" className="font-medium underline">
            Continuar cadastro
          </Link>
        </Aviso>
      )}

      <section className="rounded-xl border border-borda bg-superficie p-5">
        <h2 className="mb-3 font-semibold">Dados do trabalho</h2>
        <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-[max-content_1fr]">
          <Item k="Autor(a)" v={`${tcc.aluno.nome} · matrícula ${tcc.matricula} · ${tcc.curso.nome}`} />
          <Item k="Turma" v={`${tcc.turma.codigo} · ${tcc.turma.professor.nome} · ${tcc.turma.periodo}`} />
          <Item k="Etapa e modalidade" v={`${tcc.etapa} · ${tcc.modalidade === "ARTIGO" ? "Artigo" : "Monografia"}`} />
          <Item k="Área" v={tcc.area.nome} />
          <Item k="Palavras-chave" v={tcc.palavras_chave.join(", ") || "—"} />
          <Item k="Resumo" v={tcc.resumo || "—"} />
          {tcc.artigo && tcc.modalidade === "ARTIGO" && (
            <Item
              k="Artigo"
              v={`${tcc.artigo.veiculo} · ${NOME_SITUACAO_EDITORIAL[tcc.artigo.situacao]}${tcc.artigo.doi ? ` · DOI ${tcc.artigo.doi}` : ""}`}
            />
          )}
          <Item k="Enviado em" v={dataHora(tcc.submetido_em)} />
        </dl>
      </section>

      <section className="rounded-xl border border-borda bg-superficie p-5">
        <h2 className="mb-3 font-semibold">Orientação</h2>
        {!tcc.orientador && !tcc.coorientador ? (
          <p className="text-sm text-suave">Nenhum orientador indicado ainda.</p>
        ) : (
          <ul className="flex flex-col gap-2 text-sm">
            {[tcc.orientador, tcc.coorientador].filter(Boolean).map((v) => (
              <li key={v!.id} className="flex flex-wrap items-center gap-2">
                <span className="font-medium">{v!.papel === "ORIENTADOR" ? "Orientador" : "Coorientador"}:</span>
                {v!.professor.nome}
                <SeloOrientacao status={v!.status} />
                {v!.motivo_recusa && <span className="w-full text-[13px] text-suave">Motivo: {v!.motivo_recusa}</span>}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-xl border border-borda bg-superficie p-5">
        <h2 className="mb-3 font-semibold">Histórico</h2>
        {tcc.historico.length === 0 ? (
          <p className="text-sm text-suave">Sem mudanças de situação ainda.</p>
        ) : (
          <ol className="flex flex-col gap-3 border-l-2 border-borda pl-4 text-sm">
            {tcc.historico.map((h, i) => (
              <li key={i}>
                <p className="font-medium">
                  {nome(h.situacao_anterior)} → {nome(h.situacao_nova)}
                </p>
                <p className="text-suave">
                  {dataHora(h.registrado_em)} · {h.usuario.nome}
                </p>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}

function Item({ k, v }: { k: string; v: string }) {
  return (
    <>
      <dt className="text-suave">{k}</dt>
      <dd className="break-words whitespace-pre-wrap">{v}</dd>
    </>
  );
}
