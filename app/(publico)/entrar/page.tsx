"use client";

// TEL01 · Entrar no sistema (HU01.06)

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Aviso, type TipoAviso } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Campo, Entrada } from "@/components/campo";
import { CampoSenha } from "@/components/campo-senha";
import { api, ErroApi } from "@/lib/api";

// Mensagens mostradas quando a pessoa chega aqui vinda de outra tela (?motivo=...).
const MOTIVOS: Record<string, [TipoAviso, string]> = {
  sessao: ["info", "Sua sessão expirou. Entre novamente para continuar."],
  saiu: ["sucesso", "Você saiu do sistema."],
  ativada: ["sucesso", "Conta ativada. Entre com o seu e-mail e a nova senha."],
  redefinida: ["sucesso", "Senha alterada. Entre com a nova senha."],
};

function Formulario() {
  const router = useRouter();
  const motivo = MOTIVOS[useSearchParams().get("motivo") ?? ""];
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function entrar(evento: React.SyntheticEvent) {
    evento.preventDefault();
    setErro("");
    setEnviando(true);
    try {
      await api("/auth/login", { metodo: "POST", corpo: { email, senha }, publica: true });
      router.replace("/inicio");
    } catch (e) {
      // A API devolve a mesma mensagem para e-mail ou senha errados (não revela qual).
      setErro((e as ErroApi).message);
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={entrar} className="flex flex-col gap-5">
      <div>
        <h2 className="text-2xl font-semibold">Entrar</h2>
        <p className="mt-1 text-sm text-suave">Use o seu e-mail e a sua senha.</p>
      </div>

      {erro ? <Aviso tipo="erro">{erro}</Aviso> : motivo && <Aviso tipo={motivo[0]}>{motivo[1]}</Aviso>}

      <Campo rotulo="E-mail" obrigatorio>
        <Entrada
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="username"
          placeholder="nome@exemplo.com"
          required
        />
      </Campo>
      <CampoSenha rotulo="Senha" valor={senha} aoMudar={setSenha} autoComplete="current-password" />

      <Botao type="submit" carregando={enviando} className="w-full">
        Entrar
      </Botao>

      <div className="flex flex-col gap-3 border-t border-borda pt-4 text-sm">
        <Link href="/esqueci-senha" className="font-medium text-azul-forte hover:underline">
          Esqueci minha senha
        </Link>
        <p className="text-suave">
          Primeiro acesso? Abra o link de ativação enviado ao seu e-mail quando a coordenação fez o
          seu cadastro.
        </p>
      </div>
    </form>
  );
}

export default function PaginaEntrar() {
  return (
    <Suspense>
      <Formulario />
    </Suspense>
  );
}
