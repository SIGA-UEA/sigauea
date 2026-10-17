// Formato dos dados que a API devolve (ver backend/app/schemas).

export type Perfil =
  | "aluno"
  | "orientador"
  | "professor_disciplina"
  | "coordenador"
  | "membro_banca";

export type Cargo = "coordenador" | "professor" | "orientador";
export type Situacao = "ativo" | "aguardando_ativacao" | "inativo";

export type Curso = { id: number; sigla: string; nome: string };
export type Area = { id: number; nome: string };
export type AreaUso = Area & { docentes: number }; // gestão de áreas (RBN01.02)

export type Usuario = {
  id: number;
  nome: string;
  email: string;
  telefone: string | null;
  tipo: "docente" | "aluno";
  situacao: Situacao;
  perfis: Perfil[];
  cargo: Cargo | null;
  matricula: string | null;
  curso: Curso | null;
  areas: Area[];
  email_ativacao: "pendente" | "enviado" | "falha" | null;
  foto_versao: string | null; // nulo = sem foto
  criado_em: string;
};

// A versão na URL faz o navegador buscar a foto de novo quando ela muda.
export function urlFoto(usuario: Pick<Usuario, "id" | "foto_versao">) {
  return usuario.foto_versao ? `/api/v1/usuarios/${usuario.id}/foto?v=${usuario.foto_versao}` : null;
}

// Mesmos limites da API (backend/app/services/perfil.py).
export const FOTO_TIPOS = ["image/jpeg", "image/png", "image/webp"];
export const FOTO_MAX_BYTES = 5 * 1024 * 1024;

export function problemaNaFoto(arquivo: File): string | null {
  if (!FOTO_TIPOS.includes(arquivo.type)) return "Escolha uma imagem JPG, PNG ou WebP.";
  if (arquivo.size > FOTO_MAX_BYTES) return "A imagem passa de 5 MB. Escolha uma menor.";
  return null;
}

export const NOME_PERFIL: Record<Perfil, string> = {
  aluno: "Aluno",
  orientador: "Orientador",
  professor_disciplina: "Professor da disciplina",
  coordenador: "Coordenador",
  membro_banca: "Membro da banca",
};

export const NOME_CARGO: Record<Cargo, string> = {
  coordenador: "Coordenador",
  professor: "Professor",
  orientador: "Orientador",
};

// Perfis que a coordenação pode marcar para um docente.
export const PERFIS_DOCENTE: Perfil[] = [
  "orientador",
  "professor_disciplina",
  "coordenador",
  "membro_banca",
];

// ---------------------------------------------------------------- Sprint S03 · cadastro de TCC
// Espelha backend/app/schemas/tcc.py.

export type Pessoa = { id: number; nome: string };
export type Disciplina = "TCC1" | "TCC2";
export type Modalidade = "ARTIGO" | "MONOGRAFIA";
export type SituacaoTcc =
  | "RASCUNHO"
  | "EM_ANALISE"
  | "APROVADO"
  | "DEVOLVIDO"
  | "REPROVADO"
  | "CONCLUIDO"
  | "DESISTENCIA";
export type SituacaoEditorial = "SUBMETIDO" | "EM_REVISAO" | "ACEITO" | "RECUSADO" | "PUBLICADO";
export type SituacaoMatricula = "MATRICULADO" | "DESISTENTE" | "APROVADO" | "REPROVADO";
export type StatusOrientacao = "PENDENTE" | "ACEITA" | "RECUSADA" | "SUBSTITUIDA";

export type Periodo = { id: number; codigo: string; inicio: string; fim: string; prazo_versao_final: string | null };
export type TurmaResumo = { id: number; codigo: string; disciplina: Disciplina; periodo: string; professor: Pessoa };
export type Matricula = {
  id: number;
  aluno: Pessoa;
  matricula: string;
  curso: Curso;
  situacao: SituacaoMatricula;
  incluido_em: string;
};
export type Turma = {
  id: number;
  codigo: string;
  disciplina: Disciplina;
  curso: Curso;
  periodo: Periodo;
  professor: Pessoa;
  encerrada: boolean;
  alunos: Matricula[];
};

export type Vinculo = {
  id: number;
  professor: Pessoa;
  papel: "ORIENTADOR" | "COORIENTADOR";
  status: StatusOrientacao;
  solicitado_em: string;
  respondido_em: string | null;
  motivo_recusa: string | null;
};

export type Artigo = {
  tipo_veiculo: "PERIODICO" | "CONGRESSO";
  veiculo: string;
  situacao: SituacaoEditorial;
  doi: string | null;
  qualis: string | null;
};

export type Tcc = {
  id: number;
  protocolo: string | null;
  situacao: SituacaoTcc;
  etapa: Disciplina;
  modalidade: Modalidade;
  titulo: string;
  subtitulo: string | null;
  resumo: string;
  palavras_chave: string[];
  area: Area;
  turma: TurmaResumo;
  aluno: Pessoa;
  matricula: string;
  curso: Curso;
  orientador: Vinculo | null;
  coorientador: Vinculo | null;
  artigo: Artigo | null;
  submetido_em: string | null;
  criado_em: string;
  atualizado_em: string;
  pendencias: string[];
  historico: { situacao_anterior: string | null; situacao_nova: string; usuario: Pessoa; registrado_em: string }[];
};

export type Formulario = {
  turma: TurmaResumo;
  situacao_matricula: SituacaoMatricula;
  tcc: Tcc | null;
  origem: { tcc_origem_id: number; titulo: string; area_id: number; modalidade: Modalidade; orientador_id: number | null } | null;
  orientadores: Pessoa[];
  coorientadores: Pessoa[];
  areas: Area[];
};

export type Solicitacao = {
  id: number;
  papel: "ORIENTADOR" | "COORIENTADOR";
  status: StatusOrientacao;
  solicitado_em: string;
  respondido_em: string | null;
  motivo_recusa: string | null;
  tcc: Tcc;
};

export const NOME_SITUACAO_TCC: Record<SituacaoTcc, string> = {
  RASCUNHO: "Rascunho",
  EM_ANALISE: "Em análise",
  APROVADO: "Aprovado",
  DEVOLVIDO: "Devolvido para correção",
  REPROVADO: "Reprovado",
  CONCLUIDO: "Concluído",
  DESISTENCIA: "Desistência",
};

export const NOME_SITUACAO_EDITORIAL: Record<SituacaoEditorial, string> = {
  SUBMETIDO: "Submetido",
  EM_REVISAO: "Em revisão",
  ACEITO: "Aceito",
  RECUSADO: "Recusado",
  PUBLICADO: "Publicado",
};

export const NOME_STATUS_ORIENTACAO: Record<StatusOrientacao, string> = {
  PENDENTE: "Aguardando resposta",
  ACEITA: "Aceita",
  RECUSADA: "Recusada",
  SUBSTITUIDA: "Substituída",
};

// Datas da API vêm em UTC ("...Z"); a tela mostra no fuso de Manaus (RNF03).
export function dataHora(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("pt-BR", {
    timeZone: "America/Manaus",
    dateStyle: "short",
    timeStyle: "short",
  });
}
