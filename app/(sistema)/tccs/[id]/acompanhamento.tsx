"use client";

// RBN05.02 a RBN05.05: situação com motivo (desistência e reativação), tarefas do orientador e histórico
// cronológico. As rotas daqui não valem para a pessoa externa (403); a página não monta estas seções para ela.

import { useCallback, useEffect, useState } from "react";
import { Aviso, Selo } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Campo, Entrada } from "@/components/campo";
import { Modal } from "@/components/modal";
import { api, ErroApi } from "@/lib/api";
import { useSessao } from "@/lib/sessao";
import { dataCurta, dataHora, type Evento, type StatusTarefa, type Tarefa, type Tcc } from "@/lib/tipos";

const COR_TAREFA: Record<StatusTarefa, "ambar" | "verde" | "vermelho"> = {
  PENDENTE: "ambar",
  ENTREGUE: "verde",
  ATRASADA: "vermelho",
};
const NOME_TAREFA: Record<StatusTarefa, string> = { PENDENTE: "Pendente", ENTREGUE: "Entregue", ATRASADA: "Atrasada" };
const ROTULO_EVENTO = { SUBMISSAO: "Envio", PARECER: "Parecer", VINCULO: "Orientação", VERSAO: "Versão", SITUACAO: "Situação" } as const;

const textoErro = (e: unknown) => (e as ErroApi).message;

/** Situação com motivo: o orientador que aceitou o vínculo e o professor da turma registram a desistência ou a reativação. */
export function SecaoSituacao({ tcc, aoMudar }: { tcc: Tcc; aoMudar: () => void }) {
  const { usuario } = useSessao();
  const [aberto, setAberto] = useState(false);
  const orientou =
    (tcc.orientador?.status === "ACEITA" && tcc.orientador.professor.id === usuario.id) ||
    tcc.turma.professor.id === usuario.id;
  const desistiu = tcc.situacao === "DESISTENCIA";
  const podeAlterar = orientou && (tcc.situacao === "APROVADO" || desistiu);

  if (!desistiu && !podeAlterar) return null;
  return (
    <section className="rounded-xl border border-borda bg-superficie p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-semibold">Situação do TCC</h2>
        {podeAlterar && (
          <Botao pequeno variante={desistiu ? "contorno" : "perigo"} onClick={() => setAberto(true)}>
            {desistiu ? "Reativar TCC" : "Registrar desistência"}
          </Botao>
        )}
      </div>
      {desistiu && (
        <p className="mt-2 text-sm whitespace-pre-wrap">
          <span className="text-suave">Motivo da desistência: </span>
          {tcc.desistencia_motivo ?? "—"}
        </p>
      )}
      {aberto && (
        <ModalSituacao
          tccId={tcc.id}
          reativar={desistiu}
          aoFechar={() => setAberto(false)}
          aoSalvar={() => (setAberto(false), aoMudar())}
        />
      )}
    </section>
  );
}

function ModalSituacao({
  tccId,
  reativar,
  aoFechar,
  aoSalvar,
}: {
  tccId: number;
  reativar: boolean;
  aoFechar: () => void;
  aoSalvar: () => void;
}) {
  const [motivo, setMotivo] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    if (!motivo.trim()) return setErro("Informe o motivo.");
    setEnviando(true);
    setErro("");
    try {
      await api(`/tccs/${tccId}/situacao`, {
        metodo: "PUT",
        corpo: { situacao: reativar ? "APROVADO" : "DESISTENCIA", motivo: motivo.trim() },
      });
      aoSalvar();
    } catch (e) {
      const campos = (e as ErroApi).campos;
      setErro(campos?.motivo ?? textoErro(e));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Modal titulo={reativar ? "Reativar TCC" : "Registrar desistência"} aoFechar={aoFechar}>
      <form onSubmit={enviar} noValidate className="flex flex-col gap-4">
        <Aviso tipo="alerta">
          {reativar
            ? "O TCC volta para a situação Aprovado. A mudança fica no histórico."
            : "O TCC passa para Desistência. Você poderá reativá-lo depois. A mudança fica no histórico."}
        </Aviso>
        <Campo rotulo="Motivo" obrigatorio erro={erro}>
          <Entrada value={motivo} onChange={(e) => setMotivo(e.target.value)} maxLength={500} erro={erro} />
        </Campo>
        <div className="flex justify-end gap-2">
          <Botao variante="texto" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao type="submit" carregando={enviando} variante={reativar ? "primario" : "destrutivo"}>
            Confirmar
          </Botao>
        </div>
      </form>
    </Modal>
  );
}

/** Tarefas e entregáveis (RBN05.05): o orientador e o professor da turma cadastram; todos que veem o TCC consultam. */
export function SecaoTarefas({ tcc }: { tcc: Tcc }) {
  const { usuario } = useSessao();
  const [lista, setLista] = useState<Tarefa[] | null>(null);
  const [erroLista, setErroLista] = useState("");
  const [descricao, setDescricao] = useState("");
  const [prazo, setPrazo] = useState("");
  const [erros, setErros] = useState<Record<string, string>>({});
  const [geral, setGeral] = useState("");
  const [enviando, setEnviando] = useState(false);

  const orientou = tcc.orientador?.status === "ACEITA" && tcc.orientador.professor.id === usuario.id;
  const podeCadastrar = (orientou || tcc.turma.professor.id === usuario.id) && tcc.situacao === "APROVADO";

  const carregar = useCallback(
    () =>
      api<Tarefa[]>(`/tccs/${tcc.id}/tarefas`)
        .then(setLista)
        .catch((e) => setErroLista(textoErro(e))),
    [tcc.id],
  );
  useEffect(() => {
    carregar();
  }, [carregar]);

  async function cadastrar(e: React.FormEvent) {
    e.preventDefault();
    const faltas: Record<string, string> = {};
    if (!descricao.trim()) faltas.descricao = "Descreva a tarefa.";
    if (!prazo) faltas.prazo = "Informe o prazo.";
    setErros(faltas);
    setGeral("");
    if (Object.keys(faltas).length) return;
    setEnviando(true);
    try {
      await api(`/tccs/${tcc.id}/tarefas`, { metodo: "POST", corpo: { descricao: descricao.trim(), prazo } });
      setDescricao("");
      setPrazo("");
      await carregar();
    } catch (e) {
      const erro = e as ErroApi;
      if (erro.campos) setErros(erro.campos);
      else setGeral(erro.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="rounded-xl border border-borda bg-superficie p-5">
      <h2 className="mb-3 font-semibold">Tarefas e entregáveis</h2>
      {erroLista && <Aviso tipo="erro">{erroLista}</Aviso>}
      {lista && lista.length === 0 && <p className="text-sm text-suave">Nenhuma tarefa cadastrada.</p>}
      {lista && lista.length > 0 && (
        <ul className="divide-y divide-borda text-sm">
          {lista.map((t) => (
            <li key={t.id} className="flex flex-wrap items-start justify-between gap-2 py-2.5">
              <div className="min-w-0 flex-1 basis-64">
                <p className="break-words whitespace-pre-wrap">{t.descricao}</p>
                <p className="text-suave">
                  Prazo {dataCurta(t.prazo)} · {t.cadastrada_por.nome}
                </p>
              </div>
              <Selo cor={COR_TAREFA[t.status]}>{NOME_TAREFA[t.status]}</Selo>
            </li>
          ))}
        </ul>
      )}
      {podeCadastrar && (
        <form onSubmit={cadastrar} noValidate className="mt-4 flex flex-col gap-3 border-t border-borda pt-4">
          {geral && <Aviso tipo="erro">{geral}</Aviso>}
          <div className="grid gap-3 sm:grid-cols-[1fr_11rem]">
            <Campo rotulo="Nova tarefa" obrigatorio erro={erros.descricao}>
              <Entrada value={descricao} onChange={(e) => setDescricao(e.target.value)} maxLength={300} erro={erros.descricao} />
            </Campo>
            <Campo rotulo="Prazo" obrigatorio erro={erros.prazo}>
              <Entrada type="date" value={prazo} onChange={(e) => setPrazo(e.target.value)} erro={erros.prazo} />
            </Campo>
          </div>
          <div>
            <Botao type="submit" pequeno carregando={enviando}>
              Cadastrar tarefa
            </Botao>
          </div>
        </form>
      )}
    </section>
  );
}

/** Histórico cronológico do TCC (RBN05.04): envio, pareceres, vínculos de orientação e mudanças de situação. */
export function SecaoHistorico({ tccId, versao }: { tccId: number; versao: string }) {
  const [eventos, setEventos] = useState<Evento[] | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<Evento[]>(`/tccs/${tccId}/historico`)
      .then(setEventos)
      .catch((e) => setErro(textoErro(e)));
  }, [tccId, versao]);

  return (
    <section className="rounded-xl border border-borda bg-superficie p-5">
      <h2 className="mb-3 font-semibold">Histórico</h2>
      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      {eventos && eventos.length === 0 && <p className="text-sm text-suave">Nada registrado ainda.</p>}
      {eventos && eventos.length > 0 && (
        <ol className="flex flex-col gap-3 border-l-2 border-borda pl-4 text-sm">
          {eventos.map((ev, i) => (
            <li key={i}>
              <p className="font-medium">
                <span className="mr-2 text-xs font-normal text-suave uppercase">{ROTULO_EVENTO[ev.tipo]}</span>
                {ev.descricao}
              </p>
              {ev.detalhe && <p className="mt-0.5 break-words whitespace-pre-wrap">{ev.detalhe}</p>}
              <p className="text-suave">
                {dataHora(ev.em)}
                {ev.autor && ` · ${ev.autor.nome}`}
              </p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
