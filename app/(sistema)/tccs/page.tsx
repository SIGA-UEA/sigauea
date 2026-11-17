"use client";

// TEL04 · TCCs (RBN05.01): o aluno vê os seus; o orientador, os que orienta;
// o professor, os da sua turma; a coordenação, todos. A API filtra por perfil.

import Link from "next/link";
import { useEffect, useState } from "react";
import { Aviso } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Entrada, Selecao } from "@/components/campo";
import { Icone } from "@/components/icone";
import { SeloOrientacao, SeloSituacao } from "@/components/situacao-tcc";
import { api, ErroApi } from "@/lib/api";
import { useSessao } from "@/lib/sessao";
import {
  dataHora,
  NOME_SITUACAO_EDITORIAL,
  NOME_SITUACAO_TCC,
  type Curso,
  type Formulario,
  type Periodo,
  type SituacaoTcc,
  type Tcc,
} from "@/lib/tipos";

const FILTROS_VAZIOS = { busca: "", curso_id: "", periodo_id: "", orientador_id: "", situacao: "" };

export default function PaginaTccs() {
  const { tem } = useSessao();
  const aluno = tem("aluno");
  const [lista, setLista] = useState<Tcc[] | null>(null);
  const [form, setForm] = useState<Formulario | null>(null);
  const [semMatricula, setSemMatricula] = useState("");
  const [erro, setErro] = useState("");
  const [filtros, setFiltros] = useState(FILTROS_VAZIOS);
  const [busca, setBusca] = useState(""); // o texto só vai à API depois de uma pausa na digitação
  const [cursos, setCursos] = useState<Curso[]>([]);
  const [periodos, setPeriodos] = useState<Periodo[]>([]);
  const [orientadores, setOrientadores] = useState<Map<number, string>>(new Map());
  const filtrando = Object.values(filtros).some(Boolean);

  useEffect(() => {
    const t = setTimeout(() => setFiltros((f) => (f.busca === busca.trim() ? f : { ...f, busca: busca.trim() })), 350);
    return () => clearTimeout(t);
  }, [busca]);

  useEffect(() => {
    if (aluno) return;
    api<Curso[]>("/cursos").then(setCursos).catch(() => {});
    api<Periodo[]>("/periodos").then(setPeriodos).catch(() => {});
  }, [aluno]);

  useEffect(() => {
    const params = new URLSearchParams(Object.entries(filtros).filter(([, v]) => v));
    api<Tcc[]>(`/tccs${params.size ? `?${params}` : ""}`)
      .then((l) => {
        setErro("");
        setLista(l);
        // As opções de orientador vêm dos TCCs já carregados, sem filtro, para a lista de opções não encolher.
        if (!filtrando)
          setOrientadores(new Map(l.flatMap((t) => (t.orientador && t.orientador.status !== "RECUSADA" ? [[t.orientador.professor.id, t.orientador.professor.nome] as const] : []))));
      })
      .catch((e: ErroApi) => setErro(e.message));
  }, [filtros, filtrando]);

  useEffect(() => {
    if (aluno) {
      api<Formulario>("/tccs/formulario")
        .then(setForm)
        .catch((e: ErroApi) => e.status === 403 && setSemMatricula(e.message));
    }
  }, [aluno]);

  const mudar = (campo: keyof typeof FILTROS_VAZIOS) => (e: { target: { value: string } }) =>
    setFiltros((f) => ({ ...f, [campo]: e.target.value }));
  const limpar = () => (setBusca(""), setFiltros(FILTROS_VAZIOS));

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

      {!aluno && (
        <section aria-label="Filtros" className="flex flex-wrap items-end gap-3 rounded-xl border border-borda bg-superficie p-4">
          <label className="flex min-w-56 flex-1 flex-col gap-1 text-sm font-medium">
            Buscar
            <Entrada
              type="search"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Título, protocolo ou aluno"
              maxLength={100}
            />
          </label>
          <label className="flex w-44 flex-col gap-1 text-sm font-medium">
            Curso
            <Selecao value={filtros.curso_id} onChange={mudar("curso_id")}>
              <option value="">Todos</option>
              {cursos.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.sigla}
                </option>
              ))}
            </Selecao>
          </label>
          <label className="flex w-36 flex-col gap-1 text-sm font-medium">
            Período
            <Selecao value={filtros.periodo_id} onChange={mudar("periodo_id")}>
              <option value="">Todos</option>
              {periodos.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.codigo}
                </option>
              ))}
            </Selecao>
          </label>
          <label className="flex w-52 flex-col gap-1 text-sm font-medium">
            Orientador
            <Selecao value={filtros.orientador_id} onChange={mudar("orientador_id")}>
              <option value="">Todos</option>
              {[...orientadores].map(([id, nome]) => (
                <option key={id} value={id}>
                  {nome}
                </option>
              ))}
            </Selecao>
          </label>
          <label className="flex w-48 flex-col gap-1 text-sm font-medium">
            Situação
            <Selecao value={filtros.situacao} onChange={mudar("situacao")}>
              <option value="">Todas</option>
              {(Object.keys(NOME_SITUACAO_TCC) as SituacaoTcc[]).map((s) => (
                <option key={s} value={s}>
                  {NOME_SITUACAO_TCC[s]}
                </option>
              ))}
            </Selecao>
          </label>
          {filtrando && (
            <Botao variante="texto" onClick={limpar}>
              Limpar filtros
            </Botao>
          )}
        </section>
      )}

      <section className="overflow-hidden rounded-xl border border-borda bg-superficie">
        {!lista ? (
          <p role="status" className="p-6 text-sm text-suave">
            Carregando…
          </p>
        ) : lista.length === 0 ? (
          <p className="p-6 text-sm text-suave">
            {aluno
              ? "Você ainda não cadastrou o seu TCC."
              : filtrando
                ? "Nenhum TCC encontrado para estes filtros. Limpe os filtros para ver todos."
                : "Nenhum TCC para acompanhar ainda."}
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
                      {t.aluno.nome} · {t.curso.sigla} · {t.etapa} ·{" "}
                      {t.modalidade === "ARTIGO" ? "Artigo" : "Monografia"} · {t.turma.periodo}
                    </p>
                    {/* RBN05.01 CA-01: o orientador aparece na lista */}
                    <p className="text-sm text-suave">
                      Orientador: {t.orientador && t.orientador.status !== "RECUSADA" ? t.orientador.professor.nome : "não indicado"}
                    </p>
                  </div>
                  <div className="basis-44 text-sm">
                    <p className="font-mono">{t.protocolo ?? "sem protocolo"}</p>
                    <p className="text-suave">Atualizado em {dataHora(t.atualizado_em)}</p>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    <SeloSituacao situacao={t.situacao} />
                    {t.orientador && <SeloOrientacao status={t.orientador.status} />}
                    {/* RBN05.01 CA-03: a situação editorial do artigo fica separada da situação do cadastro */}
                    {t.artigo && t.modalidade === "ARTIGO" && (
                      <span className="rounded-full border border-borda px-2.5 py-0.5 text-[13px] text-suave">
                        Artigo: {NOME_SITUACAO_EDITORIAL[t.artigo.situacao]}
                      </span>
                    )}
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
