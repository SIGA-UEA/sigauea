"use client";

// TEL16 · Indicadores (DS-FL08-C, DS-FL08-D · RBN13.01 a RBN13.06, RN18).
//   GET /indicadores/escopo        escopo, período vigente e os filtros de cada indicador
//   GET /indicadores/situacao      TCCs por situação acadêmica e orientandos por orientador, por etapa (RBN13.02)
//   GET /indicadores               painel do DS-FL08-C; a aba Produção científica usa o bloco "producao" (RBN13.03)
//   GET /indicadores/desistencias  total por período e curso; evolução só para a coordenação (RBN13.04)
//   GET /indicadores/bancas        participações por professor e por papel (RBN13.05)
// O usuário escolhe o indicador nas abas (alt do DS-FL08-D). Cada aba só mostra os filtros do perfil para aquele
// indicador (filtros_indicadores); nenhum número traz nome de aluno (RN18).
//   POST /indicadores/relatorio    as quatro tabelas em PDF com os filtros escolhidos (RBN13.06, SCRUM-93)

import { useEffect, useState } from "react";
import { Aviso } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Campo, Selecao } from "@/components/campo";
import { Icone } from "@/components/icone";
import { api, baixarPdf, ErroApi } from "@/lib/api";
import {
  NOME_PAPEL_BANCA,
  NOME_SITUACAO_EDITORIAL,
  NOME_SITUACAO_TCC,
  type EscopoIndicadores,
  type IndicadorBancas,
  type IndicadorDesistencias,
  type IndicadorProducao,
  type IndicadorSituacao,
  type IndicadorTel16,
  type PainelIndicadores,
  type PapelBanca,
  type PorEtapa,
  type SituacaoTcc,
} from "@/lib/tipos";

type Filtros = {
  periodo: string;
  curso: string;
  etapa: string;
  turma: string;
  orientador: string;
  professor: string;
  papel: string;
  periodo_inicio: string;
  periodo_fim: string;
};
const VAZIO = {
  curso: "",
  etapa: "",
  turma: "",
  orientador: "",
  professor: "",
  papel: "",
  periodo_inicio: "",
  periodo_fim: "",
};

const ABAS: [IndicadorTel16, string][] = [
  ["situacao", "Situação e orientações"],
  ["producao", "Produção científica"],
  ["desistencias", "Desistências"],
  ["bancas", "Participações em banca"],
];
const ROTA: Record<IndicadorTel16, string> = {
  situacao: "/indicadores/situacao",
  producao: "/indicadores",
  desistencias: "/indicadores/desistencias",
  bancas: "/indicadores/bancas",
};
// a ordem das colunas da ficha (CA-01 do RBN13.05)
const PAPEIS: [PapelBanca, string][] = (["ORIENTADOR", "AVALIADOR", "COORIENTADOR", "SUPLENTE"] as const).map(
  (p) => [p, NOME_PAPEL_BANCA[p]],
);

type Dados =
  | { aba: "situacao"; corpo: IndicadorSituacao }
  | { aba: "producao"; corpo: IndicadorProducao }
  | { aba: "desistencias"; corpo: IndicadorDesistencias }
  | { aba: "bancas"; corpo: IndicadorBancas };

// Os parâmetros que cada aba manda: só os filtros que o perfil tem naquele indicador (o backend confere de novo).
function parametros(escopo: EscopoIndicadores, aba: IndicadorTel16, filtros: Filtros): string {
  const f = escopo.filtros_indicadores[aba];
  const permitido: Record<keyof Filtros, boolean> = {
    periodo: f.periodo,
    curso: f.curso,
    etapa: f.etapa,
    turma: f.turma,
    orientador: f.orientador,
    professor: f.professor,
    papel: f.papel,
    periodo_inicio: f.intervalo,
    periodo_fim: f.intervalo,
  };
  const pares = (Object.keys(filtros) as (keyof Filtros)[])
    .filter((k) => permitido[k] && filtros[k] !== "")
    .map((k) => [k, filtros[k]]);
  return new URLSearchParams(pares).toString();
}

// RBN13.06 (DS-FL08-D): o relatório leva os filtros escolhidos que valem em algum indicador; o backend aplica a cada
// indicador só os que ele tem, como as abas fazem.
function filtrosRelatorio(escopo: EscopoIndicadores, filtros: Filtros): Record<string, string | number> {
  const juntos: Record<string, string | number> = {};
  for (const [aba] of ABAS) {
    new URLSearchParams(parametros(escopo, aba, filtros)).forEach((valor, chave) => {
      juntos[chave] = chave === "etapa" || chave === "papel" ? valor : Number(valor);
    });
  }
  return juntos;
}

export default function PaginaIndicadores() {
  const [escopo, setEscopo] = useState<EscopoIndicadores | null>(null);
  const [aba, setAba] = useState<IndicadorTel16>("situacao");
  const [filtros, setFiltros] = useState<Filtros | null>(null);
  // a resposta guarda a aba e os filtros que a geraram: enquanto não chega a dos atuais, a tela está carregando
  const [resposta, setResposta] = useState<{ chave: string; dados: Dados } | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<EscopoIndicadores>("/indicadores/escopo")
      .then((e) => {
        setEscopo(e);
        setFiltros({ periodo: e.periodo_vigente_id ? String(e.periodo_vigente_id) : "", ...VAZIO }); // CA-05
      })
      .catch((e: ErroApi) => setErro(e.message));
  }, []);

  const consulta = escopo && filtros ? parametros(escopo, aba, filtros) : null;
  const chave = consulta === null ? null : `${aba}?${consulta}`;

  // H1: os números acompanham cada filtro, sem botão de aplicar
  useEffect(() => {
    if (chave === null || consulta === null) return;
    const pedido = aba;
    api<unknown>(`${ROTA[pedido]}${consulta ? `?${consulta}` : ""}`)
      .then((corpo) => {
        const dados = (
          pedido === "producao"
            ? { aba: pedido, corpo: (corpo as PainelIndicadores).producao }
            : { aba: pedido, corpo }
        ) as Dados;
        setResposta({ chave, dados });
        setErro("");
      })
      .catch((e: ErroApi) => setErro(e.message));
  }, [chave, consulta, aba]);
  const dados = resposta?.chave === chave ? resposta.dados : null;

  const mudar = (campo: keyof Filtros) => (e: React.ChangeEvent<HTMLSelectElement>) =>
    setFiltros((f) => (f ? { ...f, [campo]: e.target.value } : f));
  const limpar = () =>
    setFiltros({ periodo: escopo?.periodo_vigente_id ? String(escopo.periodo_vigente_id) : "", ...VAZIO });

  const [gerando, setGerando] = useState(false);
  const [pdf, setPdf] = useState<{ tipo: "sucesso" | "erro"; texto: string } | null>(null);
  async function gerarPdf() {
    if (!escopo || !filtros) return;
    setPdf(null);
    setGerando(true);
    try {
      await baixarPdf("/indicadores/relatorio", "relatorio-indicadores.pdf", filtrosRelatorio(escopo, filtros));
      setPdf({ tipo: "sucesso", texto: "Relatório em PDF gerado com os filtros atuais." });
    } catch (e) {
      setPdf({ tipo: "erro", texto: (e as ErroApi).message });
    }
    setGerando(false);
  }

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold tracking-widest text-suave uppercase">Gestão</p>
          <h1 className="text-2xl font-semibold">Indicadores</h1>
          <p className="mt-1 text-sm text-suave">
            Acompanhe os TCCs dentro do seu escopo. Os indicadores não mostram nomes de alunos.
          </p>
        </div>
        {escopo && filtros && (
          <Botao
            variante="contorno"
            onClick={gerarPdf}
            disabled={gerando || !dados}
            title="Situação, produção científica, desistências e bancas, com os filtros escolhidos"
          >
            <Icone nome="documento" className="size-4" />
            {gerando ? "Gerando…" : "Gerar relatório em PDF"}
          </Botao>
        )}
      </header>
      {pdf && <Aviso tipo={pdf.tipo}>{pdf.texto}</Aviso>}

      {erro && !escopo ? (
        <Aviso tipo="erro">{erro}</Aviso>
      ) : !escopo || !filtros ? (
        <p role="status" className="text-sm text-suave">
          Carregando…
        </p>
      ) : (
        <>
          <div role="tablist" aria-label="Indicador" className="flex gap-1 overflow-x-auto border-b border-borda">
            {ABAS.map(([valor, rotulo]) => (
              <button
                key={valor}
                role="tab"
                aria-selected={aba === valor}
                onClick={() => setAba(valor)}
                className={`-mb-px shrink-0 border-b-2 px-4 py-2 text-sm font-medium ${
                  aba === valor ? "border-azul text-azul-forte" : "border-transparent text-suave hover:text-texto"
                }`}
              >
                {rotulo}
              </button>
            ))}
          </div>

          <PainelFiltros escopo={escopo} aba={aba} filtros={filtros} mudar={mudar} />

          {erro && <Aviso tipo="erro">{erro}</Aviso>}
          <div role="tabpanel" aria-live="polite" aria-busy={!dados}>
            {!dados ? (
              <p role="status" className="text-sm text-suave">
                Carregando…
              </p>
            ) : dados.corpo.sem_dados && dados.aba !== "desistencias" ? (
              <SemDados aba={dados.aba} limpar={limpar} />
            ) : dados.aba === "situacao" ? (
              <Resultados dados={dados.corpo} />
            ) : dados.aba === "producao" ? (
              <Producao dados={dados.corpo} />
            ) : dados.aba === "desistencias" ? (
              <Desistencias dados={dados.corpo} limpar={limpar} />
            ) : (
              <Bancas dados={dados.corpo} />
            )}
          </div>
        </>
      )}
    </div>
  );
}

function PainelFiltros({
  escopo,
  aba,
  filtros,
  mudar,
}: {
  escopo: EscopoIndicadores;
  aba: IndicadorTel16;
  filtros: Filtros;
  mudar: (campo: keyof Filtros) => (e: React.ChangeEvent<HTMLSelectElement>) => void;
}) {
  const f = escopo.filtros_indicadores[aba];
  // o período da evolução é o intervalo; os demais filtros valem para os totais do período escolhido
  return (
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
        {f.curso && (
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
        {f.etapa && (
          <Campo rotulo="Etapa">
            <Selecao value={filtros.etapa} onChange={mudar("etapa")}>
              <option value="">TCC1 e TCC2</option>
              <option value="TCC1">TCC1</option>
              <option value="TCC2">TCC2</option>
            </Selecao>
          </Campo>
        )}
        {f.turma && (
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
        {f.orientador && (
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
        {f.professor && (
          <Campo rotulo="Professor">
            <Selecao value={filtros.professor} onChange={mudar("professor")}>
              <option value="">Todos</option>
              {escopo.professores.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nome}
                </option>
              ))}
            </Selecao>
          </Campo>
        )}
        {f.papel && (
          <Campo rotulo="Papel na banca">
            <Selecao value={filtros.papel} onChange={mudar("papel")}>
              <option value="">Todos</option>
              {PAPEIS.map(([valor, rotulo]) => (
                <option key={valor} value={valor}>
                  {rotulo}
                </option>
              ))}
            </Selecao>
          </Campo>
        )}
        {f.intervalo && (
          <>
            <Campo rotulo="Evolução: de">
              <Selecao value={filtros.periodo_inicio} onChange={mudar("periodo_inicio")}>
                <option value="">O mais antigo</option>
                {[...escopo.periodos].reverse().map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.codigo}
                  </option>
                ))}
              </Selecao>
            </Campo>
            <Campo rotulo="Evolução: até">
              <Selecao value={filtros.periodo_fim} onChange={mudar("periodo_fim")}>
                <option value="">O mais recente</option>
                {[...escopo.periodos].reverse().map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.codigo}
                  </option>
                ))}
              </Selecao>
            </Campo>
          </>
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
        {aba === "bancas"
          ? "A coordenação vê todos os professores; os demais perfis, só as próprias participações."
          : "Quem tem mais de um perfil vê a soma dos escopos; cada TCC é contado uma única vez."}
      </p>
    </section>
  );
}

const SEM_DADOS: Record<IndicadorTel16, string> = {
  situacao: "Não há TCCs no período e nos filtros escolhidos.",
  producao: "Não há artigos com publicação registrada no período e nos filtros escolhidos.",
  desistencias: "Não há desistências no período e nos filtros escolhidos.",
  bancas: "Não há participações em bancas realizadas no período e nos filtros escolhidos.",
};

function SemDados({ aba, limpar }: { aba: IndicadorTel16; limpar: () => void }) {
  return (
    <div className="rounded-xl border border-borda bg-superficie p-6 text-sm">
      <p className="font-medium">Sem dados para este filtro</p>
      <p className="mt-1 text-suave">{SEM_DADOS[aba]}</p>
      <div className="mt-3">
        <Botao variante="contorno" pequeno onClick={limpar}>
          Limpar filtros
        </Botao>
      </div>
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

// SCRUM-90 · RBN13.03: artigos por situação editorial (só modalidade artigo; cada TCC uma vez)
function Producao({ dados }: { dados: IndicadorProducao }) {
  const de = (s: string) => dados.situacoes.find((x) => x.situacao === s)?.total ?? 0;
  return (
    <div className="flex flex-col gap-5">
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label="Destaques">
        {(["SUBMETIDO", "EM_REVISAO", "ACEITO", "PUBLICADO"] as const).map((s) => (
          <Destaque key={s} rotulo={NOME_SITUACAO_EDITORIAL[s]} valor={de(s)} />
        ))}
      </ul>
      <section className="rounded-xl border border-borda bg-superficie p-5" aria-labelledby="titulo-producao">
        <h2 id="titulo-producao" className="font-semibold">
          Artigos por situação editorial
        </h2>
        <p className="mb-3 text-[13px] text-suave">
          Só TCCs da modalidade artigo. Cada TCC conta uma vez, pela submissão mais recente.
        </p>
        <TabelaSimples
          rotulo="Situação editorial"
          coluna="Artigos"
          linhas={dados.situacoes.map((s) => [NOME_SITUACAO_EDITORIAL[s.situacao] ?? s.situacao, s.total])}
          total={dados.total}
        />
      </section>
    </div>
  );
}

// SCRUM-91 · RBN13.04: total por período e curso; a evolução só vem para a coordenação
function Desistencias({ dados, limpar }: { dados: IndicadorDesistencias; limpar: () => void }) {
  return (
    <div className="flex flex-col gap-5">
      {dados.sem_dados ? (
        <SemDados aba="desistencias" limpar={limpar} />
      ) : (
        <>
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label="Destaques">
            <Destaque rotulo="Desistências no período" valor={dados.total} />
          </ul>
          <section className="rounded-xl border border-borda bg-superficie p-5" aria-labelledby="titulo-por-curso">
            <h2 id="titulo-por-curso" className="font-semibold">
              Desistências por curso
            </h2>
            <p className="mb-3 text-[13px] text-suave">Só TCCs em desistência; reprovados não entram.</p>
            <TabelaSimples
              rotulo="Curso"
              coluna="Desistências"
              linhas={dados.por_curso.map((c) => [c.curso.nome, c.total])}
              total={dados.total}
            />
          </section>
        </>
      )}
      {dados.evolucao && (
        <section className="rounded-xl border border-borda bg-superficie p-5" aria-labelledby="titulo-evolucao">
          <h2 id="titulo-evolucao" className="font-semibold">
            Evolução por período
          </h2>
          <p className="mb-3 text-[13px] text-suave">
            Desistências em cada período letivo do intervalo escolhido nos filtros.
          </p>
          {dados.evolucao.length === 0 ? (
            <p className="text-sm text-suave">Nenhum período letivo no intervalo.</p>
          ) : (
            <TabelaSimples
              rotulo="Período letivo"
              coluna="Desistências"
              linhas={dados.evolucao.map((e) => [`${e.periodo.codigo}${e.periodo.vigente ? " (vigente)" : ""}`, e.total])}
              total={Math.max(...dados.evolucao.map((e) => e.total))}
            />
          )}
        </section>
      )}
    </div>
  );
}

// SCRUM-92 · RBN13.05: participações por professor e por papel
function Bancas({ dados }: { dados: IndicadorBancas }) {
  const total = (n: Record<PapelBanca, number>) => PAPEIS.reduce((s, [p]) => s + n[p], 0);
  return (
    <section className="rounded-xl border border-borda bg-superficie p-5" aria-labelledby="titulo-bancas">
      <h2 id="titulo-bancas" className="font-semibold">
        Participações em banca
      </h2>
      <p className="mb-3 text-[13px] text-suave">
        Só bancas de defesas realizadas e docentes da UEA. O suplente conta apenas quando é convocado.
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-borda text-left text-[13px] text-suave">
              <th scope="col" className="py-2 pr-3 font-medium">
                Professor
              </th>
              {PAPEIS.map(([p, rotulo]) => (
                <th key={p} scope="col" className="py-2 pr-3 text-right font-medium">
                  {rotulo}
                </th>
              ))}
              <th scope="col" className="py-2 text-right font-medium">
                Total
              </th>
            </tr>
          </thead>
          <tbody>
            {dados.professores.map((linha) => (
              <tr key={linha.professor.id} className="border-b border-borda last:border-0">
                <th scope="row" className="py-2 pr-3 text-left font-normal break-words">
                  {linha.professor.nome}
                </th>
                {PAPEIS.map(([p]) => (
                  <td key={p} className="py-2 pr-3 text-right tabular-nums">
                    {linha.total[p]}
                  </td>
                ))}
                <td className="py-2 text-right font-medium tabular-nums">{total(linha.total)}</td>
              </tr>
            ))}
          </tbody>
          {dados.professores.length > 1 && (
            <tfoot>
              <tr className="border-t border-borda font-medium">
                <th scope="row" className="py-2 pr-3 text-left">
                  Total
                </th>
                {PAPEIS.map(([p]) => (
                  <td key={p} className="py-2 pr-3 text-right tabular-nums">
                    {dados.total[p]}
                  </td>
                ))}
                <td className="py-2 text-right tabular-nums">{total(dados.total)}</td>
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </section>
  );
}

function Destaque({ rotulo, valor }: { rotulo: string; valor: number }) {
  return (
    <li className="rounded-xl border border-borda bg-superficie p-4">
      <p className="text-[13px] text-suave">{rotulo}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{valor}</p>
    </li>
  );
}

// Tabela com barras curtas: o número é o dado; a barra só ajuda a comparar (H8, sem enfeite).
function Barra({ n, total }: { n: number; total: number }) {
  return (
    <span className="flex items-center gap-2">
      <span className="w-6 text-right tabular-nums">{n}</span>
      <span aria-hidden="true" className="h-2 w-20 overflow-hidden rounded-full bg-fundo sm:w-28">
        <span className="block h-full rounded-full bg-azul" style={{ width: `${total ? (n / total) * 100 : 0}%` }} />
      </span>
    </span>
  );
}

function Tabela({ rotulo, linhas, maximo }: { rotulo: string; linhas: [string, PorEtapa][]; maximo: PorEtapa }) {
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
              <td className="py-2 pr-3">
                <Barra n={t.TCC1} total={maximo.TCC1} />
              </td>
              <td className="py-2">
                <Barra n={t.TCC2} total={maximo.TCC2} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TabelaSimples({
  rotulo,
  coluna,
  linhas,
  total,
}: {
  rotulo: string;
  coluna: string;
  linhas: [string, number][];
  total: number;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-borda text-left text-[13px] text-suave">
            <th scope="col" className="py-2 pr-3 font-medium">
              {rotulo}
            </th>
            <th scope="col" className="py-2 font-medium">
              {coluna}
            </th>
          </tr>
        </thead>
        <tbody>
          {linhas.map(([nome, n]) => (
            <tr key={nome} className="border-b border-borda last:border-0">
              <th scope="row" className="py-2 pr-3 text-left font-normal break-words">
                {nome}
              </th>
              <td className="py-2">
                <Barra n={n} total={total} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
