"use client";

// TEL06 · Acompanhamento do TCC: dados do cadastro, vínculos de orientação, resultado da análise
// da coordenação (DS-FL02-B), banca e defesa (TEL10/TEL11, ver banca.tsx), presença e ocorrências
// (TEL19, ver presenca.tsx) e histórico de situações (RNF03). Quem pode ver é decidido pela API (404 para
// os demais, RN07). Para quem está na banca, a seção "Minha avaliação" (TEL12, ver avaliacao.tsx);
// para o orientador, "Consolidar resultado" (TEL12, ver resultado.tsx). A orientação, com as ações da coordenação e
// do orientador sobre o coorientador (DS-FL03-D), fica em orientacao.tsx. A pessoa externa (RBN01.12 e RBN01.13) vê
// só os dados do trabalho e, se for da banca, a sua avaliação: a defesa vem dos acessos da sessão (/auth/me).

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Aviso } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { SeloSituacao } from "@/components/situacao-tcc";
import { api, ErroApi } from "@/lib/api";
import { useSessao } from "@/lib/sessao";
import { SecaoAvaliacao } from "./avaliacao";
import { SecaoBanca } from "./banca";
import { SecaoOrientacao } from "./orientacao";
import { SecaoPresenca } from "./presenca";
import { SecaoResultado } from "./resultado";
import { dataHora, NOME_SITUACAO_EDITORIAL, NOME_SITUACAO_TCC, type Banca, type SituacaoTcc, type Tcc } from "@/lib/tipos";

export default function PaginaTcc() {
  const { id } = useParams<{ id: string }>();
  const { tem, usuario } = useSessao();
  const externo = usuario.tipo === "externo";
  const router = useRouter();
  const [tcc, setTcc] = useState<Tcc | null>(null);
  const [erro, setErro] = useState("");
  // A defesa vigente é buscada uma vez e repassada às seções que dependem dela (presença, avaliação e resultado).
  const [defesaId, setDefesaId] = useState<number | null>(null);
  // Muda a cada avaliação enviada: a consolidação recarrega sem precisar abrir a página de novo.
  const [envios, setEnvios] = useState(0);

  const recarregar = () => api<Tcc>(`/tccs/${id}`).then(setTcc).catch((e: ErroApi) => setErro(e.message));

  // A pessoa externa não abre a banca (403); a defesa dela vem dos acessos da sessão (decisão 32-33-a, opção A).
  const defesaExterna =
    usuario.acessos.find((a) => a.escopo === "BANCA" && a.tcc_id === Number(id))?.defesa_id ?? null;

  useEffect(() => {
    api<Tcc>(`/tccs/${id}`).then(setTcc).catch((e: ErroApi) => setErro(e.message));
    if (externo) return;
    api<Banca>(`/tccs/${id}/banca`)
      .then((b) => setDefesaId(b.defesa?.id ?? null))
      .catch(() => setDefesaId(null)); // a seção Banca e defesa mostra o erro
  }, [id, externo]);

  if (erro) return <Aviso tipo="erro">{erro}</Aviso>;
  if (!tcc)
    return (
      <p role="status" className="text-suave">
        Carregando…
      </p>
    );

  const rascunho = tcc.situacao === "RASCUNHO";
  const ultima = tcc.decisoes.at(-1);
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

      {tem("aluno") && rascunho && (
        <Aviso tipo="info">
          O cadastro ainda é um rascunho.{" "}
          <Link href="/tccs/cadastro" className="font-medium underline">
            Continuar cadastro
          </Link>
        </Aviso>
      )}

      {/* DS-FL02-B: resultado da análise e o próximo passo (RBN04.05) */}
      {tcc.situacao === "DEVOLVIDO" && (
        <Aviso tipo="alerta">
          <p className="font-semibold">Parecer da Coordenação</p>
          {ultima?.parecer && <p className="mt-1 whitespace-pre-wrap">{ultima.parecer}</p>}
          <p className="mt-2">A Coordenação devolveu o cadastro. Leia o parecer, corrija e reenvie; o protocolo é mantido.</p>
          {tem("aluno") && (
            <div className="mt-3">
              <Botao pequeno onClick={() => router.push("/tccs/cadastro")}>
                Corrigir cadastro
              </Botao>
            </div>
          )}
        </Aviso>
      )}
      {tcc.situacao === "APROVADO" && (
        <Aviso tipo="sucesso">
          <p className="font-semibold">Cadastro aprovado. O orientador vai compor a banca e agendar a defesa.</p>
          {ultima?.parecer && <p className="mt-1 whitespace-pre-wrap">Parecer da Coordenação: {ultima.parecer}</p>}
          <p className="mt-1">A aprovação do cadastro não aprova a defesa nem o artigo.</p>
        </Aviso>
      )}
      {tcc.situacao === "REPROVADO" && (
        <Aviso tipo="erro">
          <p className="font-semibold">Parecer da Coordenação</p>
          {ultima?.parecer && <p className="mt-1 whitespace-pre-wrap">{ultima.parecer}</p>}
          <p className="mt-2">Cadastro reprovado. Procure a Coordenação para saber como proceder.</p>
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

      <SecaoOrientacao tcc={tcc} aoMudar={recarregar} />

      {tcc.decisoes.length > 0 && (
        <section className="rounded-xl border border-borda bg-superficie p-5">
          <h2 className="mb-3 font-semibold">Análise da Coordenação</h2>
          <ol className="flex flex-col gap-3 border-l-2 border-borda pl-4 text-sm">
            {tcc.decisoes.map((d, i) => (
              <li key={i}>
                <p className="flex flex-wrap items-center gap-2 font-medium">
                  <SeloSituacao situacao={d.resultado} />
                </p>
                {d.parecer && <p className="mt-1 break-words whitespace-pre-wrap">{d.parecer}</p>}
                <p className="text-suave">
                  {dataHora(d.decidido_em)} · {d.coordenador.nome}
                </p>
              </li>
            ))}
          </ol>
        </section>
      )}

      {externo ? (
        defesaExterna !== null && <SecaoAvaliacao defesaId={defesaExterna} aoEnviar={() => setEnvios((n) => n + 1)} />
      ) : (
        <>
          <SecaoBanca tccId={id} />
          {defesaId !== null && (
            <>
              <SecaoPresenca defesaId={defesaId} />
              <SecaoAvaliacao defesaId={defesaId} aoEnviar={() => setEnvios((n) => n + 1)} />
              <SecaoResultado defesaId={defesaId} envios={envios} />
            </>
          )}
        </>
      )}

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
