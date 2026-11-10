"use client";

// TEL08 · Orientação do TCC, como seção da página do TCC (decisão 33-f). Mostra orientador e coorientador e, para a
// coordenação e o orientador do TCC, as ações do DS-FL03-D (RBN01.13): informar o coorientador, docente da UEA ou
// pessoa externa (POST /tccs/{id}/orientacoes), e remover o coorientador com justificativa
// (DELETE /tccs/{id}/orientacoes/{orientacao_id}). O coorientador externo aparece com a instituição e, até ativar
// a conta, com o selo "Aguardando ativação". A API confere de novo quem pode (403 para os demais).

import { useEffect, useState } from "react";
import { Aviso, Selo } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Campo, Entrada, ESTILO_ENTRADA, Selecao } from "@/components/campo";
import { Modal } from "@/components/modal";
import { SeloOrientacao } from "@/components/situacao-tcc";
import { api, ErroApi } from "@/lib/api";
import { useSessao } from "@/lib/sessao";
import type { Banca, Pessoa, Tcc, Vinculo } from "@/lib/tipos";

export function SecaoOrientacao({ tcc, aoMudar }: { tcc: Tcc; aoMudar: () => void }) {
  const { usuario, tem } = useSessao();
  const [informando, setInformando] = useState(false);
  const [removendo, setRemovendo] = useState<Vinculo | null>(null);
  const [aviso, setAviso] = useState("");

  // DS-FL03-D mensagem 3: a coordenação ou o orientador do TCC (com a orientação aceita).
  const orientadorDoTcc = tcc.orientador?.status === "ACEITA" && tcc.orientador.professor.id === usuario.id;
  const podeGerir = tem("coordenador") || orientadorDoTcc;
  const vinculos = [tcc.orientador, tcc.coorientador].filter((v): v is Vinculo => v !== null);

  return (
    <section className="rounded-xl border border-borda bg-superficie p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-semibold">Orientação</h2>
        {podeGerir && !tcc.coorientador && (
          <Botao variante="contorno" pequeno onClick={() => (setAviso(""), setInformando(true))}>
            Informar coorientador
          </Botao>
        )}
      </div>

      {vinculos.length === 0 ? (
        <p className="text-sm text-suave">Nenhum orientador indicado ainda.</p>
      ) : (
        <ul className="flex flex-col gap-3 text-sm">
          {vinculos.map((v) => (
            <li key={v.id} className="flex flex-wrap items-center gap-2">
              <span className="font-medium">{v.papel === "ORIENTADOR" ? "Orientador" : "Coorientador"}:</span>
              <span>
                {v.professor.nome}
                {v.externo && v.instituicao && <span className="text-suave"> · {v.instituicao}</span>}
              </span>
              {v.externo && <Selo cor="cinza">Externo</Selo>}
              {v.externo && v.status === "PENDENTE" ? (
                <Selo cor="ambar">Aguardando ativação</Selo>
              ) : (
                <SeloOrientacao status={v.status} />
              )}
              {podeGerir && v.papel === "COORIENTADOR" && (
                <Botao variante="perigo" pequeno className="ml-auto" onClick={() => (setAviso(""), setRemovendo(v))}>
                  Remover
                </Botao>
              )}
              {v.motivo_recusa && <span className="w-full text-[13px] text-suave">Motivo: {v.motivo_recusa}</span>}
              {v.externo && v.status === "PENDENTE" && (
                <span className="w-full text-[13px] text-suave">
                  O link para criar a senha foi enviado para o e-mail informado e vale 48 horas. Ao ativar a conta, a
                  coorientação fica aceita.
                </span>
              )}
            </li>
          ))}
        </ul>
      )}

      {aviso && (
        <div className="mt-3">
          <Aviso tipo="sucesso">{aviso}</Aviso>
        </div>
      )}

      {informando && (
        <InformarCoorientador
          tcc={tcc}
          aoFechar={() => setInformando(false)}
          aoInformar={(v) => {
            setInformando(false);
            setAviso(
              v.externo
                ? `${v.professor.nome} foi informado(a) como coorientador(a). O link de acesso foi enviado por e-mail.`
                : `${v.professor.nome} foi indicado(a) como coorientador(a) e recebe o pedido em "Orientações".`,
            );
            aoMudar();
          }}
        />
      )}
      {removendo && (
        <RemoverCoorientador
          tcc={tcc}
          vinculo={removendo}
          aoFechar={() => setRemovendo(null)}
          aoRemover={() => {
            setRemovendo(null);
            setAviso("Coorientação encerrada. O histórico do vínculo fica registrado.");
            aoMudar();
          }}
        />
      )}
    </section>
  );
}

// ---------------------------------------------------------------- DS-FL03-D mensagens 1 a 12

function InformarCoorientador({
  tcc,
  aoFechar,
  aoInformar,
}: {
  tcc: Tcc;
  aoFechar: () => void;
  aoInformar: (v: Vinculo) => void;
}) {
  const [tipo, setTipo] = useState<"docente" | "externo">("docente");
  const [docentes, setDocentes] = useState<Pessoa[] | null>(null);
  const [docente, setDocente] = useState("");
  const [externo, setExterno] = useState({ nome: "", email: "", instituicao: "" });
  const [erros, setErros] = useState<Record<string, string>>({});
  const [geral, setGeral] = useState("");
  const [enviando, setEnviando] = useState(false);

  // A lista de docentes ativos vem da consulta da banca, que a coordenação e o orientador já podem abrir.
  const orientadorId = tcc.orientador?.professor.id;
  useEffect(() => {
    api<Banca>(`/tccs/${tcc.id}/banca`)
      .then((b) => setDocentes(b.docentes.filter((d) => d.id !== orientadorId)))
      .catch(() => setDocentes([]));
  }, [tcc.id, orientadorId]);

  async function informar(e: React.FormEvent) {
    e.preventDefault();
    const faltas: Record<string, string> = {};
    if (tipo === "docente" && !docente) faltas.professor_id = "Escolha o docente.";
    if (tipo === "externo") {
      if (externo.nome.trim().length < 3) faltas.nome = "Informe o nome.";
      if (!/^\S+@\S+\.\S+$/.test(externo.email.trim())) faltas.email = "Informe um e-mail válido.";
      if (externo.instituicao.trim().length < 2) faltas.instituicao = "Informe a instituição.";
    }
    setErros(faltas);
    setGeral("");
    if (Object.keys(faltas).length) return;

    setEnviando(true);
    try {
      const corpo =
        tipo === "docente"
          ? { papel: "COORIENTADOR", professor_id: Number(docente) }
          : { papel: "COORIENTADOR", externo: { ...externo, email: externo.email.trim() } };
      aoInformar(await api<Vinculo>(`/tccs/${tcc.id}/orientacoes`, { metodo: "POST", corpo }));
    } catch (e) {
      const erro = e as ErroApi;
      if (erro.campos) setErros(erro.campos);
      else if (erro.campo) setErros({ [erro.campo]: erro.message });
      else setGeral(erro.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Modal titulo="Informar coorientador" aoFechar={aoFechar} largo>
      <form onSubmit={informar} noValidate className="flex flex-col gap-4">
        <fieldset className="flex flex-wrap gap-4 text-sm">
          <legend className="sr-only">Quem é o coorientador</legend>
          {(["docente", "externo"] as const).map((t) => (
            <label key={t} className="flex items-center gap-2">
              <input type="radio" name="tipo" checked={tipo === t} onChange={() => (setTipo(t), setErros({}))} />
              {t === "docente" ? "Docente da UEA" : "Pessoa externa"}
            </label>
          ))}
        </fieldset>

        {tipo === "docente" ? (
          <>
            <Campo rotulo="Docente" obrigatorio erro={erros.professor_id ?? erros.coorientador_id}>
              <Selecao value={docente} onChange={(e) => setDocente(e.target.value)} erro={erros.professor_id}>
                <option value="">Escolha…</option>
                {(docentes ?? []).map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.nome}
                  </option>
                ))}
              </Selecao>
            </Campo>
            <p className="text-[13px] text-suave">O docente recebe o pedido em &quot;Orientações&quot; e aceita ou recusa.</p>
          </>
        ) : (
          <>
            <Aviso tipo="info">
              Será criada uma conta limitada a este TCC: a pessoa só poderá ver este trabalho. O link para criar a senha
              vai para o e-mail informado e vale 48 horas.
            </Aviso>
            <div className="grid gap-3 sm:grid-cols-2">
              <Campo rotulo="Nome" obrigatorio erro={erros.nome}>
                <Entrada
                  value={externo.nome}
                  onChange={(e) => setExterno({ ...externo, nome: e.target.value })}
                  erro={erros.nome}
                />
              </Campo>
              <Campo rotulo="E-mail" obrigatorio erro={erros.email}>
                <Entrada
                  type="email"
                  value={externo.email}
                  onChange={(e) => setExterno({ ...externo, email: e.target.value })}
                  erro={erros.email}
                />
              </Campo>
              <Campo rotulo="Instituição" obrigatorio erro={erros.instituicao} className="sm:col-span-2">
                <Entrada
                  value={externo.instituicao}
                  onChange={(e) => setExterno({ ...externo, instituicao: e.target.value })}
                  erro={erros.instituicao}
                />
              </Campo>
            </div>
          </>
        )}

        {geral && <Aviso tipo="erro">{geral}</Aviso>}
        <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
          <Botao variante="texto" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao type="submit" carregando={enviando}>
            {tipo === "docente" ? "Enviar pedido" : "Criar acesso e enviar link"}
          </Botao>
        </div>
      </form>
    </Modal>
  );
}

// ---------------------------------------------------------------- DS-FL03-D mensagens 13 a 17

function RemoverCoorientador({
  tcc,
  vinculo,
  aoFechar,
  aoRemover,
}: {
  tcc: Tcc;
  vinculo: Vinculo;
  aoFechar: () => void;
  aoRemover: () => void;
}) {
  const [justificativa, setJustificativa] = useState("");
  const [erro, setErro] = useState("");
  const [geral, setGeral] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function remover() {
    if (justificativa.trim().length < 5) return setErro("Informe a justificativa (pelo menos 5 caracteres).");
    setErro("");
    setEnviando(true);
    try {
      await api<Vinculo>(`/tccs/${tcc.id}/orientacoes/${vinculo.id}`, {
        metodo: "DELETE",
        corpo: { justificativa: justificativa.trim() },
      });
      aoRemover();
    } catch (e) {
      const falha = e as ErroApi;
      if (falha.campo === "justificativa") setErro(falha.message);
      else setGeral(falha.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Modal titulo="Remover o coorientador?" aoFechar={aoFechar}>
      <p className="mb-4 text-sm">
        A coorientação de {vinculo.professor.nome} será encerrada nesta data. O vínculo continua no histórico do TCC
        {vinculo.externo ? " e o acesso dessa pessoa ao trabalho é encerrado." : "."}
      </p>
      <Campo rotulo="Justificativa" obrigatorio erro={erro}>
        <textarea
          value={justificativa}
          onChange={(e) => setJustificativa(e.target.value)}
          rows={4}
          maxLength={1000}
          aria-invalid={erro ? true : undefined}
          className={`${ESTILO_ENTRADA} h-auto py-2 ${erro ? "border-vermelho" : "border-borda"}`}
        />
      </Campo>
      {geral && (
        <div className="mt-3">
          <Aviso tipo="erro">{geral}</Aviso>
        </div>
      )}
      <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <Botao variante="texto" onClick={aoFechar}>
          Voltar
        </Botao>
        <Botao variante="destrutivo" carregando={enviando} onClick={remover}>
          Remover coorientador
        </Botao>
      </div>
    </Modal>
  );
}
