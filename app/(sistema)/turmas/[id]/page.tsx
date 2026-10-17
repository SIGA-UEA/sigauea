"use client";

// Turma aberta: faixa com o curso e o professor responsável e a lista de alunos com o
// TCC de cada um. Só a coordenação e o professor que conduz a turma abrem (RN07, RN24);
// para os demais a API responde 404.

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Avatar } from "@/components/avatar";
import { Aviso, Selo } from "@/components/aviso";
import { Icone } from "@/components/icone";
import { SeloOrientacao, SeloSituacao } from "@/components/situacao-tcc";
import { corDoCurso, Etiqueta, tipoDaTurma } from "@/components/turma";
import { api, ErroApi } from "@/lib/api";
import { useSessao } from "@/lib/sessao";
import { NOME_SITUACAO_MATRICULA, type SituacaoMatricula, type Turma } from "@/lib/tipos";

const COR_MATRICULA: Record<SituacaoMatricula, "verde" | "cinza" | "vermelho"> = {
  MATRICULADO: "verde",
  DESISTENTE: "cinza",
  APROVADO: "verde",
  REPROVADO: "vermelho",
};

export default function PaginaTurma() {
  const { id } = useParams<{ id: string }>();
  const { tem } = useSessao();
  const [turma, setTurma] = useState<Turma | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<Turma>(`/turmas/${id}`).then(setTurma).catch((e: ErroApi) => setErro(e.message));
  }, [id]);

  const voltar = (
    <Link href="/turmas" className="inline-flex items-center gap-1 text-sm font-medium text-azul-forte hover:underline">
      <Icone nome="voltar" className="size-4" />
      {tem("coordenador") ? "Turmas" : "Minhas turmas"}
    </Link>
  );

  if (erro)
    return (
      <div className="flex flex-col gap-4">
        {voltar}
        <Aviso tipo="erro">{erro}</Aviso>
      </div>
    );
  if (!turma)
    return (
      <p role="status" className="text-suave">
        Carregando…
      </p>
    );

  const comTcc = turma.alunos.filter((m) => m.tcc).length;

  return (
    <div className="flex max-w-5xl flex-col gap-5">
      {voltar}
      <section
        className={`flex flex-wrap items-center justify-between gap-x-6 gap-y-3 rounded-xl px-6 py-5 ${corDoCurso(turma.curso.sigla)}`}
      >
        <div>
          <Etiqueta>{turma.disciplina}</Etiqueta>
          <h1 className="mt-2 text-2xl font-semibold">{turma.curso.nome}</h1>
          <p className="text-[13px] opacity-85">
            {turma.periodo.codigo} · {tipoDaTurma(turma.disciplina)} · <span className="font-mono">{turma.codigo}</span>
            {turma.encerrada && " · encerrada"}
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <Avatar nome={turma.professor.nome} />
          <span>
            <span className="block text-xs opacity-80">Professor responsável</span>
            <b className="font-semibold">{turma.professor.nome}</b>
          </span>
        </div>
      </section>

      <section className="overflow-hidden rounded-xl border border-borda bg-superficie">
        <header className="flex flex-wrap items-baseline justify-between gap-2 border-b border-borda px-4 py-3">
          <h2 className="font-semibold">Alunos ({turma.alunos.length})</h2>
          <span className="text-sm text-suave">{comTcc} com TCC cadastrado</span>
        </header>
        {turma.alunos.length === 0 ? (
          <p className="p-6 text-sm text-suave">Nenhum aluno nesta turma ainda.</p>
        ) : (
          <ul className="divide-y divide-borda">
            {turma.alunos.map((m) => (
              <li key={m.id} className="flex flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3.5">
                <div className="flex min-w-0 basis-60 items-center gap-3">
                  <Avatar nome={m.aluno.nome} />
                  <div className="min-w-0">
                    <p className="truncate font-medium">{m.aluno.nome}</p>
                    <p className="text-[13px] text-suave">
                      <span className="font-mono">{m.matricula}</span>
                      {m.curso.sigla !== turma.curso.sigla && ` · aluno de ${m.curso.sigla}`}
                    </p>
                  </div>
                </div>

                <div className="min-w-0 flex-1 basis-72 text-sm">
                  {m.tcc ? (
                    <>
                      <Link href={`/tccs/${m.tcc.id}`} className="line-clamp-2 font-medium hover:underline">
                        {m.tcc.titulo}
                      </Link>
                      <div className="mt-1 flex flex-wrap items-center gap-1.5">
                        <SeloSituacao situacao={m.tcc.situacao} />
                        {m.tcc.orientador && m.tcc.orientacao && (
                          <span className="inline-flex items-center gap-1.5 text-[13px] text-suave">
                            Orientação: {m.tcc.orientador.nome} <SeloOrientacao status={m.tcc.orientacao} />
                          </span>
                        )}
                      </div>
                    </>
                  ) : (
                    <span className="text-suave">Ainda sem cadastro de TCC</span>
                  )}
                </div>

                <Selo cor={COR_MATRICULA[m.situacao]}>{NOME_SITUACAO_MATRICULA[m.situacao]}</Selo>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
