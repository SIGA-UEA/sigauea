"use client";

// TEL18 · Divulgação na agenda (DS-FL05): condições para publicar, como a defesa aparece na agenda,
// "Publicar na agenda" e "Retirar da agenda". Quem pode publicar e o que falta vêm da API (RN09, RN14).

import { useEffect, useState } from "react";
import { Aviso, Selo } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Icone } from "@/components/icone";
import { Modal } from "@/components/modal";
import { api, ErroApi } from "@/lib/api";
import { dataCurta, NOME_FORMATO, type Divulgacao } from "@/lib/tipos";

const hora = (t: string) => t.slice(0, 5);

export function DivulgacaoNaAgenda({
  defesaId,
  aoMudar,
}: {
  defesaId: number;
  aoMudar: (publicada: boolean) => void;
}) {
  const [dados, setDados] = useState<Divulgacao | null>(null);
  const [erro, setErro] = useState("");
  const [pendencias, setPendencias] = useState<string[]>([]);
  const [janela, setJanela] = useState<"publicar" | "retirar" | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    api<Divulgacao>(`/defesas/${defesaId}/divulgacao`).then(setDados).catch((e: ErroApi) => setErro(e.message));
  }, [defesaId]);

  async function enviar(acao: "publicacao" | "retirada") {
    setEnviando(true);
    setErro("");
    setPendencias([]);
    try {
      const novo = await api<Divulgacao>(`/defesas/${defesaId}/${acao}`, { metodo: "POST" });
      setDados(novo);
      aoMudar(novo.publicada);
    } catch (e) {
      const falha = e as ErroApi & { pendencias?: string[] };
      setErro(falha.message);
      setPendencias(falha.pendencias ?? []);
    } finally {
      setEnviando(false);
      setJanela(null);
    }
  }

  return (
    <div className="flex flex-col gap-4 border-t border-borda pt-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold">Divulgação na agenda</h3>
        {dados && <Selo cor={dados.publicada ? "verde" : "cinza"}>{dados.publicada ? "Publicada" : "Não publicada"}</Selo>}
      </div>

      {erro && (
        <Aviso tipo="erro">
          {erro}
          {pendencias.length > 0 && (
            <ul className="mt-1 list-disc pl-5">
              {pendencias.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          )}
        </Aviso>
      )}

      {!dados ? (
        !erro && (
          <p role="status" className="text-sm text-suave">
            Carregando…
          </p>
        )
      ) : dados.situacao === "CANCELADA" ? (
        <Aviso tipo="info">Esta defesa foi cancelada.</Aviso>
      ) : (
        <>
          <section>
            <h4 className="mb-2 text-sm font-medium">Condições para publicar</h4>
            <ul className="flex flex-col gap-1.5 text-sm">
              {dados.condicoes.map((c) => (
                <li key={c.descricao} className="flex items-center gap-2">
                  <Icone nome={c.atendida ? "certo" : "alerta"} className={`size-4 ${c.atendida ? "text-verde" : "text-ambar"}`} />
                  <span>{c.descricao}</span>
                  <span className="sr-only">{c.atendida ? "atendida" : "pendente"}</span>
                </li>
              ))}
            </ul>
          </section>

          {dados.previa && (
            <section>
              <h4 className="mb-2 text-sm font-medium">Como aparece na agenda</h4>
              <div className="rounded-lg border border-borda p-3 text-sm">
                <p className="font-medium">{dados.previa.titulo}</p>
                <p className="text-suave">{dados.previa.autor}</p>
                <p className="mt-1 text-suave">
                  {dataCurta(dados.previa.data)}, das {hora(dados.previa.inicio)} às {hora(dados.previa.fim)} ·{" "}
                  {dados.previa.curso.sigla} · {NOME_FORMATO[dados.previa.formato]} ·{" "}
                  {dados.previa.local ?? (dados.previa.link ? "Link divulgado" : "Link enviado aos participantes")}
                </p>
              </div>
              <p className="mt-1 text-xs text-suave">A agenda não mostra notas, matrícula nem contatos.</p>
            </section>
          )}

          {!dados.pode_publicar ? (
            <Aviso tipo="info">Somente leitura: quem publica na agenda é o responsável pelo agendamento ou a coordenação.</Aviso>
          ) : dados.publicada ? (
            <div>
              <Botao variante="contorno" onClick={() => setJanela("retirar")}>
                Retirar da agenda
              </Botao>
            </div>
          ) : (
            <div>
              <Botao onClick={() => setJanela("publicar")} disabled={dados.condicoes.some((c) => !c.atendida)}>
                Publicar na agenda
              </Botao>
            </div>
          )}
        </>
      )}

      {janela === "publicar" && (
        <Modal titulo="Publicar na agenda?" aoFechar={() => setJanela(null)}>
          <p className="text-sm">A apresentação passa a aparecer na agenda para os usuários do sistema, sem notas, matrícula nem contatos.</p>
          <div className="mt-5 flex justify-end gap-2">
            <Botao variante="texto" onClick={() => setJanela(null)}>
              Cancelar
            </Botao>
            <Botao carregando={enviando} onClick={() => enviar("publicacao")}>
              Publicar
            </Botao>
          </div>
        </Modal>
      )}
      {janela === "retirar" && (
        <Modal titulo="Retirar da agenda?" aoFechar={() => setJanela(null)}>
          <p className="text-sm">A defesa continua marcada: ela só deixa de aparecer na agenda.</p>
          <div className="mt-5 flex justify-end gap-2">
            <Botao variante="texto" onClick={() => setJanela(null)}>
              Cancelar
            </Botao>
            <Botao carregando={enviando} onClick={() => enviar("retirada")}>
              Confirmar
            </Botao>
          </div>
        </Modal>
      )}
    </div>
  );
}
