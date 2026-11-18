"use client";

// Agenda de apresentações (TEL17 · RBN14.01 a RBN14.04): as defesas vigentes por dia e horário.
// Canceladas não aparecem e uma remarcada mostra só o novo horário; tudo vem pronto da API.
//   GET /agenda?curso&de&ate   filtros por curso e período de datas (RBN14.02)
//   GET /agenda/pdf?...        a agenda com os mesmos filtros em PDF (RBN14.03): coordenação, professor e orientador

import { useEffect, useState } from "react";
import { Aviso, Selo } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Campo, Entrada, Selecao } from "@/components/campo";
import { Icone } from "@/components/icone";
import { corDoCurso } from "@/components/turma";
import { api, baixarPdf, ErroApi } from "@/lib/api";
import { useSessao } from "@/lib/sessao";
import { NOME_FORMATO, type Apresentacao, type Curso } from "@/lib/tipos";

// Período como no protótipo da TEL17 (DS-FL05-A), mais "Escolher datas" para o período de datas da ficha (RBN14.02)
type Periodo = "proximos" | "semana" | "todas" | "datas";
type Filtros = { curso: string; periodo: Periodo; de: string; ate: string };
const SEM_FILTRO: Filtros = { curso: "", periodo: "proximos", de: "", ate: "" };
const PERIODOS: [Periodo, string][] = [
  ["proximos", "Próximas apresentações"],
  ["semana", "Próximos 7 dias"],
  ["todas", "Todas (inclui passadas)"],
  ["datas", "Escolher datas"],
];

const dataCurta = (iso: string) => iso.split("-").reverse().join("/");

function consulta(f: Filtros) {
  const pares: [string, string][] =
    f.periodo === "datas"
      ? [
          ["de", f.de],
          ["ate", f.ate],
        ]
      : [["periodo", f.periodo]];
  if (f.curso) pares.unshift(["curso", f.curso]);
  return new URLSearchParams(pares.filter(([, v]) => v !== "")).toString();
}

function rotuloPeriodo(f: Filtros) {
  if (f.periodo !== "datas") return PERIODOS.find(([p]) => p === f.periodo)?.[1] ?? "";
  if (f.de && f.ate) return `De ${dataCurta(f.de)} a ${dataCurta(f.ate)}`;
  if (f.de) return `A partir de ${dataCurta(f.de)}`;
  return f.ate ? `Até ${dataCurta(f.ate)}` : "Todas as datas";
}

const hora = (t: string) => t.slice(0, 5);

function diaPorExtenso(iso: string) {
  const [a, m, d] = iso.split("-").map(Number);
  return new Date(a, m - 1, d).toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long" });
}

function agruparPorDia(lista: Apresentacao[]) {
  const dias = new Map<string, Apresentacao[]>();
  for (const a of lista) dias.set(a.data, [...(dias.get(a.data) ?? []), a]);
  return [...dias.entries()];
}

function Local({ a }: { a: Apresentacao }) {
  const link = a.link && (
    <a href={a.link} target="_blank" rel="noreferrer" className="text-azul-forte underline">
      Entrar na defesa
    </a>
  );
  if (a.local) {
    return (
      <span>
        {a.local}
        {link && <> · {link}</>}
      </span>
    );
  }
  return link || <span>{a.formato === "REMOTO" ? "Link enviado aos participantes" : "Local a confirmar"}</span>;
}

export default function PaginaAgenda() {
  const { tem } = useSessao();
  const podeExportar = tem("coordenador") || tem("professor_disciplina") || tem("orientador");
  const [cursos, setCursos] = useState<Curso[]>([]);
  const [filtros, setFiltros] = useState<Filtros>(SEM_FILTRO);
  // a resposta guarda os filtros que a geraram: enquanto não chega a dos atuais, a lista está carregando
  const [resposta, setResposta] = useState<{ chave: string; lista: Apresentacao[] } | null>(null);
  const [erro, setErro] = useState("");
  const [exportando, setExportando] = useState(false);
  const [erroPdf, setErroPdf] = useState("");

  // RBN14.02: a data final não pode vir antes da inicial; com o erro, a consulta não sai
  const erroData =
    filtros.periodo === "datas" && filtros.de && filtros.ate && filtros.ate < filtros.de
      ? "A data final deve ser igual ou posterior à inicial."
      : "";
  const chave = erroData ? null : consulta(filtros);
  const filtrando = filtros.curso !== "" || filtros.periodo !== "proximos";

  useEffect(() => {
    api<Curso[]>("/cursos")
      .then(setCursos)
      .catch(() => setCursos([]));
  }, []);

  // H1: a lista acompanha cada filtro, sem botão de aplicar
  useEffect(() => {
    if (chave === null) return;
    api<Apresentacao[]>(`/agenda${chave ? `?${chave}` : ""}`)
      .then((lista) => {
        setResposta({ chave, lista });
        setErro("");
      })
      .catch((e: ErroApi) => setErro(e.campos?.ate ?? e.message));
  }, [chave]);
  const lista = resposta && resposta.chave === chave ? resposta.lista : null;

  const mudar = (campo: keyof Filtros) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setFiltros((f) => ({ ...f, [campo]: e.target.value }) as Filtros);
  const limpar = () => setFiltros(SEM_FILTRO);

  async function exportar() {
    setErroPdf("");
    setExportando(true);
    try {
      await baixarPdf(`/agenda/pdf${chave ? `?${chave}` : ""}`, "agenda-de-apresentacoes.pdf");
    } catch (e) {
      setErroPdf((e as ErroApi).message);
    }
    setExportando(false);
  }

  // filtros ativos (ficha do RBN14.02): cada um sai sozinho; "Limpar filtros" volta às próximas de todos os cursos
  const nomeCurso = cursos.find((c) => String(c.id) === filtros.curso)?.nome ?? filtros.curso;
  const ativos: [string, string, () => void][] = [];
  if (filtros.curso) ativos.push(["curso", nomeCurso, () => setFiltros((f) => ({ ...f, curso: "" }))]);
  if (filtros.periodo !== "proximos")
    ativos.push([
      "periodo",
      rotuloPeriodo(filtros),
      () => setFiltros((f) => ({ ...f, periodo: "proximos", de: "", ate: "" })),
    ]);

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold tracking-widest text-suave uppercase">Defesas</p>
          <h1 className="text-2xl font-semibold">Agenda de apresentações</h1>
          <p className="mt-1 text-sm text-suave">Programação das apresentações autorizadas para divulgação.</p>
        </div>
        {podeExportar && (
          <Botao variante="contorno" onClick={exportar} carregando={exportando} disabled={!!erroData}>
            <Icone nome="documento" className="size-4" />
            Exportar PDF
          </Botao>
        )}
      </header>

      <section aria-label="Filtros" className="rounded-xl border border-borda bg-superficie p-5">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Campo rotulo="Curso">
            <Selecao value={filtros.curso} onChange={mudar("curso")}>
              <option value="">Todos os cursos</option>
              {cursos.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nome}
                </option>
              ))}
            </Selecao>
          </Campo>
          <Campo rotulo="Período">
            <Selecao value={filtros.periodo} onChange={mudar("periodo")}>
              {PERIODOS.map(([valor, rotulo]) => (
                <option key={valor} value={valor}>
                  {rotulo}
                </option>
              ))}
            </Selecao>
          </Campo>
          {filtros.periodo === "datas" && (
            <>
              <Campo rotulo="De" dica="data inicial">
                <Entrada type="date" value={filtros.de} onChange={mudar("de")} />
              </Campo>
              <Campo rotulo="Até" dica="data final" erro={erroData}>
                <Entrada
                  type="date"
                  value={filtros.ate}
                  min={filtros.de || undefined}
                  onChange={mudar("ate")}
                  erro={erroData}
                />
              </Campo>
            </>
          )}
        </div>
        {ativos.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-2" aria-label="Filtros ativos">
            {ativos.map(([campo, rotulo, remover]) => (
              <button
                key={campo}
                type="button"
                onClick={remover}
                aria-label={`Remover o filtro ${rotulo}`}
                className="inline-flex items-center gap-1 rounded-full bg-azul-claro px-3 py-1 text-xs font-medium text-azul-forte"
              >
                {rotulo}
                <Icone nome="fechar" className="size-3" />
              </button>
            ))}
            <Botao variante="texto" pequeno onClick={limpar}>
              Limpar filtros
            </Botao>
          </div>
        )}
      </section>

      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      {erroPdf && <Aviso tipo="erro">{erroPdf}</Aviso>}

      {erroData ? null : !lista ? (
        !erro && (
          <p role="status" className="text-sm text-suave">
            Carregando…
          </p>
        )
      ) : lista.length === 0 ? (
        <div className="rounded-xl border border-borda bg-superficie p-6 text-sm">
          <p className="font-medium">Nenhuma apresentação encontrada</p>
          <p className="mt-1 text-suave">
            {filtrando ? "Nada corresponde aos filtros escolhidos." : "Ainda não há apresentações publicadas."}
          </p>
          {filtrando && (
            <div className="mt-3">
              <Botao variante="contorno" pequeno onClick={limpar}>
                Limpar filtros
              </Botao>
            </div>
          )}
        </div>
      ) : (
        agruparPorDia(lista).map(([dia, itens]) => (
          <section key={dia} aria-labelledby={`dia-${dia}`} className="flex flex-col gap-3">
            <h2 id={`dia-${dia}`} className="text-sm font-semibold text-suave first-letter:uppercase">
              {diaPorExtenso(dia)}
            </h2>
            <ul className="flex flex-col gap-3">
              {itens.map((a) => (
                <li key={a.id} className="flex gap-4 rounded-xl border border-borda bg-superficie p-4">
                  <div className="flex w-16 shrink-0 flex-col items-center text-center">
                    <Icone nome="relogio" className="size-4 text-suave" />
                    <span className="mt-1 text-lg font-semibold">{hora(a.inicio)}</span>
                    <span className="text-xs text-suave">até {hora(a.fim)}</span>
                  </div>
                  <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                    <h3 className="font-medium">{a.titulo}</h3>
                    <p className="text-sm text-suave">
                      {a.autor}
                      {a.orientador && ` · Orientador(a): ${a.orientador}`}
                    </p>
                    <div className="flex flex-wrap items-center gap-2 text-sm">
                      <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${corDoCurso(a.curso.sigla)}`}>
                        {a.curso.sigla}
                      </span>
                      <Selo cor="cinza">{NOME_FORMATO[a.formato]}</Selo>
                      {a.remarcada && <Selo cor="ambar">Remarcada</Selo>}
                      <Local a={a} />
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        ))
      )}
    </div>
  );
}
