"use client";

// TEL05 · Cadastro de TCC (RBN03.01 a RBN03.05), seguindo os diagramas:
//   DS-FL01-A  GET  /tccs/formulario      abre o formulário (403 sem matrícula, RN05)
//   DS-FL01-B  POST /tccs | PUT /tccs/{id} salva o rascunho ao avançar de passo
//   DS-FL01    POST /tccs/{id}/submissao  envia para análise e recebe o protocolo
// O PDF não é exigido aqui (D02): ele vai depois, em Documentos e versões (RAN07).

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Aviso } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Campo, ESTILO_ENTRADA, Entrada, Selecao } from "@/components/campo";
import { Icone } from "@/components/icone";
import { Modal } from "@/components/modal";
import { SeloOrientacao } from "@/components/situacao-tcc";
import { api, ErroApi } from "@/lib/api";
import {
  NOME_SITUACAO_EDITORIAL,
  type Artigo,
  type Formulario,
  type Modalidade,
  type SituacaoEditorial,
  type Tcc,
} from "@/lib/tipos";

const PASSOS = ["Trabalho", "Orientação", "Revisar e enviar"];
const MAX_PALAVRAS_RESUMO = 500;
const MAX_PALAVRAS_CHAVE = 10;

type Erros = Record<string, string>;

const contarPalavras = (t: string) => (t.trim() ? t.trim().split(/\s+/).length : 0);

export default function PaginaCadastroTcc() {
  const router = useRouter();
  const [form, setForm] = useState<Formulario | null>(null);
  const [bloqueio, setBloqueio] = useState("");
  const [tcc, setTcc] = useState<Tcc | null>(null);
  const [passo, setPasso] = useState(1);

  // Campos do formulário (o que já foi preenchido nunca se perde num erro).
  const [titulo, setTitulo] = useState("");
  const [subtitulo, setSubtitulo] = useState("");
  const [resumo, setResumo] = useState("");
  const [palavras, setPalavras] = useState<string[]>([]);
  const [novaPalavra, setNovaPalavra] = useState("");
  const [areaId, setAreaId] = useState("");
  const [modalidade, setModalidade] = useState<Modalidade | "">("");
  const [artigo, setArtigo] = useState<Artigo>({
    tipo_veiculo: "PERIODICO",
    veiculo: "",
    situacao: "SUBMETIDO",
    doi: "",
    qualis: "",
  });
  const [orientadorId, setOrientadorId] = useState("");
  const [coorientadorId, setCoorientadorId] = useState("");

  const [erros, setErros] = useState<Erros>({});
  const [erroGeral, setErroGeral] = useState("");
  const [salvoEm, setSalvoEm] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [confirmando, setConfirmando] = useState(false);
  const [protocolo, setProtocolo] = useState("");

  function preencher(t: Tcc) {
    setTcc(t);
    setTitulo(t.titulo);
    setSubtitulo(t.subtitulo ?? "");
    setResumo(t.resumo);
    setPalavras(t.palavras_chave);
    setAreaId(String(t.area.id));
    setModalidade(t.modalidade);
    if (t.artigo) setArtigo({ ...t.artigo, doi: t.artigo.doi ?? "", qualis: t.artigo.qualis ?? "" });
    const vigente = (v: Tcc["orientador"]) => (v && v.status !== "RECUSADA" ? String(v.professor.id) : "");
    setOrientadorId(vigente(t.orientador));
    setCoorientadorId(vigente(t.coorientador));
  }

  useEffect(() => {
    api<Formulario>("/tccs/formulario")
      .then((f) => {
        setForm(f);
        if (f.tcc) preencher(f.tcc);
        else if (f.origem) {
          // TCC2: começa com os dados do TCC1, todos editáveis (RBN08.04)
          setTitulo(f.origem.titulo);
          setAreaId(String(f.origem.area_id));
          setModalidade(f.origem.modalidade);
          if (f.origem.orientador_id) setOrientadorId(String(f.origem.orientador_id));
        }
      })
      .catch((e: ErroApi) => setBloqueio(e.message));
  }, []);

  if (bloqueio) {
    return (
      <div className="flex max-w-3xl flex-col gap-5">
        <h1 className="text-2xl font-semibold">Cadastro de TCC</h1>
        <Aviso tipo="alerta">
          <strong>Seu cadastro de TCC está bloqueado.</strong> {bloqueio}
        </Aviso>
      </div>
    );
  }
  if (!form) {
    return (
      <p role="status" className="text-suave">
        Carregando…
      </p>
    );
  }

  const editavel = !tcc || tcc.situacao === "RASCUNHO" || tcc.situacao === "DEVOLVIDO";
  if (tcc && !editavel && !protocolo) {
    return (
      <div className="flex max-w-3xl flex-col gap-5">
        <h1 className="text-2xl font-semibold">Cadastro de TCC</h1>
        <Aviso tipo="info">
          O cadastro <strong className="font-mono">{tcc.protocolo}</strong> está em análise pela coordenação e não pode
          ser editado agora. <Link href={`/tccs/${tcc.id}`} className="font-medium underline">Ver acompanhamento</Link>
        </Aviso>
      </div>
    );
  }

  if (protocolo && tcc) {
    return (
      <div className="flex max-w-3xl flex-col gap-5">
        <h1 className="text-2xl font-semibold">Cadastro enviado para análise</h1>
        <Aviso tipo="sucesso">
          Protocolo <strong className="font-mono">{protocolo}</strong>. A coordenação vai analisar o cadastro e você
          será avisado por e-mail. Enquanto isso, o cadastro fica bloqueado para edição.
        </Aviso>
        <div>
          <Botao onClick={() => router.push(`/tccs/${tcc.id}`)}>Acompanhar meu TCC</Botao>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------- validação na tela
  function validar(n: number): Erros {
    const e: Erros = {};
    if (n === 1) {
      if (titulo.trim().length < 3) e.titulo = "Informe o título.";
      if (!areaId) e.area_id = "Escolha a área de interesse.";
      if (!modalidade) e.modalidade = "Escolha a modalidade.";
      if (contarPalavras(resumo) > MAX_PALAVRAS_RESUMO) e.resumo = `O resumo passa de ${MAX_PALAVRAS_RESUMO} palavras.`;
      if (modalidade === "ARTIGO" && artigo.veiculo.trim() && artigo.situacao === "PUBLICADO" && !artigo.doi?.trim())
        e.doi = "Informe o DOI do artigo publicado.";
    }
    if (n === 2 && coorientadorId && coorientadorId === orientadorId)
      e.coorientador_id = "O coorientador não pode ser o próprio orientador.";
    return e;
  }

  function corpo() {
    return {
      titulo,
      subtitulo: subtitulo || null,
      resumo,
      palavras_chave: palavras,
      area_id: Number(areaId),
      modalidade,
      orientador_id: orientadorId ? Number(orientadorId) : null,
      coorientador_id: coorientadorId ? Number(coorientadorId) : null,
      artigo:
        modalidade === "ARTIGO" && artigo.veiculo.trim()
          ? { ...artigo, doi: artigo.doi || null, qualis: artigo.qualis || null }
          : null,
    };
  }

  // DS-FL01-B: salva o rascunho (cria na primeira vez, depois atualiza)
  async function salvar(): Promise<boolean> {
    setErroGeral("");
    setOcupado(true);
    try {
      const salvo = tcc
        ? await api<Tcc>(`/tccs/${tcc.id}`, { metodo: "PUT", corpo: corpo() })
        : await api<Tcc>("/tccs", { metodo: "POST", corpo: corpo() });
      preencher(salvo);
      setSalvoEm(new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }));
      setOcupado(false);
      return true;
    } catch (e) {
      const erro = e as ErroApi;
      if (erro.campos) setErros(erro.campos);
      setErroGeral(erro.message);
      setOcupado(false);
      return false;
    }
  }

  async function avancar() {
    const e = validar(passo);
    setErros(e);
    if (Object.keys(e).length) return;
    if (await salvar()) setPasso(passo + 1);
  }

  // RBN03.01: salvar o rascunho mantém o aluno em TEL05 ("Rascunho salvo às HH:MM").
  async function salvarRascunho() {
    const e = validar(1);
    setErros(e);
    if (Object.keys(e).length) return setPasso(1);
    await salvar();
  }

  // DS-FL01: submissão
  async function enviar() {
    if (!tcc) return;
    setOcupado(true);
    try {
      const r = await api<{ protocolo: string; tcc: Tcc }>(`/tccs/${tcc.id}/submissao`, { metodo: "POST" });
      setTcc(r.tcc);
      setProtocolo(r.protocolo);
    } catch (e) {
      const erro = e as ErroApi;
      setErroGeral(erro.campos_pendentes ? "Ainda falta: " + erro.campos_pendentes.join(" ") : erro.message);
    }
    setOcupado(false);
    setConfirmando(false);
  }

  // Ao mexer num campo, a mensagem de erro dele some (as outras ficam).
  function limpar(campo: string) {
    if (erros[campo]) setErros({ ...erros, [campo]: "" });
  }

  function adicionarPalavra() {
    const p = novaPalavra.trim();
    if (!p) return;
    if (palavras.length >= MAX_PALAVRAS_CHAVE) return setErros({ ...erros, palavras_chave: "No máximo 10 palavras-chave." });
    if (palavras.some((x) => x.toLowerCase() === p.toLowerCase()))
      return setErros({ ...erros, palavras_chave: "Esta palavra-chave já foi incluída." });
    setPalavras([...palavras, p]);
    setNovaPalavra("");
    setErros({ ...erros, palavras_chave: "" });
  }

  const area = form.areas.find((a) => String(a.id) === areaId);
  const devolvido = tcc?.situacao === "DEVOLVIDO";

  return (
    <div className="flex max-w-4xl flex-col gap-5">
      <header>
        <p className="text-sm font-medium text-azul-forte">
          {form.turma.codigo} · {form.turma.disciplina} · {form.turma.periodo}
        </p>
        <h1 className="text-2xl font-semibold">Cadastro de TCC</h1>
        <p className="mt-1 text-sm text-suave">
          Três passos, com salvamento ao continuar. Depois de enviado, a coordenação analisa e você recebe o parecer.
        </p>
      </header>

      {devolvido && tcc?.protocolo && (
        <Aviso tipo="alerta">
          <strong>Cadastro devolvido para correção.</strong> Ao reenviar, o protocolo{" "}
          <span className="font-mono">{tcc.protocolo}</span> é mantido.
        </Aviso>
      )}
      {erroGeral && <Aviso tipo="erro">{erroGeral}</Aviso>}

      <ol className="flex flex-wrap gap-2" aria-label="Passos do cadastro">
        {PASSOS.map((nome, i) => {
          const n = i + 1;
          const atual = n === passo;
          return (
            <li
              key={nome}
              aria-current={atual ? "step" : undefined}
              className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm ${
                atual
                  ? "border-azul bg-azul-claro font-medium text-azul-escuro"
                  : n < passo
                    ? "border-borda text-verde"
                    : "border-borda text-suave"
              }`}
            >
              <span className="flex size-5 items-center justify-center rounded-full border text-xs">
                {n < passo ? <Icone nome="certo" className="size-3" /> : n}
              </span>
              {nome}
            </li>
          );
        })}
      </ol>

      <section className="flex flex-col gap-5 rounded-xl border border-borda bg-superficie p-5">
        {passo === 1 && (
          <>
            <h2 className="font-semibold">1. Trabalho</h2>
            <Campo rotulo="Título do trabalho" obrigatorio erro={erros.titulo}>
              <Entrada value={titulo} onChange={(e) => (setTitulo(e.target.value), limpar("titulo"))} maxLength={300} erro={erros.titulo} />
            </Campo>
            <Campo rotulo="Subtítulo" dica="opcional" erro={erros.subtitulo}>
              <Entrada value={subtitulo} onChange={(e) => setSubtitulo(e.target.value)} maxLength={300} />
            </Campo>
            <Campo rotulo="Resumo" obrigatorio erro={erros.resumo}>
              <textarea
                value={resumo}
                onChange={(e) => (setResumo(e.target.value), limpar("resumo"))}
                rows={6}
                aria-invalid={erros.resumo ? true : undefined}
                className={`${ESTILO_ENTRADA} h-auto py-2 ${erros.resumo ? "border-vermelho" : "border-borda"}`}
              />
              <span
                className={`text-[13px] ${contarPalavras(resumo) > MAX_PALAVRAS_RESUMO ? "font-medium text-vermelho" : "text-suave"}`}
              >
                {contarPalavras(resumo)} de {MAX_PALAVRAS_RESUMO} palavras
              </span>
            </Campo>

            <fieldset className="flex flex-col gap-2 text-sm">
              <legend className="mb-1 font-medium">
                Palavras-chave <span className="text-vermelho">*</span>{" "}
                <span className="font-normal text-suave">
                  ({palavras.length} de {MAX_PALAVRAS_CHAVE})
                </span>
              </legend>
              <div className="flex flex-wrap gap-2">
                {palavras.map((p) => (
                  <span key={p} className="inline-flex items-center gap-1 rounded-full bg-azul-claro py-1 pr-1 pl-3 text-azul-escuro">
                    {p}
                    <button
                      type="button"
                      onClick={() => setPalavras(palavras.filter((x) => x !== p))}
                      aria-label={`Remover ${p}`}
                      className="flex size-6 items-center justify-center rounded-full hover:bg-white/60"
                    >
                      <Icone nome="fechar" className="size-3.5" />
                    </button>
                  </span>
                ))}
              </div>
              <div className="flex gap-2">
                <Entrada
                  value={novaPalavra}
                  onChange={(e) => setNovaPalavra(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      adicionarPalavra();
                    }
                  }}
                  maxLength={60}
                  placeholder="Digite e tecle Enter"
                  aria-label="Nova palavra-chave"
                  className="max-w-xs"
                />
                <Botao variante="contorno" onClick={adicionarPalavra}>
                  Incluir
                </Botao>
              </div>
              {erros.palavras_chave && (
                <span role="alert" className="text-[13px] font-medium text-vermelho">
                  {erros.palavras_chave}
                </span>
              )}
            </fieldset>

            <div className="grid gap-4 sm:grid-cols-2">
              <Campo rotulo="Área de interesse" obrigatorio erro={erros.area_id}>
                <Selecao value={areaId} onChange={(e) => (setAreaId(e.target.value), limpar("area_id"))} erro={erros.area_id}>
                  <option value="">Escolha…</option>
                  {form.areas.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.nome}
                    </option>
                  ))}
                </Selecao>
              </Campo>
              <div className="flex flex-col gap-1.5 text-sm">
                <span className="font-medium">Etapa</span>
                <p className="flex h-11 items-center text-texto">{form.turma.disciplina} (vem da sua turma)</p>
              </div>
            </div>

            <fieldset className="text-sm">
              <legend className="mb-2 font-medium">
                Modalidade <span className="text-vermelho">*</span>
              </legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {(
                  [
                    ["MONOGRAFIA", "Monografia", "Texto completo do trabalho"],
                    ["ARTIGO", "Artigo", "Artigo científico, com registro de submissão"],
                  ] as const
                ).map(([valor, rotulo, dica]) => (
                  <label
                    key={valor}
                    className="flex cursor-pointer items-start gap-2.5 rounded-lg border border-borda px-3 py-2.5 has-checked:border-azul has-checked:bg-azul-claro"
                  >
                    <input
                      type="radio"
                      name="modalidade"
                      checked={modalidade === valor}
                      onChange={() => (setModalidade(valor), limpar("modalidade"))}
                      className="mt-0.5 size-4 accent-azul"
                    />
                    <span>
                      <span className="font-medium">{rotulo}</span>
                      <span className="block text-[13px] text-suave">{dica}</span>
                    </span>
                  </label>
                ))}
              </div>
              {erros.modalidade && (
                <span role="alert" className="mt-1 block text-[13px] font-medium text-vermelho">
                  {erros.modalidade}
                </span>
              )}
            </fieldset>

            {modalidade === "ARTIGO" && (
              <div className="flex flex-col gap-4 rounded-lg bg-fundo p-4">
                <div>
                  <h3 className="font-medium">Informações do artigo</h3>
                  <p className="text-[13px] text-suave">
                    Opcional agora; pode completar depois. A situação editorial não é a situação do cadastro.
                  </p>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <Campo rotulo="Veículo (revista ou evento)" erro={erros.veiculo}>
                    <Entrada
                      value={artigo.veiculo}
                      onChange={(e) => setArtigo({ ...artigo, veiculo: e.target.value })}
                      maxLength={200}
                    />
                  </Campo>
                  <Campo rotulo="Tipo de veículo">
                    <Selecao
                      value={artigo.tipo_veiculo}
                      onChange={(e) => setArtigo({ ...artigo, tipo_veiculo: e.target.value as Artigo["tipo_veiculo"] })}
                    >
                      <option value="PERIODICO">Revista / periódico</option>
                      <option value="CONGRESSO">Congresso</option>
                    </Selecao>
                  </Campo>
                  <Campo rotulo="Situação editorial">
                    <Selecao
                      value={artigo.situacao}
                      onChange={(e) => setArtigo({ ...artigo, situacao: e.target.value as SituacaoEditorial })}
                    >
                      {Object.entries(NOME_SITUACAO_EDITORIAL).map(([v, r]) => (
                        <option key={v} value={v}>
                          {r}
                        </option>
                      ))}
                    </Selecao>
                  </Campo>
                  <Campo
                    rotulo="DOI"
                    obrigatorio={artigo.situacao === "PUBLICADO"}
                    dica="obrigatório se publicado"
                    erro={erros.doi}
                  >
                    <Entrada
                      value={artigo.doi ?? ""}
                      onChange={(e) => (setArtigo({ ...artigo, doi: e.target.value }), limpar("doi"))}
                      placeholder="10.xxxx/xxxxx"
                      erro={erros.doi}
                    />
                  </Campo>
                </div>
              </div>
            )}
          </>
        )}

        {passo === 2 && (
          <>
            <h2 className="font-semibold">2. Orientação</h2>
            <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-[max-content_1fr]">
              <dt className="text-suave">Autor(a)</dt>
              <dd>{tcc?.aluno.nome}, matrícula {tcc?.matricula}</dd>
              <dt className="text-suave">Curso</dt>
              <dd>{tcc?.curso.nome}</dd>
            </dl>
            <div className="grid gap-4 sm:grid-cols-2">
              <Campo rotulo="Orientador" obrigatorio erro={erros.orientador_id}>
                <Selecao
                  value={orientadorId}
                  onChange={(e) => (setOrientadorId(e.target.value), limpar("orientador_id"))}
                  erro={erros.orientador_id}
                  disabled={tcc?.orientador?.status === "ACEITA"}
                >
                  <option value="">Selecione…</option>
                  {form.orientadores.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.nome}
                    </option>
                  ))}
                </Selecao>
              </Campo>
              <Campo rotulo="Coorientador" dica="opcional" erro={erros.coorientador_id}>
                <Selecao
                  value={coorientadorId}
                  onChange={(e) => (setCoorientadorId(e.target.value), limpar("coorientador_id"))}
                  erro={erros.coorientador_id}
                  disabled={tcc?.coorientador?.status === "ACEITA"}
                >
                  <option value="">Sem coorientador</option>
                  {form.coorientadores
                    .filter((d) => String(d.id) !== orientadorId)
                    .map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.nome}
                      </option>
                    ))}
                </Selecao>
              </Campo>
            </div>
            <VinculoAtual tcc={tcc} />
            <p className="text-[13px] text-suave">
              O orientador recebe um e-mail e precisa aceitar o pedido. O cadastro só pode ser enviado depois do aceite.
              Depois do aceite, a troca de orientador é feita pela coordenação.
            </p>
          </>
        )}

        {passo === 3 && tcc && (
          <>
            <h2 className="font-semibold">3. Revisar e enviar</h2>
            {tcc.pendencias.length > 0 ? (
              <Aviso tipo="alerta">
                <strong>Antes de enviar:</strong>
                <ul className="mt-1 list-disc pl-5">
                  {tcc.pendencias.map((p) => (
                    <li key={p}>{p}</li>
                  ))}
                </ul>
              </Aviso>
            ) : (
              <Aviso tipo="sucesso">Tudo certo. O cadastro pode ser enviado para análise.</Aviso>
            )}
            <Resumo
              itens={[
                ["Título", tcc.titulo + (tcc.subtitulo ? `: ${tcc.subtitulo}` : "")],
                ["Resumo", tcc.resumo || "não informado"],
                ["Palavras-chave", tcc.palavras_chave.join(", ") || "não informadas"],
                ["Área", area?.nome ?? "—"],
                ["Etapa e modalidade", `${tcc.etapa} · ${tcc.modalidade === "ARTIGO" ? "Artigo" : "Monografia"}`],
                ["Orientador", tcc.orientador ? `${tcc.orientador.professor.nome}` : "não indicado"],
                ["Coorientador", tcc.coorientador ? tcc.coorientador.professor.nome : "—"],
                ...(tcc.artigo
                  ? [["Artigo", `${tcc.artigo.veiculo} · ${NOME_SITUACAO_EDITORIAL[tcc.artigo.situacao]}`] as [string, string]]
                  : []),
              ]}
            />
            <p className="text-[13px] text-suave">
              O PDF do trabalho não é exigido agora; ele será enviado depois, em Documentos e versões.
            </p>
          </>
        )}
      </section>

      <div className="flex flex-col-reverse items-stretch justify-between gap-3 sm:flex-row sm:items-center">
        <span className="text-[13px] text-suave">
          {salvoEm ? `Rascunho salvo às ${salvoEm}.` : "Campos com * são obrigatórios."}
        </span>
        <div className="flex flex-wrap justify-end gap-2">
          {passo > 1 && (
            <Botao variante="texto" onClick={() => setPasso(passo - 1)}>
              <Icone nome="voltar" className="size-4" />
              Voltar
            </Botao>
          )}
          <Botao variante="contorno" carregando={ocupado} onClick={salvarRascunho}>
            Salvar rascunho
          </Botao>
          {passo < 3 ? (
            <Botao carregando={ocupado} onClick={avancar}>
              Continuar
            </Botao>
          ) : (
            <Botao disabled={!tcc || tcc.pendencias.length > 0} onClick={() => setConfirmando(true)}>
              <Icone nome="enviar" className="size-4" />
              Enviar para análise
            </Botao>
          )}
        </div>
      </div>

      {confirmando && (
        <Modal titulo="Enviar cadastro para análise?" aoFechar={() => setConfirmando(false)}>
          <p className="text-sm">
            Depois de enviado, o cadastro só volta a ficar editável se a coordenação devolver. Você recebe um protocolo
            e é avisado do parecer.
          </p>
          <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Botao variante="texto" onClick={() => setConfirmando(false)}>
              Cancelar
            </Botao>
            <Botao carregando={ocupado} onClick={enviar}>
              Enviar para análise
            </Botao>
          </div>
        </Modal>
      )}
    </div>
  );
}

function VinculoAtual({ tcc }: { tcc: Tcc | null }) {
  const vinculos = [tcc?.orientador, tcc?.coorientador].filter(Boolean) as NonNullable<Tcc["orientador"]>[];
  if (!vinculos.length) return null;
  return (
    <ul className="flex flex-col gap-2 text-sm">
      {vinculos.map((v) => (
        <li key={v.id} className="flex flex-wrap items-center gap-2 rounded-lg border border-borda px-3 py-2">
          <span className="font-medium">{v.papel === "ORIENTADOR" ? "Orientador" : "Coorientador"}:</span>
          {v.professor.nome}
          <SeloOrientacao status={v.status} />
          {v.motivo_recusa && <span className="w-full text-[13px] text-suave">Motivo da recusa: {v.motivo_recusa}</span>}
        </li>
      ))}
    </ul>
  );
}

function Resumo({ itens }: { itens: [string, string][] }) {
  return (
    <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-[max-content_1fr]">
      {itens.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="text-suave">{k}</dt>
          <dd className="break-words whitespace-pre-wrap">{v}</dd>
        </div>
      ))}
    </dl>
  );
}
