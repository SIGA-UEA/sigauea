// Cartão e faixa de turma (Minhas turmas), no visual do protótipo: a faixa tem a cor do curso.

import Link from "next/link";
import type { ReactNode } from "react";
import { NOME_SITUACAO_MATRICULA, type TurmaCartao } from "@/lib/tipos";
import { Avatar } from "./avatar";
import { Icone } from "./icone";
import { SeloSituacao } from "./situacao-tcc";

const COR_CURSO: Record<string, string> = {
  EC: "bg-curso-ec text-curso-ec-tinta",
  SI: "bg-curso-si text-curso-si-tinta",
  LC: "bg-curso-lc text-curso-lc-tinta",
};
export const corDoCurso = (sigla: string) => COR_CURSO[sigla] ?? "bg-azul-claro text-azul-escuro";

// TCC1 é conduzida pelo professor da disciplina; TCC2, pelo orientador (RN24, RN26).
export const tipoDaTurma = (disciplina: string) =>
  disciplina === "TCC2" ? "Turma de orientação" : "Turma da disciplina";

export function Etiqueta({ children }: { children: ReactNode }) {
  return (
    <span className="inline-block rounded-full border border-current px-2.5 py-px font-mono text-xs font-semibold tracking-wide opacity-90">
      {children}
    </span>
  );
}

const plural = (n: number, um: string, varios: string) => `${n} ${n === 1 ? um : varios}`;

export function CartaoTurma({ turma, aluno }: { turma: TurmaCartao; aluno: boolean }) {
  return (
    <article className="flex flex-col overflow-hidden rounded-xl border border-borda bg-superficie shadow-sm">
      <div className={`px-4.5 pt-4 pb-3.5 ${corDoCurso(turma.curso.sigla)}`}>
        <Etiqueta>{turma.disciplina}</Etiqueta>
        <h2 className="mt-1.5 text-lg font-semibold">{turma.curso.nome}</h2>
        <p className="text-[13px] opacity-85">
          {turma.periodo} · {tipoDaTurma(turma.disciplina)}
          {turma.encerrada && " · encerrada"}
        </p>
      </div>

      <div className="flex flex-1 flex-col gap-2.5 px-4.5 pt-3.5 pb-1.5">
        <div className="flex items-center gap-2.5 text-[15px]">
          <Avatar nome={turma.professor.nome} />
          <span className="min-w-0">
            {aluno && <span className="block text-xs text-suave">Professor responsável</span>}
            {turma.professor.nome}
          </span>
        </div>

        {aluno ? (
          <>
            <p className="text-sm text-suave">
              Sua matrícula:{" "}
              <b className="font-medium text-texto">
                {turma.minha_matricula ? NOME_SITUACAO_MATRICULA[turma.minha_matricula] : "—"}
              </b>
            </p>
            {turma.meu_tcc ? (
              <div className="flex flex-col gap-1 text-sm">
                <span className="line-clamp-2 font-medium">{turma.meu_tcc.titulo}</span>
                <span className="flex flex-wrap items-center gap-2">
                  <SeloSituacao situacao={turma.meu_tcc.situacao} />
                  {turma.meu_tcc.protocolo && <span className="font-mono text-xs text-suave">{turma.meu_tcc.protocolo}</span>}
                </span>
              </div>
            ) : (
              turma.minha_matricula === "MATRICULADO" && (
                <p className="flex items-center gap-1.5 text-[13px] font-semibold text-ambar">
                  <Icone nome="relogio" className="size-4" />
                  Você ainda não cadastrou o seu TCC
                </p>
              )
            )}
          </>
        ) : (
          <>
            <p className="flex gap-4 text-sm text-suave">
              <span>
                <b className="font-semibold text-texto">{turma.alunos}</b> {turma.alunos === 1 ? "aluno" : "alunos"}
              </span>
              <span>
                <b className="font-semibold text-texto">{turma.com_tcc}</b> com TCC
              </span>
            </p>
            {turma.pendentes > 0 ? (
              <p className="flex items-center gap-1.5 text-[13px] font-semibold text-ambar">
                <Icone nome="relogio" className="size-4" />
                {plural(turma.pendentes, "pedido de orientação espera", "pedidos de orientação esperam")} você
              </p>
            ) : (
              <p className="flex items-center gap-1.5 text-[13px] font-medium text-suave">
                <Icone nome="certo" className="size-4" />
                Nada pendente
              </p>
            )}
          </>
        )}
      </div>

      <div className="px-4.5 pt-1.5 pb-4">
        {aluno ? (
          <Link href={turma.meu_tcc ? `/tccs/${turma.meu_tcc.id}` : "/tccs/cadastro"} className={BOTAO_CONTORNO}>
            <Icone nome="seta" className="size-4" />
            {turma.meu_tcc ? "Ver meu TCC" : "Cadastrar TCC"}
          </Link>
        ) : (
          <Link href={`/turmas/${turma.id}`} className={BOTAO_CONTORNO}>
            <Icone nome="seta" className="size-4" />
            Abrir turma
          </Link>
        )}
      </div>
    </article>
  );
}

const BOTAO_CONTORNO =
  "inline-flex h-9 items-center gap-1.5 rounded-full border border-borda bg-superficie px-4 text-sm font-medium text-azul-forte hover:bg-azul-claro";
