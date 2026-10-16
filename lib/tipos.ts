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
