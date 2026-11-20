"use client";

// TEL15 · Publicações (DS-FL08 e DS-FL08-B): situação atual do artigo, o formulário "Adicionar ao histórico" e o
// histórico, do mais recente para o mais antigo. Só aparece na modalidade artigo; quem registra (aluno autor ou
// orientador) vem da API (RN07). Os registros passados são somente leitura (CA-04 do RBN12.02).

import { useEffect, useState } from "react";
import { Aviso, Selo } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Campo, Entrada, Selecao } from "@/components/campo";
import { api, ErroApi } from "@/lib/api";
import {
  dataCurta,
  ESTRATOS_QUALIS,
  NOME_SITUACAO_EDITORIAL,
  type Publicacao,
  type SituacaoEditorial,
  type TipoVeiculo,
} from "@/lib/tipos";

const NOME_TIPO: Record<TipoVeiculo, string> = { PERIODICO: "Revista / periódico", CONGRESSO: "Congresso" };
const COR_SITUACAO: Record<SituacaoEditorial, "azul" | "ambar" | "verde" | "vermelho"> = {
  SUBMETIDO: "azul",
  EM_REVISAO: "ambar",
  ACEITO: "verde",
  PUBLICADO: "verde",
  RECUSADO: "vermelho",
};

// O dia de hoje no fuso de Manaus, no formato do campo de data (AAAA-MM-DD).
const hoje = () => new Date().toLocaleDateString("en-CA", { timeZone: "America/Manaus" });

type Formulario = {
  veiculo: string;
  tipo_veiculo: TipoVeiculo;
  qualis: string;
  situacao: SituacaoEditorial;
  data: string;
  link: string;
};

function formularioDe(p: Publicacao): Formulario {
  // CA-02 do RBN12.01: o formulário abre com os dados do cadastro (ou do último registro).
  return {
    veiculo: p.atual?.veiculo ?? "",
    tipo_veiculo: p.atual?.tipo_veiculo ?? "PERIODICO",
    qualis: p.atual?.qualis ?? "",
    situacao: p.atual?.situacao ?? "SUBMETIDO",
    data: hoje(),
    link: p.atual?.link ?? "",
  };
}

export function SecaoArtigo({ tccId, aoMudar }: { tccId: string; aoMudar: () => void }) {
  const [dados, setDados] = useState<Publicacao | null>(null);
  const [form, setForm] = useState<Formulario | null>(null);
  const [erro, setErro] = useState("");
  const [erros, setErros] = useState<Record<string, string>>({});
  const [sucesso, setSucesso] = useState(false);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    api<Publicacao>(`/tccs/${tccId}/publicacao`)
      .then((p) => {
        setDados(p);
        setForm(formularioDe(p));
        // O link do e-mail (RBN12.03) abre direto nesta seção: a âncora só existe depois de carregar.
        if (window.location.hash === "#artigo") document.getElementById("artigo")?.scrollIntoView();
      })
      .catch((e: ErroApi) => setErro(e.message));
  }, [tccId]);

  const mudar = <K extends keyof Formulario>(campo: K, valor: Formulario[K]) => {
    setForm((f) => (f ? { ...f, [campo]: valor } : f));
    setErros((atuais) => {
      const resto = { ...atuais };
      delete resto[campo];
      return resto;
    });
    setSucesso(false);
  };

  // Outro veículo vira uma submissão nova; o tipo do veículo só é pedido nesse caso.
  const veiculoNovo =
    !!form && (!dados?.atual || dados.atual.veiculo.trim().toLowerCase() !== form.veiculo.trim().toLowerCase());

  async function adicionar(e: React.FormEvent) {
    e.preventDefault();
    if (!form) return;
    setEnviando(true);
    setErro("");
    setErros({});
    setSucesso(false);
    try {
      const novo = await api<Publicacao>(`/tccs/${tccId}/publicacao`, {
        metodo: "POST",
        corpo: {
          veiculo: form.veiculo,
          tipo_veiculo: veiculoNovo ? form.tipo_veiculo : null,
          qualis: form.qualis || null,
          situacao: form.situacao,
          data: form.data || null,
          link: form.link.trim() || null,
        },
      });
      setDados(novo);
      setForm(formularioDe(novo));
      setSucesso(true);
      aoMudar(); // os dados do trabalho mostram a situação editorial nova
    } catch (falha) {
      const f = falha as ErroApi;
      setErro(f.message);
      setErros(f.campos ?? {});
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section id="artigo" className="scroll-mt-20 rounded-xl border border-borda bg-superficie p-5">
      <h2 className="mb-1 font-semibold">Artigo</h2>
      <p className="mb-4 text-[13px] text-suave">
        A situação editorial não muda o cadastro nem a defesa. Aceito ou publicado em Qualis A ou B pode mudar a nota
        final.
      </p>

      {erro && (
        <div className="mb-4">
          <Aviso tipo="erro">{erro}</Aviso>
        </div>
      )}

      {!dados || !form ? (
        !erro && (
          <p role="status" className="text-sm text-suave">
            Carregando…
          </p>
        )
      ) : (
        <div className="flex flex-col gap-5">
          {/* Situação atual (DS-FL08 mensagens 2 a 5) */}
          {dados.atual && (
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg bg-fundo p-3 text-sm">
              <span className="text-suave">Situação atual</span>
              <Selo cor={COR_SITUACAO[dados.atual.situacao]}>{NOME_SITUACAO_EDITORIAL[dados.atual.situacao]}</Selo>
              <span className="min-w-0 break-words">
                {dados.atual.veiculo}
                {dados.atual.qualis && ` · Qualis ${dados.atual.qualis}`}
              </span>
            </div>
          )}

          {dados.pode_registrar ? (
            <form onSubmit={adicionar} noValidate className="flex flex-col gap-4">
              <h3 className="text-sm font-medium">Registrar alteração</h3>
              <div className="grid gap-4 sm:grid-cols-2">
                <Campo rotulo="Veículo (revista ou evento)" obrigatorio erro={erros.veiculo} className="sm:col-span-2">
                  <Entrada
                    value={form.veiculo}
                    onChange={(e) => mudar("veiculo", e.target.value)}
                    maxLength={200}
                    erro={erros.veiculo}
                  />
                </Campo>
                {veiculoNovo && (
                  <Campo rotulo="Tipo de veículo" obrigatorio erro={erros.tipo_veiculo}>
                    <Selecao
                      value={form.tipo_veiculo}
                      onChange={(e) => mudar("tipo_veiculo", e.target.value as TipoVeiculo)}
                      erro={erros.tipo_veiculo}
                    >
                      {Object.entries(NOME_TIPO).map(([v, r]) => (
                        <option key={v} value={v}>
                          {r}
                        </option>
                      ))}
                    </Selecao>
                  </Campo>
                )}
                <Campo rotulo="Qualis" dica="opcional" erro={erros.qualis}>
                  <Selecao value={form.qualis} onChange={(e) => mudar("qualis", e.target.value)} erro={erros.qualis}>
                    <option value="">Não informado</option>
                    {ESTRATOS_QUALIS.map((q) => (
                      <option key={q} value={q}>
                        {q}
                      </option>
                    ))}
                  </Selecao>
                </Campo>
                <Campo rotulo="Situação editorial" obrigatorio erro={erros.situacao}>
                  <Selecao
                    value={form.situacao}
                    onChange={(e) => mudar("situacao", e.target.value as SituacaoEditorial)}
                    erro={erros.situacao}
                  >
                    {Object.entries(NOME_SITUACAO_EDITORIAL).map(([v, r]) => (
                      <option key={v} value={v}>
                        {r}
                      </option>
                    ))}
                  </Selecao>
                </Campo>
                <Campo rotulo="Data da alteração" obrigatorio erro={erros.data}>
                  <Entrada
                    type="date"
                    value={form.data}
                    max={hoje()}
                    onChange={(e) => mudar("data", e.target.value)}
                    erro={erros.data}
                  />
                </Campo>
                <Campo
                  rotulo="DOI ou endereço"
                  obrigatorio={form.situacao === "PUBLICADO"}
                  dica="obrigatório se publicado"
                  erro={erros.link}
                  className="sm:col-span-2"
                >
                  <Entrada
                    value={form.link}
                    onChange={(e) => mudar("link", e.target.value)}
                    placeholder="10.xxxx/xxxxx ou https://..."
                    maxLength={300}
                    erro={erros.link}
                  />
                </Campo>
              </div>
              {sucesso && (
                <Aviso tipo="sucesso">Registro adicionado ao histórico. O orientador e o autor recebem um aviso por e-mail.</Aviso>
              )}
              <div>
                <Botao type="submit" carregando={enviando}>
                  Adicionar ao histórico
                </Botao>
              </div>
            </form>
          ) : (
            <Aviso tipo="info">Somente leitura: quem registra a publicação é o aluno autor ou o orientador.</Aviso>
          )}

          {/* DS-FL08-B: histórico, somente leitura, do mais recente para o mais antigo */}
          <div>
            <h3 className="mb-2 text-sm font-medium">Histórico de submissões</h3>
            {dados.historico.length === 0 ? (
              <p className="text-sm text-suave">Nenhuma submissão registrada.</p>
            ) : (
              <ol className="flex flex-col gap-3 border-l-2 border-borda pl-4 text-sm">
                {dados.historico.map((h) => (
                  <li key={h.id} className="min-w-0">
                    <p className="flex flex-wrap items-center gap-2">
                      <Selo cor={COR_SITUACAO[h.situacao]}>{NOME_SITUACAO_EDITORIAL[h.situacao]}</Selo>
                      <span className="font-medium break-words">{h.veiculo}</span>
                    </p>
                    <p className="mt-0.5 text-suave">
                      {dataCurta(h.data)} · {h.responsavel?.nome ?? "Sistema"} · {NOME_TIPO[h.tipo_veiculo]}
                      {h.qualis && ` · Qualis ${h.qualis}`}
                    </p>
                    {h.link && (
                      <p className="mt-0.5 break-all">
                        <a
                          href={h.link.startsWith("https://") ? h.link : `https://doi.org/${h.link}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-azul-forte hover:underline"
                        >
                          {h.link}
                        </a>
                      </p>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
