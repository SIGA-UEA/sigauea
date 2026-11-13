"use client";

// TEL13 · Documentos da defesa, seção "Ata e certificados" (DS-FL06-C, DS-FL06-E e DS-FL06-F · RBN09.14 a
// RBN09.17, RN15), na página do TCC (TEL06).
//   GET  /defesas/{id}/documentos               ata, folha e certificados, com as versões e o que falta
//   POST /defesas/{id}/documentos/ata           gera a ata (nova versão; a anterior fica substituída)
//   POST /defesas/{id}/documentos/folha         gera a Folha de Aprovação (TCC2 ou artigo)
//   POST /defesas/{id}/documentos/certificados  emite e envia por e-mail os certificados escolhidos
//   POST /documentos/{id}/reenvio               reenvia o e-mail do certificado, sem gerar outro
//   GET  /documentos/{id}/arquivo               baixa o PDF (conferido pelo SHA-256)
// Quem gera e emite: a coordenação e o orientador. Aluno, banca e coordenação consultam e baixam; a folha só chega
// ao aluno depois de liberada e o certificado só ao próprio membro. Sem vínculo, a API responde 403 e nada aparece.

import { useCallback, useEffect, useState } from "react";
import { Aviso, Selo } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { api, ErroApi } from "@/lib/api";
import {
  dataHora,
  NOME_PAPEL_BANCA,
  type CertificadoParticipante,
  type DocumentoDefesa,
  type DocumentosDefesa,
  type SituacaoEnvio,
  type VersaoDocumento,
} from "@/lib/tipos";

const arquivo = (id: number) => `/api/v1/documentos/${id}/arquivo`;

const ENVIO: Record<SituacaoEnvio, { texto: string; cor: "verde" | "ambar" | "vermelho" | "cinza" }> = {
  NAO_ENVIADO: { texto: "Não enviado", cor: "cinza" },
  PENDENTE: { texto: "Enviando…", cor: "ambar" },
  ENVIADO: { texto: "Enviado por e-mail", cor: "verde" },
  FALHA: { texto: "Falha no envio", cor: "vermelho" },
};

// `recarga` muda quando o resultado é confirmado ou retificado nesta página: a seção se atualiza sozinha.
export function SecaoDocumentos({ defesaId, recarga = 0 }: { defesaId: number; recarga?: number }) {
  const [dados, setDados] = useState<DocumentosDefesa | null>(null);
  const [oculta, setOculta] = useState(false);
  const [erro, setErro] = useState("");

  const carregar = useCallback(
    () =>
      api<DocumentosDefesa>(`/defesas/${defesaId}/documentos`)
        .then((d) => {
          setDados(d);
          setErro("");
        })
        .catch((e: ErroApi) => (e.status === 403 || e.status === 404 ? setOculta(true) : setErro(e.message))),
    [defesaId],
  );

  useEffect(() => {
    carregar();
  }, [carregar, recarga]);

  if (oculta) return null;
  // Para quem só consulta, a seção aparece quando há algo para ver
  if (dados && !dados.pode_gerar && !dados.resultado_confirmado && dados.meus_certificados.length === 0) return null;

  return (
    <section className="rounded-xl border border-borda bg-superficie p-5" aria-labelledby="titulo-documentos">
      <h2 id="titulo-documentos" className="mb-1 font-semibold">
        Ata e certificados
      </h2>
      <p className="mb-4 text-[13px] text-suave">
        {dados?.pode_gerar
          ? "Gere a ata e a Folha de Aprovação e emita os certificados de participação."
          : "Documentos oficiais da defesa. Baixe a versão vigente; as substituídas ficam no histórico."}
      </p>
      {erro ? (
        <Aviso tipo="erro">{erro}</Aviso>
      ) : !dados ? (
        <p role="status" className="text-sm text-suave">
          Carregando…
        </p>
      ) : (
        <div className="flex flex-col gap-6">
          <Documento
            titulo="Ata da defesa"
            tipo="ata"
            doc={dados.ata}
            podeGerar={dados.pode_gerar}
            defesaId={defesaId}
            aoMudar={setDados}
          />
          {dados.folha.aplica ? (
            <Documento
              titulo="Folha de Aprovação"
              tipo="folha"
              doc={dados.folha}
              podeGerar={dados.pode_gerar}
              defesaId={defesaId}
              aoMudar={setDados}
            />
          ) : (
            <div>
              <h3 className="font-semibold">Folha de Aprovação</h3>
              <p className="text-sm text-suave">Aplica-se a TCC2 ou à modalidade artigo. Este TCC não exige a folha.</p>
            </div>
          )}
          {dados.pode_gerar && (
            <Certificados defesaId={defesaId} linhas={dados.certificados} aoMudar={setDados} recarregar={carregar} />
          )}
          {dados.meus_certificados.length > 0 && (
            <div>
              <h3 className="mb-2 font-semibold">Seu certificado de participação</h3>
              <a
                href={arquivo(dados.meus_certificados[0].id)}
                className="inline-flex h-8 items-center rounded-full border border-borda px-3 text-sm font-medium text-azul-forte hover:bg-azul-claro"
              >
                Baixar certificado
              </a>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------- DS-FL06-C · ata e Folha de Aprovação

function Documento({
  titulo,
  tipo,
  doc,
  podeGerar,
  defesaId,
  aoMudar,
}: {
  titulo: string;
  tipo: "ata" | "folha";
  doc: DocumentoDefesa;
  podeGerar: boolean;
  defesaId: number;
  aoMudar: (d: DocumentosDefesa) => void;
}) {
  const [gerando, setGerando] = useState(false);
  const [falhou, setFalhou] = useState(false);
  const [faltas, setFaltas] = useState<string[]>([]);
  const [aviso, setAviso] = useState("");
  const gerada = doc.versoes.length > 0;
  const nome = tipo === "ata" ? "ata" : "folha";

  const gerar = () => {
    setGerando(true);
    setFalhou(false);
    setAviso("");
    api<DocumentosDefesa>(`/defesas/${defesaId}/documentos/${tipo}`, { metodo: "POST" })
      .then((d) => {
        aoMudar(d);
        setFaltas([]);
        setAviso(`${tipo === "ata" ? "Ata gerada" : "Folha de Aprovação gerada"} em PDF.`);
      })
      .catch((e: ErroApi & { faltas?: string[] }) => {
        if (e.status === 409 && e.faltas) setFaltas(e.faltas);
        else setFalhou(true); // E2: "Não foi possível gerar o documento"
      })
      .finally(() => setGerando(false));
  };

  const lista = faltas.length ? faltas : doc.faltas;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-semibold">{titulo}</h3>
        <Selo cor={gerada ? "verde" : "cinza"}>{gerada ? "Gerada" : "Não gerada"}</Selo>
      </div>

      {!doc.disponivel && doc.motivo && (
        <Aviso tipo="info">
          <span className="font-medium">Indisponível por enquanto.</span>{" "}
          {doc.motivo.replace(/^Indisponível por enquanto: /, "")}
          {podeGerar && lista.length > 0 && (
            <ul className="mt-1 list-disc pl-5">
              {lista.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
          )}
        </Aviso>
      )}
      {doc.desatualizada && (
        <Aviso tipo="alerta">
          <span className="font-medium">
            {doc.presenca_mudou ? "A presença da banca mudou." : "O resultado foi retificado."}
          </span>{" "}
          A versão vigente reflete {doc.presenca_mudou ? "a presença anterior" : "o resultado anterior"}.
          {podeGerar && " Gere uma nova versão; a anterior fica como substituída."}
        </Aviso>
      )}
      {falhou && (
        <Aviso tipo="erro">
          <span className="font-medium">Não foi possível gerar o documento.</span> Nada foi alterado; tente de novo.
          <div className="mt-2">
            <Botao variante="contorno" pequeno onClick={gerar} carregando={gerando}>
              Tentar de novo
            </Botao>
          </div>
        </Aviso>
      )}
      <div role="status" className="empty:hidden">
        {gerando && <p className="text-sm text-suave">Gerando a {nome}…</p>}
        {aviso && <Aviso tipo="sucesso">{aviso}</Aviso>}
      </div>

      {podeGerar && (
        <div>
          <Botao onClick={gerar} carregando={gerando} disabled={!doc.disponivel}>
            {gerada ? "Gerar nova versão" : tipo === "ata" ? "Gerar ata da defesa" : "Gerar folha de aprovação"}
          </Botao>
        </div>
      )}

      {gerada && <Versoes versoes={doc.versoes} />}
    </div>
  );
}

// DS-FL06-E / RBN09.16: vigente e substituídas, cada uma com "Baixar PDF"
function Versoes({ versoes }: { versoes: VersaoDocumento[] }) {
  return (
    <ul className="divide-y divide-borda rounded-lg border border-borda text-sm" aria-label="Versões">
      {versoes.map((v) => (
        <li key={v.id} className="flex flex-wrap items-center justify-between gap-3 p-3">
          <span className="flex flex-wrap items-center gap-2">
            <span className="font-medium">v{v.versao}</span>
            <span className="text-suave">{dataHora(v.gerado_em)}</span>
            <Selo cor={v.vigente ? "verde" : "cinza"}>{v.vigente ? "Vigente" : "Substituída"}</Selo>
          </span>
          <a
            href={arquivo(v.id)}
            className="inline-flex h-8 items-center rounded-full px-3 text-sm font-medium text-azul-forte hover:bg-azul-claro"
          >
            Baixar PDF<span className="sr-only"> da versão {v.versao}</span>
          </a>
        </li>
      ))}
    </ul>
  );
}

// ---------------------------------------------------------------- DS-FL06-F · certificados

function Certificados({
  defesaId,
  linhas,
  aoMudar,
  recarregar,
}: {
  defesaId: number;
  linhas: CertificadoParticipante[];
  aoMudar: (d: DocumentosDefesa) => void;
  recarregar: () => Promise<void>;
}) {
  const [ocupado, setOcupado] = useState<string | null>(null);
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");
  const pendentes = linhas.filter((l) => l.pode_emitir);

  // O e-mail sai depois da resposta: a situação do envio é conferida de novo logo em seguida.
  const depois = (d: DocumentosDefesa, mensagem: string) => {
    aoMudar(d);
    setAviso(mensagem);
    window.setTimeout(() => void recarregar(), 2500);
  };

  const emitir = (ids: number[], chave: string) => {
    setOcupado(chave);
    setErro("");
    setAviso("");
    api<DocumentosDefesa>(`/defesas/${defesaId}/documentos/certificados`, {
      metodo: "POST",
      corpo: { ids_membro: ids },
    })
      .then((d) =>
        depois(d, ids.length === 1 ? "Certificado emitido e enviado por e-mail." : "Certificados emitidos e enviados por e-mail."),
      )
      .catch((e: ErroApi) => setErro(e.message))
      .finally(() => setOcupado(null));
  };

  const reenviar = (certificadoId: number) => {
    setOcupado(`r${certificadoId}`);
    setErro("");
    setAviso("");
    api<DocumentosDefesa>(`/documentos/${certificadoId}/reenvio`, { metodo: "POST" })
      .then((d) => depois(d, "Certificado reenviado por e-mail."))
      .catch((e: ErroApi) => setErro(e.message))
      .finally(() => setOcupado(null));
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="font-semibold">Certificados de participação</h3>
          <p className="text-[13px] text-suave">
            Emitidos só para quem esteve presente na defesa realizada; o arquivo vai anexado ao e-mail de cada um.
          </p>
        </div>
        {pendentes.length > 1 && (
          <Botao
            variante="contorno"
            pequeno
            carregando={ocupado === "todos"}
            onClick={() => emitir(pendentes.map((l) => l.membro_id), "todos")}
          >
            Emitir todos
          </Botao>
        )}
      </div>
      <ul className="divide-y divide-borda rounded-lg border border-borda text-sm" aria-label="Certificados">
        {linhas.map((l) => (
          <li key={l.membro_id} className="flex flex-wrap items-center justify-between gap-3 p-3">
            <span className="min-w-0 break-words">
              <span className="font-medium">{l.pessoa.nome}</span>{" "}
              <span className="text-suave">· {NOME_PAPEL_BANCA[l.papel]}</span>
              <span className="mt-1 flex flex-wrap gap-2">
                {l.certificado_id ? (
                  <>
                    <Selo cor="verde">Emitido</Selo>
                    <Selo cor={ENVIO[l.envio].cor}>{ENVIO[l.envio].texto}</Selo>
                  </>
                ) : l.motivo ? (
                  <Selo cor="cinza">{l.motivo}</Selo>
                ) : (
                  <Selo cor="azul">Disponível para emitir</Selo>
                )}
              </span>
            </span>
            <span className="flex flex-wrap gap-2">
              {l.certificado_id ? (
                <>
                  {(l.envio === "FALHA" || l.envio === "ENVIADO") && (
                    <Botao
                      variante="texto"
                      pequeno
                      carregando={ocupado === `r${l.certificado_id}`}
                      onClick={() => reenviar(l.certificado_id!)}
                    >
                      Reenviar
                    </Botao>
                  )}
                  <a
                    href={arquivo(l.certificado_id)}
                    className="inline-flex h-8 items-center rounded-full px-3 text-sm font-medium text-azul-forte hover:bg-azul-claro"
                  >
                    Baixar<span className="sr-only"> o certificado de {l.pessoa.nome}</span>
                  </a>
                </>
              ) : (
                l.pode_emitir && (
                  <Botao
                    variante="contorno"
                    pequeno
                    carregando={ocupado === String(l.membro_id)}
                    onClick={() => emitir([l.membro_id], String(l.membro_id))}
                  >
                    Emitir
                  </Botao>
                )
              )}
            </span>
          </li>
        ))}
      </ul>
      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      <div role="status" className="empty:hidden">
        {aviso && <Aviso tipo="sucesso">{aviso}</Aviso>}
      </div>
    </div>
  );
}
