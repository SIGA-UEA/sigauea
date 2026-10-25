// Telefone com DDD: 10 a 13 dígitos, com ou sem parênteses, espaços, hífen ou "+". Mesma regra da API
// (schemas/usuario.py); o campo é opcional, então vazio vale.
export const MENSAGEM_TELEFONE = "Informe o telefone com DDD, só com números (ex.: (92) 99123-4567).";

export function telefoneValido(valor: string): boolean {
  const t = valor.trim();
  if (!t) return true;
  const digitos = t.replace(/\D/g, "").length;
  return /^\+?[\d\s().-]+$/.test(t) && digitos >= 10 && digitos <= 13;
}

// Máscara simples: ao digitar, só ficam números e os sinais de um telefone.
export function soTelefone(valor: string): string {
  return valor.replace(/[^\d\s()+.-]/g, "");
}
