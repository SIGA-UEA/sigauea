"use client";

// TEL08 · Solicitações de orientação, seguindo os diagramas:
//   DS-FL03    GET  /orientacoes?status=PENDENTE   lista o que espera resposta
//   DS-FL03-A  POST /orientacoes/{id}/resposta     aceita ou recusa (recusa exige motivo; 409 se já respondida)

import Link from "next/link";
import { useEffect, useState } from "react";
import { Aviso, type TipoAviso } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Campo, ESTILO_ENTRADA } from "@/components/campo";
import { Modal } from "@/components/modal";
import { SeloOrientacao, SeloSituacao } from "@/components/situacao-tcc";
import { api, ErroApi } from "@/lib/api";
import { dataHora, type Solicitacao } from "@/lib/tipos";

type Aba = "PENDENTE" | "respondidas";

export default function PaginaOrientacoes() {
  const [aba, setAba] = useState<Aba>("PENDENTE");
  const [lista, setLista] = useState<Solicitacao[] | null>(null);
  const [versao, setVersao] = useState(0);
  const [aviso, setAviso] = useState<{ tipo: TipoAviso; texto: string } | null>(null);
  const [recusando, setRecusando] = useState<Solicitacao | null>(null);
  const [motivo, setMotivo] = useState("");
  const [erroMotivo, setErroMotivo] = useState("");
  const [ocupado, setOcupado] = useState<number | null>(null);

  useEffect(() => {
    const filtro = aba === "PENDENTE" ? "?status=PENDENTE" : "";
    api<Solicitacao[]>(`/orientacoes${filtro}`)
      .then((l) => setLista(aba === "PENDENTE" ? l : l.filter((s) => s.status !== "PENDENTE")))
      .catch((e: ErroApi) => setAviso({ tipo: "erro", texto: e.message }));
  }, [aba, versao]);

  async function responder(s: Solicitacao, decisao: "ACEITAR" | "RECUSAR", texto?: string) {
    setOcupado(s.id);
    try {
      await api(`/orientacoes/${s.id}/resposta`, { metodo: "POST", corpo: { decisao, motivo: texto || null } });
      setAviso({
        tipo: "sucesso",
        texto:
          decisao === "ACEITAR"
            ? `Orientação de ${s.tcc.aluno.nome} aceita. O aluno foi avisado por e-mail.`
            : `Solicitação de ${s.tcc.aluno.nome} recusada. O aluno foi avisado e pode indicar outro orientador.`,
      });
      setRecusando(null);
      setMotivo("");
    } catch (e) {
      const erro = e as ErroApi;
      if (recusando && erro.campos?.motivo) setErroMotivo(erro.campos.motivo);
      else {
        setAviso({ tipo: "erro", texto: erro.message });
        setRecusando(null);
      }
    }
    setOcupado(null);
    setVersao((v) => v + 1);
  }

  function confirmarRecusa() {
    if (!recusando) return;
    if (!motivo.trim()) return setErroMotivo("Informe o motivo da recusa; o aluno vai recebê-lo.");
    responder(recusando, "RECUSAR", motivo.trim());
  }

  return (
    <div className="flex flex-col gap-5">
      <header>
        <h1 className="text-2xl font-semibold">Orientações</h1>
        <p className="mt-1 text-sm text-suave">
          Pedidos de orientação feitos pelos alunos no cadastro do TCC. O aluno só envia o cadastro depois do seu aceite.
        </p>
      </header>

      <div role="tablist" className="flex gap-1 border-b border-borda">
        {(
          [
            ["PENDENTE", "Aguardando resposta"],
            ["respondidas", "Respondidas"],
          ] as const
        ).map(([valor, rotulo]) => (
          <button
            key={valor}
            role="tab"
            aria-selected={aba === valor}
            onClick={() => {
              setLista(null);
              setAba(valor);
            }}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
              aba === valor ? "border-azul text-azul-forte" : "border-transparent text-suave hover:text-texto"
            }`}
          >
            {rotulo}
          </button>
        ))}
      </div>

      {aviso && <Aviso tipo={aviso.tipo}>{aviso.texto}</Aviso>}

      {!lista ? (
        <p role="status" className="text-sm text-suave">
          Carregando…
        </p>
      ) : lista.length === 0 ? (
        <p className="rounded-xl border border-borda bg-superficie p-6 text-sm text-suave">
          {aba === "PENDENTE" ? "Nenhum pedido aguardando a sua resposta." : "Nenhum pedido respondido ainda."}
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {lista.map((s) => (
            <li key={s.id} className="flex flex-col gap-3 rounded-xl border border-borda bg-superficie p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="font-medium break-words">{s.tcc.titulo}</p>
                  <p className="text-sm text-suave">
                    {s.tcc.aluno.nome} · {s.tcc.curso.sigla} · {s.tcc.etapa} ·{" "}
                    {s.tcc.modalidade === "ARTIGO" ? "Artigo" : "Monografia"} · {s.tcc.area.nome}
                  </p>
                  <p className="text-[13px] text-suave">
                    Como {s.papel === "ORIENTADOR" ? "orientador" : "coorientador"} · pedido em {dataHora(s.solicitado_em)}
                    {s.respondido_em && ` · respondido em ${dataHora(s.respondido_em)}`}
                  </p>
                </div>
                <div className="flex gap-1.5">
                  <SeloOrientacao status={s.status} />
                  <SeloSituacao situacao={s.tcc.situacao} />
                </div>
              </div>
              {s.tcc.resumo && <p className="line-clamp-3 text-sm">{s.tcc.resumo}</p>}
              {s.motivo_recusa && <p className="text-[13px] text-suave">Motivo da recusa: {s.motivo_recusa}</p>}
              <div className="flex flex-wrap items-center justify-between gap-2">
                <Link href={`/tccs/${s.tcc.id}`} className="text-sm font-medium text-azul-forte hover:underline">
                  Ver cadastro
                </Link>
                {s.status === "PENDENTE" && (
                  <div className="flex gap-2">
                    <Botao
                      variante="perigo"
                      disabled={ocupado !== null}
                      onClick={() => {
                        setErroMotivo("");
                        setRecusando(s);
                      }}
                    >
                      Recusar
                    </Botao>
                    <Botao carregando={ocupado === s.id} disabled={ocupado !== null} onClick={() => responder(s, "ACEITAR")}>
                      Aceitar orientação
                    </Botao>
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {recusando && (
        <Modal titulo="Recusar orientação" aoFechar={() => setRecusando(null)}>
          <p className="mb-4 text-sm">
            O pedido de <strong>{recusando.tcc.aluno.nome}</strong> será recusado e o aluno poderá indicar outro
            orientador.
          </p>
          <Campo rotulo="Motivo" obrigatorio erro={erroMotivo}>
            <textarea
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
              rows={4}
              maxLength={1000}
              aria-invalid={erroMotivo ? true : undefined}
              className={`${ESTILO_ENTRADA} h-auto py-2 ${erroMotivo ? "border-vermelho" : "border-borda"}`}
            />
          </Campo>
          <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Botao variante="texto" onClick={() => setRecusando(null)}>
              Cancelar
            </Botao>
            <Botao variante="destrutivo" carregando={ocupado === recusando.id} onClick={confirmarRecusa}>
              Recusar pedido
            </Botao>
          </div>
        </Modal>
      )}
    </div>
  );
}
