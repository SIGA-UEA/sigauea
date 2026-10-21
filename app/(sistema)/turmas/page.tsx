"use client";

// Turmas de TCC (RBN08.01 a RBN08.03): a coordenação abre o período letivo, cria as
// turmas de TCC1/TCC2 com o professor da disciplina e inclui os alunos. Sem matrícula
// (MATRICULADO) numa turma do período, o aluno não consegue cadastrar o TCC (RN05).
// Professor e aluno veem aqui "Minhas turmas", em cartões como no protótipo.

import Link from "next/link";
import { useEffect, useState } from "react";
import { Aviso, Selo, type TipoAviso } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Campo, Entrada, Selecao } from "@/components/campo";
import { Icone } from "@/components/icone";
import { Modal } from "@/components/modal";
import { CartaoTurma } from "@/components/turma";
import { api, ErroApi } from "@/lib/api";
import { useSessao } from "@/lib/sessao";
import {
  NOME_SITUACAO_MATRICULA as NOME_MATRICULA,
  type Curso,
  type Periodo,
  type Turma,
  type TurmaCartao,
  type Usuario,
} from "@/lib/tipos";

type Erros = Record<string, string>;

export default function PaginaTurmas() {
  const { tem } = useSessao();
  return tem("coordenador") ? <GestaoTurmas /> : <MinhasTurmas aluno={tem("aluno")} />;
}

function MinhasTurmas({ aluno }: { aluno: boolean }) {
  const [lista, setLista] = useState<TurmaCartao[] | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    api<TurmaCartao[]>("/turmas/minhas").then(setLista).catch((e: ErroApi) => setErro(e.message));
  }, []);

  return (
    <div className="flex flex-col gap-5">
      <header>
        <p className="text-xs font-semibold tracking-widest text-suave uppercase">{aluno ? "Aluno" : "Docente"}</p>
        <h1 className="text-2xl font-semibold">{aluno ? "Minha turma" : "Minhas turmas"}</h1>
        <p className="mt-1 text-sm text-suave">
          {aluno
            ? "A turma em que você está matriculado, com o professor responsável e o seu TCC."
            : "Cada turma reúne os seus alunos e os TCCs deles."}
        </p>
      </header>
      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      {!lista ? (
        <p role="status" className="text-sm text-suave">
          Carregando…
        </p>
      ) : lista.length === 0 ? (
        <div className="rounded-xl border border-borda bg-superficie p-6 text-sm">
          <p className="font-medium">{aluno ? "Você ainda não está em uma turma" : "Você ainda não tem turma"}</p>
          <p className="mt-1 text-suave">
            {aluno
              ? "Quando a coordenação incluir você numa turma de TCC, ela aparece aqui e o cadastro do TCC é liberado."
              : "Quando a coordenação criar uma turma e indicar você como responsável, ela aparece aqui."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(min(100%,300px),1fr))] gap-4">
          {lista.map((t) => (
            <CartaoTurma key={t.id} turma={t} aluno={aluno} />
          ))}
        </div>
      )}
    </div>
  );
}

function GestaoTurmas() {
  const [periodos, setPeriodos] = useState<Periodo[]>([]);
  const [periodoId, setPeriodoId] = useState("");
  const [turmas, setTurmas] = useState<Turma[] | null>(null);
  const [cursos, setCursos] = useState<Curso[]>([]);
  const [docentes, setDocentes] = useState<Usuario[]>([]);
  const [alunos, setAlunos] = useState<Usuario[]>([]);
  const [aberta, setAberta] = useState<number | null>(null);
  const [versao, setVersao] = useState(0);
  const [aviso, setAviso] = useState<{ tipo: TipoAviso; texto: string } | null>(null);
  const [janela, setJanela] = useState<"periodo" | "turma" | null>(null);

  useEffect(() => {
    api<Periodo[]>("/periodos").then((l) => {
      setPeriodos(l);
      if (l.length) setPeriodoId((atual) => atual || String(l[0].id));
      else setTurmas([]);
    });
    api<Curso[]>("/cursos").then(setCursos);
    api<Usuario[]>("/docentes").then(setDocentes);
    api<Usuario[]>("/alunos").then(setAlunos);
  }, []);

  useEffect(() => {
    if (!periodoId) return;
    api<Turma[]>(`/turmas?periodo=${periodoId}`)
      .then(setTurmas)
      .catch((e: ErroApi) => setAviso({ tipo: "erro", texto: e.message }));
  }, [periodoId, versao]);

  function atualizar(t: Turma, texto: string) {
    setTurmas((l) => l?.map((x) => (x.id === t.id ? t : x)) ?? l);
    setAviso({ tipo: "sucesso", texto });
  }

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Turmas de TCC</h1>
          <p className="mt-1 text-sm text-suave">
            Só alunos matriculados numa turma do período conseguem cadastrar o TCC.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Botao variante="contorno" onClick={() => setJanela("periodo")}>
            Novo período
          </Botao>
          <Botao disabled={!periodos.length} onClick={() => setJanela("turma")}>
            <Icone nome="mais" className="size-4" />
            Nova turma
          </Botao>
        </div>
      </header>

      {periodos.length > 0 && (
        <label className="flex max-w-xs flex-col gap-1.5 text-sm">
          <span className="font-medium">Período letivo</span>
          <Selecao value={periodoId} onChange={(e) => setPeriodoId(e.target.value)}>
            {periodos.map((p) => (
              <option key={p.id} value={p.id}>
                {p.codigo}
              </option>
            ))}
          </Selecao>
        </label>
      )}

      {aviso && <Aviso tipo={aviso.tipo}>{aviso.texto}</Aviso>}

      {!turmas ? (
        <p role="status" className="text-sm text-suave">
          Carregando…
        </p>
      ) : turmas.length === 0 ? (
        <p className="rounded-xl border border-borda bg-superficie p-6 text-sm text-suave">
          {periodos.length ? "Nenhuma turma neste período." : "Cadastre o primeiro período letivo para criar turmas."}
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {turmas.map((t) => (
            <li key={t.id} className="rounded-xl border border-borda bg-superficie">
              <button
                onClick={() => setAberta(aberta === t.id ? null : t.id)}
                aria-expanded={aberta === t.id}
                className="flex w-full flex-wrap items-center justify-between gap-2 px-4 py-3.5 text-left hover:bg-fundo"
              >
                <span>
                  <span className="font-medium">{t.codigo}</span>
                  <span className="block text-sm text-suave">
                    {t.disciplina} · {t.curso.nome} · {t.professor.nome}
                  </span>
                </span>
                <span className="flex items-center gap-2">
                  <Selo cor="azul">{t.alunos.length} aluno(s)</Selo>
                  {t.encerrada && <Selo cor="cinza">Encerrada</Selo>}
                </span>
              </button>
              {aberta === t.id && <AlunosDaTurma turma={t} alunos={alunos} aoMudar={atualizar} />}
            </li>
          ))}
        </ul>
      )}

      {janela === "periodo" && (
        <NovoPeriodo
          aoFechar={() => setJanela(null)}
          aoCriar={(p) => {
            setPeriodos((l) => [p, ...l]);
            setPeriodoId(String(p.id));
            setJanela(null);
            setAviso({ tipo: "sucesso", texto: `Período ${p.codigo} cadastrado.` });
          }}
        />
      )}
      {janela === "turma" && (
        <NovaTurma
          periodos={periodos}
          periodoId={periodoId}
          cursos={cursos}
          docentes={docentes}
          aoFechar={() => setJanela(null)}
          aoCriar={(t) => {
            setPeriodoId(String(t.periodo.id));
            setVersao((v) => v + 1);
            setAberta(t.id);
            setJanela(null);
            setAviso({ tipo: "sucesso", texto: `Turma ${t.codigo} criada.` });
          }}
        />
      )}
    </div>
  );
}

function AlunosDaTurma({
  turma,
  alunos,
  aoMudar,
}: {
  turma: Turma;
  alunos: Usuario[];
  aoMudar: (t: Turma, texto: string) => void;
}) {
  const [alunoId, setAlunoId] = useState("");
  const [erro, setErro] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const naTurma = new Set(turma.alunos.map((m) => m.aluno.id));
  const disponiveis = alunos.filter((a) => a.situacao !== "inativo" && !naTurma.has(a.id));

  async function incluir() {
    if (!alunoId) return setErro("Escolha o aluno.");
    setOcupado(true);
    setErro("");
    try {
      const t = await api<Turma>(`/turmas/${turma.id}/alunos`, { metodo: "POST", corpo: { aluno_id: Number(alunoId) } });
      setAlunoId("");
      aoMudar(t, "Aluno incluído na turma.");
    } catch (e) {
      const x = e as ErroApi;
      setErro(x.campos?.aluno_id ?? x.message);
    }
    setOcupado(false);
  }

  async function mudarSituacao(matriculaId: number, situacao: string) {
    try {
      const t = await api<Turma>(`/turmas/${turma.id}/alunos/${matriculaId}`, { metodo: "PATCH", corpo: { situacao } });
      aoMudar(t, "Situação do aluno atualizada.");
    } catch (e) {
      setErro((e as ErroApi).message);
    }
  }

  return (
    <div className="flex flex-col gap-3 border-t border-borda px-4 py-4">
      <Link href={`/turmas/${turma.id}`} className="self-start text-sm font-medium text-azul-forte hover:underline">
        Abrir turma e ver os TCCs dos alunos
      </Link>
      {turma.alunos.length === 0 ? (
        <p className="text-sm text-suave">Nenhum aluno nesta turma ainda.</p>
      ) : (
        <ul className="divide-y divide-borda text-sm">
          {turma.alunos.map((m) => (
            <li key={m.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
              <span>
                <span className="font-medium">{m.aluno.nome}</span>
                <span className="block text-[13px] text-suave">
                  {m.matricula} · {m.curso.sigla}
                </span>
              </span>
              <Selecao
                value={m.situacao}
                onChange={(e) => mudarSituacao(m.id, e.target.value)}
                aria-label={`Situação de ${m.aluno.nome}`}
                className="w-44"
              >
                {Object.entries(NOME_MATRICULA).map(([v, r]) => (
                  <option key={v} value={v}>
                    {r}
                  </option>
                ))}
              </Selecao>
            </li>
          ))}
        </ul>
      )}
      {!turma.encerrada && (
        <div className="flex flex-wrap items-start gap-2">
          <Selecao
            value={alunoId}
            onChange={(e) => setAlunoId(e.target.value)}
            aria-label="Aluno a incluir"
            className="max-w-sm"
          >
            <option value="">Incluir aluno…</option>
            {disponiveis.map((a) => (
              <option key={a.id} value={a.id}>
                {a.nome} ({a.matricula})
              </option>
            ))}
          </Selecao>
          <Botao variante="contorno" carregando={ocupado} onClick={incluir}>
            Incluir
          </Botao>
        </div>
      )}
      {erro && (
        <p role="alert" className="text-[13px] font-medium text-vermelho">
          {erro}
        </p>
      )}
    </div>
  );
}

function NovoPeriodo({ aoFechar, aoCriar }: { aoFechar: () => void; aoCriar: (p: Periodo) => void }) {
  const [codigo, setCodigo] = useState("");
  const [inicio, setInicio] = useState("");
  const [fim, setFim] = useState("");
  const [erros, setErros] = useState<Erros>({});
  const [erro, setErro] = useState("");
  const [ocupado, setOcupado] = useState(false);

  async function salvar() {
    setOcupado(true);
    setErro("");
    try {
      aoCriar(await api<Periodo>("/periodos", { metodo: "POST", corpo: { codigo, inicio, fim } }));
    } catch (e) {
      const x = e as ErroApi;
      setErros(x.campos ?? {});
      setErro(x.message);
    }
    setOcupado(false);
  }

  return (
    <Modal titulo="Novo período letivo" aoFechar={aoFechar}>
      <div className="flex flex-col gap-4">
        {erro && <Aviso tipo="erro">{erro}</Aviso>}
        <Campo rotulo="Código" obrigatorio dica="ex.: 2026/2" erro={erros.codigo}>
          <Entrada value={codigo} onChange={(e) => setCodigo(e.target.value)} placeholder="2026/2" erro={erros.codigo} />
        </Campo>
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo rotulo="Início" obrigatorio erro={erros.inicio}>
            <Entrada type="date" value={inicio} onChange={(e) => setInicio(e.target.value)} erro={erros.inicio} />
          </Campo>
          <Campo rotulo="Fim" obrigatorio erro={erros.fim}>
            <Entrada type="date" value={fim} onChange={(e) => setFim(e.target.value)} erro={erros.fim} />
          </Campo>
        </div>
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Botao variante="texto" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao carregando={ocupado} onClick={salvar}>
            Cadastrar período
          </Botao>
        </div>
      </div>
    </Modal>
  );
}

function NovaTurma({
  periodos,
  periodoId: periodoInicial,
  cursos,
  docentes,
  aoFechar,
  aoCriar,
}: {
  periodos: Periodo[];
  periodoId: string;
  cursos: Curso[];
  docentes: Usuario[];
  aoFechar: () => void;
  aoCriar: (t: Turma) => void;
}) {
  const [disciplina, setDisciplina] = useState("TCC1");
  const [cursoId, setCursoId] = useState(cursos[0] ? String(cursos[0].id) : "");
  const [periodoId, setPeriodoId] = useState(periodoInicial);
  const [professorId, setProfessorId] = useState("");
  const [erros, setErros] = useState<Erros>({});
  const [erro, setErro] = useState("");
  const [ocupado, setOcupado] = useState(false);

  // TCC1 é conduzida pelo professor da disciplina; TCC2, por um orientador.
  const perfil = disciplina === "TCC1" ? "professor_disciplina" : "orientador";
  const elegiveis = docentes.filter((d) => d.situacao !== "inativo" && d.perfis.includes(perfil));

  async function salvar() {
    setOcupado(true);
    setErro("");
    try {
      aoCriar(
        await api<Turma>("/turmas", {
          metodo: "POST",
          corpo: {
            disciplina,
            curso_id: Number(cursoId),
            periodo_id: Number(periodoId),
            professor_id: Number(professorId),
          },
        }),
      );
    } catch (e) {
      const x = e as ErroApi;
      setErros(x.campos ?? {});
      setErro(x.message);
    }
    setOcupado(false);
  }

  return (
    <Modal titulo="Nova turma de TCC" aoFechar={aoFechar}>
      <div className="flex flex-col gap-4">
        {erro && <Aviso tipo="erro">{erro}</Aviso>}
        <div className="grid gap-4 sm:grid-cols-2">
          <Campo rotulo="Disciplina" obrigatorio>
            <Selecao
              value={disciplina}
              onChange={(e) => {
                setDisciplina(e.target.value);
                setProfessorId("");
              }}
            >
              <option value="TCC1">TCC1</option>
              <option value="TCC2">TCC2</option>
            </Selecao>
          </Campo>
          <Campo rotulo="Período" obrigatorio erro={erros.periodo_id}>
            <Selecao value={periodoId} onChange={(e) => setPeriodoId(e.target.value)}>
              {periodos.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.codigo}
                </option>
              ))}
            </Selecao>
          </Campo>
        </div>
        <Campo rotulo="Curso" obrigatorio erro={erros.curso_id}>
          <Selecao value={cursoId} onChange={(e) => setCursoId(e.target.value)}>
            {cursos.map((c) => (
              <option key={c.id} value={c.id}>
                {c.nome}
              </option>
            ))}
          </Selecao>
        </Campo>
        <Campo
          rotulo={disciplina === "TCC1" ? "Professor da disciplina" : "Orientador responsável"}
          obrigatorio
          erro={erros.professor_id}
        >
          <Selecao value={professorId} onChange={(e) => setProfessorId(e.target.value)} erro={erros.professor_id}>
            <option value="">Selecione…</option>
            {elegiveis.map((d) => (
              <option key={d.id} value={d.id}>
                {d.nome}
              </option>
            ))}
          </Selecao>
        </Campo>
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Botao variante="texto" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao carregando={ocupado} disabled={!professorId} onClick={salvar}>
            Criar turma
          </Botao>
        </div>
      </div>
    </Modal>
  );
}
