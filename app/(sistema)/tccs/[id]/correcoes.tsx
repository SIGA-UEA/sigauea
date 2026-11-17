"use client";

// TEL14 · Correções e conclusão do TCC (DS-FL07, DS-FL07-A a DS-FL07-D · RBN11.01 a RBN11.04), na página do TCC.
//   GET  /tccs/{id}/correcoes                  prazo, correções, versão final e o que falta para concluir
//   POST /tccs/{id}/correcoes                  membro da banca registra uma exigência
//   POST /tccs/{id}/correcoes/anuencia         aluno dá anuência às correções (libera a Folha de Aprovação)
//   POST /correcoes/{id}/atendida              aluno marca a correção como atendida
//   POST /tccs/{id}/correcoes/versao-final     aluno envia o PDF da versão final (até 20 MB)
//   GET  /tccs/{id}/correcoes/versao-final     baixa a versão final, conferida pelo SHA-256
//   POST /correcoes/{id}/decisao               professor responsável aprova ou devolve com justificativa
//   POST /tccs/{id}/correcoes/atraso           professor responsável aceita ou recusa a entrega com atraso
//   POST /tccs/{id}/correcoes/prazo            professor responsável muda o prazo com motivo
// A seção só aparece depois que o resultado da defesa é confirmado; cada botão aparece para quem pode usá-lo,
// e a API confere tudo de novo. Quando a última condição é satisfeita, o TCC passa a Concluído (RBN11.04).

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { Aviso, Selo } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Campo, Entrada } from "@/components/campo";
import { Modal } from "@/components/modal";
import { api, ErroApi } from "@/lib/api";
import {
  dataCurta,
  dataHora,
  NOME_SITUACAO_CORRECAO,
  type CorrecaoTcc,
  type Correcoes,
  type SituacaoCorrecao,
} from "@/lib/tipos";

const AREA_TEXTO =
  "w-full min-w-0 rounded-lg border bg-superficie px-3 py-2 text-[14px] leading-relaxed placeholder:text-suave";
const LIMITE_PDF = 20 * 1024 * 1024;

/** Tamanho do arquivo em KB abaixo de 1 MB (um PDF pequeno não aparece como "0.0 MB"). */
const tamanho = (bytes: number) =>
  bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024)).toLocaleString("pt-BR")} KB`
    : `${(bytes / 1024 / 1024).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} MB`;

const COR: Record<SituacaoCorrecao, "cinza" | "azul" | "verde" | "ambar"> = {
  PENDENTE: "cinza",
  ATENDIDA: "azul",
  APROVADA: "verde",
  DEVOLVIDA: "ambar",
};

// `recarga` muda quando o resultado é confirmado ou retificado nesta página; `aoConcluir` atualiza a capa do TCC.
export function SecaoCorrecoes({
  tccId,
  recarga = 0,
  aoConcluir,
}: {
  tccId: string;
  recarga?: number;
  aoConcluir?: () => void;
}) {
  const [dados, setDados] = useState<Correcoes | null>(null);
  const [oculta, setOculta] = useState(false);
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");
  const concluido = useRef<boolean | null>(null);
  // Em ref: a página recria o callback a cada render, e ele não pode disparar uma nova busca.
  const aoConcluirRef = useRef(aoConcluir);
  useEffect(() => {
    aoConcluirRef.current = aoConcluir;
  }, [aoConcluir]);

  const aplicar = useCallback((d: Correcoes, mensagem = "") => {
    setDados(d);
    setErro("");
    setAviso(mensagem);
    const agora = d.situacao_tcc === "CONCLUIDO";
    if (concluido.current === false && agora) aoConcluirRef.current?.(); // a capa do TCC passa a "Concluído"
    concluido.current = agora;
  }, []);

  useEffect(() => {
    api<Correcoes>(`/tccs/${tccId}/correcoes`)
      .then((d) => aplicar(d))
      .catch((e: ErroApi) => (e.status === 403 || e.status === 404 ? setOculta(true) : setErro(e.message)));
  }, [tccId, recarga, aplicar]);

  // Ações devolvem a consulta atualizada; o erro aparece no topo da seção.
  const agir = useCallback(
    async (caminho: string, corpo?: unknown, mensagem = "") => {
      try {
        aplicar(await api<Correcoes>(caminho, { metodo: "POST", corpo }), mensagem);
        return true;
      } catch (e) {
        setAviso("");
        setErro((e as ErroApi).message);
        return false;
      }
    },
    [aplicar],
  );

  if (oculta || (dados && dados.resultado === null)) return null;

  return (
    <section className="rounded-xl border border-borda bg-superficie p-5" aria-labelledby="titulo-correcoes">
      <h2 id="titulo-correcoes" className="mb-1 font-semibold">
        Correções e conclusão
      </h2>
      {!dados ? (
        erro ? (
          <Aviso tipo="erro">{erro}</Aviso>
        ) : (
          <p role="status" className="text-sm text-suave">
            Carregando…
          </p>
        )
      ) : (
        <div className="flex flex-col gap-5">
          <Condicoes dados={dados} />
          {erro && <Aviso tipo="erro">{erro}</Aviso>}
          {aviso && <Aviso tipo="sucesso">{aviso}</Aviso>}

          <Prazo dados={dados} tccId={tccId} agir={agir} />

          {dados.resultado === "APROVADO_COM_CORRECOES" && (
            <>
              {dados.permissoes.dar_anuencia && <Anuencia tccId={tccId} agir={agir} />}
              {dados.anuencia_em && (
                <p className="text-[13px] text-suave">Anuência às correções registrada em {dataHora(dados.anuencia_em)}.</p>
              )}
              <ListaCorrecoes dados={dados} agir={agir} />
              {dados.permissoes.registrar && <NovaExigencia tccId={tccId} agir={agir} />}
            </>
          )}

          <VersaoFinalBloco dados={dados} tccId={tccId} aplicar={aplicar} agir={agir} setErro={setErro} />
        </div>
      )}
    </section>
  );
}

type Agir = (caminho: string, corpo?: unknown, mensagem?: string) => Promise<boolean>;

// ---------------------------------------------------------------- DS-FL07-C · condições para concluir

function Condicoes({ dados }: { dados: Correcoes }) {
  if (dados.situacao_tcc === "CONCLUIDO")
    return (
      <Aviso tipo="sucesso">
        <p className="font-semibold">TCC concluído em {dataHora(dados.concluido_em)}.</p>
        <p>Resultado confirmado, correções aprovadas e versão final enviada.</p>
      </Aviso>
    );
  if (dados.resultado === "REPROVADO") return <Aviso tipo="erro">{dados.pendencias[0]}</Aviso>;
  return (
    <div className="rounded-lg border border-borda bg-fundo px-4 py-3 text-sm">
      <p className="mb-1 font-medium">Para concluir o TCC, falta:</p>
      <ul className="list-disc pl-5 text-suave">
        {dados.pendencias.map((p) => (
          <li key={p}>{p}</li>
        ))}
      </ul>
    </div>
  );
}

// ---------------------------------------------------------------- RBN11.01 · prazo (DS-FL07-D, A1)

function Prazo({ dados, tccId, agir }: { dados: Correcoes; tccId: string; agir: Agir }) {
  const [aberto, setAberto] = useState(false);
  const [prazo, setPrazo] = useState(dados.prazo ?? "");
  const [motivo, setMotivo] = useState("");
  const [erro, setErro] = useState("");
  const [erroPrazo, setErroPrazo] = useState("");
  const [enviando, setEnviando] = useState(false);
  // hoje no horário de Manaus (AAAA-MM-DD), a mesma referência da API para recusar prazo já passado
  const hoje = new Date().toLocaleDateString("en-CA", { timeZone: "America/Manaus" });

  async function salvar(e: FormEvent) {
    e.preventDefault();
    setErro("");
    setErroPrazo("");
    if (!prazo) return setErroPrazo("Escolha a nova data.");
    if (prazo < hoje) return setErroPrazo("O novo prazo não pode ser anterior a hoje.");
    if (!motivo.trim()) return setErro("Informe o motivo da alteração do prazo.");
    setEnviando(true);
    const ok = await agir(`/tccs/${tccId}/correcoes/prazo`, { prazo, motivo }, "Prazo da versão final alterado.");
    setEnviando(false);
    if (ok) {
      setAberto(false);
      setMotivo("");
    }
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
      <p>
        <span className="text-suave">Prazo da versão final: </span>
        <b className="font-semibold">{dados.prazo ? dataCurta(dados.prazo) : "não definido no calendário"}</b>
        {dados.prazo_motivo && <span className="text-suave"> · alterado: {dados.prazo_motivo}</span>}
        <span className="block text-[13px] text-suave">
          Professor responsável pela turma: {dados.professor_responsavel.nome}
        </span>
      </p>
      {dados.permissoes.alterar_prazo && (
        <Botao variante="contorno" pequeno onClick={() => setAberto(true)}>
          Alterar prazo
        </Botao>
      )}
      {aberto && (
        <Modal titulo="Alterar o prazo da versão final" aoFechar={() => setAberto(false)}>
          <form onSubmit={salvar} className="flex flex-col gap-4">
            <Campo rotulo="Novo prazo" obrigatorio erro={erroPrazo}>
              <Entrada type="date" min={hoje} value={prazo} onChange={(e) => setPrazo(e.target.value)} />
            </Campo>
            <Campo rotulo="Motivo" obrigatorio erro={erro}>
              <textarea
                value={motivo}
                rows={3}
                maxLength={500}
                onChange={(e) => setMotivo(e.target.value)}
                className={`${AREA_TEXTO} ${erro ? "border-vermelho" : "border-borda"}`}
              />
            </Campo>
            <div className="flex justify-end gap-2">
              <Botao variante="texto" onClick={() => setAberto(false)}>
                Voltar
              </Botao>
              <Botao type="submit" carregando={enviando}>
                Salvar prazo
              </Botao>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- RBN09.15 · anuência (DS-FL07, mensagens 6 a 8)

function Anuencia({ tccId, agir }: { tccId: string; agir: Agir }) {
  const [li, setLi] = useState(false);
  const [enviando, setEnviando] = useState(false);
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-azul-borda bg-azul-claro px-4 py-3 text-sm">
      <label className="flex items-start gap-2">
        <input type="checkbox" checked={li} onChange={(e) => setLi(e.target.checked)} className="mt-1" />
        <span>Li as correções exigidas e estou de acordo.</span>
      </label>
      <div>
        <Botao
          pequeno
          disabled={!li}
          carregando={enviando}
          onClick={async () => {
            setEnviando(true);
            await agir(`/tccs/${tccId}/correcoes/anuencia`, undefined, "Anuência registrada. Folha de Aprovação liberada.");
            setEnviando(false);
          }}
        >
          Dar anuência
        </Botao>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- RBN11.01 a RBN11.03 · lista de correções

function ListaCorrecoes({ dados, agir }: { dados: Correcoes; agir: Agir }) {
  const [devolvendo, setDevolvendo] = useState<CorrecaoTcc | null>(null);
  const [ocupado, setOcupado] = useState<number | null>(null);

  async function acao(c: CorrecaoTcc, caminho: string, corpo?: unknown, mensagem?: string) {
    setOcupado(c.id);
    await agir(caminho, corpo, mensagem);
    setOcupado(null);
  }

  if (dados.correcoes.length === 0)
    return <p className="text-sm text-suave">A banca ainda não registrou as correções exigidas.</p>;

  return (
    <>
      <ul className="divide-y divide-borda rounded-lg border border-borda">
        {dados.correcoes.map((c) => (
          <li key={c.id} className="flex flex-col gap-2 px-4 py-3 text-sm">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <p className="min-w-0 flex-1 break-words whitespace-pre-wrap">{c.descricao}</p>
              <Selo cor={COR[c.situacao]}>{NOME_SITUACAO_CORRECAO[c.situacao]}</Selo>
            </div>
            <p className="text-[13px] text-suave">
              Exigida por {c.avaliador.nome} em {dataHora(c.criada_em)}
              {c.decidida_por && ` · decidida por ${c.decidida_por.nome} em ${dataHora(c.decidida_em)}`}
            </p>
            {c.situacao === "DEVOLVIDA" && c.justificativa && (
              <p className="rounded-md bg-ambar-claro px-3 py-2 text-[13px] text-ambar">O que falta: {c.justificativa}</p>
            )}
            <div className="flex flex-wrap gap-2">
              {dados.permissoes.marcar_atendida && (c.situacao === "PENDENTE" || c.situacao === "DEVOLVIDA") && (
                <Botao
                  variante="contorno"
                  pequeno
                  carregando={ocupado === c.id}
                  onClick={() => acao(c, `/correcoes/${c.id}/atendida`, undefined, "Correção marcada como atendida.")}
                >
                  Marcar como atendida
                </Botao>
              )}
              {dados.permissoes.decidir && c.situacao === "ATENDIDA" && (
                <>
                  <Botao
                    pequeno
                    carregando={ocupado === c.id}
                    onClick={() =>
                      acao(c, `/correcoes/${c.id}/decisao`, { decisao: "APROVAR" }, "Correção aprovada.")
                    }
                  >
                    Aprovar
                  </Botao>
                  <Botao variante="perigo" pequeno onClick={() => setDevolvendo(c)}>
                    Devolver
                  </Botao>
                </>
              )}
            </div>
          </li>
        ))}
      </ul>
      {devolvendo && <Devolver correcao={devolvendo} agir={agir} aoFechar={() => setDevolvendo(null)} />}
    </>
  );
}

function Devolver({ correcao, agir, aoFechar }: { correcao: CorrecaoTcc; agir: Agir; aoFechar: () => void }) {
  const [texto, setTexto] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function devolver(e: FormEvent) {
    e.preventDefault();
    if (!texto.trim()) return setErro("Escreva o que falta corrigir.");
    setEnviando(true);
    const ok = await agir(
      `/correcoes/${correcao.id}/decisao`,
      { decisao: "DEVOLVER", justificativa: texto },
      "Correção devolvida ao aluno.",
    );
    setEnviando(false);
    if (ok) aoFechar();
  }

  return (
    <Modal titulo="Devolver a correção" aoFechar={aoFechar}>
      <form onSubmit={devolver} className="flex flex-col gap-4 text-sm">
        <p className="text-suave">{correcao.descricao}</p>
        <Campo rotulo="O que falta corrigir" obrigatorio erro={erro}>
          <textarea
            value={texto}
            rows={4}
            maxLength={1000}
            onChange={(e) => setTexto(e.target.value)}
            className={`${AREA_TEXTO} ${erro ? "border-vermelho" : "border-borda"}`}
          />
        </Campo>
        <div className="flex justify-end gap-2">
          <Botao variante="texto" onClick={aoFechar}>
            Voltar
          </Botao>
          <Botao type="submit" variante="destrutivo" carregando={enviando}>
            Devolver
          </Botao>
        </div>
      </form>
    </Modal>
  );
}

// DS-FL07-A: o membro da banca descreve a correção (10 caracteres ou mais) e adiciona a exigência.
function NovaExigencia({ tccId, agir }: { tccId: string; agir: Agir }) {
  const [texto, setTexto] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function adicionar(e: FormEvent) {
    e.preventDefault();
    if (texto.trim().length < 10) return setErro("Descreva a correção com ao menos 10 caracteres.");
    setErro("");
    setEnviando(true);
    const ok = await agir(`/tccs/${tccId}/correcoes`, { descricao: texto }, "Exigência registrada. O aluno foi avisado.");
    setEnviando(false);
    if (ok) setTexto("");
  }

  return (
    <form onSubmit={adicionar} className="flex flex-col gap-2">
      <Campo rotulo="Registrar nova exigência" erro={erro}>
        <textarea
          value={texto}
          rows={3}
          maxLength={1000}
          placeholder="Ex.: Revisar as referências conforme a ABNT."
          onChange={(e) => setTexto(e.target.value)}
          className={`${AREA_TEXTO} ${erro ? "border-vermelho" : "border-borda"}`}
        />
      </Campo>
      <div>
        <Botao type="submit" variante="contorno" pequeno carregando={enviando}>
          Adicionar exigência
        </Botao>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------- RBN11.02 · versão final e atraso

function VersaoFinalBloco({
  dados,
  tccId,
  aplicar,
  agir,
  setErro,
}: {
  dados: Correcoes;
  tccId: string;
  aplicar: (d: Correcoes, mensagem?: string) => void;
  agir: Agir;
  setErro: (m: string) => void;
}) {
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [erroArquivo, setErroArquivo] = useState("");
  const [enviando, setEnviando] = useState(false);
  const v = dados.versao_final;

  function escolher(f: File | null) {
    setArquivo(null);
    setErroArquivo("");
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".pdf")) return setErroArquivo("Escolha um arquivo PDF.");
    if (f.size === 0) return setErroArquivo("O arquivo está vazio.");
    if (f.size > LIMITE_PDF) return setErroArquivo("O arquivo passa de 20 MB.");
    setArquivo(f);
  }

  async function enviar() {
    if (!arquivo) return;
    const corpo = new FormData();
    corpo.append("arquivo", arquivo);
    setEnviando(true);
    try {
      const d = await api<Correcoes>(`/tccs/${tccId}/correcoes/versao-final`, { metodo: "POST", corpo });
      aplicar(d, d.situacao_tcc === "CONCLUIDO" ? "TCC concluído." : "Documento enviado. A nova versão é a vigente.");
      setArquivo(null);
    } catch (e) {
      setErro((e as ErroApi).message);
    } finally {
      setEnviando(false);
    }
  }

  if (dados.resultado === "REPROVADO") return null;

  return (
    <div className="flex flex-col gap-3 border-t border-borda pt-4 text-sm">
      <h3 className="font-semibold">Versão final</h3>
      {v ? (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <a
            href={`/api/v1/tccs/${tccId}/correcoes/versao-final`}
            className="font-medium break-all text-azul-forte hover:underline"
          >
            {v.nome_arquivo}
          </a>
          <span className="text-suave">
            versão {v.versao} · enviada em {dataHora(v.enviado_em)} · {tamanho(v.tamanho_bytes)}
          </span>
          {v.entregue_com_atraso && (
            <Selo cor={v.atraso_aceito === null ? "ambar" : v.atraso_aceito ? "verde" : "vermelho"}>
              {v.atraso_aceito === null
                ? "Entregue com atraso"
                : v.atraso_aceito
                  ? "Atraso aceito"
                  : "Atraso recusado"}
            </Selo>
          )}
        </div>
      ) : (
        <p className="text-suave">Ainda não enviada.</p>
      )}

      {v?.entregue_com_atraso && v.atraso_aceito === null && dados.permissoes.decidir && (
        <div className="flex flex-wrap items-center gap-2 rounded-lg border border-ambar/25 bg-ambar-claro px-4 py-3">
          <span className="flex-1">A versão final foi entregue depois do prazo. Aceita a entrega?</span>
          <Botao pequeno onClick={() => agir(`/tccs/${tccId}/correcoes/atraso`, { aceita: true }, "Entrega com atraso aceita.")}>
            Aceitar
          </Botao>
          <Botao
            variante="perigo"
            pequeno
            onClick={() => agir(`/tccs/${tccId}/correcoes/atraso`, { aceita: false }, "Entrega com atraso recusada.")}
          >
            Recusar
          </Botao>
        </div>
      )}

      {dados.permissoes.enviar_versao_final && (
        <div className="flex flex-col gap-2">
          <Campo rotulo={v ? "Enviar nova versão final" : "Enviar versão final"} dica="PDF de até 20 MB" erro={erroArquivo}>
            <input
              type="file"
              accept="application/pdf,.pdf"
              onChange={(e) => escolher(e.target.files?.[0] ?? null)}
              className="text-sm file:mr-3 file:rounded-full file:border file:border-borda file:bg-superficie file:px-3 file:py-1.5 file:text-azul-forte"
            />
          </Campo>
          {arquivo && (
            <p className="text-[13px] text-verde">
              Arquivo válido. Será criada a versão final v{(v?.versao ?? 0) + 1}.
            </p>
          )}
          <div>
            <Botao pequeno disabled={!arquivo} carregando={enviando} onClick={enviar}>
              Enviar documento
            </Botao>
          </div>
        </div>
      )}
    </div>
  );
}
