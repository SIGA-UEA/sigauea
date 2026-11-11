"use client";

// TEL03 · proposta aberta (RBN02.02 · DS-FL12-A): autor, data, texto e a discussão.
//   GET  /ideias/{id}              403 para quem não é o autor nem destinatário (E1): nada da proposta aparece
//   POST /ideias/{id}/comentarios  {texto}; 400 {campos} com texto vazio (E2)
// O professor destinatário comenta; o aluno autor lê os comentários (CA-05).

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { Aviso } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Campo, ESTILO_ENTRADA } from "@/components/campo";
import { Icone } from "@/components/icone";
import { api, ErroApi } from "@/lib/api";
import { dataHora, destinoDaProposta, type PropostaDetalhe } from "@/lib/tipos";

export default function PaginaProposta() {
  const { id } = useParams<{ id: string }>();
  const [p, setP] = useState<PropostaDetalhe | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<PropostaDetalhe>(`/ideias/${id}`).then(setP).catch((e: ErroApi) => setErro(e.message));
  }, [id]);

  return (
    <div className="flex flex-col gap-5">
      <Link href="/ideias" className="flex w-fit items-center gap-1 text-sm text-azul-forte hover:underline">
        <Icone nome="voltar" className="size-4" /> Ideias de TCC
      </Link>

      {erro ? (
        <Aviso tipo="erro">{erro}</Aviso>
      ) : !p ? (
        <p role="status" className="text-sm text-suave">
          Carregando…
        </p>
      ) : (
        <>
          <header>
            <p className="text-xs font-semibold tracking-widest text-suave uppercase">Proposta de TCC</p>
            <h1 className="text-2xl font-semibold break-words">{p.titulo}</h1>
            <p className="mt-1 text-sm text-suave">
              {p.autor.nome} · {dataHora(p.criado_em)}
              {p.area && <> · {p.area.nome}</>}
            </p>
          </header>

          <section className="rounded-xl border border-borda bg-superficie p-5" aria-label="Proposta">
            <p className="text-[15px] break-words whitespace-pre-line">{p.descricao}</p>
            <dl className="mt-4 grid gap-x-6 gap-y-2 border-t border-borda pt-4 text-sm sm:grid-cols-[max-content_1fr]">
              <dt className="text-suave">Enviada para</dt>
              <dd className="break-words">{destinoDaProposta(p)}</dd>
            </dl>
            <p className="mt-3 text-[13px] text-suave">Proposta para discussão: não é um cadastro de TCC.</p>
          </section>

          <Discussao p={p} aoComentar={setP} />
        </>
      )}
    </div>
  );
}

function Discussao({ p, aoComentar }: { p: PropostaDetalhe; aoComentar: (p: PropostaDetalhe) => void }) {
  const [texto, setTexto] = useState("");
  const [erroTexto, setErroTexto] = useState("");
  const [falha, setFalha] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [aviso, setAviso] = useState("");

  const enviar = (e: FormEvent) => {
    e.preventDefault();
    setFalha("");
    setAviso("");
    if (!texto.trim()) {
      setErroTexto("Escreva o comentário."); // CA-03: vazio ou só espaços
      return;
    }
    setErroTexto("");
    setEnviando(true);
    api<PropostaDetalhe>(`/ideias/${p.id}/comentarios`, { metodo: "POST", corpo: { texto: texto.trim() } })
      .then((novo) => {
        aoComentar(novo);
        setTexto("");
        setAviso("Comentário publicado. O aluno vê ao abrir a proposta.");
      })
      .catch((err: ErroApi) => {
        if (err.campos?.texto) setErroTexto(err.campos.texto);
        else setFalha(err.message);
      })
      .finally(() => setEnviando(false));
  };

  return (
    <section className="rounded-xl border border-borda bg-superficie p-5" aria-labelledby="titulo-discussao">
      <h2 id="titulo-discussao" className="mb-3 font-semibold">
        Discussão
      </h2>
      {p.discussao.length === 0 ? (
        <p className="text-sm text-suave">
          {p.pode_comentar ? "Ainda não há comentários. Seja o primeiro a orientar esta ideia." : "Ainda não há comentários dos professores."}
        </p>
      ) : (
        <ol className="flex flex-col gap-3" aria-label="Comentários">
          {p.discussao.map((c) => (
            <li key={c.id} className="rounded-lg border border-borda p-3 text-sm">
              <p className="text-[13px] text-suave">
                <span className="font-medium text-texto">{c.autor.nome}</span> · {dataHora(c.criado_em)}
              </p>
              <p className="mt-1 break-words whitespace-pre-line">{c.texto}</p>
            </li>
          ))}
        </ol>
      )}

      {p.pode_comentar && (
        <form onSubmit={enviar} noValidate className="mt-4 flex flex-col gap-3 border-t border-borda pt-4">
          <Campo rotulo="Seu comentário" obrigatorio erro={erroTexto}>
            <textarea
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              rows={3}
              maxLength={2000}
              aria-invalid={erroTexto ? true : undefined}
              className={`${ESTILO_ENTRADA} h-auto py-2 ${erroTexto ? "border-vermelho" : "border-borda"}`}
            />
          </Campo>
          {falha && <Aviso tipo="erro">{falha}</Aviso>}
          <div role="status" className="empty:hidden">
            {aviso && <Aviso tipo="sucesso">{aviso}</Aviso>}
          </div>
          <div>
            <Botao type="submit" carregando={enviando}>
              Comentar
            </Botao>
          </div>
        </form>
      )}
    </section>
  );
}
