import { NextResponse, type NextRequest } from "next/server";

// Atalho de navegação: quem não tem o cookie de sessão nem chega a abrir uma
// página interna. A proteção de verdade está na API, que confere a sessão em
// toda rota (o cookie pode existir e já estar expirado).
export function proxy(request: NextRequest) {
  const logado = request.cookies.has("siga_sessao");

  // A raiz não tem conteúdo próprio: leva ao painel ou ao login.
  if (request.nextUrl.pathname === "/") {
    return NextResponse.redirect(new URL(logado ? "/inicio" : "/entrar", request.url));
  }
  if (!logado) {
    return NextResponse.redirect(new URL("/entrar", request.url));
  }
}

export const config = {
  matcher: ["/", "/inicio/:path*", "/usuarios/:path*", "/perfil/:path*"],
};
