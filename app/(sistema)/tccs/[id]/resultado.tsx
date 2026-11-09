"use client";

// TEL12 · seções "Consolidar resultado" e "Resultado da defesa" (DS-FL06, DS-FL06-B e DS-FL06-D · RBN09.11,
// RBN09.12, RN13, RN21), na página do TCC (TEL06).
//   GET  /defesas/{id}/resultado              {pendentes[]} enquanto falta avaliação; com todas enviadas,
//                                             {notas, média, regra de exceção, nota final}; depois da
//                                             confirmação, {resultado} com as retificações
//   POST /defesas/{id}/resultado              {resultado, parecer}: confirma (janela "Confirmar o resultado?")
//   POST /defesas/{id}/resultado/retificacao  {resultado, motivo}: retifica o resultado confirmado
// Só o orientador do TCC vê esta seção: para os demais a API responde 403 e nada aparece aqui.
// A nota final é sempre calculada no servidor; a tela só mostra, com duas casas (CA-06 do RBN09.11).

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Aviso, Selo } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Campo, ESTILO_ENTRADA, Selecao } from "@/components/campo";
import { Modal } from "@/components/modal";
import { api, ErroApi } from "@/lib/api";
import {
  dataHora,
  NOME_RESULTADO,
  type ConsultaResultado,
  type PapelAvaliador,
  type ResultadoDefesa,
  type ValorResultado,
} from "@/lib/tipos";

const NOME_PAPEL: Record<PapelAvaliador, string> = {
  ORIENTADOR: "Orientador(a)",
  AVALIADOR: "Avaliador(a)",
  SUPLENTE: "Suplente convocado(a)",
};

const OPCOES: { valor: ValorResultado; dica: string }[] = [
  { valor: "APROVADO", dica: "Sem correções." },
  { valor: "APROVADO_COM_CORRECOES", dica: "O aluno precisa fazer as correções exigidas pela banca." },
  { valor: "REPROVADO", dica: "A defesa não foi aprovada." },
];

const COR: Record<ValorResultado, "verde" | "ambar" | "vermelho"> = {
  APROVADO: "verde",
  APROVADO_COM_CORRECOES: "ambar",
  REPROVADO: "vermelho",
};

// Mesma precisão em tela, ata e relatórios (CA-06): duas casas, vírgula decimal.
const nota = (n: number) => n.toFixed(2).replace(".", ",");

const textoArea = (erro?: string) =>
  `${ESTILO_ENTRADA} h-auto py-2 ${erro ? "border-vermelho" : "border-borda"}`;

// envios muda quando alguém da banca envia a avaliação nesta página (o orientador avalia e consolida aqui).
export function SecaoResultado({
  defesaId,
  envios = 0,
}: {
  defesaId: number;
  envios?: number;
}) {
  const [dados, setDados] = useState<ConsultaResultado | null>(null);
  const [oculta, setOculta] = useState(false);
  const [erro, setErro] = useState("");
  const [aviso, setAviso] = useState("");

  const carregar = useCallback(
    () =>
      api<ConsultaResultado>(`/defesas/${defesaId}/resultado`)
        .then((d) => {
          setDados(d);
          setErro("");
        })
        .catch((e: ErroApi) =>
          // 403: não é o orientador; 404: sem acesso ao TCC; 409: defesa cancelada
          e.status === 403 || e.status === 404 || e.status === 409
            ? setOculta(true)
            : setErro(e.message),
        ),
    [defesaId],
  );

  useEffect(() => {
    carregar();
  }, [carregar, envios]);

  if (oculta) return null;

  // Depois de confirmar ou retificar, a tela mostra o que o servidor gravou (H1: estado visível).
  const gravado = (d: ConsultaResultado, mensagem: string) => {
    setDados(d);
    setAviso(mensagem);
  };

  const resultado = dados?.resultado;
  return (
    <section
      className="rounded-xl border border-borda bg-superficie p-5"
      aria-labelledby="titulo-resultado"
    >
      <div className="mb-1 flex flex-wrap items-center gap-2">
        <h2 id="titulo-resultado" className="font-semibold">
          {resultado ? "Resultado da defesa" : "Consolidar resultado"}
        </h2>
        {resultado && <Selo cor={COR[resultado.resultado]}>{NOME_RESULTADO[resultado.resultado]}</Selo>}
      </div>
      {!resultado && (
        <p className="mb-4 text-[13px] text-suave">
          A nota final é a média das notas do orientador e dos dois avaliadores,
          calculada pelo sistema a partir das avaliações enviadas.
        </p>
      )}
      <div role="status" className="mb-3 empty:hidden">
        {aviso && <Aviso tipo="sucesso">{aviso}</Aviso>}
      </div>
      {erro ? (
        <Aviso tipo="erro">{erro}</Aviso>
      ) : !dados ? (
        <p role="status" className="text-sm text-suave">
          Carregando…
        </p>
      ) : resultado ? (
        <Confirmado defesaId={defesaId} r={resultado} aoGravar={gravado} />
      ) : !dados.consolidacao ? (
        // DS-FL06, [falta avaliação]: "Aguardando avaliações. Faltam: ..." (RBN10.05)
        <Aviso tipo="info">
          <span className="font-medium">Aguardando avaliações.</span> Faltam:{" "}
          {dados.pendentes.map((p, i) => (
            <span key={p.membro_id}>
              {i > 0 && ", "}
              <span className="font-medium">{p.pessoa.nome}</span> (
              {NOME_PAPEL[p.papel].toLowerCase()})
            </span>
          ))}
          . O resultado só pode ser confirmado depois que todos enviarem.
        </Aviso>
      ) : (
        <div className="flex flex-col gap-5">
          <Consolidacao c={dados.consolidacao} />
          <Confirmacao
            defesaId={defesaId}
            notaFinal={dados.consolidacao.nota_final}
            aoGravar={gravado}
            aoDesatualizar={carregar}
          />
        </div>
      )}
    </section>
  );
}

function Consolidacao({
  c,
}: {
  c: NonNullable<ConsultaResultado["consolidacao"]>;
}) {
  return (
    <div className="flex flex-col gap-4">
      <ul
        className="divide-y divide-borda rounded-lg border border-borda text-sm"
        aria-label="Notas da banca"
      >
        {c.notas.map((n) => (
          <li
            key={n.membro_id}
            className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 p-3"
          >
            <span className="min-w-0 break-words">
              <span className="font-medium">{n.pessoa.nome}</span>{" "}
              <span className="text-suave">· {NOME_PAPEL[n.papel]}</span>
            </span>
            <span className="tabular-nums">{nota(n.nota)}</span>
          </li>
        ))}
      </ul>

      <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-[max-content_1fr]">
        <dt className="text-suave">Média</dt>
        <dd className="tabular-nums">{nota(c.media)}</dd>
        <dt className="text-suave">Regra de exceção</dt>
        <dd className="flex flex-col gap-1">
          <span>
            <Selo cor={c.regra.aplicada ? "verde" : "cinza"}>
              {c.regra.aplicada ? "Aplicada" : "Não aplicada"}
            </Selo>
          </span>
          {/* H10: a regra do artigo Qualis A ou B (RN21) é explicada na própria consolidação */}
          <span className="text-suave">{c.regra.porque}</span>
        </dd>
        <dt className="text-suave">Nota final</dt>
        <dd>
          <span
            className="text-2xl font-semibold tabular-nums"
            aria-live="polite"
          >
            {nota(c.nota_final)}
          </span>
        </dd>
      </dl>
    </div>
  );
}

// ---------------------------------------------------------------- DS-FL06 · confirmar o resultado

function Confirmacao({
  defesaId,
  notaFinal,
  aoGravar,
  aoDesatualizar,
}: {
  defesaId: number;
  notaFinal: number;
  aoGravar: (d: ConsultaResultado, mensagem: string) => void;
  aoDesatualizar: () => void;
}) {
  const [escolha, setEscolha] = useState<ValorResultado | null>(null);
  const [parecer, setParecer] = useState("");
  const [erros, setErros] = useState<{ resultado?: string; parecer?: string }>({});
  const [confirmando, setConfirmando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [falha, setFalha] = useState("");

  // H5: a tela confere antes de abrir a janela; o servidor confere de novo.
  const revisar = (e: FormEvent) => {
    e.preventDefault();
    const novos: typeof erros = {};
    if (!escolha) novos.resultado = "Escolha o resultado da defesa.";
    if (!parecer.trim()) novos.parecer = "Escreva o parecer da banca.";
    setErros(novos);
    setFalha("");
    if (Object.keys(novos).length === 0) setConfirmando(true);
  };

  const confirmar = () => {
    setEnviando(true);
    api<ConsultaResultado>(`/defesas/${defesaId}/resultado`, {
      metodo: "POST",
      corpo: { resultado: escolha, parecer: parecer.trim() },
    })
      .then((d) => {
        setConfirmando(false);
        aoGravar(
          d,
          escolha === "APROVADO_COM_CORRECOES"
            ? "Resultado confirmado. O aluno e a banca foram avisados por e-mail; as correções exigidas são registradas a partir deste resultado."
            : "Resultado confirmado. O aluno e a banca foram avisados por e-mail.",
        );
      })
      .catch((e: ErroApi) => {
        setConfirmando(false);
        if (e.status === 422 && e.campo === "parecer") setErros({ parecer: e.message });
        else if (e.status === 409) {
          // já confirmado em outra janela, ou avaliação pendente: mostra a situação atual
          setFalha(e.message);
          aoDesatualizar();
        } else setFalha(e.message);
      })
      .finally(() => setEnviando(false));
  };

  return (
    <form onSubmit={revisar} noValidate className="flex flex-col gap-4 border-t border-borda pt-4">
      <fieldset className="flex flex-col gap-2" aria-describedby={erros.resultado ? "erro-resultado" : undefined}>
        <legend className="mb-1 text-sm font-medium">
          Resultado da defesa <span className="text-vermelho" title="Obrigatório">*</span>
        </legend>
        <div className="grid gap-2 sm:grid-cols-3">
          {OPCOES.map((o) => (
            <label
              key={o.valor}
              className={`flex cursor-pointer gap-3 rounded-lg border p-3 text-sm has-[:checked]:border-azul has-[:checked]:bg-azul-claro ${
                erros.resultado ? "border-vermelho" : "border-borda"
              }`}
            >
              <input
                type="radio"
                name="resultado"
                value={o.valor}
                checked={escolha === o.valor}
                onChange={() => setEscolha(o.valor)}
                className="mt-0.5 size-4 shrink-0 accent-azul"
              />
              <span className="flex flex-col gap-0.5">
                <span className="font-medium">{NOME_RESULTADO[o.valor]}</span>
                <span className="text-[13px] text-suave">{o.dica}</span>
              </span>
            </label>
          ))}
        </div>
        {erros.resultado && (
          <span id="erro-resultado" role="alert" className="text-[13px] font-medium text-vermelho">
            {erros.resultado}
          </span>
        )}
      </fieldset>

      <Campo rotulo="Parecer da banca" obrigatorio erro={erros.parecer}>
        <textarea
          value={parecer}
          onChange={(e) => setParecer(e.target.value)}
          rows={4}
          maxLength={2000}
          aria-invalid={erros.parecer ? true : undefined}
          className={textoArea(erros.parecer)}
        />
      </Campo>

      {falha && <Aviso tipo="erro">{falha}</Aviso>}
      <div>
        <Botao type="submit">Confirmar resultado</Botao>
      </div>

      {confirmando && escolha && (
        <Modal titulo="Confirmar o resultado?" aoFechar={() => setConfirmando(false)}>
          <p className="text-sm">
            Resultado: <span className="font-semibold">{NOME_RESULTADO[escolha]}</span> · nota final{" "}
            <span className="font-semibold tabular-nums">{nota(notaFinal)}</span>.
          </p>
          <p className="mt-2 text-sm">
            Depois de confirmado, alterar o resultado exige <span className="font-semibold">retificação</span>,
            com registro de quem alterou e quando. O aluno e a banca recebem o resultado por e-mail.
          </p>
          <div className="mt-4 flex flex-wrap justify-end gap-2">
            <Botao variante="texto" onClick={() => setConfirmando(false)}>
              Voltar
            </Botao>
            <Botao onClick={confirmar} carregando={enviando}>
              Confirmar resultado
            </Botao>
          </div>
        </Modal>
      )}
    </form>
  );
}

// ---------------------------------------------------------------- resultado confirmado e DS-FL06-D

function Confirmado({
  defesaId,
  r,
  aoGravar,
}: {
  defesaId: number;
  r: ResultadoDefesa;
  aoGravar: (d: ConsultaResultado, mensagem: string) => void;
}) {
  const [retificando, setRetificando] = useState(false);
  return (
    <div className="flex flex-col gap-4">
      <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-[max-content_1fr]">
        <dt className="text-suave">Média das notas</dt>
        <dd className="tabular-nums">{nota(r.media)}</dd>
        <dt className="text-suave">Nota final</dt>
        <dd>
          <span className="font-semibold tabular-nums">{nota(r.nota_final)}</span>
          {r.regra_qualis && <span className="text-[13px] text-suave"> (regra de exceção aplicada)</span>}
        </dd>
        <dt className="text-suave">Parecer</dt>
        <dd className="break-words whitespace-pre-line">{r.parecer}</dd>
        <dt className="text-suave">Confirmado por</dt>
        <dd>
          {r.confirmado_por.nome} em {dataHora(r.confirmado_em)}
        </dd>
      </dl>

      {r.resultado === "APROVADO_COM_CORRECOES" && (
        <Aviso tipo="info">
          O aluno precisa fazer as correções exigidas pela banca. Elas são registradas a partir deste resultado.
        </Aviso>
      )}

      {r.retificacoes.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-semibold">Retificações</h3>
          <ol className="flex flex-col gap-2 text-sm">
            {r.retificacoes.map((x, i) => (
              <li key={i} className="rounded-lg border border-borda p-3">
                {NOME_RESULTADO[x.de]} → <span className="font-medium">{NOME_RESULTADO[x.para]}</span>
                <span className="mt-0.5 block text-[13px] break-words text-suave">
                  {dataHora(x.em)} · {x.por.nome} · {x.motivo}
                </span>
              </li>
            ))}
          </ol>
        </div>
      )}

      <div>
        <Botao variante="contorno" onClick={() => setRetificando(true)}>
          Retificar resultado
        </Botao>
      </div>

      {retificando && (
        <JanelaRetificacao
          defesaId={defesaId}
          atual={r.resultado}
          aoFechar={() => setRetificando(false)}
          aoGravar={(d) => {
            setRetificando(false);
            aoGravar(d, "Resultado retificado e registrado. O aluno e a banca foram avisados por e-mail.");
          }}
        />
      )}
    </div>
  );
}

function JanelaRetificacao({
  defesaId,
  atual,
  aoFechar,
  aoGravar,
}: {
  defesaId: number;
  atual: ValorResultado;
  aoFechar: () => void;
  aoGravar: (d: ConsultaResultado) => void;
}) {
  const [novo, setNovo] = useState<ValorResultado>(atual);
  const [motivo, setMotivo] = useState("");
  const [erros, setErros] = useState<{ resultado?: string; motivo?: string }>({});
  const [falha, setFalha] = useState("");
  const [enviando, setEnviando] = useState(false);

  const registrar = (e: FormEvent) => {
    e.preventDefault();
    const novos: typeof erros = {};
    if (novo === atual) novos.resultado = "Nenhuma mudança: o resultado escolhido é o mesmo.";
    if (!motivo.trim()) novos.motivo = "Informe o motivo da retificação.";
    setErros(novos);
    setFalha("");
    if (Object.keys(novos).length) return;
    setEnviando(true);
    api<ConsultaResultado>(`/defesas/${defesaId}/resultado/retificacao`, {
      metodo: "POST",
      corpo: { resultado: novo, motivo: motivo.trim() },
    })
      .then(aoGravar)
      .catch((err: ErroApi) => {
        if (err.status === 422 && (err.campo === "motivo" || err.campo === "resultado"))
          setErros({ [err.campo]: err.message });
        else setFalha(err.message);
      })
      .finally(() => setEnviando(false));
  };

  return (
    <Modal titulo="Retificar resultado" aoFechar={aoFechar}>
      <form onSubmit={registrar} noValidate className="flex flex-col gap-4">
        <p className="text-sm">
          O resultado anterior fica registrado, com quem alterou e quando, e a ata já gerada passa a ficar
          desatualizada.
        </p>
        <Campo rotulo="Novo resultado" obrigatorio erro={erros.resultado}>
          <Selecao
            value={novo}
            onChange={(e) => setNovo(e.target.value as ValorResultado)}
            erro={erros.resultado}
          >
            {(Object.keys(NOME_RESULTADO) as ValorResultado[]).map((v) => (
              <option key={v} value={v}>
                {NOME_RESULTADO[v]}
                {v === atual ? " (atual)" : ""}
              </option>
            ))}
          </Selecao>
        </Campo>
        <Campo rotulo="Motivo da retificação" obrigatorio erro={erros.motivo}>
          <textarea
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            rows={3}
            maxLength={1000}
            aria-invalid={erros.motivo ? true : undefined}
            className={textoArea(erros.motivo)}
          />
        </Campo>
        {falha && <Aviso tipo="erro">{falha}</Aviso>}
        <div className="flex flex-wrap justify-end gap-2">
          <Botao variante="texto" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao type="submit" carregando={enviando}>
            Registrar retificação
          </Botao>
        </div>
      </form>
    </Modal>
  );
}
