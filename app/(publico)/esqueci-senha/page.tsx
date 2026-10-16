"use client";

// TEL01 · Pedir link de recuperação de senha (HU01.07)

import Link from "next/link";
import { useState } from "react";
import { Aviso } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Campo, Entrada } from "@/components/campo";
import { api, ErroApi } from "@/lib/api";

export default function PaginaEsqueciSenha() {
  const [email, setEmail] = useState("");
  const [mensagem, setMensagem] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(evento: React.SyntheticEvent) {
    evento.preventDefault();
    setErro("");
    setEnviando(true);
    try {
      // A resposta é a mesma, exista o e-mail ou não: a tela não revela quem tem cadastro.
      const resposta = await api<{ detail: string }>("/auth/esqueci-senha", {
        metodo: "POST",
        corpo: { email },
        publica: true,
      });
      setMensagem(resposta.detail);
    } catch (e) {
      setErro((e as ErroApi).message);
    }
    setEnviando(false);
  }

  return (
    <form onSubmit={enviar} className="flex flex-col gap-5">
      <div>
        <h2 className="text-2xl font-semibold">Esqueci minha senha</h2>
        <p className="mt-1 text-sm text-suave">
          Informe o seu e-mail cadastrado. Enviaremos um link para você criar uma nova senha.
        </p>
      </div>

      {erro && <Aviso tipo="erro">{erro}</Aviso>}
      {mensagem ? (
        <Aviso tipo="sucesso">
          {mensagem} O link vale por 10 minutos e só pode ser usado uma vez.
        </Aviso>
      ) : (
        <>
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
          <Botao type="submit" carregando={enviando} className="w-full">
            Enviar link de recuperação
          </Botao>
        </>
      )}

      <Link href="/entrar" className="text-sm font-medium text-azul-forte hover:underline">
        Voltar para o login
      </Link>
    </form>
  );
}
