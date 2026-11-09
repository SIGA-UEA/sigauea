"use client";

// TEL12 · Avaliação da defesa (DS-FL06-A), na página do TCC (TEL06). Aparece só para quem avalia esta defesa
// (orientador, avaliadores e suplente convocado); para os demais a API responde 403 e a seção fica oculta.
// Um critério por passo (loop do diagrama): os três conceitos com os textos, a nota dentro da faixa do conceito
// e a nota ponderada; depois o parecer e a revisão com a nota total. O rascunho pode ser salvo a qualquer momento,
// inclusive antes da defesa; o envio só é liberado depois dela (decisão da equipe, 07/11/2026).
// A conta da tela é só para acompanhar: quem grava ponderadas e total é a API (RBN10.04, CA-05).

import { useCallback, useEffect, useMemo, useState } from "react";
import { Aviso, Selo } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Campo, Entrada } from "@/components/campo";
import { Modal } from "@/components/modal";
import { api, ErroApi } from "@/lib/api";
import {
  dataHora,
  type Conceito,
  type ConsultaAvaliacao,
  type CriterioAvaliacao,
  type CriterioComProblema,
  type CriterioLancado,
  type FaixaConceito,
  type MinhaAvaliacao,
} from "@/lib/tipos";

const PARECER_MINIMO = 20;
const COR_CONCEITO = { EXEMPLAR: "verde", COMPETENTE: "azul", NECESSITA: "ambar" } as const;
const TEXTO: Record<Conceito, "texto_exemplar" | "texto_competente" | "texto_necessita"> = {
  EXEMPLAR: "texto_exemplar",
  COMPETENTE: "texto_competente",
  NECESSITA: "texto_necessita",
};

type Valor = { conceito?: Conceito; nota: string };
type Item = CriterioAvaliacao & { parte: string };

const br = (n: number, casas = 1) => n.toFixed(casas).replace(".", ",");

// Nota digitada ("7,5" ou "7.5") em décimos inteiros; null se não for um número com até 1 casa.
function decimos(texto: string): number | null {
  const t = texto.trim().replace(",", ".");
  if (!/^\d{1,2}(\.\d)?$/.test(t)) return null;
  return Math.round(Number(t) * 10);
}

// Mesma conta da API, em inteiros para não errar com ponto flutuante: nota × peso ÷ 10.
// Ponderada com 2 casas; total = soma exata arredondada só no final para 1 casa (meio para cima).
const exata = (notaDecimos: number, peso: number) => notaDecimos * Math.round(peso * 100); // em 1/10000
const ponderada = (notaDecimos: number, peso: number) => Math.floor((exata(notaDecimos, peso) + 50) / 100) / 100;

function erroDaNota(valor: Valor, faixa?: FaixaConceito): string | undefined {
  if (!valor.conceito || !faixa) return undefined;
  if (!valor.nota.trim()) return "Informe a nota.";
  const d = decimos(valor.nota);
  if (d === null) return "Use uma casa decimal, por exemplo 7,5.";
  if (d < faixa.minimo * 10 || d > faixa.maximo * 10) return `A nota de ${faixa.rotulo} vai de ${br(faixa.minimo)} a ${br(faixa.maximo)}.`;
  return undefined;
}

// aoEnviar avisa a página quando a avaliação é enviada, para a consolidação do resultado recarregar (RBN09.11).
export function SecaoAvaliacao({ defesaId, aoEnviar }: { defesaId: number; aoEnviar?: () => void }) {
  const [dados, setDados] = useState<ConsultaAvaliacao | null>(null);
  const [oculta, setOculta] = useState(false);
  const [erro, setErro] = useState("");

  const carregar = useCallback(() => {
    api<ConsultaAvaliacao>(`/defesas/${defesaId}/avaliacao`)
      .then(setDados)
      .catch((e: ErroApi) => (e.status === 403 || e.status === 409 || e.status === 404 ? setOculta(true) : setErro(e.message)));
  }, [defesaId]);
  useEffect(carregar, [carregar]);

  if (oculta) return null; // não avalia esta defesa (E2/E6), defesa cancelada ou ainda sem defesa
  return (
    <section className="rounded-xl border border-borda bg-superficie p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold">Minha avaliação</h2>
        {dados && <SeloStatus minha={dados.minha_avaliacao} />}
      </div>
      {erro ? (
        <Aviso tipo="erro">{erro}</Aviso>
      ) : !dados ? (
        <p role="status" className="text-sm text-suave">
          Carregando…
        </p>
      ) : dados.minha_avaliacao?.status === "ENVIADA" ? (
        <Enviada dados={dados} minha={dados.minha_avaliacao} />
      ) : (
        <Formulario dados={dados} aoAtualizar={setDados} aoEnviar={aoEnviar} />
      )}
    </section>
  );
}

function SeloStatus({ minha }: { minha: MinhaAvaliacao | null }) {
  if (!minha) return <Selo cor="cinza">Não iniciada</Selo>;
  return minha.status === "ENVIADA" ? <Selo cor="verde">Enviada</Selo> : <Selo cor="ambar">Rascunho</Selo>;
}

function Envios({ dados }: { dados: ConsultaAvaliacao }) {
  // Passo 7: só a contagem; ninguém vê as notas dos outros (RBN10.02, CA-02)
  return (
    <p className="text-sm text-suave">
      Avaliações da banca: {dados.envios.enviadas} de {dados.envios.esperadas} enviadas
    </p>
  );
}

function itens(dados: ConsultaAvaliacao): Item[] {
  return dados.instrumento.componentes.flatMap((c) => c.criterios.map((k) => ({ ...k, parte: c.nome })));
}

// ------------------------------------------------------------------ preenchimento (passos 8 a 19)

function Formulario({
  dados,
  aoAtualizar,
  aoEnviar,
}: {
  dados: ConsultaAvaliacao;
  aoAtualizar: (d: ConsultaAvaliacao) => void;
  aoEnviar?: () => void;
}) {
  const criterios = useMemo(() => itens(dados), [dados]);
  const faixas = useMemo(
    () => Object.fromEntries(dados.instrumento.conceitos.map((f) => [f.conceito, f])) as Record<Conceito, FaixaConceito>,
    [dados],
  );
  const inicial = dados.minha_avaliacao;
  const [valores, setValores] = useState<Record<number, Valor>>(() =>
    Object.fromEntries((inicial?.criterios ?? []).map((c) => [c.criterio_id, { conceito: c.conceito, nota: br(c.nota) }])),
  );
  const [parecer, setParecer] = useState(inicial?.parecer ?? "");
  const [passo, setPasso] = useState(0); // 0..n-1 critérios, n = parecer, n+1 = revisão
  const [problemas, setProblemas] = useState<Record<number, string>>({});
  const [aviso, setAviso] = useState<{ tipo: "sucesso" | "erro"; texto: string } | null>(null);
  const [erroParecer, setErroParecer] = useState("");
  const [salvando, setSalvando] = useState<"rascunho" | "envio" | null>(null);
  const [confirmar, setConfirmar] = useState(false);

  const n = criterios.length;
  const valor = (id: number): Valor => valores[id] ?? { nota: "" };
  const completo = (k: Item) => {
    const v = valor(k.id);
    return !!v.conceito && !erroDaNota(v, faixas[v.conceito]);
  };
  const preenchidos = criterios.filter(completo);
  const somaExata = preenchidos.reduce((s, k) => s + exata(decimos(valor(k.id).nota)!, k.peso), 0);
  const total = preenchidos.length === n ? Math.floor((somaExata + 500) / 1000) / 10 : null;

  function mudar(id: number, novo: Valor) {
    setValores((v) => ({ ...v, [id]: novo }));
    setProblemas((p) => {
      const resto = { ...p };
      delete resto[id];
      return resto;
    });
    setAviso(null);
  }

  // Só vão os critérios completos; um critério pela metade impede o salvamento e é mostrado (decisão D7).
  function lancados(): CriterioLancado[] | null {
    const metade = criterios.filter((k) => valor(k.id).conceito && !completo(k));
    if (metade.length) {
      setProblemas(Object.fromEntries(metade.map((k) => [k.id, erroDaNota(valor(k.id), faixas[valor(k.id).conceito!])!])));
      setPasso(criterios.indexOf(metade[0]));
      setAviso({ tipo: "erro", texto: "Complete a nota ou limpe o conceito dos critérios destacados." });
      return null;
    }
    return preenchidos.map((k) => ({
      criterio_id: k.id,
      conceito: valor(k.id).conceito!,
      nota: (decimos(valor(k.id).nota)! / 10).toFixed(1),
    }));
  }

  function tratar(e: ErroApi) {
    // No 422 da avaliação, "criterios" são os critérios destacados (no da senha, os critérios da senha)
    const destacados = (e as unknown as { criterios?: CriterioComProblema[] }).criterios;
    if (destacados?.length) {
      setProblemas(Object.fromEntries(destacados.map((c) => [c.id, c.motivo])));
      setPasso(n + 1);
    }
    if (e.campo === "parecer") {
      setErroParecer(e.message);
      setPasso(n);
    }
    setAviso({ tipo: "erro", texto: e.message });
  }

  async function gravar(tipo: "rascunho" | "envio") {
    const corpo = lancados();
    if (!corpo) return;
    setSalvando(tipo);
    setAviso(null);
    try {
      const minha = await api<MinhaAvaliacao>(
        `/defesas/${dados.defesa_id}/avaliacao${tipo === "envio" ? "/envio" : ""}`,
        { metodo: tipo === "envio" ? "POST" : "PUT", corpo: { criterios: corpo, parecer } },
      );
      const enviadas = dados.envios.enviadas + (minha.status === "ENVIADA" ? 1 : 0);
      aoAtualizar({ ...dados, minha_avaliacao: minha, envios: { ...dados.envios, enviadas } });
      if (minha.status === "ENVIADA") aoEnviar?.();
      if (tipo === "rascunho") setAviso({ tipo: "sucesso", texto: "Rascunho salvo. Você pode continuar depois." });
    } catch (e) {
      tratar(e as ErroApi);
    } finally {
      setSalvando(null);
      setConfirmar(false);
    }
  }

  function pedirEnvio() {
    const faltam = criterios.filter((k) => !completo(k));
    if (faltam.length) {
      // Fluxo E4: volta para o primeiro critério que falta, com os demais destacados na revisão
      setProblemas(Object.fromEntries(faltam.map((k) => [k.id, "Escolha o conceito e informe a nota."])));
      setPasso(criterios.indexOf(faltam[0]));
      setAviso({ tipo: "erro", texto: `Faltam ${faltam.length} critério(s) para enviar.` });
      return;
    }
    if (parecer.trim().length < PARECER_MINIMO) {
      setErroParecer(`O parecer precisa de pelo menos ${PARECER_MINIMO} caracteres.`);
      setPasso(n);
      return;
    }
    setConfirmar(true);
  }

  return (
    <div className="flex flex-col gap-4">
      <Envios dados={dados} />
      {!dados.envio_liberado && (
        <Aviso tipo="info">
          A defesa ainda não foi realizada. Você já pode preencher e salvar o rascunho; o envio fica liberado depois da
          defesa.
        </Aviso>
      )}

      <Passos criterios={criterios} completo={completo} problemas={problemas} passo={passo} irPara={setPasso} />

      {aviso && <Aviso tipo={aviso.tipo}>{aviso.texto}</Aviso>}

      {passo < n ? (
        <PassoCriterio
          key={criterios[passo].id}
          indice={passo}
          total={n}
          criterio={criterios[passo]}
          faixas={faixas}
          valor={valor(criterios[passo].id)}
          problema={problemas[criterios[passo].id]}
          aoMudar={(v) => mudar(criterios[passo].id, v)}
        />
      ) : passo === n ? (
        <Campo rotulo="Parecer" obrigatorio erro={erroParecer}>
          <textarea
            value={parecer}
            rows={6}
            aria-invalid={erroParecer ? true : undefined}
            onChange={(e) => {
              setParecer(e.target.value);
              setErroParecer("");
            }}
            className={`w-full min-w-0 rounded-lg border bg-superficie px-3 py-2 text-[14px] leading-relaxed ${
              erroParecer ? "border-vermelho" : "border-borda"
            }`}
          />
          <span className={`text-[13px] ${parecer.trim().length < PARECER_MINIMO ? "text-suave" : "text-verde"}`}>
            {parecer.trim().length} caracteres · mínimo de {PARECER_MINIMO} para enviar
          </span>
        </Campo>
      ) : (
        <Revisao
          criterios={criterios}
          valor={valor}
          completo={completo}
          problemas={problemas}
          total={total}
          irPara={setPasso}
        />
      )}

      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-borda pt-4">
        <div className="flex gap-2">
          <Botao variante="contorno" pequeno disabled={passo === 0} onClick={() => setPasso(passo - 1)}>
            Anterior
          </Botao>
          {passo <= n && (
            <Botao variante="contorno" pequeno onClick={() => setPasso(passo + 1)}>
              {passo === n ? "Revisar" : "Próximo"}
            </Botao>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Botao variante="texto" carregando={salvando === "rascunho"} disabled={!!salvando} onClick={() => gravar("rascunho")}>
            Salvar rascunho
          </Botao>
          {passo === n + 1 && (
            <Botao
              disabled={!dados.envio_liberado || !!salvando}
              title={dados.envio_liberado ? undefined : "O envio fica liberado depois da defesa."}
              onClick={pedirEnvio}
            >
              Enviar avaliação
            </Botao>
          )}
        </div>
      </div>

      {confirmar && (
        <Modal titulo="Enviar a avaliação?" aoFechar={() => setConfirmar(false)}>
          <p className="text-sm">
            Nota total: <strong>{total !== null ? br(total) : "—"}</strong>
          </p>
          <p className="mt-2 text-sm text-suave">Depois de enviada, a avaliação não pode mais ser alterada.</p>
          <div className="mt-5 flex justify-end gap-2">
            <Botao variante="contorno" onClick={() => setConfirmar(false)}>
              Voltar
            </Botao>
            <Botao carregando={salvando === "envio"} onClick={() => gravar("envio")}>
              Enviar
            </Botao>
          </div>
        </Modal>
      )}
    </div>
  );
}

function Passos({
  criterios,
  completo,
  problemas,
  passo,
  irPara,
}: {
  criterios: Item[];
  completo: (k: Item) => boolean;
  problemas: Record<number, string>;
  passo: number;
  irPara: (p: number) => void;
}) {
  const n = criterios.length;
  const etiquetas = [...criterios.map((_, i) => String(i + 1)), "Parecer", "Revisão"];
  return (
    <nav aria-label="Etapas da avaliação" className="flex flex-wrap gap-1.5">
      {etiquetas.map((rotulo, i) => {
        const k = criterios[i];
        const estado = i === passo ? "atual" : k && problemas[k.id] ? "problema" : k && completo(k) ? "feito" : "vazio";
        const estilo = {
          atual: "bg-azul text-white",
          problema: "bg-vermelho-claro text-vermelho ring-1 ring-vermelho/40",
          feito: "bg-verde-claro text-verde",
          vazio: "bg-fundo text-suave ring-1 ring-inset ring-borda",
        }[estado];
        return (
          <button
            key={rotulo}
            type="button"
            onClick={() => irPara(i)}
            aria-current={i === passo ? "step" : undefined}
            title={k ? k.nome : rotulo}
            className={`h-8 rounded-full text-sm font-medium ${i < n ? "w-8" : "px-3"} ${estilo}`}
          >
            {rotulo}
          </button>
        );
      })}
    </nav>
  );
}

function PassoCriterio({
  indice,
  total,
  criterio,
  faixas,
  valor,
  problema,
  aoMudar,
}: {
  indice: number;
  total: number;
  criterio: Item;
  faixas: Record<Conceito, FaixaConceito>;
  valor: Valor;
  problema?: string;
  aoMudar: (v: Valor) => void;
}) {
  const faixa = valor.conceito ? faixas[valor.conceito] : undefined;
  const erroNota = problema ?? (valor.nota.trim() ? erroDaNota(valor, faixa) : undefined);
  const d = decimos(valor.nota);
  const valida = valor.conceito && !erroDaNota(valor, faixa);
  return (
    <fieldset className="flex min-w-0 flex-col gap-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <legend className="min-w-0 font-medium break-words">
          <span className="text-sm font-normal text-suave">
            Critério {indice + 1} de {total} · {criterio.parte}
          </span>
          <br />
          {criterio.nome}
        </legend>
        <Selo cor="cinza">Peso {br(criterio.peso)}</Selo>
      </div>

      <div className="grid gap-3 lg:grid-cols-3" role="radiogroup" aria-label="Conceito">
        {(Object.keys(TEXTO) as Conceito[]).map((c) => {
          const f = faixas[c];
          const marcado = valor.conceito === c;
          return (
            <label
              key={c}
              className={`flex min-w-0 cursor-pointer flex-col gap-1.5 rounded-lg border p-3 ${
                marcado ? "border-azul bg-azul-claro/50 ring-1 ring-azul" : "border-borda bg-fundo hover:border-azul-borda"
              }`}
            >
              <span className="flex flex-wrap items-center gap-2 text-[13px] font-medium">
                <input
                  type="radio"
                  name={`conceito-${criterio.id}`}
                  checked={marcado}
                  // Trocar o conceito limpa a nota (RBN10.03, CA-04)
                  onChange={() => aoMudar({ conceito: c, nota: "" })}
                  className="accent-azul"
                />
                <Selo cor={COR_CONCEITO[c]}>{f.rotulo}</Selo>
                <span className="text-suave">
                  {br(f.minimo)} a {br(f.maximo)}
                </span>
              </span>
              <span className="text-[13px] leading-relaxed whitespace-pre-line">{criterio[TEXTO[c]]}</span>
            </label>
          );
        })}
      </div>

      {/* A nota só aparece depois do conceito (RBN10.03, CA-02) */}
      {faixa && (
        <div className="flex flex-wrap items-end gap-4">
          <Campo rotulo="Nota" obrigatorio erro={erroNota} className="w-40">
            <Entrada
              inputMode="decimal"
              value={valor.nota}
              placeholder={`${br(faixa.minimo)} a ${br(faixa.maximo)}`}
              erro={erroNota}
              onChange={(e) => aoMudar({ ...valor, nota: e.target.value })}
            />
          </Campo>
          <p className="pb-2.5 text-sm">
            Nota ponderada: <strong>{valida && d !== null ? br(ponderada(d, criterio.peso), 2) : "—"}</strong>
          </p>
          <Botao variante="texto" pequeno className="mb-1.5" onClick={() => aoMudar({ nota: "" })}>
            Limpar
          </Botao>
        </div>
      )}
    </fieldset>
  );
}

function Revisao({
  criterios,
  valor,
  completo,
  problemas,
  total,
  irPara,
}: {
  criterios: Item[];
  valor: (id: number) => Valor;
  completo: (k: Item) => boolean;
  problemas: Record<number, string>;
  total: number | null;
  irPara: (p: number) => void;
}) {
  const faltam = criterios.filter((k) => !completo(k)).length;
  return (
    <div className="flex flex-col gap-3">
      <TabelaNotas
        linhas={criterios.map((k, i) => {
          const v = valor(k.id);
          const d = completo(k) ? decimos(v.nota) : null;
          return {
            criterio: k,
            conceito: completo(k) ? v.conceito : undefined,
            nota: d !== null ? d / 10 : undefined,
            ponderada: d !== null ? ponderada(d, k.peso) : undefined,
            problema: problemas[k.id],
            irPara: () => irPara(i),
          };
        })}
        total={total}
      />
      {faltam > 0 && (
        <p className="text-sm text-ambar">
          Faltam {faltam} critério(s). A nota total aparece quando todos estiverem preenchidos.
        </p>
      )}
    </div>
  );
}

type Linha = {
  criterio: Item;
  conceito?: Conceito;
  nota?: number;
  ponderada?: number;
  problema?: string;
  irPara?: () => void;
};

function TabelaNotas({ linhas, total }: { linhas: Linha[]; total: number | null }) {
  const ROTULO: Record<Conceito, string> = { EXEMPLAR: "Exemplar", COMPETENTE: "Competente", NECESSITA: "Necessita de Trabalho" };
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-borda text-left text-suave">
            <th className="py-2 pr-3 font-medium">Critério</th>
            <th className="py-2 pr-3 text-right font-medium">Peso</th>
            <th className="py-2 pr-3 font-medium">Conceito</th>
            <th className="py-2 pr-3 text-right font-medium">Nota</th>
            <th className="py-2 text-right font-medium">Ponderada</th>
          </tr>
        </thead>
        <tbody>
          {linhas.map((l) => (
            <tr key={l.criterio.id} className={`border-b border-borda ${l.problema ? "bg-vermelho-claro" : ""}`}>
              <td className="py-2 pr-3">
                {l.irPara ? (
                  <button type="button" onClick={l.irPara} className="text-left text-azul-forte hover:underline">
                    {l.criterio.nome}
                  </button>
                ) : (
                  l.criterio.nome
                )}
                <span className="block text-xs text-suave">{l.problema ?? l.criterio.parte}</span>
              </td>
              <td className="py-2 pr-3 text-right">{br(l.criterio.peso)}</td>
              <td className="py-2 pr-3">
                {l.conceito ? <Selo cor={COR_CONCEITO[l.conceito]}>{ROTULO[l.conceito]}</Selo> : <span className="text-ambar">Pendente</span>}
              </td>
              <td className="py-2 pr-3 text-right">{l.nota !== undefined ? br(l.nota) : "—"}</td>
              <td className="py-2 text-right">{l.ponderada !== undefined ? br(l.ponderada, 2) : "—"}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={4} className="pt-3 pr-3 text-right font-semibold">
              Nota total
            </td>
            <td className="pt-3 text-right text-lg font-semibold">{total !== null ? br(total) : "—"}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

// ------------------------------------------------------------------ enviada (fluxo E3)

function Enviada({ dados, minha }: { dados: ConsultaAvaliacao; minha: MinhaAvaliacao }) {
  const por = Object.fromEntries(minha.criterios.map((c) => [c.criterio_id, c]));
  return (
    <div className="flex flex-col gap-4">
      <Envios dados={dados} />
      <Aviso tipo="sucesso">Avaliação enviada em {dataHora(minha.enviada_em)}. Ela não pode mais ser alterada.</Aviso>
      <TabelaNotas
        linhas={itens(dados).map((k) => ({
          criterio: k,
          conceito: por[k.id]?.conceito,
          nota: por[k.id]?.nota,
          ponderada: por[k.id]?.nota_ponderada,
        }))}
        total={minha.nota_total}
      />
      {minha.parecer && (
        <div>
          <h3 className="mb-1 text-sm font-medium">Parecer</h3>
          <p className="text-sm break-words whitespace-pre-wrap">{minha.parecer}</p>
        </div>
      )}
    </div>
  );
}
