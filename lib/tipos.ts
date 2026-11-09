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
export type TccDaTurma = {
  id: number;
  titulo: string;
  situacao: SituacaoTcc;
  protocolo: string | null;
  orientador: Pessoa | null;
  orientacao: StatusOrientacao | null;
};
export type Matricula = {
  id: number;
  aluno: Pessoa;
  matricula: string;
  curso: Curso;
  situacao: SituacaoMatricula;
  incluido_em: string;
  tcc: TccDaTurma | null;
};
// Minhas turmas: o professor vê as que conduz; o aluno, a sua (com a matrícula e o próprio TCC).
export type TurmaCartao = {
  id: number;
  codigo: string;
  disciplina: Disciplina;
  curso: Curso;
  periodo: string;
  professor: Pessoa;
  encerrada: boolean;
  alunos: number;
  com_tcc: number;
  pendentes: number;
  minha_matricula: SituacaoMatricula | null;
  meu_tcc: TccDaTurma | null;
};
export const NOME_SITUACAO_MATRICULA: Record<SituacaoMatricula, string> = {
  MATRICULADO: "Matriculado",
  DESISTENTE: "Desistente",
  APROVADO: "Aprovado",
  REPROVADO: "Reprovado",
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
  decisoes: Decisao[]; // decisões da coordenação, da mais antiga para a mais nova (RBN04.05)
};

// Análise do cadastro pela coordenação (TEL07, DS-FL02-A e DS-FL02)
export type ResultadoAnalise = "APROVADO" | "DEVOLVIDO" | "REPROVADO";
export type Decisao = { resultado: ResultadoAnalise; parecer: string; coordenador: Pessoa; decidido_em: string };
export type CadastroResumo = {
  id: number;
  protocolo: string;
  titulo: string;
  aluno: Pessoa;
  matricula: string;
  curso: Curso;
  etapa: Disciplina;
  modalidade: Modalidade;
  periodo: string;
  situacao: SituacaoTcc;
  submetido_em: string | null;
  dias_aguardando: number;
  decisao: Decisao | null;
};
export type Cadastro = { tcc: Tcc; documento: { nome: string } | null; decisao: Decisao | null };

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

// ---------------------------------------------------------------- Sprint S04 · banca e defesa
// Espelha backend/app/schemas/defesa.py.

export type PapelBanca = "AVALIADOR" | "ORIENTADOR" | "COORIENTADOR" | "SUPLENTE";
export type FormatoDefesa = "PRESENCIAL" | "REMOTO" | "HIBRIDO";
export type ConvidadoExterno = { nome: string; email: string; instituicao: string };
// Quem ocupa a vaga: um docente da UEA ou um convidado externo (nunca os dois).
export type PessoaBanca = { usuario_id: number; externo?: undefined } | { usuario_id?: undefined; externo: ConvidadoExterno };
export type MembroEntrada = PessoaBanca & { papel: PapelBanca };

export type MembroBanca = {
  id: number | null; // nulo enquanto a vaga só existe na tela
  papel: PapelBanca;
  pessoa: Pessoa;
  email: string;
  interno: boolean;
  instituicao: string | null;
  convite_enviado_em: string | null;
  convite: SituacaoConvite; // RBN09.05: situação do último convite por e-mail
  // RBN09.09: no suplente convocado, quando e no lugar de quem; no titular, quem o substitui
  convocado_em: string | null;
  substitui_membro_id: number | null;
  substituido_por_id: number | null;
};
export type EventoDefesa = {
  evento: "AGENDAMENTO" | "REMARCACAO" | "CANCELAMENTO" | "SUPLENTE_CONVOCADO" | "BANCA_ALTERADA" | "PUBLICACAO" | "RETIRADA";
  motivo: string | null;
  valores_anteriores: Record<string, string | number | boolean | null> | null;
  por: Pessoa;
  registrado_em: string;
};
export type SituacaoConvite = "NAO_ENVIADO" | "PENDENTE" | "ENVIADO" | "FALHA";
export type LocalDefesa = { id: number; nome: string; descricao: string | null };
// RBN09.04: outra defesa no mesmo horário com o mesmo local ou alguém desta banca.
export type Conflito = { tipo: "PARTICIPANTE" | "LOCAL"; nome: string; data: string; inicio: string; fim: string };
export type Conflitos = { conflitos: Conflito[]; aviso: string };
export type Defesa = {
  id: number;
  titulo: string; // herdado do TCC (RBN09.03 CA-01)
  autor: Pessoa;
  situacao: "CONFIRMADA" | "REMARCADA" | "CANCELADA" | "REALIZADA";
  formato: FormatoDefesa;
  data: string;
  inicio: string;
  fim: string;
  local: LocalDefesa | null;
  link: string | null;
  publicada: boolean;
  responsavel: Pessoa;
  membros: MembroBanca[];
  criado_em: string;
  historico: EventoDefesa[]; // mais recente primeiro
};
export type Banca = {
  tcc_id: number;
  etapa: Disciplina;
  liberada: boolean;
  pode_editar: boolean;
  orientador: Pessoa | null;
  coorientador: Pessoa | null;
  docentes: Pessoa[];
  locais: LocalDefesa[];
  defesa: Defesa | null;
  pode_convocar: boolean; // RBN09.09: coordenação ou orientador do TCC
  cancelada: Defesa | null; // RBN09.08: sem defesa vigente, a última cancelada
};

export const NOME_PAPEL_BANCA: Record<PapelBanca, string> = {
  AVALIADOR: "Avaliador(a)",
  ORIENTADOR: "Orientador(a)",
  COORIENTADOR: "Coorientador(a)",
  SUPLENTE: "Suplente",
};
export const NOME_FORMATO: Record<FormatoDefesa, string> = {
  PRESENCIAL: "Presencial",
  REMOTO: "Remoto",
  HIBRIDO: "Híbrido",
};

// Data "AAAA-MM-DD" da API mostrada como dd/mm/aaaa, sem passar por fuso (é só um dia).
export function dataCurta(iso: string) {
  const [a, m, d] = iso.split("-");
  return `${d}/${m}/${a}`;
}

// ---------------------------------------------------------------- Sprint S04 · agenda de apresentações
// Espelha backend/app/schemas/agenda.py.

export type Apresentacao = {
  id: number;
  titulo: string;
  autor: string;
  orientador: string | null;
  curso: { sigla: string; nome: string };
  formato: FormatoDefesa;
  data: string;
  inicio: string;
  fim: string;
  local: string | null;
  link: string | null;
  remarcada: boolean;
};

// TEL18 · divulgação na agenda (DS-FL05): condições de RN09, prévia e se pode publicar.
export type Divulgacao = {
  defesa_id: number;
  tcc_id: number;
  situacao: Defesa["situacao"];
  publicada: boolean;
  pode_publicar: boolean;
  condicoes: { descricao: string; atendida: boolean }[];
  previa: Apresentacao | null;
};
// ---------------------------------------------------------------- Sprint S04 · instrumento de avaliação
// Espelha backend/app/schemas/instrumento.py (DS-FL06-G).

export type Conceito = "EXEMPLAR" | "COMPETENTE" | "NECESSITA";
export type FaixaConceito = { conceito: Conceito; rotulo: string; minimo: number; maximo: number };
export type CriterioAvaliacao = {
  id: number;
  nome: string;
  peso: number;
  texto_exemplar: string;
  texto_competente: string;
  texto_necessita: string;
  ordem: number;
};
export type ComponenteAvaliacao = {
  id: number;
  nome: string;
  pontos: number;
  ordem: number;
  criterios: CriterioAvaliacao[];
};
export type InstrumentoAvaliacao = {
  id: number;
  versao: number;
  vigente: boolean;
  criado_em: string;
  autor: Pessoa;
  componentes: ComponenteAvaliacao[];
  conceitos: FaixaConceito[];
};
export type VersaoInstrumento = { id: number; versao: number; vigente: boolean; criado_em: string; autor: Pessoa };
export type ConsultaInstrumento = { instrumento: InstrumentoAvaliacao; versoes: VersaoInstrumento[] };
export type CriterioEntrada = Pick<CriterioAvaliacao, "nome" | "texto_exemplar" | "texto_competente" | "texto_necessita"> & {
  peso: string; // vai como texto ("0.5") para a API somar em decimal exato
};
// 422 do PUT: os componentes cuja soma dos pesos não fecha os pontos (DS-FL06-G passo 7)
export type SomaIncorreta = { id: number; nome: string; pontos: number; soma: number };

// ---------------------------------------------------------------- TEL19 · ocorrências e ouvintes (RBN09.10)

export type Ocorrencia = {
  id: number;
  texto: string;
  autor: { id: number; nome: string };
  criado_em: string;
  alterada_em: string | null;
};

export type Declaracao = { id: number; ouvinte_id: number; versao: number; gerado_em: string };

export type Ouvinte = {
  id: number;
  nome: string;
  matricula: string | null;
  pronto: boolean; // matrícula completa: pode emitir a declaração
  declaracao: Declaracao | null;
};

export type Presenca = {
  defesa_id: number;
  situacao: Defesa["situacao"];
  liberada: boolean; // a defesa já começou ou foi realizada
  pode_emitir: boolean; // a defesa já terminou ou foi realizada (RN15)
  ocorrencias: Ocorrencia[];
  ouvintes: Ouvinte[];
  prontos: number;
};

export type LoteOuvintes = {
  adicionados: Ouvinte[];
  linhas_com_problema: { linha: number; texto: string; motivo: string }[];
};


// ---------------------------------------------------------------- Sprint S04 · avaliação da defesa
// Espelha backend/app/schemas/avaliacao.py (DS-FL06-A).

export type CriterioAvaliado = { criterio_id: number; conceito: Conceito; nota: number; nota_ponderada: number };
export type MinhaAvaliacao = {
  id: number;
  status: "RASCUNHO" | "ENVIADA";
  parecer: string | null;
  criterios: CriterioAvaliado[];
  pendentes: number[]; // critérios ainda sem conceito e nota
  nota_total: number | null; // só com todos os critérios preenchidos
  enviada_em: string | null;
};
export type ConsultaAvaliacao = {
  defesa_id: number;
  envio_liberado: boolean; // a defesa já foi realizada
  instrumento: InstrumentoAvaliacao;
  minha_avaliacao: MinhaAvaliacao | null;
  envios: { enviadas: number; esperadas: number };
};
// O que vai no PUT e no POST: a nota vai como texto ("7.5") para a API conferir a faixa em decimal exato
export type CriterioLancado = { criterio_id: number; conceito: Conceito; nota: string };
// 422: critérios com problema (faltando ou fora da faixa), destacados na tela
export type CriterioComProblema = { id: number; nome: string; motivo: string };
