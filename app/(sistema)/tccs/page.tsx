"use client";

// TEL04 · TCCs (RBN05.01): o aluno vê os seus; o orientador, os que orienta;
// o professor, os da sua turma; a coordenação, todos. A API filtra por perfil.

import Link from "next/link";
import { useEffect, useState } from "react";
import { Aviso } from "@/components/aviso";
import { Icone } from "@/components/icone";
import { SeloOrientacao, SeloSituacao } from "@/components/situacao-tcc";
import { api, ErroApi } from "@/lib/api";
import { useSessao } from "@/lib/sessao";
import { dataHora, type Formulario, type Tcc } from "@/lib/tipos";

export default function PaginaTccs() {
  const { tem } = useSessao();
  const aluno = tem("aluno");
  const [lista, setLista] = useState<Tcc[] | null>(null);
  const [form, setForm] = useState<Formulario | null>(null);
  const [semMatricula, setSemMatricula] = useState("");
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<Tcc[]>("/tccs").then(setLista).catch((e: ErroApi) => setErro(e.message));
    if (aluno) {
      api<Formulario>("/tccs/formulario")
        .then(setForm)
        .catch((e: ErroApi) => e.status === 403 && setSemMatricula(e.message));
    }
  }, [aluno]);

  const meu = form?.tcc;
  const editavel = !meu || meu.situacao === "RASCUNHO" || meu.situacao === "DEVOLVIDO";

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">{aluno ? "Meu TCC" : "TCCs"}</h1>
          <p className="mt-1 text-sm text-suave">
            {aluno
              ? "Cadastre o seu trabalho, acompanhe a orientação e envie para a análise da coordenação."
              : "Trabalhos que você acompanha. Clique em um para ver os detalhes e o histórico."}
          </p>
        </div>
        {aluno && form && editavel && (
          <Link
            href="/tccs/cadastro"
            className="inline-flex h-10 items-center gap-2 rounded-full bg-azul px-5 text-sm font-medium text-white shadow-sm hover:bg-azul-forte"
          >
            <Icone nome={meu ? "lapis" : "mais"} className="size-4" />
            {meu ? "Continuar cadastro" : "Cadastrar TCC"}
          </Link>
        )}
      </header>

      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      {semMatricula && (
        <Aviso tipo="alerta">
          <strong>Seu cadastro de TCC está bloqueado.</strong> {semMatricula}
        </Aviso>
      )}
      {aluno && form && !meu && (
        <Aviso tipo="info">
          Você está na turma <strong>{form.turma.codigo}</strong> ({form.turma.periodo}), com{" "}
          {form.turma.professor.nome}. Já pode cadastrar o seu TCC.
        </Aviso>
      )}

      <section className="overflow-hidden rounded-xl border border-borda bg-superficie">
        {!lista ? (
          <p role="status" className="p-6 text-sm text-suave">
            Carregando…
          </p>
        ) : lista.length === 0 ? (
          <p className="p-6 text-sm text-suave">
            {aluno ? "Você ainda não cadastrou o seu TCC." : "Nenhum TCC para acompanhar ainda."}
          </p>
        ) : (
          <ul className="divide-y divide-borda">
            {lista.map((t) => (
              <li key={t.id}>
                <Link
                  href={`/tccs/${t.id}`}
                  className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3.5 hover:bg-fundo"
                >
                  <div className="min-w-0 flex-1 basis-72">
                    <p className="truncate font-medium">{t.titulo}</p>
                    <p className="text-sm text-suave">
                      {t.aluno.nome} · {t.etapa} · {t.modalidade === "ARTIGO" ? "Artigo" : "Monografia"} ·{" "}
                      {t.turma.periodo}
                    </p>
                  </div>
                  <div className="basis-44 text-sm">
                    <p className="font-mono">{t.protocolo ?? "sem protocolo"}</p>
                    <p className="text-suave">Atualizado em {dataHora(t.atualizado_em)}</p>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    <SeloSituacao situacao={t.situacao} />
                    {t.orientador && <SeloOrientacao status={t.orientador.status} />}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
