"use client";

// TEL07 · Análise de cadastros, seguindo os diagramas:
//   DS-FL02-A  GET  /cadastros?situacao=EM_ANALISE[&curso=]        fila, do mais antigo para o mais recente
//              GET  /cadastros/{id}                                 dados, PDF e a decisão já registrada
//              GET  /cadastros/{id}/documento                       abrir o PDF
//              GET  /cadastros?situacao=APROVADO,DEVOLVIDO,REPROVADO aba "Já analisados"
//   DS-FL02    POST /cadastros/{id}/decisao                         aprovar, devolver ou reprovar
//              (403 sem perfil Coordenação; 409 outra pessoa já decidiu; 422 sem parecer)
// Os filtros de período e de situação (RBN04.01 CA-02 e CA-03) vão nos mesmos GET.

import { useCallback, useEffect, useState } from "react";
import { Aviso, Selo, type TipoAviso } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Campo, ESTILO_ENTRADA, Selecao } from "@/components/campo";
import { Icone } from "@/components/icone";
import { Modal } from "@/components/modal";
import { SeloSituacao } from "@/components/situacao-tcc";
import { api, ErroApi } from "@/lib/api";
import {
  dataHora,
  NOME_SITUACAO_TCC,
  type Cadastro,
  type CadastroResumo,
  type Curso,
  type Decisao,
  type Periodo,
  type ResultadoAnalise,
} from "@/lib/tipos";

type Aba = "fila" | "analisados";
type Filtros = { curso: string; periodo: string; situacao: string };

const ANALISADOS = "APROVADO,DEVOLVIDO,REPROVADO";
const MINIMO_PARECER = 10;

// Janela de confirmação e mensagem de cada decisão (TEL07)
const CONFIRMACAO: Record<
  ResultadoAnalise,
  { titulo: string; texto: React.ReactNode; botao: string; perigo: boolean; mensagem: string }
> = {
  APROVADO: {
    titulo: "Aprovar este cadastro?",
    texto: "O aluno e o orientador serão avisados por e-mail. A banca e a defesa serão tratadas depois.",
    botao: "Aprovar",
    perigo: false,
    mensagem: "Cadastro aprovado.",
  },
  DEVOLVIDO: {
    titulo: "Devolver para correção?",
    texto: "O aluno receberá o seu parecer e poderá corrigir e reenviar. O protocolo é mantido.",
    botao: "Devolver",
    perigo: false,
    mensagem: "Cadastro devolvido ao aluno.",
  },
  REPROVADO: {
    titulo: "Reprovar este cadastro?",
    texto: (
      <>
        <strong>Esta decisão encerra o cadastro.</strong> O aluno será avisado com a sua justificativa. Confirme
        apenas se for definitiva.
      </>
    ),
    botao: "Reprovar cadastro",
    perigo: true,
    mensagem: "Cadastro reprovado.",
  },
};

function consulta(situacao: string, f: Filtros) {
  const p = new URLSearchParams({ situacao });
  if (f.curso) p.set("curso", f.curso);
  if (f.periodo) p.set("periodo", f.periodo);
  return `/cadastros?${p}`;
}

export default function PaginaAnalise() {
  const [aba, setAba] = useState<Aba>("fila");
  const [filtros, setFiltros] = useState<Filtros>({ curso: "", periodo: "", situacao: "" });
  const [cursos, setCursos] = useState<Curso[]>([]);
  const [periodos, setPeriodos] = useState<Periodo[]>([]);
  const [fila, setFila] = useState<CadastroResumo[] | null>(null);
  const [analisados, setAnalisados] = useState<CadastroResumo[] | null>(null);
  const [contagem, setContagem] = useState({ fila: 0, analisados: 0 });
  const [selecionado, setSelecionado] = useState<number | null>(null);
  const [aberto, setAberto] = useState<number | null>(null); // cadastro já analisado aberto para consulta
  const [aviso, setAviso] = useState<{ tipo: TipoAviso; texto: string } | null>(null);
  const [erroCarga, setErroCarga] = useState("");

  useEffect(() => {
    api<Curso[]>("/cursos").then(setCursos).catch(() => {});
    api<Periodo[]>("/periodos").then(setPeriodos).catch(() => {});
  }, []);

  // Recarrega as duas listas: a decisão mais recente aparece antes de qualquer nova decisão (RBN04.01 CA-05).
  const carregar = useCallback(async (f: Filtros) => {
    try {
      const [naFila, feitos, todosNaFila, todosFeitos] = await Promise.all([
        api<CadastroResumo[]>(consulta("EM_ANALISE", { ...f, situacao: "" })),
        api<CadastroResumo[]>(consulta(f.situacao || ANALISADOS, f)),
        api<CadastroResumo[]>("/cadastros?situacao=EM_ANALISE"),
        api<CadastroResumo[]>(`/cadastros?situacao=${ANALISADOS}`),
      ]);
      setFila(naFila);
      setAnalisados(feitos);
      setContagem({ fila: todosNaFila.length, analisados: todosFeitos.length });
      setErroCarga("");
      return naFila;
    } catch (e) {
      setErroCarga((e as ErroApi).message);
      return null;
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- busca na API ao trocar os filtros
    carregar(filtros);
  }, [carregar, filtros]);

  const filtrando = Boolean(filtros.curso || filtros.periodo || (aba === "analisados" && filtros.situacao));

  function mudarFiltro(campo: keyof Filtros, valor: string) {
    setFiltros((f) => ({ ...f, [campo]: valor }));
  }

  async function aposDecidir(mensagem: string, decidido: number) {
    const nova = (await carregar(filtros)) ?? [];
    const proximo = nova.find((c) => c.id !== decidido) ?? null;
    setSelecionado(proximo?.id ?? null);
    setAviso({
      tipo: "sucesso",
      texto: `${mensagem}${proximo ? ` Próximo da fila: ${proximo.aluno.nome}.` : " A fila está vazia."}`,
    });
  }

  return (
    <div className="flex flex-col gap-5">
      <header>
        <h1 className="text-2xl font-semibold">Análise de cadastros</h1>
        <p className="mt-1 text-sm text-suave">
          Analise os cadastros enviados: aprove, devolva para correção ou reprove. Aprovar o cadastro não aprova a
          defesa nem o artigo.
        </p>
      </header>

      <div role="tablist" className="flex gap-1 border-b border-borda">
        {(
          [
            ["fila", `Aguardando análise (${contagem.fila})`],
            ["analisados", `Já analisados (${contagem.analisados})`],
          ] as const
        ).map(([valor, rotulo]) => (
          <button
            key={valor}
            role="tab"
            aria-selected={aba === valor}
            onClick={() => {
              setAba(valor);
              setAberto(null);
            }}
            className={`-mb-px shrink-0 border-b-2 px-4 py-2 text-sm font-medium ${
              aba === valor ? "border-azul text-azul-forte" : "border-transparent text-suave hover:text-texto"
            }`}
          >
            {rotulo}
          </button>
        ))}
      </div>

      {aviso && <Aviso tipo={aviso.tipo}>{aviso.texto}</Aviso>}
      {erroCarga && <Aviso tipo="erro">{erroCarga}</Aviso>}

      <div className="flex flex-wrap items-end gap-3" role="group" aria-label="Filtros">
        <Campo rotulo="Curso" className="w-full sm:w-56">
          <Selecao value={filtros.curso} onChange={(e) => mudarFiltro("curso", e.target.value)}>
            <option value="">Todos os cursos</option>
            {cursos.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
              </option>
            ))}
          </Selecao>
        </Campo>
        <Campo rotulo="Período letivo" className="w-full sm:w-40">
          <Selecao value={filtros.periodo} onChange={(e) => mudarFiltro("periodo", e.target.value)}>
            <option value="">Todos</option>
            {periodos.map((p) => (
              <option key={p.id} value={p.codigo}>
                {p.codigo}
              </option>
            ))}
          </Selecao>
        </Campo>
        {aba === "analisados" && (
          <Campo rotulo="Situação" className="w-full sm:w-56">
            <Selecao value={filtros.situacao} onChange={(e) => mudarFiltro("situacao", e.target.value)}>
              <option value="">Todas as decisões</option>
              {(["APROVADO", "DEVOLVIDO", "REPROVADO"] as const).map((s) => (
                <option key={s} value={s}>
                  {NOME_SITUACAO_TCC[s]}
                </option>
              ))}
            </Selecao>
          </Campo>
        )}
        {filtrando && (
          <Botao variante="texto" onClick={() => setFiltros({ curso: "", periodo: "", situacao: "" })}>
            Limpar filtros
          </Botao>
        )}
      </div>

      {aba === "fila" ? (
        <Fila
          fila={fila}
          filtrando={Boolean(filtros.curso || filtros.periodo)}
          selecionado={selecionado}
          selecionar={(id) => {
            setAviso(null);
            setSelecionado(id);
          }}
          limpar={() => setFiltros({ curso: "", periodo: "", situacao: "" })}
          aposDecidir={aposDecidir}
          aposConflito={(texto) => {
            setAviso({ tipo: "erro", texto });
            carregar(filtros);
          }}
        />
      ) : (
        aberto !== null ? (
          // DS-FL02-A, cadastro já decidido: os dados, o PDF e a decisão registrada, sem os botões
          <Detalhe
            key={aberto}
            id={aberto}
            rotuloVoltar="Voltar aos já analisados"
            voltar={() => setAberto(null)}
            aposDecidir={aposDecidir}
            aposConflito={(texto) => setAviso({ tipo: "erro", texto })}
          />
        ) : (
          <JaAnalisados lista={analisados} filtrando={filtrando} abrir={setAberto} />
        )
      )}
    </div>
  );
}

// ---------------------------------------------------------------- aba "Aguardando análise"

function Fila({
  fila,
  filtrando,
  selecionado,
  selecionar,
  limpar,
  aposDecidir,
  aposConflito,
}: {
  fila: CadastroResumo[] | null;
  filtrando: boolean;
  selecionado: number | null;
  selecionar: (id: number | null) => void;
  limpar: () => void;
  aposDecidir: (mensagem: string, decidido: number) => void;
  aposConflito: (texto: string) => void;
}) {
  if (!fila)
    return (
      <p role="status" className="text-sm text-suave">
        Carregando…
      </p>
    );
  if (fila.length === 0 && selecionado === null)
    return (
      <div className="flex flex-col items-center gap-2 rounded-xl border border-borda bg-superficie p-8 text-center">
        <Icone nome="certo" className="size-6 text-verde" />
        <p className="font-medium">Nenhum cadastro aguardando análise</p>
        <p className="text-sm text-suave">
          {filtrando
            ? "Não há cadastros deste curso ou período na fila."
            : "Tudo em dia. Novos cadastros enviados pelos alunos aparecem aqui."}
        </p>
        {filtrando && (
          <Botao variante="contorno" pequeno onClick={limpar}>
            Ver todos os cursos
          </Botao>
        )}
      </div>
    );

  return (
    <div className="flex flex-col gap-2">
      <p className={`text-[13px] text-suave ${selecionado ? "hidden lg:block" : ""}`}>
        Ordenados do mais antigo para o mais recente.
      </p>
      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
        <div className={selecionado ? "hidden lg:block" : ""}>
          <ul className="flex flex-col gap-2">
            {fila.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => selecionar(c.id)}
                  aria-current={selecionado === c.id}
                  className={`w-full rounded-xl border bg-superficie p-3 text-left hover:border-azul ${
                    selecionado === c.id ? "border-azul ring-1 ring-azul" : "border-borda"
                  }`}
                >
                  <p className="font-medium break-words">{c.titulo}</p>
                  <p className="text-[13px] text-suave">
                    {c.aluno.nome} · {c.curso.sigla} · {c.etapa}
                  </p>
                  <p className="mt-1.5 flex items-center gap-1.5 text-[13px]">
                    <Icone nome="relogio" className="size-3.5 text-suave" />
                    {c.dias_aguardando >= 5 ? (
                      <Selo cor="ambar">Aguarda há {c.dias_aguardando} dias</Selo>
                    ) : (
                      <Selo cor="cinza">
                        {c.dias_aguardando === 0
                          ? "Enviado hoje"
                          : `Enviado há ${c.dias_aguardando} ${c.dias_aguardando === 1 ? "dia" : "dias"}`}
                      </Selo>
                    )}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        </div>
        <div className={selecionado ? "" : "hidden lg:block"}>
          {selecionado === null ? (
            <section className="flex flex-col items-center gap-2 rounded-xl border border-borda bg-superficie p-8 text-center">
              <p className="font-medium">Selecione um cadastro</p>
              <p className="text-sm text-suave">Escolha um item da fila para ver os dados, o PDF e registrar o parecer.</p>
            </section>
          ) : (
            <Detalhe
              key={selecionado}
              id={selecionado}
              voltar={() => selecionar(null)}
              aposDecidir={aposDecidir}
              aposConflito={aposConflito}
            />
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- detalhe e decisão

function Detalhe({
  id,
  rotuloVoltar = "Voltar à fila",
  voltar,
  aposDecidir,
  aposConflito,
}: {
  id: number;
  rotuloVoltar?: string;
  voltar: () => void;
  aposDecidir: (mensagem: string, decidido: number) => void;
  aposConflito: (texto: string) => void;
}) {
  const [cadastro, setCadastro] = useState<Cadastro | null>(null);
  const [erro, setErro] = useState("");
  const [parecer, setParecer] = useState("");
  const [erroParecer, setErroParecer] = useState("");
  const [confirmando, setConfirmando] = useState<ResultadoAnalise | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [erroPdf, setErroPdf] = useState("");

  const abrir = useCallback(() => {
    api<Cadastro>(`/cadastros/${id}`)
      .then(setCadastro)
      .catch((e: ErroApi) => setErro(e.message));
  }, [id]);

  useEffect(abrir, [abrir]);

  if (erro) return <Aviso tipo="erro">{erro}</Aviso>;
  if (!cadastro)
    return (
      <p role="status" className="text-sm text-suave">
        Carregando…
      </p>
    );

  const { tcc, documento, decisao } = cadastro;
  const emAnalise = tcc.situacao === "EM_ANALISE";

  // DS-FL02 passo 2: devolver ou reprovar pede parecer de pelo menos 10 caracteres
  function pedir(resultado: ResultadoAnalise) {
    if (resultado !== "APROVADO" && parecer.trim().length < MINIMO_PARECER) {
      setErroParecer(
        resultado === "DEVOLVIDO"
          ? "Explique o que o aluno precisa corrigir (mínimo de 10 caracteres)."
          : "Justifique a reprovação (mínimo de 10 caracteres).",
      );
      document.getElementById("parecer")?.focus();
      return;
    }
    setErroParecer("");
    setConfirmando(resultado);
  }

  async function confirmar() {
    if (!confirmando) return;
    setEnviando(true);
    try {
      await api<Decisao>(`/cadastros/${id}/decisao`, {
        metodo: "POST",
        corpo: { resultado: confirmando, parecer: parecer.trim() },
      });
      const mensagem = CONFIRMACAO[confirmando].mensagem;
      setConfirmando(null);
      aposDecidir(mensagem, id);
    } catch (e) {
      const falha = e as ErroApi;
      setConfirmando(null);
      if (falha.status === 409) {
        abrir(); // mostra a decisão existente
        aposConflito(falha.message);
      } else if (falha.campos?.parecer) {
        setErroParecer(falha.campos.parecer);
      } else {
        setErro(falha.message);
      }
    }
    setEnviando(false);
  }

  async function abrirPdf() {
    setErroPdf("");
    try {
      const resposta = await fetch(`/api/v1/cadastros/${id}/documento`);
      if (!resposta.ok) throw new Error((await resposta.json().catch(() => null))?.detail ?? "Não foi possível abrir o PDF.");
      window.open(URL.createObjectURL(await resposta.blob()), "_blank", "noopener");
    } catch (e) {
      setErroPdf((e as Error).message);
    }
  }

  const orientador = tcc.orientador?.status === "ACEITA" ? tcc.orientador.professor.nome : "—";

  return (
    <section aria-labelledby="titulo-cadastro" className="flex flex-col gap-4 rounded-xl border border-borda bg-superficie p-5">
      <div>
        <Botao variante="texto" pequeno onClick={voltar}>
          <Icone nome="voltar" className="size-4" /> {rotuloVoltar}
        </Botao>
      </div>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h2 id="titulo-cadastro" tabIndex={-1} className="text-lg font-semibold break-words">
            {tcc.titulo}
          </h2>
          <p className="text-sm text-suave">
            <span className="font-mono">{tcc.protocolo}</span> · enviado em {dataHora(tcc.submetido_em)}
          </p>
        </div>
        <SeloSituacao situacao={tcc.situacao} />
      </div>

      <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-[max-content_1fr]">
        <Item k="Autor(a)">
          {tcc.aluno.nome} · <span className="font-mono">{tcc.matricula}</span>
        </Item>
        <Item k="Curso · etapa">
          {tcc.curso.nome} · {tcc.etapa}
        </Item>
        <Item k="Modalidade">{tcc.modalidade === "ARTIGO" ? "Artigo" : "Monografia"}</Item>
        <Item k="Orientador">{orientador}</Item>
        <Item k="Resumo">{tcc.resumo || "—"}</Item>
        <Item k="Documento">
          {documento ? (
            <span className="flex flex-wrap items-center gap-2">
              <span className="font-mono">{documento.nome}</span>
              <Botao variante="contorno" pequeno onClick={abrirPdf}>
                <Icone nome="documento" className="size-4" /> Abrir PDF
              </Botao>
            </span>
          ) : (
            <span className="inline-flex items-center gap-1.5 font-medium text-vermelho">
              <Icone nome="alerta" className="size-4" /> Nenhum PDF enviado
            </span>
          )}
          {erroPdf && <span className="block text-[13px] text-vermelho">{erroPdf}</span>}
        </Item>
      </dl>

      {!emAnalise ? (
        // DS-FL02-A, já decidido por outra pessoa: a decisão registrada, sem os botões
        <DecisaoRegistrada decisao={decisao} situacao={NOME_SITUACAO_TCC[tcc.situacao]} />
      ) : (
        <>
          <Campo rotulo="Parecer da Coordenação" erro={erroParecer}>
            <textarea
              id="parecer"
              value={parecer}
              onChange={(e) => {
                setParecer(e.target.value);
                if (erroParecer) setErroParecer("");
              }}
              rows={4}
              maxLength={1000}
              aria-invalid={erroParecer ? true : undefined}
              aria-describedby="dica-parecer"
              className={`${ESTILO_ENTRADA} h-auto py-2 ${erroParecer ? "border-vermelho" : "border-borda"}`}
            />
            <span id="dica-parecer" className="text-[13px] text-suave">
              Obrigatório para devolver ou reprovar. Opcional para aprovar. ({parecer.length}/1000)
            </span>
          </Campo>
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:justify-between">
            <div className="flex flex-col gap-2 sm:flex-row">
              <Botao onClick={() => pedir("APROVADO")}>
                <Icone nome="certo" className="size-4" /> Aprovar cadastro
              </Botao>
              <Botao variante="contorno" onClick={() => pedir("DEVOLVIDO")}>
                <Icone nome="voltar" className="size-4" /> Devolver para correção
              </Botao>
            </div>
            <Botao variante="perigo" onClick={() => pedir("REPROVADO")}>
              <Icone nome="fechar" className="size-4" /> Reprovar
            </Botao>
          </div>
          <p className="text-[13px] text-suave">Aprovar o cadastro não aprova a defesa nem o artigo.</p>
        </>
      )}

      {confirmando && (
        <Modal titulo={CONFIRMACAO[confirmando].titulo} aoFechar={() => setConfirmando(null)}>
          <p className="text-sm">{CONFIRMACAO[confirmando].texto}</p>
          <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Botao variante="texto" onClick={() => setConfirmando(null)}>
              Cancelar
            </Botao>
            <Botao
              variante={CONFIRMACAO[confirmando].perigo ? "destrutivo" : "primario"}
              carregando={enviando}
              onClick={confirmar}
            >
              {CONFIRMACAO[confirmando].botao}
            </Botao>
          </div>
        </Modal>
      )}
    </section>
  );
}

function DecisaoRegistrada({ decisao, situacao }: { decisao: Decisao | null; situacao: string }) {
  if (!decisao) return <Aviso tipo="info">Este cadastro não está aguardando análise ({situacao}).</Aviso>;
  return (
    <Aviso tipo={decisao.resultado === "APROVADO" ? "sucesso" : decisao.resultado === "DEVOLVIDO" ? "alerta" : "erro"}>
      <p>
        <strong>Decisão registrada: {NOME_SITUACAO_TCC[decisao.resultado]}</strong> · {decisao.coordenador.nome} ·{" "}
        {dataHora(decisao.decidido_em)}
      </p>
      {decisao.parecer && <p className="mt-1 whitespace-pre-wrap">Parecer: {decisao.parecer}</p>}
    </Aviso>
  );
}

function Item({ k, children }: { k: string; children: React.ReactNode }) {
  return (
    <>
      <dt className="text-suave">{k}</dt>
      <dd className="break-words whitespace-pre-wrap">{children}</dd>
    </>
  );
}

// ---------------------------------------------------------------- aba "Já analisados"

function JaAnalisados({
  lista,
  filtrando,
  abrir,
}: {
  lista: CadastroResumo[] | null;
  filtrando: boolean;
  abrir: (id: number) => void;
}) {
  if (!lista)
    return (
      <p role="status" className="text-sm text-suave">
        Carregando…
      </p>
    );
  if (lista.length === 0)
    return (
      <p className="rounded-xl border border-borda bg-superficie p-6 text-sm text-suave">
        {filtrando ? "Nenhum cadastro encontrado com esses filtros." : "Nenhum cadastro analisado ainda."}
      </p>
    );
  return (
    <section className="rounded-xl border border-borda bg-superficie">
      <div className="hidden grid-cols-[10rem_minmax(0,1fr)_minmax(0,18rem)] gap-4 border-b border-borda px-4 py-2 text-[13px] font-medium text-suave sm:grid">
        <span>Protocolo</span>
        <span>Trabalho</span>
        <span>Resultado da análise</span>
      </div>
      <ul>
        {lista.map((c) => (
          <li key={c.id} className="border-b border-borda last:border-b-0">
            <button
              type="button"
              onClick={() => abrir(c.id)}
              aria-label={`Ver o cadastro ${c.protocolo}: ${c.titulo}`}
              className="grid w-full gap-1 px-4 py-3 text-left hover:bg-fundo sm:grid-cols-[10rem_minmax(0,1fr)_minmax(0,18rem)] sm:gap-4"
            >
              <span className="font-mono text-sm">{c.protocolo}</span>
              <span className="block min-w-0">
                <span className="block font-medium break-words">{c.titulo}</span>
                <span className="block text-[13px] text-suave">
                  {c.aluno.nome} · {c.curso.sigla} · {c.periodo}
                </span>
                <span className="mt-1 block text-[13px] font-medium text-azul-forte">Ver cadastro e PDF</span>
              </span>
              <span className="block min-w-0">
                <SeloSituacao situacao={c.situacao} />
                {c.decisao?.parecer && (
                  <span className="mt-1 block text-[13px] break-words text-suave">{c.decisao.parecer}</span>
                )}
                {c.decisao && (
                  <span className="block text-[12px] text-suave">
                    {c.decisao.coordenador.nome} · {dataHora(c.decisao.decidido_em)}
                  </span>
                )}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
