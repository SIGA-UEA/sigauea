"use client";

// TEL19 · Ocorrências e frequência (DS-FL09, DS-FL09-A e DS-FL09-B · RBN09.10, RN23).
// Seção "Presença e ocorrências" do acompanhamento do TCC, liberada depois que a defesa começa.
//   GET    /defesas/{id}/ocorrencias            ocorrências e ouvintes, com "x prontos para declaração"
//   POST   /defesas/{id}/ocorrencias            registrar ocorrência
//   PUT    /defesas/{id}/ocorrencias/{id}       corrigir ocorrência ("corrigido em ...")
//   POST   /defesas/{id}/ouvintes               adicionar ouvinte (nome e matrícula)
//   POST   /defesas/{id}/ouvintes/lote          colar uma lista
//   PUT    /defesas/{id}/ouvintes/{id}          corrigir matrícula
//   DELETE /defesas/{id}/ouvintes/{id}          remover ouvinte, com "Desfazer"
//   POST   /defesas/{id}/declaracoes            emitir a declaração de horas
// Só a coordenação e o orientador do TCC veem esta seção: para os demais a API responde 403 e nada
// aparece aqui (CA-05, CA-06).

import { useCallback, useEffect, useState } from "react";
import { Aviso, Selo } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Campo, Entrada } from "@/components/campo";
import { Icone } from "@/components/icone";
import { Modal } from "@/components/modal";
import { api, ErroApi } from "@/lib/api";
import {
  dataHora,
  type Banca,
  type Declaracao,
  type LoteOuvintes,
  type Ocorrencia,
  type Ouvinte,
  type Presenca,
} from "@/lib/tipos";

// Mesma regra do cadastro de aluno e da API: só números, de 6 a 20 dígitos.
const matriculaOk = (m: string) => /^\d{6,20}$/.test(m.trim());
// Nome completo (nome e sobrenome): é o que sai na declaração de horas.
const nomeCompleto = (t: string) =>
  t
    .trim()
    .split(/\s+/)
    .filter((p) => (p.match(/\p{L}/gu) ?? []).length >= 2).length >= 2;
const AREA_TEXTO =
  "w-full min-w-0 rounded-lg border bg-superficie px-3 py-2 text-[14px] leading-relaxed placeholder:text-suave";

// A seção só existe depois que há defesa agendada; o id dela vem da consulta da banca (DS-FL04-A).
export function SecaoPresenca({ tccId }: { tccId: string }) {
  const [defesaId, setDefesaId] = useState<number | null>(null);
  useEffect(() => {
    api<Banca>(`/tccs/${tccId}/banca`)
      .then((b) => setDefesaId(b.defesa?.id ?? null))
      .catch(() => setDefesaId(null)); // a seção Banca e defesa já mostra o erro
  }, [tccId]);
  return defesaId === null ? null : <PainelPresenca defesaId={defesaId} />;
}

function PainelPresenca({ defesaId }: { defesaId: number }) {
  const [dados, setDados] = useState<Presenca | null>(null);
  const [oculta, setOculta] = useState(false);
  const [erro, setErro] = useState("");

  const carregar = useCallback(() => {
    api<Presenca>(`/defesas/${defesaId}/ocorrencias`)
      .then((d) => {
        setDados(d);
        setErro("");
      })
      .catch((e: ErroApi) =>
        e.status === 403 || e.status === 404
          ? setOculta(true)
          : setErro(e.message),
      );
  }, [defesaId]);
  useEffect(carregar, [carregar]);

  if (oculta) return null;

  return (
    <section
      className="rounded-xl border border-borda bg-superficie p-5"
      aria-labelledby="titulo-presenca"
    >
      <h2 id="titulo-presenca" className="mb-1 font-semibold">
        Presença e ocorrências
      </h2>
      <p className="mb-4 text-[13px] text-suave">
        Registre as ocorrências da defesa e a lista de ouvintes para a
        declaração de horas complementares.
      </p>
      {erro ? (
        <Aviso tipo="erro">{erro}</Aviso>
      ) : !dados ? (
        <p role="status" className="text-sm text-suave">
          Carregando…
        </p>
      ) : dados.situacao === "CANCELADA" ? (
        <Aviso tipo="info">Esta defesa foi cancelada.</Aviso>
      ) : !dados.liberada ? (
        <Aviso tipo="info">
          Etapa ainda não liberada: presença e ocorrências são registradas
          depois que a defesa começar.
        </Aviso>
      ) : (
        <div className="flex flex-col gap-6">
          <Ocorrencias
            defesaId={defesaId}
            lista={dados.ocorrencias}
            aoMudar={carregar}
          />
          <Ouvintes defesaId={defesaId} dados={dados} aoMudar={carregar} />
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------- DS-FL09 e DS-FL09-A · ocorrências

function Ocorrencias({
  defesaId,
  lista,
  aoMudar,
}: {
  defesaId: number;
  lista: Ocorrencia[];
  aoMudar: () => void;
}) {
  const [texto, setTexto] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [editando, setEditando] = useState<number | null>(null);
  const [textoEdicao, setTextoEdicao] = useState("");
  const [erroEdicao, setErroEdicao] = useState("");

  async function registrar(e: React.FormEvent) {
    e.preventDefault();
    if (texto.trim().length < 5) {
      setErro("Descreva a ocorrência (mínimo de 5 caracteres)."); // CA-02
      return;
    }
    setEnviando(true);
    setErro("");
    try {
      await api<Ocorrencia>(`/defesas/${defesaId}/ocorrencias`, {
        metodo: "POST",
        corpo: { texto: texto.trim() },
      });
      setTexto("");
      aoMudar();
    } catch (falha) {
      setErro((falha as ErroApi).message);
    } finally {
      setEnviando(false);
    }
  }

  async function salvarCorrecao(id: number) {
    if (textoEdicao.trim().length < 5) {
      setErroEdicao("Descreva a ocorrência (mínimo de 5 caracteres).");
      return;
    }
    try {
      await api<Ocorrencia>(`/defesas/${defesaId}/ocorrencias/${id}`, {
        metodo: "PUT",
        corpo: { texto: textoEdicao.trim() },
      });
      setEditando(null);
      aoMudar();
    } catch (falha) {
      setErroEdicao((falha as ErroApi).message);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <h3 className="font-medium">Ocorrências da sessão</h3>
      <form onSubmit={registrar} noValidate className="flex flex-col gap-2">
        <Campo
          rotulo="Registrar ocorrência"
          dica="texto livre: atraso, problema técnico, intercorrência"
          erro={erro}
        >
          <textarea
            value={texto}
            rows={3}
            maxLength={800}
            aria-invalid={erro ? true : undefined}
            onChange={(e) => setTexto(e.target.value)}
            className={`${AREA_TEXTO} ${erro ? "border-vermelho" : "border-borda"}`}
          />
        </Campo>
        <div>
          <Botao
            type="submit"
            variante="contorno"
            pequeno
            carregando={enviando}
          >
            <Icone nome="mais" className="size-4" /> Registrar ocorrência
          </Botao>
        </div>
      </form>

      {lista.length === 0 ? (
        <p className="text-sm text-suave">Nenhuma ocorrência registrada.</p>
      ) : (
        <ol className="flex flex-col gap-2">
          {[...lista].reverse().map((o) => (
            <li
              key={o.id}
              className="rounded-lg border border-borda p-3 text-sm"
            >
              {editando === o.id ? (
                <div className="flex flex-col gap-2">
                  <Campo rotulo="Editar ocorrência" erro={erroEdicao}>
                    <textarea
                      value={textoEdicao}
                      rows={3}
                      maxLength={800}
                      aria-invalid={erroEdicao ? true : undefined}
                      onChange={(e) => setTextoEdicao(e.target.value)}
                      className={`${AREA_TEXTO} ${erroEdicao ? "border-vermelho" : "border-borda"}`}
                    />
                  </Campo>
                  <div className="flex flex-wrap gap-2">
                    <Botao pequeno onClick={() => salvarCorrecao(o.id)}>
                      Salvar correção
                    </Botao>
                    <Botao
                      variante="texto"
                      pequeno
                      onClick={() => setEditando(null)}
                    >
                      Cancelar
                    </Botao>
                  </div>
                </div>
              ) : (
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="break-words whitespace-pre-line">{o.texto}</p>
                    <p className="mt-1 text-[13px] text-suave">
                      {dataHora(o.criado_em)} · {o.autor.nome}
                      {o.alterada_em &&
                        ` · corrigido em ${dataHora(o.alterada_em)}`}
                    </p>
                  </div>
                  <Botao
                    variante="texto"
                    pequeno
                    onClick={() => {
                      setEditando(o.id);
                      setTextoEdicao(o.texto);
                      setErroEdicao("");
                    }}
                  >
                    <Icone nome="lapis" className="size-4" /> Corrigir
                  </Botao>
                </div>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- DS-FL09, DS-FL09-A e DS-FL09-B · ouvintes

function Ouvintes({
  defesaId,
  dados,
  aoMudar,
}: {
  defesaId: number;
  dados: Presenca;
  aoMudar: () => void;
}) {
  const [novo, setNovo] = useState({ nome: "", matricula: "" });
  const [erros, setErros] = useState<{ nome?: string; matricula?: string }>({});
  const [geral, setGeral] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [lote, setLote] = useState("");
  const [resultadoLote, setResultadoLote] = useState<LoteOuvintes | null>(null);
  const [desfazer, setDesfazer] = useState<Ouvinte | null>(null);
  const ouvintes = dados.ouvintes;

  async function adicionar(e: React.FormEvent) {
    e.preventDefault();
    const faltas: typeof erros = {};
    if (!nomeCompleto(novo.nome))
      faltas.nome = "Informe o nome completo (nome e sobrenome).";
    if (!matriculaOk(novo.matricula))
      faltas.matricula = "A matrícula deve ter só números (de 6 a 20 dígitos).";
    else if (ouvintes.some((o) => o.matricula === novo.matricula.trim()))
      faltas.matricula = "Esta matrícula já está na lista."; // CA-04
    setErros(faltas);
    setGeral("");
    if (Object.keys(faltas).length) return;
    setEnviando(true);
    try {
      await api<Ouvinte>(`/defesas/${defesaId}/ouvintes`, {
        metodo: "POST",
        corpo: { nome: novo.nome.trim(), matricula: novo.matricula.trim() },
      });
      setNovo({ nome: "", matricula: "" });
      setDesfazer(null);
      aoMudar();
      document.getElementById("ouvinte-nome")?.focus(); // adicionar em sequência sem usar o mouse
    } catch (falha) {
      const erro = falha as ErroApi;
      if (erro.campo === "nome" || erro.campo === "matricula")
        setErros({ [erro.campo]: erro.message });
      else setGeral(erro.message);
    } finally {
      setEnviando(false);
    }
  }

  async function adicionarLista() {
    const linhas = lote.split("\n").filter((l) => l.trim());
    if (!linhas.length) return;
    try {
      const r = await api<LoteOuvintes>(`/defesas/${defesaId}/ouvintes/lote`, {
        metodo: "POST",
        corpo: { linhas },
      });
      setResultadoLote(r);
      if (!r.linhas_com_problema.length) setLote("");
      aoMudar();
    } catch (falha) {
      setGeral((falha as ErroApi).message);
    }
  }

  // Ação destrutiva: confirma num modal antes de remover; depois ainda dá para desfazer (DS-FL09-A).
  const [confirmar, setConfirmar] = useState<Ouvinte | null>(null);
  const [removendo, setRemovendo] = useState(false);

  async function remover(o: Ouvinte) {
    setRemovendo(true);
    try {
      const removido = await api<Ouvinte>(
        `/defesas/${defesaId}/ouvintes/${o.id}`,
        { metodo: "DELETE" },
      );
      setDesfazer(removido);
      aoMudar();
    } catch (falha) {
      setGeral((falha as ErroApi).message);
    } finally {
      setRemovendo(false);
      setConfirmar(null);
    }
  }

  async function voltar(o: Ouvinte) {
    try {
      await api<Ouvinte>(`/defesas/${defesaId}/ouvintes`, {
        metodo: "POST",
        corpo: { nome: o.nome, matricula: o.matricula ?? "" },
      });
      setDesfazer(null);
      aoMudar();
    } catch (falha) {
      setGeral((falha as ErroApi).message);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-medium">Ouvintes presentes</h3>
        <span className="text-sm text-suave" aria-live="polite">
          {ouvintes.length} registrados · {dados.prontos} prontos para
          declaração
        </span>
      </div>

      <form
        onSubmit={adicionar}
        noValidate
        className="grid items-start gap-3 sm:grid-cols-[1fr_12rem_auto]"
      >
        <Campo rotulo="Nome completo" obrigatorio erro={erros.nome}>
          <Entrada
            id="ouvinte-nome"
            value={novo.nome}
            erro={erros.nome}
            onChange={(e) => {
              setNovo({ ...novo, nome: e.target.value });
              setErros((x) => ({ ...x, nome: undefined }));
            }}
          />
        </Campo>
        <Campo rotulo="Matrícula" obrigatorio erro={erros.matricula}>
          <Entrada
            value={novo.matricula}
            inputMode="numeric"
            erro={erros.matricula}
            onChange={(e) => {
              setNovo({ ...novo, matricula: e.target.value });
              setErros((x) => ({ ...x, matricula: undefined }));
            }}
          />
        </Campo>
        <div className="sm:pt-6">
          <Botao type="submit" carregando={enviando}>
            <Icone nome="mais" className="size-4" /> Adicionar ouvinte
          </Botao>
        </div>
      </form>
      <p className="text-[13px] text-suave">
        A declaração de horas sai com o nome completo e a matrícula exatamente
        como estão aqui; confira antes de emitir.
      </p>

      <details className="text-sm">
        <summary className="cursor-pointer py-1 text-azul-forte">
          Colar uma lista (um por linha: nome; matrícula)
        </summary>
        <div className="mt-2 flex flex-col gap-2">
          <Campo rotulo="Lista de ouvintes">
            <textarea
              value={lote}
              rows={4}
              placeholder={"Maria Souza; 2026000011\nJoão Lima; 2026000012"}
              onChange={(e) => setLote(e.target.value)}
              className={`${AREA_TEXTO} border-borda`}
            />
          </Campo>
          {resultadoLote && (
            <Aviso
              tipo={
                resultadoLote.linhas_com_problema.length ? "alerta" : "sucesso"
              }
            >
              {resultadoLote.adicionados.length} ouvinte(s) adicionado(s).
              {resultadoLote.linhas_com_problema.length > 0 && (
                <ul className="mt-1 list-disc pl-5">
                  {resultadoLote.linhas_com_problema.map((l) => (
                    <li key={l.linha}>
                      Linha {l.linha} ({l.texto}): {l.motivo}
                    </li>
                  ))}
                </ul>
              )}
            </Aviso>
          )}
          <div>
            <Botao variante="contorno" pequeno onClick={adicionarLista}>
              Adicionar da lista
            </Botao>
          </div>
        </div>
      </details>

      {geral && <Aviso tipo="erro">{geral}</Aviso>}
      {desfazer && (
        <Aviso tipo="info">
          {desfazer.nome} saiu da lista.{" "}
          <button
            type="button"
            className="font-medium underline"
            onClick={() => voltar(desfazer)}
          >
            Desfazer
          </button>
        </Aviso>
      )}
      {!dados.pode_emitir && ouvintes.length > 0 && (
        <p className="text-[13px] text-suave">
          A declaração de horas pode ser emitida depois do horário de término da
          defesa.
        </p>
      )}

      {ouvintes.length === 0 ? (
        <p className="text-sm text-suave">
          Nenhum ouvinte registrado. Adicione nome e matrícula de quem assistiu
          à defesa; a lista alimenta a declaração de horas complementares.
        </p>
      ) : (
        <ul className="divide-y divide-borda rounded-lg border border-borda">
          {ouvintes.map((o) => (
            <LinhaOuvinte
              key={o.id}
              defesaId={defesaId}
              ouvinte={o}
              podeEmitir={dados.pode_emitir}
              outras={ouvintes
                .filter((x) => x.id !== o.id)
                .map((x) => x.matricula)}
              aoMudar={aoMudar}
              aoRemover={() => setConfirmar(o)}
            />
          ))}
        </ul>
      )}

      {confirmar && (
        <Modal titulo="Remover ouvinte?" aoFechar={() => setConfirmar(null)}>
          <p className="text-sm">
            {confirmar.nome} (matrícula {confirmar.matricula ?? "não informada"}
            ) sai da lista de ouvintes desta defesa e não recebe a declaração de
            horas.
          </p>
          <div className="mt-4 flex flex-wrap justify-end gap-2">
            <Botao
              variante="texto"
              onClick={() => setConfirmar(null)}
              disabled={removendo}
            >
              Cancelar
            </Botao>
            <Botao
              variante="destrutivo"
              onClick={() => remover(confirmar)}
              carregando={removendo}
            >
              Remover
            </Botao>
          </div>
        </Modal>
      )}
    </div>
  );
}

function LinhaOuvinte({
  defesaId,
  ouvinte,
  podeEmitir,
  outras,
  aoMudar,
  aoRemover,
}: {
  defesaId: number;
  ouvinte: Ouvinte;
  podeEmitir: boolean;
  outras: (string | null)[];
  aoMudar: () => void;
  aoRemover: () => void;
}) {
  const [editando, setEditando] = useState(false);
  const [matricula, setMatricula] = useState(ouvinte.matricula ?? "");
  const [erro, setErro] = useState("");
  const [emitindo, setEmitindo] = useState(false);
  const emitida = ouvinte.declaracao;

  async function salvar() {
    if (!matriculaOk(matricula))
      return setErro("A matrícula deve ter só números (de 6 a 20 dígitos).");
    if (outras.includes(matricula.trim()))
      return setErro("Esta matrícula já está na lista.");
    try {
      await api<Ouvinte>(`/defesas/${defesaId}/ouvintes/${ouvinte.id}`, {
        metodo: "PUT",
        corpo: { matricula: matricula.trim() },
      });
      setEditando(false);
      setErro("");
      aoMudar();
    } catch (falha) {
      setErro((falha as ErroApi).message);
    }
  }

  async function emitir() {
    setEmitindo(true);
    setErro("");
    try {
      await api<Declaracao>(`/defesas/${defesaId}/declaracoes`, {
        metodo: "POST",
        corpo: { ouvinte_id: ouvinte.id },
      });
      aoMudar();
    } catch (falha) {
      const e = falha as ErroApi;
      if (e.campo === "matricula") setEditando(true); // E5: corrigir a matrícula (DS-FL09-A)
      setErro(e.message);
    } finally {
      setEmitindo(false);
    }
  }

  return (
    <li className="flex flex-col gap-2 p-3 text-sm sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
      <div className="min-w-0">
        <p className="font-medium break-words">{ouvinte.nome}</p>
        {editando ? (
          <div className="mt-2 flex flex-wrap items-start gap-2">
            <Campo rotulo={`Matrícula de ${ouvinte.nome}`} erro={erro}>
              <Entrada
                value={matricula}
                inputMode="numeric"
                erro={erro}
                onChange={(e) => setMatricula(e.target.value)}
              />
            </Campo>
          </div>
        ) : (
          <p className="flex flex-wrap items-center gap-2 text-suave">
            <span className="font-mono">
              {ouvinte.matricula || "sem matrícula"}
            </span>
            {!ouvinte.pronto && <Selo cor="ambar">Incompleta</Selo>}
          </p>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {emitida ? (
          <>
            <Selo cor="verde">Emitida</Selo>
            <a
              href={`/api/v1/defesas/${defesaId}/declaracoes/${emitida.id}/arquivo`}
              target="_blank"
              rel="noopener"
              className="text-sm font-medium text-azul-forte underline"
            >
              Abrir declaração
            </a>
          </>
        ) : ouvinte.pronto ? (
          <Selo cor="cinza">Pronta para emitir</Selo>
        ) : (
          <span className="text-[13px] text-suave">
            Corrija a matrícula para emitir
          </span>
        )}
        {editando ? (
          <>
            <Botao pequeno onClick={salvar}>
              Salvar
            </Botao>
            <Botao
              variante="texto"
              pequeno
              onClick={() => {
                setEditando(false);
                setMatricula(ouvinte.matricula ?? "");
                setErro("");
              }}
            >
              Cancelar
            </Botao>
          </>
        ) : (
          !emitida && (
            <>
              <Botao
                variante="contorno"
                pequeno
                onClick={() => setEditando(true)}
              >
                <Icone nome="lapis" className="size-4" /> Corrigir matrícula
              </Botao>
              {ouvinte.pronto && podeEmitir && (
                <Botao
                  variante="contorno"
                  pequeno
                  carregando={emitindo}
                  onClick={emitir}
                >
                  <Icone nome="documento" className="size-4" /> Emitir
                  declaração
                </Botao>
              )}
              <Botao variante="perigo" pequeno onClick={aoRemover}>
                <Icone nome="lixeira" className="size-4" /> Remover
              </Botao>
            </>
          )
        )}
      </div>
      {erro && !editando && (
        <p
          role="alert"
          className="w-full text-[13px] font-medium text-vermelho"
        >
          {erro}
        </p>
      )}
    </li>
  );
}
