"use client";

// TEL16 · Indicadores (DS-FL08-D · RBN13.01 e RBN13.02, RN18).
//   GET /indicadores/escopo    escopo e filtros do perfil, com o período letivo vigente
//   GET /indicadores/situacao  TCCs por situação acadêmica e orientandos por orientador, por etapa
// Cada perfil só vê os filtros dele (CA-04); TCC1 e TCC2 aparecem sempre lado a lado, nunca somados; nenhum número
// traz nome de aluno (RN18). Produção científica, desistências, bancas e o PDF entram com o SCRUM-90 a SCRUM-93.

import { useEffect, useState } from "react";
import { Aviso } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Campo, Selecao } from "@/components/campo";
import { api, ErroApi } from "@/lib/api";
import {
  NOME_SITUACAO_TCC,
  type EscopoIndicadores,
  type IndicadorSituacao,
  type PorEtapa,
  type SituacaoTcc,
} from "@/lib/tipos";

type Filtros = { periodo: string; curso: string; etapa: string; turma: string; orientador: string };
const VAZIO = { curso: "", etapa: "", turma: "", orientador: "" };

export default function PaginaIndicadores() {
  const [escopo, setEscopo] = useState<EscopoIndicadores | null>(null);
  const [filtros, setFiltros] = useState<Filtros | null>(null);
  // a resposta guarda os filtros que a geraram: enquanto não chega a dos filtros atuais, a tela está carregando
  const [resposta, setResposta] = useState<{ chave: string; dados: IndicadorSituacao } | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<EscopoIndicadores>("/indicadores/escopo")
      .then((e) => {
        setEscopo(e);
        setFiltros({ periodo: e.periodo_vigente_id ? String(e.periodo_vigente_id) : "", ...VAZIO }); // CA-05
      })
      .catch((e: ErroApi) => setErro(e.message));
  }, []);

  const chave = filtros ? new URLSearchParams(Object.entries(filtros).filter(([, v]) => v !== "")).toString() : null;

  // H1: os números acompanham cada filtro, sem botão de aplicar
  useEffect(() => {
    if (chave === null) return;
    api<IndicadorSituacao>(`/indicadores/situacao?${chave}`)
      .then((d) => {
        setResposta({ chave, dados: d });
        setErro("");
      })
      .catch((e: ErroApi) => setErro(e.message));
  }, [chave]);
  const dados = resposta?.dados ?? null;
  const carregando = resposta?.chave !== chave;

  const mudar = (campo: keyof Filtros) => (e: React.ChangeEvent<HTMLSelectElement>) =>
    setFiltros((f) => (f ? { ...f, [campo]: e.target.value } : f));
  const limpar = () =>
    setFiltros({ periodo: escopo?.periodo_vigente_id ? String(escopo.periodo_vigente_id) : "", ...VAZIO });

  return (
    <div className="flex flex-col gap-5">
      <header>
        <p className="text-xs font-semibold tracking-widest text-suave uppercase">Gestão</p>
        <h1 className="text-2xl font-semibold">Indicadores</h1>
        <p className="mt-1 text-sm text-suave">
          Veja a situação dos TCCs dentro do seu escopo. Os indicadores não mostram nomes de alunos.
        </p>
      </header>

      {erro && !escopo ? (
        <Aviso tipo="erro">{erro}</Aviso>
      ) : !escopo || !filtros ? (
        <p role="status" className="text-sm text-suave">
          Carregando…
        </p>
      ) : (
        <>
          <section className="rounded-xl border border-borda bg-superficie p-5" aria-label="Filtros">
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Campo rotulo="Período letivo">
                <Selecao value={filtros.periodo} onChange={mudar("periodo")}>
                  {escopo.periodos.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.codigo}
                      {p.vigente ? " (vigente)" : ""}
                    </option>
                  ))}
                </Selecao>
              </Campo>
              {escopo.filtros.curso && (
                <Campo rotulo="Curso">
                  <Selecao value={filtros.curso} onChange={mudar("curso")}>
                    <option value="">Todos do escopo</option>
                    {escopo.cursos.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.nome}
                      </option>
                    ))}
                  </Selecao>
                </Campo>
              )}
              {escopo.filtros.etapa && (
                <Campo rotulo="Etapa">
                  <Selecao value={filtros.etapa} onChange={mudar("etapa")}>
                    <option value="">TCC1 e TCC2</option>
                    <option value="TCC1">TCC1</option>
                    <option value="TCC2">TCC2</option>
                  </Selecao>
                </Campo>
              )}
              {escopo.filtros.turma && (
                <Campo rotulo="Turma">
                  <Selecao value={filtros.turma} onChange={mudar("turma")}>
                    <option value="">Todas as suas turmas</option>
                    {escopo.turmas.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.codigo}
                      </option>
                    ))}
                  </Selecao>
                </Campo>
              )}
              {escopo.filtros.orientador && (
                <Campo rotulo="Orientador">
                  <Selecao value={filtros.orientador} onChange={mudar("orientador")}>
                    <option value="">Todos</option>
                    {escopo.orientadores.map((o) => (
                      <option key={o.id} value={o.id}>
                        {o.nome}
                      </option>
                    ))}
                  </Selecao>
                </Campo>
              )}
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2 text-[13px]">
              <span className="text-suave">Escopo:</span>
              {escopo.descricao.map(([perfil, alcance]) => (
                <span key={perfil} className="rounded-full bg-fundo px-2.5 py-0.5 ring-1 ring-borda ring-inset">
                  {perfil}: {alcance}
                </span>
              ))}
            </div>
            <p className="mt-2 text-[13px] text-suave">
              Quem tem mais de um perfil vê a soma dos escopos; cada TCC é contado uma única vez.
            </p>
          </section>

          {erro && <Aviso tipo="erro">{erro}</Aviso>}
          <div aria-live="polite" aria-busy={carregando}>
            {!dados ? (
              <p role="status" className="text-sm text-suave">
                Carregando…
              </p>
            ) : dados.sem_dados ? (
              <div className="rounded-xl border border-borda bg-superficie p-6 text-sm">
                <p className="font-medium">Sem dados para este filtro</p>
                <p className="mt-1 text-suave">Não há TCCs no período e nos filtros escolhidos.</p>
                <div className="mt-3">
                  <Botao variante="contorno" pequeno onClick={limpar}>
                    Limpar filtros
                  </Botao>
                </div>
              </div>
            ) : (
              <Resultados dados={dados} />
            )}
          </div>
        </>
      )}
    </div>
  );
}

function Resultados({ dados }: { dados: IndicadorSituacao }) {
  const de = (s: string) => dados.situacoes.find((x) => x.situacao === s)?.total ?? { TCC1: 0, TCC2: 0 };
  const destaques: [string, PorEtapa][] = [
    ["TCCs no escopo", dados.total],
    ["Em análise", de("EM_ANALISE")],
    ["Aprovados", de("APROVADO")],
    ["Desistências", de("DESISTENCIA")],
  ];
  return (
    <div className="flex flex-col gap-5">
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label="Destaques">
        {destaques.map(([rotulo, t]) => (
          <li key={rotulo} className="rounded-xl border border-borda bg-superficie p-4">
            <p className="text-[13px] text-suave">{rotulo}</p>
            <p className="mt-1 flex gap-4 tabular-nums">
              <span>
                <span className="text-2xl font-semibold">{t.TCC1}</span>{" "}
                <span className="text-[13px] text-suave">TCC1</span>
              </span>
              <span>
                <span className="text-2xl font-semibold">{t.TCC2}</span>{" "}
                <span className="text-[13px] text-suave">TCC2</span>
              </span>
            </p>
          </li>
        ))}
      </ul>

      <section className="rounded-xl border border-borda bg-superficie p-5" aria-labelledby="titulo-situacao">
        <h2 id="titulo-situacao" className="font-semibold">
          Situação acadêmica
        </h2>
        <p className="mb-3 text-[13px] text-suave">TCC1 e TCC2 separados; cada TCC é contado uma vez.</p>
        <Tabela
          rotulo="Situação"
          linhas={dados.situacoes.map((s) => [NOME_SITUACAO_TCC[s.situacao as SituacaoTcc] ?? s.situacao, s.total])}
          maximo={dados.total}
        />
      </section>

      <section className="rounded-xl border border-borda bg-superficie p-5" aria-labelledby="titulo-orientacoes">
        <h2 id="titulo-orientacoes" className="font-semibold">
          Orientações
        </h2>
        <p className="mb-3 text-[13px] text-suave">Orientandos por orientador, por etapa.</p>
        {dados.orientacoes.length === 0 ? (
          <p className="text-sm text-suave">Nenhuma orientação aceita neste filtro.</p>
        ) : (
          <Tabela
            rotulo="Orientador"
            linhas={dados.orientacoes.map((o) => [o.orientador.nome, o.total])}
            maximo={dados.total}
          />
        )}
      </section>
    </div>
  );
}

// Tabela com barras curtas: o número é o dado; a barra só ajuda a comparar (H8, sem enfeite).
function Tabela({ rotulo, linhas, maximo }: { rotulo: string; linhas: [string, PorEtapa][]; maximo: PorEtapa }) {
  const barra = (n: number, total: number) => (
    <span className="flex items-center gap-2">
      <span className="w-6 text-right tabular-nums">{n}</span>
      <span aria-hidden="true" className="h-2 w-20 overflow-hidden rounded-full bg-fundo sm:w-28">
        <span className="block h-full rounded-full bg-azul" style={{ width: `${total ? (n / total) * 100 : 0}%` }} />
      </span>
    </span>
  );
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-borda text-left text-[13px] text-suave">
            <th scope="col" className="py-2 pr-3 font-medium">
              {rotulo}
            </th>
            <th scope="col" className="py-2 pr-3 font-medium">
              TCC1
            </th>
            <th scope="col" className="py-2 font-medium">
              TCC2
            </th>
          </tr>
        </thead>
        <tbody>
          {linhas.map(([nome, t]) => (
            <tr key={nome} className="border-b border-borda last:border-0">
              <th scope="row" className="py-2 pr-3 text-left font-normal break-words">
                {nome}
              </th>
              <td className="py-2 pr-3">{barra(t.TCC1, maximo.TCC1)}</td>
              <td className="py-2">{barra(t.TCC2, maximo.TCC2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
