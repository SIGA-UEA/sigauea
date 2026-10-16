"use client";

// Painel inicial: é para cá que o login leva. Mostra só o que o perfil pode usar.

import Link from "next/link";
import { Selo } from "@/components/aviso";
import { Icone } from "@/components/icone";
import { useSessao } from "@/lib/sessao";
import { NOME_PERFIL, type Perfil } from "@/lib/tipos";

type Cartao = {
  titulo: string;
  descricao: string;
  cor: string;
  perfis: Perfil[];
  href?: string; // sem href = módulo ainda não implementado
};

const TODOS: Perfil[] = ["aluno", "orientador", "professor_disciplina", "coordenador", "membro_banca"];

const CARTOES: Cartao[] = [
  {
    titulo: "Usuários e perfis",
    descricao: "Cadastrar docentes e alunos, atribuir perfis, editar e inativar cadastros.",
    cor: "bg-azul",
    perfis: ["coordenador"],
    href: "/usuarios",
  },
  {
    titulo: "TCCs",
    descricao: "Cadastro, análise, orientação e acompanhamento dos trabalhos.",
    cor: "bg-[#0b8043]",
    perfis: ["aluno", "orientador", "professor_disciplina", "coordenador"],
  },
  {
    titulo: "Defesas",
    descricao: "Banca, agendamento, avaliação, ata e correções.",
    cor: "bg-[#8430ce]",
    perfis: ["orientador", "professor_disciplina", "coordenador", "membro_banca"],
  },
  {
    titulo: "Agenda de apresentações",
    descricao: "Programação das defesas divulgadas.",
    cor: "bg-[#0e7490]",
    perfis: TODOS,
  },
];

export default function PaginaInicio() {
  const { usuario } = useSessao();
  const cartoes = CARTOES.filter((c) => c.perfis.some((p) => usuario.perfis.includes(p)));

  return (
    <div className="flex flex-col gap-6">
      <section className="relative overflow-hidden rounded-2xl bg-azul px-6 py-8 text-white sm:px-8 sm:py-10">
        <span aria-hidden="true" className="absolute -top-20 -right-10 size-64 rounded-full bg-white/10" />
        <span aria-hidden="true" className="absolute right-40 -bottom-16 size-40 rounded-full bg-white/10" />
        <div className="relative">
          <h1 className="text-2xl font-semibold sm:text-3xl">Olá, {usuario.nome.split(" ")[0]}</h1>
          <p className="mt-1.5 text-white/85">
            {usuario.perfis.map((p) => NOME_PERFIL[p]).join(" · ")}
            {usuario.curso && ` · ${usuario.curso.nome}`}
          </p>
        </div>
      </section>

      <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {cartoes.map((cartao) => {
          const conteudo = (
            <>
              <div className={`${cartao.cor} px-5 py-4 text-white`}>
                <h2 className="text-lg font-medium">{cartao.titulo}</h2>
              </div>
              <div className="flex flex-1 flex-col gap-4 px-5 py-4">
                <p className="text-sm text-suave">{cartao.descricao}</p>
                <div className="mt-auto">
                  {cartao.href ? (
                    <span className="inline-flex items-center gap-1 text-sm font-medium text-azul-forte">
                      Abrir <Icone nome="seta" className="size-4" />
                    </span>
                  ) : (
                    <Selo cor="cinza">Em desenvolvimento</Selo>
                  )}
                </div>
              </div>
            </>
          );
          const moldura = "flex h-full flex-col overflow-hidden rounded-xl border border-borda bg-superficie";
          return (
            <li key={cartao.titulo}>
              {cartao.href ? (
                <Link href={cartao.href} className={`${moldura} transition-shadow hover:shadow-md`}>
                  {conteudo}
                </Link>
              ) : (
                <div className={`${moldura} opacity-80`}>{conteudo}</div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
