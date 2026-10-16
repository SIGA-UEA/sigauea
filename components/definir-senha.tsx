"use client";

// Tela aberta pelo link do e-mail. Serve para os dois casos:
// - ativação da conta (HU01.05), em /ativar?token=...
// - redefinição de senha (HU01.07), em /redefinir-senha?token=...

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ErroApi } from "@/lib/api";
import { senhaValida } from "@/lib/senha";
import { Aviso } from "./aviso";
import { Botao } from "./botao";
import { CampoSenha } from "./campo-senha";

const TEXTOS = {
  ativacao: {
    titulo: "Ativar conta",
    subtitulo: "Crie a senha que você vai usar para entrar no SIGA UEA.",
    botao: "Ativar conta",
    rota: "/auth/ativar",
    destino: "/entrar?motivo=ativada",
  },
  recuperacao: {
    titulo: "Nova senha",
    subtitulo: "Crie uma nova senha para a sua conta.",
    botao: "Salvar nova senha",
    rota: "/auth/redefinir-senha",
    destino: "/entrar?motivo=redefinida",
  },
};

const PROBLEMA = {
  invalido: "Este link não é válido.",
  expirado: "Este link expirou.",
  usado: "Este link já foi usado.",
};
type Motivo = keyof typeof PROBLEMA;

export function DefinirSenha({ tipo }: { tipo: "ativacao" | "recuperacao" }) {
  const textos = TEXTOS[tipo];
  const router = useRouter();
  const token = useSearchParams().get("token");

  // undefined = ainda conferindo o link; null = link válido; texto = motivo da recusa.
  const [motivo, setMotivo] = useState<Motivo | null | undefined>(token ? undefined : "invalido");
  const [senha, setSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [erros, setErros] = useState<{ senha?: string; confirmacao?: string; geral?: string }>({});
  const [enviando, setEnviando] = useState(false);

  // Antes de mostrar o formulário, pergunta à API se o link ainda vale.
  useEffect(() => {
    if (!token) return;
    api<{ valido: boolean; motivo: Motivo | null }>("/auth/validar-token", {
      metodo: "POST",
      corpo: { token, tipo },
      publica: true,
    })
      .then((r) => setMotivo(r.valido ? null : r.motivo))
      .catch(() => setMotivo(null)); // sem resposta: deixa tentar; o envio valida de novo
  }, [token, tipo]);

  async function salvar(evento: React.SyntheticEvent) {
    evento.preventDefault();
    if (!senhaValida(senha)) {
      return setErros({ senha: "A senha ainda não atende a todos os critérios abaixo." });
    }
    if (senha !== confirmacao) {
      return setErros({ confirmacao: "A confirmação é diferente da senha." });
    }
    setErros({});
    setEnviando(true);
    try {
      await api(textos.rota, { metodo: "POST", corpo: { token, senha }, publica: true });
      router.replace(textos.destino);
    } catch (e) {
      const erro = e as ErroApi;
      if (erro.motivo) setMotivo(erro.motivo);
      else if (erro.criterios) {
        // O backend valida de novo e diz o que falta.
        setErros({ senha: "Falta: " + erro.criterios.map((c) => c.descricao).join("; ") + "." });
      } else setErros({ geral: erro.message });
      setEnviando(false);
    }
  }

  if (motivo === undefined) {
    return (
      <p role="status" className="text-suave">
        Conferindo o link…
      </p>
    );
  }

  if (motivo) {
    return (
      <div className="flex flex-col gap-5">
        <h2 className="text-2xl font-semibold">{textos.titulo}</h2>
        <Aviso tipo="alerta">
          <strong>{PROBLEMA[motivo]}</strong>{" "}
          {tipo === "ativacao"
            ? "Peça um novo link de ativação à coordenação do seu curso."
            : "Peça um novo link para redefinir a senha."}
        </Aviso>
        {tipo === "recuperacao" && (
          <Link href="/esqueci-senha" className="text-sm font-medium text-azul-forte hover:underline">
            Pedir novo link
          </Link>
        )}
        <Link href="/entrar" className="text-sm font-medium text-azul-forte hover:underline">
          Ir para o login
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={salvar} className="flex flex-col gap-5">
      <div>
        <h2 className="text-2xl font-semibold">{textos.titulo}</h2>
        <p className="mt-1 text-sm text-suave">{textos.subtitulo}</p>
      </div>

      {erros.geral && <Aviso tipo="erro">{erros.geral}</Aviso>}

      <CampoSenha
        rotulo="Nova senha"
        valor={senha}
        aoMudar={setSenha}
        erro={erros.senha}
        autoComplete="new-password"
        mostrarCriterios
      />
      <CampoSenha
        rotulo="Confirmar senha"
        valor={confirmacao}
        aoMudar={setConfirmacao}
        erro={erros.confirmacao}
        autoComplete="new-password"
      />

      <Botao type="submit" carregando={enviando} className="w-full">
        {textos.botao}
      </Botao>
    </form>
  );
}
