// HU01.04: os 4 critérios de complexidade da senha.
// O backend valida de novo com a mesma regra (backend/app/security.py).

export type CriterioSenha = { codigo: string; descricao: string };

const CRITERIOS: (CriterioSenha & { atende: (senha: string) => boolean })[] = [
  { codigo: "tamanho", descricao: "Mínimo de 8 caracteres", atende: (s) => s.length >= 8 },
  { codigo: "maiuscula", descricao: "Ao menos 1 letra maiúscula", atende: (s) => /[A-Z]/.test(s) },
  { codigo: "numero", descricao: "Ao menos 1 número", atende: (s) => /[0-9]/.test(s) },
  {
    codigo: "especial",
    descricao: "Ao menos 1 caractere especial",
    atende: (s) => /[^A-Za-z0-9]/.test(s),
  },
];

export function avaliarSenha(senha: string) {
  return CRITERIOS.map((c) => ({
    codigo: c.codigo,
    descricao: c.descricao,
    ok: c.atende(senha),
  }));
}

export function senhaValida(senha: string) {
  return CRITERIOS.every((c) => c.atende(senha));
}
