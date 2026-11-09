"use client";

// TEL03 · Ideias de TCC (RBN02.01 e RBN02.02 · DS-FL12 e DS-FL12-A).
//   GET  /ideias             o aluno vê as próprias propostas; o professor, as direcionadas a ele (RN25)
//   GET  /ideias/formulario  áreas e professores para a "Nova proposta" (só aluno)
//   POST /ideias             cadastra a proposta; 400 {campos} destaca o que falta (E1)
// A proposta serve à discussão e não é um cadastro de TCC (CA-01): a tela diz isso antes e depois de enviar.

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { Aviso } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Campo, Entrada, ESTILO_ENTRADA, Selecao } from "@/components/campo";
import { Icone } from "@/components/icone";
import { api, ErroApi } from "@/lib/api";
import { useSessao } from "@/lib/sessao";
import {
  dataHora,
  destinoDaProposta,
  type DestinoProposta,
  type FormularioIdeia,
  type PropostaDetalhe,
  type PropostaResumo,
} from "@/lib/tipos";

export default function PaginaIdeias() {
  const { tem } = useSessao();
  const aluno = tem("aluno");
  const [lista, setLista] = useState<PropostaResumo[] | null>(null);
  const [erro, setErro] = useState("");
  const [nova, setNova] = useState(false);
  const [aviso, setAviso] = useState("");

  useEffect(() => {
    api<PropostaResumo[]>("/ideias").then(setLista).catch((e: ErroApi) => setErro(e.message));
  }, []);

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold tracking-widest text-suave uppercase">Ideias</p>
          <h1 className="text-2xl font-semibold">Ideias de TCC</h1>
          <p className="mt-1 text-sm text-suave">
            {aluno
              ? "Compartilhe uma ideia com os professores antes de cadastrar o TCC."
              : "Propostas de alunos enviadas para você ou para uma área em que você atua."}
          </p>
        </div>
        {aluno && !nova && (
          <Botao onClick={() => setNova(true)}>
            <Icone nome="mais" className="size-4" /> Nova proposta
          </Botao>
        )}
      </header>

      <div role="status" className="empty:hidden">
        {aviso && <Aviso tipo="sucesso">{aviso}</Aviso>}
      </div>

      {nova && (
        <NovaProposta
          aoCancelar={() => setNova(false)}
          aoCriar={(p) => {
            setNova(false);
            setLista((l) => [p, ...(l ?? [])]);
            setAviso(
              p.destino === "AREA"
                ? `Proposta enviada. Os professores da área ${p.area?.nome ?? ""} já podem ver e comentar.`
                : "Proposta enviada. Os professores escolhidos já podem ver e comentar.",
            );
          }}
        />
      )}

      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      {!lista ? (
        !erro && (
          <p role="status" className="text-sm text-suave">
            Carregando…
          </p>
        )
      ) : lista.length === 0 ? (
        <div className="rounded-xl border border-borda bg-superficie p-6 text-sm">
          <p className="font-medium">{aluno ? "Você ainda não enviou propostas" : "Nenhuma proposta para você"}</p>
          <p className="mt-1 text-suave">
            {aluno
              ? "Use “Nova proposta” para mostrar sua ideia a professores ou a uma área de interesse."
              : "Quando um aluno enviar uma proposta para você ou para uma área em que você atua, ela aparece aqui."}
          </p>
        </div>
      ) : (
        <ul className="flex flex-col gap-3" aria-label="Propostas">
          {lista.map((p) => (
            <li key={p.id}>
              <Link
                href={`/ideias/${p.id}`}
                className="flex flex-col gap-1 rounded-xl border border-borda bg-superficie p-4 hover:border-azul focus-visible:border-azul"
              >
                <span className="font-semibold break-words">{p.titulo}</span>
                <span className="text-[13px] text-suave">
                  {aluno ? "Enviada" : p.autor.nome} · {dataHora(p.criado_em)}
                  {p.area && <> · {p.area.nome}</>}
                </span>
                <span className="text-[13px] break-words text-suave">Para: {destinoDaProposta(p)}</span>
                <span className="text-[13px] font-medium text-azul-forte">
                  {p.comentarios === 0
                    ? "Sem comentários"
                    : p.comentarios === 1
                      ? "1 comentário"
                      : `${p.comentarios} comentários`}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- DS-FL12 · nova proposta

type Erros = Partial<Record<"titulo" | "descricao" | "area_id" | "destino" | "professores_ids", string>>;

function NovaProposta({
  aoCancelar,
  aoCriar,
}: {
  aoCancelar: () => void;
  aoCriar: (p: PropostaDetalhe) => void;
}) {
  const [form, setForm] = useState<FormularioIdeia | null>(null);
  const [falha, setFalha] = useState("");
  const [titulo, setTitulo] = useState("");
  const [descricao, setDescricao] = useState("");
  const [area, setArea] = useState("");
  const [destino, setDestino] = useState<DestinoProposta | null>(null);
  const [professores, setProfessores] = useState<number[]>([]);
  const [erros, setErros] = useState<Erros>({});
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    api<FormularioIdeia>("/ideias/formulario").then(setForm).catch((e: ErroApi) => setFalha(e.message));
  }, []);

  const alternar = (id: number) =>
    setProfessores((l) => (l.includes(id) ? l.filter((x) => x !== id) : [...l, id]));

  // H5: confere na tela o que a API confere de novo (E1).
  const enviar = (e: FormEvent) => {
    e.preventDefault();
    const novos: Erros = {};
    if (!titulo.trim()) novos.titulo = "Informe o título.";
    if (!descricao.trim()) novos.descricao = "Descreva a ideia.";
    if (!area) novos.area_id = "Escolha a área de interesse.";
    if (!destino) novos.destino = "Escolha para quem enviar: professores ou a área.";
    if (destino === "PROFESSORES" && professores.length === 0) novos.professores_ids = "Escolha ao menos um professor.";
    setErros(novos);
    setFalha("");
    if (Object.keys(novos).length) return;
    setEnviando(true);
    api<PropostaDetalhe>("/ideias", {
      metodo: "POST",
      corpo: {
        titulo: titulo.trim(),
        descricao: descricao.trim(),
        area_id: Number(area),
        destino,
        professores_ids: destino === "PROFESSORES" ? professores : [],
      },
    })
      .then(aoCriar)
      .catch((err: ErroApi) => {
        if (err.campos) setErros(err.campos as Erros);
        else setFalha(err.message);
      })
      .finally(() => setEnviando(false));
  };

  const areaEscolhida = form?.areas.find((a) => String(a.id) === area);
  return (
    <section className="rounded-xl border border-borda bg-superficie p-5" aria-labelledby="titulo-nova">
      <h2 id="titulo-nova" className="font-semibold">
        Nova proposta
      </h2>
      <p className="mb-4 text-[13px] text-suave">
        A proposta é só para conversar sobre a ideia: não gera protocolo nem cadastro de TCC.
      </p>
      {!form ? (
        falha ? (
          <Aviso tipo="erro">{falha}</Aviso>
        ) : (
          <p role="status" className="text-sm text-suave">
            Carregando…
          </p>
        )
      ) : (
        <form onSubmit={enviar} noValidate className="flex flex-col gap-4">
          <Campo rotulo="Título" obrigatorio erro={erros.titulo}>
            <Entrada value={titulo} onChange={(e) => setTitulo(e.target.value)} maxLength={200} erro={erros.titulo} />
          </Campo>
          <Campo rotulo="Descrição da ideia" obrigatorio erro={erros.descricao}>
            <textarea
              value={descricao}
              onChange={(e) => setDescricao(e.target.value)}
              rows={5}
              maxLength={5000}
              aria-invalid={erros.descricao ? true : undefined}
              className={`${ESTILO_ENTRADA} h-auto py-2 ${erros.descricao ? "border-vermelho" : "border-borda"}`}
            />
          </Campo>
          <Campo rotulo="Área de interesse" obrigatorio erro={erros.area_id}>
            <Selecao value={area} onChange={(e) => setArea(e.target.value)} erro={erros.area_id}>
              <option value="">Escolha a área</option>
              {form.areas.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.nome}
                </option>
              ))}
            </Selecao>
          </Campo>

          <fieldset className="flex flex-col gap-2">
            <legend className="mb-1 text-sm font-medium">
              Enviar para <span className="text-vermelho" title="Obrigatório">*</span>
            </legend>
            <div className="grid gap-2 sm:grid-cols-2">
              {(
                [
                  ["PROFESSORES", "Professores que eu escolher", "Só eles veem a proposta."],
                  [
                    "AREA",
                    "Todos os professores da área",
                    areaEscolhida
                      ? `Quem atua em ${areaEscolhida.nome} vê a proposta.`
                      : "Quem atua na área escolhida vê a proposta.",
                  ],
                ] as const
              ).map(([valor, rotulo, dica]) => (
                <label
                  key={valor}
                  className={`flex cursor-pointer gap-3 rounded-lg border p-3 text-sm has-[:checked]:border-azul has-[:checked]:bg-azul-claro ${
                    erros.destino ? "border-vermelho" : "border-borda"
                  }`}
                >
                  <input
                    type="radio"
                    name="destino"
                    checked={destino === valor}
                    onChange={() => setDestino(valor)}
                    className="mt-0.5 size-4 shrink-0 accent-azul"
                  />
                  <span className="flex flex-col gap-0.5">
                    <span className="font-medium">{rotulo}</span>
                    <span className="text-[13px] text-suave">{dica}</span>
                  </span>
                </label>
              ))}
            </div>
            {erros.destino && (
              <span role="alert" className="text-[13px] font-medium text-vermelho">
                {erros.destino}
              </span>
            )}
          </fieldset>

          {destino === "PROFESSORES" && (
            <fieldset className="flex flex-col gap-2">
              <legend className="mb-1 text-sm font-medium">
                Professores <span className="text-vermelho" title="Obrigatório">*</span>
              </legend>
              <div
                className={`grid max-h-64 gap-1 overflow-y-auto rounded-lg border p-2 sm:grid-cols-2 ${
                  erros.professores_ids ? "border-vermelho" : "border-borda"
                }`}
              >
                {form.docentes.map((d) => (
                  <label key={d.id} className="flex cursor-pointer items-center gap-2 rounded-md p-2 text-sm hover:bg-fundo">
                    <input
                      type="checkbox"
                      checked={professores.includes(d.id)}
                      onChange={() => alternar(d.id)}
                      className="size-4 shrink-0 accent-azul"
                    />
                    <span className="break-words">{d.nome}</span>
                  </label>
                ))}
              </div>
              <span className="text-[13px] text-suave" aria-live="polite">
                {professores.length === 0
                  ? "Nenhum professor escolhido."
                  : `${professores.length} ${professores.length === 1 ? "professor escolhido" : "professores escolhidos"}.`}
              </span>
              {erros.professores_ids && (
                <span role="alert" className="text-[13px] font-medium text-vermelho">
                  {erros.professores_ids}
                </span>
              )}
            </fieldset>
          )}

          {falha && <Aviso tipo="erro">{falha}</Aviso>}
          <div className="flex flex-wrap gap-2">
            <Botao type="submit" carregando={enviando}>
              Enviar proposta
            </Botao>
            <Botao variante="texto" onClick={aoCancelar}>
              Cancelar
            </Botao>
          </div>
        </form>
      )}
    </section>
  );
}
