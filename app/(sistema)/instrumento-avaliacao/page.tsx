"use client";

// TEL20 · Instrumento de avaliação, seguindo o diagrama DS-FL06-G:
//   passo 2  GET /instrumento-avaliacao   versão vigente, histórico de versões (data e autor) e a estrutura:
//                                          componentes (escrita 7,0; oral 3,0), critérios, pesos e os
//                                          três conceitos com faixas e textos
//   passo 6  PUT /instrumento-avaliacao   {componentes, critérios, pesos, conceitos}
//            (403 sem perfil Coordenação; 422 pesos não fecham 7,0 e 3,0; 409 outra pessoa salvou antes)
// A coordenação altera critérios, pesos ou textos dos conceitos (passo 5). Os componentes e as faixas
// dos conceitos são fixos.

import { useCallback, useEffect, useState } from "react";
import { Aviso, Selo, type TipoAviso } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Campo, Entrada } from "@/components/campo";
import { Icone } from "@/components/icone";
import { api, ErroApi } from "@/lib/api";
import { useSessao } from "@/lib/sessao";
import {
  dataHora,
  type ComponenteAvaliacao,
  type ConsultaInstrumento,
  type CriterioEntrada,
  type FaixaConceito,
  type InstrumentoAvaliacao,
  type SomaIncorreta,
} from "@/lib/tipos";

// Critério em edição: "chave" só existe na tela, para o React acompanhar cada linha.
type Rascunho = CriterioEntrada & { chave: string };
type ErrosCriterio = Partial<Record<keyof CriterioEntrada, string>>;

const TEXTOS = [
  ["texto_exemplar", "EXEMPLAR"],
  ["texto_competente", "COMPETENTE"],
  ["texto_necessita", "NECESSITA"],
] as const;

const COR_CONCEITO = { EXEMPLAR: "verde", COMPETENTE: "azul", NECESSITA: "ambar" } as const;

let proximaChave = 0;
const novaChave = () => `c${++proximaChave}`;

// 0.5 -> "0,5" e 2 -> "2,0" (pontos e pesos como na planilha da coordenação)
function numero(valor: number, casas = 1) {
  return valor.toLocaleString("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: 2 });
}

// "0,5" ou "0.5" -> 0.5; texto inválido -> NaN
function lerPeso(texto: string) {
  const limpo = texto.trim().replace(",", ".");
  return /^\d+(\.\d{1,2})?$/.test(limpo) ? Number(limpo) : NaN;
}

function paraRascunho(c: ComponenteAvaliacao): Rascunho[] {
  return c.criterios.map((k) => ({
    chave: novaChave(),
    nome: k.nome,
    peso: numero(k.peso),
    texto_exemplar: k.texto_exemplar,
    texto_competente: k.texto_competente,
    texto_necessita: k.texto_necessita,
  }));
}

export default function PaginaInstrumento() {
  const { tem } = useSessao();
  const coordenador = tem("coordenador"); // a API confere de novo (403 para os demais, CA-06)
  const [dados, setDados] = useState<ConsultaInstrumento | null>(null);
  const [erroCarga, setErroCarga] = useState("");
  const [editando, setEditando] = useState(false);
  const [aviso, setAviso] = useState<{ tipo: TipoAviso; texto: string } | null>(null);

  const carregar = useCallback(async () => {
    try {
      setDados(await api<ConsultaInstrumento>("/instrumento-avaliacao")); // passo 2
      setErroCarga("");
    } catch (e) {
      setErroCarga((e as ErroApi).message);
    }
  }, []);

  useEffect(() => {
    if (!coordenador) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- busca na API ao abrir a tela
    carregar();
  }, [coordenador, carregar]);

  if (!coordenador) {
    return <Aviso tipo="alerta">Esta tela é exclusiva da coordenação.</Aviso>;
  }

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold">Instrumento de avaliação</h1>
          <p className="mt-1 text-sm text-suave">
            Critérios, pesos e conceitos usados pela banca para avaliar as defesas. A primeira avaliação de cada
            defesa fica presa à versão vigente naquele momento.
          </p>
        </div>
        {dados && !editando && (
          <Botao
            onClick={() => {
              setAviso(null);
              setEditando(true);
            }}
          >
            <Icone nome="lapis" className="size-4" /> Editar instrumento
          </Botao>
        )}
      </header>

      {aviso && <Aviso tipo={aviso.tipo}>{aviso.texto}</Aviso>}
      {erroCarga && <Aviso tipo="erro">{erroCarga}</Aviso>}

      {!dados ? (
        !erroCarga && (
          <p role="status" className="text-sm text-suave">
            Carregando…
          </p>
        )
      ) : editando ? (
        <Edicao
          instrumento={dados.instrumento}
          cancelar={() => setEditando(false)}
          aposSalvar={async (texto) => {
            setEditando(false);
            await carregar();
            setAviso({ tipo: "sucesso", texto });
          }}
          aposConflito={async (texto) => {
            setEditando(false);
            await carregar();
            setAviso({ tipo: "erro", texto });
          }}
        />
      ) : (
        <Consulta dados={dados} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------- consulta (passo 2)

function Consulta({ dados }: { dados: ConsultaInstrumento }) {
  const { instrumento, versoes } = dados;
  return (
    <>
      <section className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-borda bg-superficie px-4 py-3 text-sm">
        <Selo cor="verde">Versão {instrumento.versao} vigente</Selo>
        <span className="text-suave">
          criada em {dataHora(instrumento.criado_em)} por {instrumento.autor.nome}
        </span>
      </section>

      <Faixas conceitos={instrumento.conceitos} />

      {instrumento.componentes.map((c) => (
        <section key={c.id} className="flex flex-col gap-3 rounded-xl border border-borda bg-superficie p-4 sm:p-5">
          <TituloComponente componente={c} />
          <ol className="flex flex-col gap-3">
            {c.criterios.map((k) => (
              <li key={k.id} className="rounded-lg border border-borda p-3 sm:p-4">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h3 className="min-w-0 font-medium break-words">{k.nome}</h3>
                  <Selo cor="cinza">Peso {numero(k.peso)}</Selo>
                </div>
                <div className="mt-3 grid gap-3 lg:grid-cols-3">
                  {TEXTOS.map(([campo, conceito]) => {
                    const faixa = instrumento.conceitos.find((f) => f.conceito === conceito)!;
                    return (
                      <div key={campo} className="min-w-0 rounded-md bg-fundo p-3">
                        <p className="mb-1.5 flex flex-wrap items-center gap-2 text-[13px] font-medium">
                          <Selo cor={COR_CONCEITO[conceito]}>{faixa.rotulo}</Selo>
                          <span className="text-suave">
                            {numero(faixa.minimo)} a {numero(faixa.maximo)}
                          </span>
                        </p>
                        <p className="text-[13px] leading-relaxed whitespace-pre-line text-texto">{k[campo]}</p>
                      </div>
                    );
                  })}
                </div>
              </li>
            ))}
          </ol>
        </section>
      ))}

      <Historico versoes={versoes} />
    </>
  );
}

function TituloComponente({ componente, soma }: { componente: ComponenteAvaliacao; soma?: number }) {
  const fecha = soma === undefined || Math.abs(soma - componente.pontos) < 0.001;
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-2">
      <h2 className="text-lg font-semibold">
        {componente.nome} <span className="font-normal text-suave">· {numero(componente.pontos)} pontos</span>
      </h2>
      {soma !== undefined && (
        <span className={`text-sm font-medium ${fecha ? "text-verde" : "text-vermelho"}`}>
          Soma dos pesos: {Number.isNaN(soma) ? "—" : numero(soma)} de {numero(componente.pontos)}
        </span>
      )}
    </div>
  );
}

function Faixas({ conceitos }: { conceitos: FaixaConceito[] }) {
  return (
    <section aria-label="Conceitos e faixas de nota" className="flex flex-wrap items-center gap-2 text-sm">
      <span className="text-suave">Conceitos:</span>
      {conceitos.map((f) => (
        <Selo key={f.conceito} cor={COR_CONCEITO[f.conceito]}>
          {f.rotulo} · {numero(f.minimo)} a {numero(f.maximo)}
        </Selo>
      ))}
      <span className="text-[13px] text-suave">Nota ponderada = nota × peso ÷ 10</span>
    </section>
  );
}

function Historico({ versoes }: { versoes: ConsultaInstrumento["versoes"] }) {
  return (
    <section className="flex flex-col gap-2 rounded-xl border border-borda bg-superficie p-4 sm:p-5">
      <h2 className="text-lg font-semibold">Histórico de versões</h2>
      <p className="text-[13px] text-suave">
        Alterar um instrumento já usado em avaliações cria uma nova versão. As defesas já avaliadas continuam na
        versão em que foram avaliadas.
      </p>
      <ul className="divide-y divide-borda text-sm">
        {versoes.map((v) => (
          <li key={v.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2">
            <span className="font-medium">Versão {v.versao}</span>
            {v.vigente && <Selo cor="verde">Vigente</Selo>}
            <span className="text-suave">
              {dataHora(v.criado_em)} · {v.autor.nome}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

// ---------------------------------------------------------------- edição (passos 5 e 6)

function Edicao({
  instrumento,
  cancelar,
  aposSalvar,
  aposConflito,
}: {
  instrumento: InstrumentoAvaliacao;
  cancelar: () => void;
  aposSalvar: (texto: string) => void;
  aposConflito: (texto: string) => void;
}) {
  const [rascunho, setRascunho] = useState<Record<number, Rascunho[]>>(() =>
    Object.fromEntries(instrumento.componentes.map((c) => [c.id, paraRascunho(c)])),
  );
  const [erros, setErros] = useState<Record<string, ErrosCriterio>>({});
  const [somasIncorretas, setSomasIncorretas] = useState<SomaIncorreta[]>([]);
  const [erro, setErro] = useState("");
  const [salvando, setSalvando] = useState(false);

  function mudar(componente: number, chave: string, campo: keyof CriterioEntrada, valor: string) {
    setRascunho((r) => ({
      ...r,
      [componente]: r[componente].map((k) => (k.chave === chave ? { ...k, [campo]: valor } : k)),
    }));
    if (erros[chave]?.[campo]) setErros((e) => ({ ...e, [chave]: { ...e[chave], [campo]: undefined } }));
  }

  function mover(componente: number, indice: number, passo: -1 | 1) {
    setRascunho((r) => {
      const lista = [...r[componente]];
      [lista[indice], lista[indice + passo]] = [lista[indice + passo], lista[indice]];
      return { ...r, [componente]: lista };
    });
  }

  function remover(componente: number, chave: string) {
    setRascunho((r) => ({ ...r, [componente]: r[componente].filter((k) => k.chave !== chave) }));
  }

  function adicionar(componente: number) {
    setRascunho((r) => ({
      ...r,
      [componente]: [
        ...r[componente],
        { chave: novaChave(), nome: "", peso: "", texto_exemplar: "", texto_competente: "", texto_necessita: "" },
      ],
    }));
  }

  // Os mesmos limites que a API confere (400); a soma dos pesos fica com a API (passo 7, 422).
  function conferir(): boolean {
    const novos: Record<string, ErrosCriterio> = {};
    for (const lista of Object.values(rascunho)) {
      for (const k of lista) {
        const e: ErrosCriterio = {};
        if (!k.nome.trim()) e.nome = "Informe o nome do critério.";
        else if (k.nome.trim().length > 120) e.nome = "Use no máximo 120 caracteres.";
        const peso = lerPeso(k.peso);
        if (Number.isNaN(peso)) e.peso = "Use um número com até duas casas (ex.: 0,5).";
        else if (peso <= 0) e.peso = "O peso precisa ser maior que zero.";
        for (const [campo] of TEXTOS) if (!k[campo].trim()) e[campo] = "Descreva este conceito.";
        if (Object.keys(e).length) novos[k.chave] = e;
      }
    }
    setErros(novos);
    return Object.keys(novos).length === 0;
  }

  async function salvar() {
    setErro("");
    setSomasIncorretas([]);
    if (!conferir()) {
      setErro("Confira os campos destacados.");
      return;
    }
    setSalvando(true);
    try {
      const salvo = await api<InstrumentoAvaliacao>("/instrumento-avaliacao", {
        metodo: "PUT", // passo 6
        corpo: {
          componentes: instrumento.componentes.map((c) => ({
            id: c.id,
            criterios: rascunho[c.id].map((k) => ({
              nome: k.nome,
              peso: String(lerPeso(k.peso)),
              texto_exemplar: k.texto_exemplar,
              texto_competente: k.texto_competente,
              texto_necessita: k.texto_necessita,
            })),
          })),
        },
      });
      aposSalvar(
        salvo.versao === instrumento.versao
          ? `Instrumento salvo. A versão ${salvo.versao} continua vigente.`
          : `Instrumento salvo como versão ${salvo.versao}, agora vigente. A versão ${instrumento.versao} continua no histórico.`,
      );
    } catch (e) {
      const falha = e as ErroApi & { componentes?: SomaIncorreta[] };
      if (falha.status === 422 && falha.componentes) {
        // E1: mostra os componentes com soma incorreta e não salva
        setSomasIncorretas(falha.componentes);
        setErro(falha.message);
      } else if (falha.status === 409) {
        aposConflito(falha.message);
      } else {
        setErro(falha.message);
      }
    }
    setSalvando(false);
  }

  return (
    <div className="flex flex-col gap-4">
      <Aviso tipo="info">
        Altere critérios, pesos ou textos dos conceitos. Em cada parte, os pesos precisam somar os pontos da parte
        (escrita {numero(instrumento.componentes[0]?.pontos ?? 7)}; oral{" "}
        {numero(instrumento.componentes[1]?.pontos ?? 3)}). Se esta versão já tiver sido usada em alguma
        avaliação, salvar cria uma nova versão.
      </Aviso>

      {erro && (
        <Aviso tipo="erro">
          {erro}
          {somasIncorretas.length > 0 && (
            <ul className="mt-1 list-disc pl-5">
              {somasIncorretas.map((s) => (
                <li key={s.id}>
                  {s.nome}: soma {numero(s.soma)}, precisa ser {numero(s.pontos)}
                </li>
              ))}
            </ul>
          )}
        </Aviso>
      )}

      {instrumento.componentes.map((c) => {
        const lista = rascunho[c.id];
        const soma = lista.reduce((t, k) => t + lerPeso(k.peso), 0);
        const incorreto = somasIncorretas.some((s) => s.id === c.id);
        return (
          <section
            key={c.id}
            className={`flex flex-col gap-3 rounded-xl border bg-superficie p-4 sm:p-5 ${
              incorreto ? "border-vermelho" : "border-borda"
            }`}
          >
            <TituloComponente componente={c} soma={soma} />
            <ol className="flex flex-col gap-3">
              {lista.map((k, i) => (
                <li key={k.chave} className="flex flex-col gap-3 rounded-lg border border-borda p-3 sm:p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-[13px] font-medium text-suave">Critério {i + 1}</span>
                    <div className="flex gap-1">
                      <Botao
                        variante="texto"
                        pequeno
                        aria-label="Mover para cima"
                        disabled={i === 0}
                        onClick={() => mover(c.id, i, -1)}
                      >
                        <Icone nome="seta" className="size-4 -rotate-90" />
                      </Botao>
                      <Botao
                        variante="texto"
                        pequeno
                        aria-label="Mover para baixo"
                        disabled={i === lista.length - 1}
                        onClick={() => mover(c.id, i, 1)}
                      >
                        <Icone nome="seta" className="size-4 rotate-90" />
                      </Botao>
                      <Botao
                        variante="perigo"
                        pequeno
                        disabled={lista.length === 1}
                        title={lista.length === 1 ? "Cada parte precisa de ao menos um critério." : undefined}
                        onClick={() => remover(c.id, k.chave)}
                      >
                        <Icone nome="lixeira" className="size-4" /> Remover
                      </Botao>
                    </div>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_8rem]">
                    <Campo rotulo="Nome do critério" obrigatorio erro={erros[k.chave]?.nome}>
                      <Entrada
                        value={k.nome}
                        maxLength={120}
                        erro={erros[k.chave]?.nome}
                        onChange={(e) => mudar(c.id, k.chave, "nome", e.target.value)}
                      />
                    </Campo>
                    <Campo rotulo="Peso" obrigatorio erro={erros[k.chave]?.peso}>
                      <Entrada
                        value={k.peso}
                        inputMode="decimal"
                        erro={erros[k.chave]?.peso}
                        onChange={(e) => mudar(c.id, k.chave, "peso", e.target.value)}
                      />
                    </Campo>
                  </div>
                  <div className="grid gap-3 lg:grid-cols-3">
                    {TEXTOS.map(([campo, conceito]) => {
                      const faixa = instrumento.conceitos.find((f) => f.conceito === conceito)!;
                      const mensagem = erros[k.chave]?.[campo];
                      return (
                        <Campo
                          key={campo}
                          rotulo={`${faixa.rotulo} (${numero(faixa.minimo)} a ${numero(faixa.maximo)})`}
                          obrigatorio
                          erro={mensagem}
                        >
                          <textarea
                            value={k[campo]}
                            rows={6}
                            aria-invalid={mensagem ? true : undefined}
                            onChange={(e) => mudar(c.id, k.chave, campo, e.target.value)}
                            className={`w-full min-w-0 rounded-lg border bg-superficie px-3 py-2 text-[14px] leading-relaxed ${
                              mensagem ? "border-vermelho" : "border-borda"
                            }`}
                          />
                        </Campo>
                      );
                    })}
                  </div>
                </li>
              ))}
            </ol>
            <div>
              <Botao variante="contorno" pequeno onClick={() => adicionar(c.id)}>
                <Icone nome="mais" className="size-4" /> Adicionar critério
              </Botao>
            </div>
          </section>
        );
      })}

      <div className="sticky bottom-0 -mx-1 flex flex-wrap justify-end gap-2 border-t border-borda bg-fundo/95 px-1 py-3 backdrop-blur">
        <Botao variante="contorno" onClick={cancelar} disabled={salvando}>
          Cancelar
        </Botao>
        <Botao onClick={salvar} carregando={salvando}>
          Salvar alterações
        </Botao>
      </div>
    </div>
  );
}