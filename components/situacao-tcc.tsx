// Selos de situação do TCC e do vínculo de orientação, com as mesmas cores em todas as telas.

import { NOME_SITUACAO_TCC, NOME_STATUS_ORIENTACAO, type SituacaoTcc, type StatusOrientacao } from "@/lib/tipos";
import { Selo } from "./aviso";

const COR_TCC: Record<SituacaoTcc, "azul" | "verde" | "ambar" | "cinza" | "vermelho"> = {
  RASCUNHO: "cinza",
  EM_ANALISE: "azul",
  APROVADO: "verde",
  DEVOLVIDO: "ambar",
  REPROVADO: "vermelho",
  CONCLUIDO: "verde",
  DESISTENCIA: "cinza",
};

const COR_ORIENTACAO: Record<StatusOrientacao, "azul" | "verde" | "ambar" | "cinza" | "vermelho"> = {
  PENDENTE: "ambar",
  ACEITA: "verde",
  RECUSADA: "vermelho",
  SUBSTITUIDA: "cinza",
};

export function SeloSituacao({ situacao }: { situacao: SituacaoTcc }) {
  return <Selo cor={COR_TCC[situacao]}>{NOME_SITUACAO_TCC[situacao]}</Selo>;
}

export function SeloOrientacao({ status }: { status: StatusOrientacao }) {
  return <Selo cor={COR_ORIENTACAO[status]}>{NOME_STATUS_ORIENTACAO[status]}</Selo>;
}
