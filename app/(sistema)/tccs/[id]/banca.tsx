"use client";

// TEL10 · Banca examinadora e TEL11 · Agendamento (DS-FL04-A, DS-FL04-B e DS-FL04).
// A banca é montada aqui na tela; cada vaga é conferida pela API sem gravar
// (POST /tccs/{id}/banca/validar) e tudo é gravado junto com a defesa na confirmação
// (POST /tccs/{id}/defesa), porque todo membro da banca pertence a uma defesa.
// Quem pode editar é decidido pela API (RN14); aqui só se esconde o que não cabe.

import { useCallback, useEffect, useState } from "react";
import { Aviso, Selo } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Campo, Entrada, Selecao } from "@/components/campo";
import { Modal } from "@/components/modal";
import { DivulgacaoNaAgenda } from "./divulgacao";
import { api, ErroApi } from "@/lib/api";
import {
  dataCurta,
  dataHora,
  NOME_FORMATO,
  NOME_PAPEL_BANCA,
  type Banca,
  type Conflito,
  type Conflitos,
  type Defesa,
  type FormatoDefesa,
  type MembroBanca,
  type MembroEntrada,
  type PapelBanca,
  type PessoaBanca,
  type SituacaoConvite,
} from "@/lib/tipos";

// Vagas da banca (RN12): orientador obrigatório, 2 avaliadores, coorientador e suplente opcionais.
type Chave = "ORIENTADOR" | "COORIENTADOR" | "AVALIADOR1" | "AVALIADOR2" | "SUPLENTE";
const VAGAS: { chave: Chave; papel: PapelBanca; rotulo: string; obrigatoria: boolean }[] = [
  { chave: "ORIENTADOR", papel: "ORIENTADOR", rotulo: "Orientador(a)", obrigatoria: true },
  { chave: "COORIENTADOR", papel: "COORIENTADOR", rotulo: "Coorientador(a)", obrigatoria: false },
  { chave: "AVALIADOR1", papel: "AVALIADOR", rotulo: "Avaliador(a) 1", obrigatoria: true },
  { chave: "AVALIADOR2", papel: "AVALIADOR", rotulo: "Avaliador(a) 2", obrigatoria: true },
  { chave: "SUPLENTE", papel: "SUPLENTE", rotulo: "Suplente", obrigatoria: false },
];
const FIXAS: Chave[] = ["ORIENTADOR", "COORIENTADOR"]; // a pessoa é a vinculada ao TCC

type Vaga = { membro: MembroBanca; entrada: MembroEntrada };

export function SecaoBanca({ tccId }: { tccId: string }) {
  const [banca, setBanca] = useState<Banca | null>(null);
  const [erro, setErro] = useState("");

  const carregar = useCallback(() => {
    api<Banca>(`/tccs/${tccId}/banca`).then(setBanca).catch((e: ErroApi) => setErro(e.message));
  }, [tccId]);
  useEffect(carregar, [carregar]);

  return (
    <section className="rounded-xl border border-borda bg-superficie p-5">
      <h2 className="mb-3 font-semibold">Banca e defesa</h2>
      {erro ? (
        <Aviso tipo="erro">{erro}</Aviso>
      ) : !banca ? (
        <p role="status" className="text-sm text-suave">
          Carregando…
        </p>
      ) : !banca.liberada ? (
        <Aviso tipo="info">Etapa ainda não liberada: o cadastro do TCC precisa estar aprovado.</Aviso>
      ) : banca.defesa ? (
        <DefesaConfirmada banca={banca} defesa={banca.defesa} aoMudar={setBanca} />
      ) : banca.pode_editar ? (
        <MontarBanca banca={banca} aoConfirmar={carregar} />
      ) : (
        <p className="text-sm text-suave">A banca ainda não foi definida.</p>
      )}
    </section>
  );
}

// ---------------------------------------------------------------- DS-FL04-A · montar a banca na tela

function MontarBanca({ banca, aoConfirmar }: { banca: Banca; aoConfirmar: () => void }) {
  const [vagas, setVagas] = useState<Partial<Record<Chave, Vaga>>>(() => {
    // As vagas fixas já vêm com a pessoa vinculada ao TCC.
    const inicio: Partial<Record<Chave, Vaga>> = {};
    if (banca.orientador) inicio.ORIENTADOR = fixa("ORIENTADOR", banca.orientador.id, banca.orientador.nome);
    if (banca.coorientador) inicio.COORIENTADOR = fixa("COORIENTADOR", banca.coorientador.id, banca.coorientador.nome);
    return inicio;
  });
  const [editando, setEditando] = useState<Chave | null>(null);
  const [desfazer, setDesfazer] = useState<{ chave: Chave; vaga: Vaga } | null>(null);
  const [agendando, setAgendando] = useState(false);

  // Na ordem fixa das vagas (não na de preenchimento): é a ordem em que a banca é gravada e exibida.
  const entradas = (exceto?: Chave) =>
    VAGAS.flatMap(({ chave }) => (chave !== exceto && vagas[chave] ? [vagas[chave].entrada] : []));
  const preenchidas = (["ORIENTADOR", "AVALIADOR1", "AVALIADOR2"] as Chave[]).filter((c) => vagas[c]).length;
  const completa = preenchidas === 3;

  function remover(chave: Chave) {
    setDesfazer({ chave, vaga: vagas[chave]! });
    setVagas((v) => {
      const resto = { ...v };
      delete resto[chave];
      return resto;
    });
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <span className="font-medium">{preenchidas} de 3 membros obrigatórios</span>
        {completa && <Selo cor="verde">Banca completa</Selo>}
      </div>
      <p className="text-[13px] text-suave">
        Nada é gravado até você confirmar a defesa. Os convites só saem depois da confirmação, e o suplente não conta
        para o quórum (RN20).
      </p>

      {desfazer && (
        <Aviso tipo="info">
          Vaga esvaziada.{" "}
          <button
            type="button"
            className="font-medium underline"
            onClick={() => {
              setVagas((v) => ({ ...v, [desfazer.chave]: desfazer.vaga }));
              setDesfazer(null);
            }}
          >
            Desfazer
          </button>
        </Aviso>
      )}

      <ul className="flex flex-col gap-3">
        {VAGAS.map(({ chave, papel, rotulo, obrigatoria }) => {
          const vaga = vagas[chave];
          const fixaSemVinculo = FIXAS.includes(chave) && !(chave === "ORIENTADOR" ? banca.orientador : banca.coorientador);
          return (
            <li key={chave} className="rounded-lg border border-borda p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="min-w-0 text-sm">
                  <p className="font-medium">
                    {rotulo}
                    {!obrigatoria && <span className="font-normal text-suave"> (opcional)</span>}
                  </p>
                  {vaga ? (
                    <PessoaDaVaga membro={vaga.membro} />
                  ) : fixaSemVinculo ? (
                    <p className="text-suave">
                      {chave === "ORIENTADOR" ? "O TCC ainda não tem orientador vinculado." : "O TCC não tem coorientador."}
                    </p>
                  ) : (
                    <p className="text-suave">Vaga livre</p>
                  )}
                </div>
                <div className="flex gap-2">
                  {vaga && chave !== "ORIENTADOR" && (
                    <Botao variante="perigo" pequeno onClick={() => remover(chave)}>
                      Remover
                    </Botao>
                  )}
                  {!vaga && FIXAS.includes(chave) && !fixaSemVinculo && (
                    <Botao
                      variante="contorno"
                      pequeno
                      onClick={() =>
                        setVagas((v) => ({ ...v, [chave]: fixa("COORIENTADOR", banca.coorientador!.id, banca.coorientador!.nome) }))
                      }
                    >
                      Incluir
                    </Botao>
                  )}
                  {!vaga && !FIXAS.includes(chave) && editando !== chave && (
                    <Botao variante="contorno" pequeno onClick={() => setEditando(chave)}>
                      Adicionar
                    </Botao>
                  )}
                </div>
              </div>
              {editando === chave && (
                <FormularioVaga
                  banca={banca}
                  aoCancelar={() => setEditando(null)}
                  aoEnviar={async (pessoa) => {
                    const entrada = { ...pessoa, papel } as MembroEntrada;
                    const membro = await api<MembroBanca>(`/tccs/${banca.tcc_id}/banca/validar`, {
                      metodo: "POST",
                      corpo: { membro: entrada, banca: entradas(chave) },
                    });
                    setVagas((v) => ({ ...v, [chave]: { membro, entrada } }));
                    setEditando(null);
                    setDesfazer(null);
                  }}
                />
              )}
            </li>
          );
        })}
      </ul>

      {completa && !agendando && (
        <div>
          <Botao onClick={() => setAgendando(true)}>Agendar defesa</Botao>
        </div>
      )}
      {agendando && (
        <FormularioAgendamento
          banca={banca}
          membros={entradas()}
          aoCancelar={() => setAgendando(false)}
          aoConfirmar={aoConfirmar}
        />
      )}
    </div>
  );
}

function fixa(papel: PapelBanca, id: number, nome: string): Vaga {
  return {
    entrada: { papel, usuario_id: id },
    membro: {
      id: null,
      papel,
      pessoa: { id, nome },
      email: "",
      interno: true,
      instituicao: null,
      convite_enviado_em: null,
      convite: "NAO_ENVIADO",
    },
  };
}

// RBN09.05: situação do convite por e-mail de cada vaga.
const SELO_CONVITE: Record<SituacaoConvite, { cor: "verde" | "cinza" | "ambar" | "vermelho"; texto: string }> = {
  NAO_ENVIADO: { cor: "cinza", texto: "Convite não enviado" },
  PENDENTE: { cor: "ambar", texto: "Enviando convite…" },
  ENVIADO: { cor: "verde", texto: "Convite enviado" },
  FALHA: { cor: "vermelho", texto: "Falha no envio do convite" },
};

function PessoaDaVaga({ membro }: { membro: MembroBanca }) {
  const selo = SELO_CONVITE[membro.convite];
  return (
    <p className="flex flex-wrap items-center gap-2 break-words">
      {membro.pessoa.nome}
      {membro.interno ? <Selo cor="cinza">UEA</Selo> : <Selo cor="ambar">Externo · {membro.instituicao}</Selo>}
      <Selo cor={selo.cor}>
        {selo.texto}
        {membro.convite === "ENVIADO" && membro.convite_enviado_em && ` em ${dataHora(membro.convite_enviado_em)}`}
      </Selo>
    </p>
  );
}

// ---------------------------------------------------------------- DS-FL04-A passo 7 e DS-FL04-B · escolher a pessoa

function FormularioVaga({
  banca,
  aoEnviar,
  aoCancelar,
  textoBotao = "Adicionar à banca",
}: {
  banca: Banca;
  aoEnviar: (pessoa: PessoaBanca) => Promise<void>;
  aoCancelar: () => void;
  textoBotao?: string;
}) {
  const [tipo, setTipo] = useState<"docente" | "externo">("docente");
  const [docente, setDocente] = useState("");
  const [externo, setExterno] = useState({ nome: "", email: "", instituicao: "" });
  const [erros, setErros] = useState<Record<string, string>>({});
  const [geral, setGeral] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    // DS-FL04-B passo 3: nome, e-mail válido e instituição preenchidos?
    const faltas: Record<string, string> = {};
    if (tipo === "docente" && !docente) faltas.usuario_id = "Escolha o docente.";
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
      await aoEnviar(tipo === "docente" ? { usuario_id: Number(docente) } : { externo });
    } catch (e) {
      const erro = e as ErroApi;
      if (erro.campos) setErros(erro.campos);
      else if (erro.campo) setErros({ [erro.campo === "papel" ? "usuario_id" : erro.campo]: erro.message });
      else setGeral(erro.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={enviar} className="mt-3 flex flex-col gap-3 border-t border-borda pt-3" noValidate>
      <fieldset className="flex flex-wrap gap-4 text-sm">
        <legend className="sr-only">Quem ocupa a vaga</legend>
        {(["docente", "externo"] as const).map((t) => (
          <label key={t} className="flex items-center gap-2">
            <input type="radio" name="tipo" checked={tipo === t} onChange={() => setTipo(t)} />
            {t === "docente" ? "Docente da UEA" : "Convidado externo"}
          </label>
        ))}
      </fieldset>

      {tipo === "docente" ? (
        <Campo rotulo="Docente" obrigatorio erro={erros.usuario_id}>
          <Selecao value={docente} onChange={(e) => setDocente(e.target.value)} erro={erros.usuario_id}>
            <option value="">Escolha…</option>
            {banca.docentes.map((d) => (
              <option key={d.id} value={d.id}>
                {d.nome}
              </option>
            ))}
          </Selecao>
        </Campo>
      ) : (
        <>
          <Aviso tipo="info">
            O convidado recebe uma conta limitada a esta defesa. O link de acesso vai junto com o convite, quando a defesa
            for confirmada.
          </Aviso>
          <div className="grid gap-3 sm:grid-cols-2">
            <Campo rotulo="Nome" obrigatorio erro={erros.nome}>
              <Entrada value={externo.nome} onChange={(e) => setExterno({ ...externo, nome: e.target.value })} erro={erros.nome} />
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
      <div className="flex flex-wrap gap-2">
        <Botao type="submit" pequeno carregando={enviando}>
          {textoBotao}
        </Botao>
        <Botao variante="texto" pequeno onClick={aoCancelar}>
          Cancelar
        </Botao>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------- DS-FL04 · agendar e confirmar

// Data de hoje no fuso do navegador, no formato do campo date (AAAA-MM-DD).
function hojeISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

// Hora atual no formato do campo time (HH:MM).
function agoraHHMM() {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

// O link traz um endereço depois do https:// (só "https://" não leva a lugar nenhum).
function temEndereco(link: string) {
  try {
    return Boolean(new URL(link).hostname);
  } catch {
    return false;
  }
}

const hora = (h: string) => h.slice(0, 5);

// RBN09.04 · CA-01/CA-02: quem ou que local já está ocupado, e em que horário.
function ListaConflitos({ conflitos }: { conflitos: Conflito[] }) {
  return (
    <ul className="mt-1 list-disc pl-5">
      {conflitos.map((c, i) => (
        <li key={i}>
          {c.tipo === "LOCAL" ? `Local ${c.nome}` : c.nome}: outra defesa das {hora(c.inicio)} às {hora(c.fim)}
        </li>
      ))}
    </ul>
  );
}

function FormularioAgendamento({
  banca,
  membros,
  aoCancelar,
  aoConfirmar,
}: {
  banca: Banca;
  membros: MembroEntrada[];
  aoCancelar: () => void;
  aoConfirmar: () => void;
}) {
  const [dados, setDados] = useState({ data: "", inicio: "", fim: "", formato: "REMOTO" as FormatoDefesa, local_id: "", link: "" });
  const [erros, setErros] = useState<Record<string, string>>({});
  const [pendencias, setPendencias] = useState<string[]>([]);
  const [geral, setGeral] = useState("");
  const [confirmando, setConfirmando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [verificando, setVerificando] = useState(false);
  // Resultado da verificação de conflitos (DS-FL04 mensagens 11 a 13), mostrado na janela de confirmação.
  const [verificacao, setVerificacao] = useState<Conflitos | null>(null);
  const precisaLocal = dados.formato !== "REMOTO";
  const precisaLink = dados.formato !== "PRESENCIAL";

  async function conferir(e: React.FormEvent) {
    e.preventDefault();
    // DS-FL04 mensagens 8 e 10: a API confere de novo na confirmação.
    const faltas: Record<string, string> = {};
    if (!dados.data) faltas.data = "Informe a data.";
    else if (dados.data < hojeISO()) faltas.data = "A data da defesa não pode estar no passado.";
    if (!dados.inicio) faltas.inicio = "Informe o início.";
    else if (dados.data === hojeISO() && dados.inicio < agoraHHMM()) faltas.inicio = "O início da defesa não pode estar no passado.";
    if (!dados.fim) faltas.fim = "Informe o término.";
    else if (dados.inicio && dados.fim <= dados.inicio) faltas.fim = "O término deve ser depois do início.";
    if (precisaLocal && !dados.local_id) faltas.local_id = "Escolha o local da defesa.";
    if (precisaLink && !dados.link.trim()) faltas.link = "Informe o link da sala virtual.";
    else if (precisaLink && !dados.link.trim().toLowerCase().startsWith("https://"))
      faltas.link = "O link da sala virtual deve começar com https://.";
    else if (precisaLink && !temEndereco(dados.link.trim())) faltas.link = "Informe o link completo da sala virtual.";
    setErros(faltas);
    setGeral("");
    if (Object.keys(faltas).length) return;

    // RBN09.04: o convidado externo novo ainda não tem agenda; vão só as pessoas já cadastradas.
    const consulta = new URLSearchParams({ tcc_id: String(banca.tcc_id), data: dados.data, inicio: dados.inicio, fim: dados.fim });
    if (precisaLocal) consulta.set("local_id", dados.local_id);
    membros.forEach((m) => m.usuario_id && consulta.append("pessoa", String(m.usuario_id)));
    setVerificando(true);
    try {
      setVerificacao(await api<Conflitos>(`/defesas/conflitos?${consulta}`));
      setConfirmando(true);
    } catch (e) {
      const erro = e as ErroApi;
      if (erro.campos) setErros(erro.campos);
      setGeral(erro.message);
    } finally {
      setVerificando(false);
    }
  }
  const comConflito = (verificacao?.conflitos.length ?? 0) > 0;

  async function confirmar() {
    setEnviando(true);
    setGeral("");
    setPendencias([]);
    try {
      await api<Defesa>(`/tccs/${banca.tcc_id}/defesa`, {
        metodo: "POST",
        corpo: {
          banca: membros,
          formato: dados.formato,
          data: dados.data,
          inicio: dados.inicio,
          fim: dados.fim,
          local_id: precisaLocal ? Number(dados.local_id) : null,
          link: precisaLink ? dados.link.trim() : null,
        },
      });
      aoConfirmar();
    } catch (e) {
      const erro = e as ErroApi & { pendencias?: string[]; conflitos?: Conflito[] };
      if (erro.conflitos) {
        // E4: surgiu um conflito depois da verificação; volta para a janela com o conflito
        setVerificacao((v) => ({ aviso: v?.aviso ?? "", conflitos: erro.conflitos! }));
        return;
      }
      setConfirmando(false);
      if (erro.campos) setErros(erro.campos);
      if (erro.pendencias) setPendencias(erro.pendencias);
      setGeral(erro.message);
    } finally {
      setEnviando(false);
    }
  }

  const mudar = (campo: keyof typeof dados) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setDados({ ...dados, [campo]: e.target.value });

  return (
    <form onSubmit={conferir} className="flex flex-col gap-3 rounded-lg border border-borda p-4" noValidate>
      <h3 className="font-semibold">Quando e onde será a defesa?</h3>
      <p className="text-[13px] text-suave">
        Duração prevista: {banca.etapa === "TCC1" ? "15" : "20"} minutos no total (pode ser maior, RN22).
      </p>
      <div className="grid gap-3 sm:grid-cols-3">
        <Campo rotulo="Data" obrigatorio erro={erros.data}>
          <Entrada type="date" value={dados.data} onChange={mudar("data")} erro={erros.data} />
        </Campo>
        <Campo rotulo="Início" obrigatorio erro={erros.inicio}>
          <Entrada type="time" value={dados.inicio} onChange={mudar("inicio")} erro={erros.inicio} />
        </Campo>
        <Campo rotulo="Término" obrigatorio erro={erros.fim}>
          <Entrada type="time" value={dados.fim} onChange={mudar("fim")} erro={erros.fim} />
        </Campo>
      </div>
      <Campo rotulo="Formato" obrigatorio erro={erros.formato}>
        <Selecao value={dados.formato} onChange={mudar("formato")}>
          {(Object.keys(NOME_FORMATO) as FormatoDefesa[]).map((f) => (
            <option key={f} value={f}>
              {NOME_FORMATO[f]}
            </option>
          ))}
        </Selecao>
      </Campo>
      {precisaLocal && (
        <Campo rotulo="Local" obrigatorio erro={erros.local_id}>
          <Selecao value={dados.local_id} onChange={mudar("local_id")} erro={erros.local_id}>
            <option value="">{banca.locais.length ? "Escolha…" : "Nenhum local cadastrado"}</option>
            {banca.locais.map((l) => (
              <option key={l.id} value={l.id}>
                {l.nome}
              </option>
            ))}
          </Selecao>
        </Campo>
      )}
      {precisaLink && (
        <Campo rotulo="Link da sala virtual" obrigatorio erro={erros.link}>
          <Entrada type="url" placeholder="https://" value={dados.link} onChange={mudar("link")} erro={erros.link} />
        </Campo>
      )}

      {geral && (
        <Aviso tipo="erro">
          {geral}
          {pendencias.length > 0 && (
            <ul className="mt-1 list-disc pl-5">
              {pendencias.map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          )}
        </Aviso>
      )}
      <div className="flex flex-wrap gap-2">
        <Botao type="submit" carregando={verificando}>
          Confirmar defesa
        </Botao>
        <Botao variante="texto" onClick={aoCancelar}>
          Voltar para a banca
        </Botao>
      </div>

      {confirmando && (
        <Modal titulo="Confirmar a defesa?" aoFechar={() => setConfirmando(false)}>
          <p className="text-sm">
            {dataCurta(dados.data)}, das {dados.inicio} às {dados.fim} · {NOME_FORMATO[dados.formato]}. A defesa e a banca
            serão gravadas e cada membro da banca recebe o convite por e-mail.
          </p>
          <div className="mt-3">
            {comConflito ? (
              <Aviso tipo="erro">
                Há conflito neste horário. Escolha outro horário ou outro local.
                <ListaConflitos conflitos={verificacao!.conflitos} />
              </Aviso>
            ) : (
              <Aviso tipo="sucesso">Nenhum conflito conhecido.</Aviso>
            )}
            {verificacao?.aviso && <p className="mt-2 text-[13px] text-suave">{verificacao.aviso}</p>}
          </div>
          <div className="mt-4 flex flex-wrap justify-end gap-2">
            <Botao variante="texto" onClick={() => setConfirmando(false)}>
              Revisar
            </Botao>
            <Botao onClick={confirmar} carregando={enviando} disabled={comConflito}>
              Confirmar e enviar convites
            </Botao>
          </div>
        </Modal>
      )}
    </form>
  );
}

// ---------------------------------------------------------------- defesa confirmada e troca de membro (CA-06)

function DefesaConfirmada({
  banca,
  defesa,
  aoMudar,
}: {
  banca: Banca;
  defesa: Defesa;
  aoMudar: (b: Banca) => void;
}) {
  const [trocando, setTrocando] = useState<MembroBanca | null>(null);
  const [reenviando, setReenviando] = useState<number | null>(null);
  const [erroConvite, setErroConvite] = useState("");
  const alteravel = banca.pode_editar && (defesa.situacao === "CONFIRMADA" || defesa.situacao === "REMARCADA");

  // Os convites saem logo depois da resposta da API: enquanto algum estiver "enviando",
  // relê a banca algumas vezes para mostrar o resultado (enviado ou falha).
  const pendentes = defesa.membros.some((m) => m.convite === "PENDENTE");
  const [tentativas, setTentativas] = useState(0);
  useEffect(() => {
    if (!pendentes || tentativas >= 5) return;
    const t = setTimeout(() => {
      api<Banca>(`/tccs/${banca.tcc_id}/banca`)
        .then((b) => aoMudar(b))
        .catch(() => {})
        .finally(() => setTentativas((n) => n + 1));
    }, 2000);
    return () => clearTimeout(t);
  }, [pendentes, tentativas, banca.tcc_id, aoMudar]);

  async function reenviar(m: MembroBanca) {
    setReenviando(m.id);
    setErroConvite("");
    try {
      const novo = await api<MembroBanca>(`/defesas/${defesa.id}/banca/${m.id}/convite`, { metodo: "POST" });
      aoMudar({ ...banca, defesa: { ...defesa, membros: defesa.membros.map((x) => (x.id === novo.id ? novo : x)) } });
      setTentativas(0);
    } catch (e) {
      setErroConvite((e as ErroApi).message);
    } finally {
      setReenviando(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <Selo cor="verde">Defesa confirmada</Selo>
        <Selo cor="cinza">{defesa.publicada ? "Publicada na agenda" : "Não publicada"}</Selo>
      </div>
      <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-[max-content_1fr]">
        <dt className="text-suave">Data e horário</dt>
        <dd>
          {dataCurta(defesa.data)}, das {hora(defesa.inicio)} às {hora(defesa.fim)}
        </dd>
        <dt className="text-suave">Formato</dt>
        <dd>{NOME_FORMATO[defesa.formato]}</dd>
        {defesa.local && (
          <>
            <dt className="text-suave">Local</dt>
            <dd>{defesa.local.nome}</dd>
          </>
        )}
        {defesa.link && (
          <>
            <dt className="text-suave">Link</dt>
            <dd className="break-all">{defesa.link}</dd>
          </>
        )}
      </dl>

      <ul className="flex flex-col gap-2">
        {defesa.membros.map((m) => (
          <li key={m.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-borda p-3 text-sm">
            <div className="min-w-0">
              <p className="font-medium">{NOME_PAPEL_BANCA[m.papel]}</p>
              <PessoaDaVaga membro={m} />
            </div>
            {alteravel && (
              <div className="flex flex-wrap gap-2">
                {m.convite !== "PENDENTE" && (
                  <Botao variante="texto" pequeno carregando={reenviando === m.id} onClick={() => reenviar(m)}>
                    Reenviar convite
                  </Botao>
                )}
                {(m.papel === "AVALIADOR" || m.papel === "SUPLENTE") && (
                  <Botao variante="contorno" pequeno onClick={() => setTrocando(m)}>
                    Trocar
                  </Botao>
                )}
              </div>
            )}
          </li>
        ))}
      </ul>
      {erroConvite && <Aviso tipo="erro">{erroConvite}</Aviso>}

      <DivulgacaoNaAgenda
        defesaId={defesa.id}
        aoMudar={(publicada) => aoMudar({ ...banca, defesa: { ...defesa, publicada } })}
      />

      {trocando && (
        <Modal titulo={`Trocar ${NOME_PAPEL_BANCA[trocando.papel].toLowerCase()}`} aoFechar={() => setTrocando(null)} largo>
          <p className="text-sm text-suave">Sai: {trocando.pessoa.nome}. A troca fica registrada no histórico.</p>
          <FormularioVaga
            banca={banca}
            textoBotao="Trocar membro"
            aoCancelar={() => setTrocando(null)}
            aoEnviar={async (pessoa) => {
              const nova = await api<Defesa>(`/defesas/${defesa.id}/banca/${trocando.id}`, { metodo: "PUT", corpo: pessoa });
              aoMudar({ ...banca, defesa: nova });
              setTrocando(null);
            }}
          />
        </Modal>
      )}
    </div>
  );
}
