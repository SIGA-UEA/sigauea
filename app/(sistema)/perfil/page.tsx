"use client";

// TEL02 · Meu perfil (RBN01.09 aluno, RBN01.10 docentes)
// Cada pessoa troca a foto, o telefone e, se for docente, o curso. Quem orienta ou
// dá a disciplina também escolhe as áreas de interesse (RN25). Nome, e-mail e
// matrícula só a coordenação altera (RBN01.08), por isso aparecem só para leitura.

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Avatar } from "@/components/avatar";
import { Aviso, type TipoAviso } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Campo, Entrada, Selecao } from "@/components/campo";
import { CampoSenha } from "@/components/campo-senha";
import { Icone } from "@/components/icone";
import { api, ErroApi } from "@/lib/api";
import { senhaValida } from "@/lib/senha";
import { useSessao } from "@/lib/sessao";
import {
  FOTO_TIPOS,
  NOME_CARGO,
  NOME_PERFIL,
  problemaNaFoto,
  urlFoto,
  type Area,
  type Curso,
  type Usuario,
} from "@/lib/tipos";

type Aba = "perfil" | "senha";

export default function PaginaPerfil() {
  const { usuario: eu, tem } = useSessao();
  const [aba, setAba] = useState<Aba>("perfil");

  return (
    <div className="flex flex-col gap-5">
      <header>
        <h1 className="text-2xl font-semibold">Meu perfil</h1>
        <p className="mt-1 text-sm text-suave">
          Foto e contato que as outras pessoas veem. Dados de identificação só a coordenação altera.
        </p>
      </header>

      <div role="tablist" aria-label="Seção" className="flex gap-1 border-b border-borda">
        {(["perfil", "senha"] as const).map((opcao) => (
          <button
            key={opcao}
            type="button"
            role="tab"
            aria-selected={aba === opcao}
            onClick={() => setAba(opcao)}
            className={`-mb-px border-b-[3px] px-4 py-2.5 text-sm font-medium ${
              aba === opcao
                ? "border-azul text-azul-forte"
                : "border-transparent text-suave hover:text-texto"
            }`}
          >
            {opcao === "perfil" ? "Perfil" : "Senha"}
          </button>
        ))}
      </div>

      {aba === "perfil" ? (
        <SecaoPerfil eu={eu} escolheAreas={tem("orientador") || tem("professor_disciplina")} />
      ) : (
        <SecaoSenha />
      )}
    </div>
  );
}

const CARTAO = "rounded-xl border border-borda bg-superficie p-5";

function SecaoPerfil({ eu, escolheAreas }: { eu: Usuario; escolheAreas: boolean }) {
  const router = useRouter();
  const docente = eu.tipo === "docente";
  const seletor = useRef<HTMLInputElement>(null);

  const [cursos, setCursos] = useState<Curso[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [telefone, setTelefone] = useState(eu.telefone ?? "");
  const [cursoId, setCursoId] = useState(eu.curso ? String(eu.curso.id) : "");
  const [areasIds, setAreasIds] = useState<number[]>(eu.areas.map((a) => a.id));
  const [erros, setErros] = useState<Record<string, string>>({});
  const [aviso, setAviso] = useState<{ tipo: TipoAviso; texto: string } | null>(null);
  const [erroFoto, setErroFoto] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [enviandoFoto, setEnviandoFoto] = useState(false);

  // Para o coordenador o curso não se aplica: ele acessa todos os cursos do núcleo (SCRUM-30).
  const editaCurso = docente && !eu.perfis.includes("coordenador");

  useEffect(() => {
    if (editaCurso) api<Curso[]>("/cursos").then(setCursos).catch(() => {});
    if (escolheAreas) api<Area[]>("/areas").then(setAreas).catch(() => {});
  }, [editaCurso, escolheAreas]);

  async function enviarFoto(arquivo: File | undefined) {
    if (!arquivo) return;
    // Confere aqui para não mandar 5 MB à toa; a API confere de novo pelo conteúdo.
    const problema = problemaNaFoto(arquivo);
    if (problema) return setErroFoto(problema);
    setErroFoto("");
    setEnviandoFoto(true);
    const formulario = new FormData();
    formulario.append("foto", arquivo);
    try {
      await api<Usuario>("/usuarios/me/foto", { metodo: "PUT", corpo: formulario });
      setAviso({ tipo: "sucesso", texto: "Foto atualizada." });
      router.refresh(); // a barra do topo busca o usuário de novo, já com a foto
    } catch (e) {
      setErroFoto((e as ErroApi).message);
    }
    setEnviandoFoto(false);
    if (seletor.current) seletor.current.value = "";
  }

  async function removerFoto() {
    setEnviandoFoto(true);
    try {
      await api<Usuario>("/usuarios/me/foto", { metodo: "DELETE" });
      setAviso({ tipo: "sucesso", texto: "Foto removida." });
      router.refresh();
    } catch (e) {
      setErroFoto((e as ErroApi).message);
    }
    setEnviandoFoto(false);
  }

  async function salvar(evento: React.SyntheticEvent) {
    evento.preventDefault();
    setAviso(null);
    if (editaCurso && !cursoId) return setErros({ curso_id: "Escolha o curso." });
    setErros({});
    setSalvando(true);
    const corpo = {
      telefone,
      ...(editaCurso ? { curso_id: Number(cursoId) } : {}),
      ...(escolheAreas ? { areas: areasIds } : {}),
    };
    try {
      await api<Usuario>("/usuarios/me", { metodo: "PUT", corpo });
      setAviso({ tipo: "sucesso", texto: "Alterações salvas." });
      router.refresh();
    } catch (e) {
      const erro = e as ErroApi;
      if (erro.campos) setErros(erro.campos);
      else setAviso({ tipo: "erro", texto: erro.message });
    }
    setSalvando(false);
  }

  return (
    <div className="flex flex-col gap-5">
      {aviso && <Aviso tipo={aviso.tipo}>{aviso.texto}</Aviso>}

      <section className={`${CARTAO} flex flex-wrap items-center gap-5`}>
        <Avatar nome={eu.nome} foto={urlFoto(eu)} tamanho="perfil" />
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-semibold">{eu.nome}</h2>
          <p className="text-sm text-suave">{eu.perfis.map((p) => NOME_PERFIL[p]).join(" · ")}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <input
              ref={seletor}
              id="foto"
              type="file"
              accept={FOTO_TIPOS.join(",")}
              className="sr-only"
              onChange={(e) => enviarFoto(e.target.files?.[0])}
            />
            <Botao variante="contorno" pequeno carregando={enviandoFoto} onClick={() => seletor.current?.click()}>
              <Icone nome="camera" className="size-4" />
              {eu.foto_versao ? "Trocar foto" : "Adicionar foto"}
            </Botao>
            {eu.foto_versao && (
              <Botao variante="perigo" pequeno disabled={enviandoFoto} onClick={removerFoto}>
                <Icone nome="lixeira" className="size-4" />
                Remover
              </Botao>
            )}
          </div>
          {erroFoto ? (
            <p role="alert" className="mt-2 text-[13px] font-medium text-vermelho">
              {erroFoto}
            </p>
          ) : (
            <p className="mt-2 text-[13px] text-suave">JPG, PNG ou WebP, até 5 MB. A foto é opcional.</p>
          )}
        </div>
      </section>

      <section className={CARTAO}>
        <h2 className="mb-3 font-semibold">Identificação</h2>
        <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-[max-content_1fr]">
          <dt className="text-suave">Nome</dt>
          <dd>{eu.nome}</dd>
          <dt className="text-suave">E-mail</dt>
          <dd className="break-all">{eu.email}</dd>
          {eu.matricula && (
            <>
              <dt className="text-suave">Matrícula</dt>
              <dd className="font-mono">{eu.matricula}</dd>
              <dt className="text-suave">Curso</dt>
              <dd>{eu.curso?.nome}</dd>
            </>
          )}
          {eu.cargo && (
            <>
              <dt className="text-suave">Cargo</dt>
              <dd>{NOME_CARGO[eu.cargo]}</dd>
            </>
          )}
          {docente && !editaCurso && (
            <>
              <dt className="text-suave">Curso</dt>
              <dd>Todos os cursos do núcleo</dd>
            </>
          )}
        </dl>
        <p className="mt-4 flex items-center gap-2 text-[13px] text-suave">
          <Icone nome="cadeado" className="size-4" />
          Estes dados vêm do cadastro da coordenação. Para corrigir, procure a coordenação.
        </p>
      </section>

      <section className={CARTAO}>
        <h2 className="mb-4 font-semibold">Contato{editaCurso ? " e vínculo" : ""}</h2>
        <form onSubmit={salvar} noValidate className="flex flex-col gap-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <Campo rotulo="Telefone" dica="opcional" erro={erros.telefone}>
              <Entrada
                type="tel"
                autoComplete="tel"
                value={telefone}
                onChange={(e) => setTelefone(e.target.value)}
                erro={erros.telefone}
                placeholder="(92) 90000-0000"
                maxLength={20}
              />
            </Campo>

            {editaCurso && (
              <Campo rotulo="Curso" obrigatorio erro={erros.curso_id}>
                <Selecao value={cursoId} onChange={(e) => setCursoId(e.target.value)} erro={erros.curso_id}>
                  <option value="">Escolha…</option>
                  {cursos.map((curso) => (
                    <option key={curso.id} value={curso.id}>
                      {curso.nome}
                    </option>
                  ))}
                </Selecao>
              </Campo>
            )}
          </div>

          {escolheAreas && (
            <fieldset className="text-sm">
              <legend className="mb-1 font-medium">
                Áreas de interesse <span className="font-normal text-suave">(opcional)</span>
              </legend>
              <p className="mb-2 text-[13px] text-suave">
                Propostas de TCC enviadas para uma área aparecem para os professores dela.
              </p>
              <div className="flex flex-wrap gap-2">
                {areas.map((area) => {
                  const marcada = areasIds.includes(area.id);
                  return (
                    <button
                      key={area.id}
                      type="button"
                      aria-pressed={marcada}
                      onClick={() =>
                        setAreasIds(marcada ? areasIds.filter((id) => id !== area.id) : [...areasIds, area.id])
                      }
                      className={`rounded-full border px-3 py-1.5 font-medium ${
                        marcada
                          ? "border-azul bg-azul-claro text-azul-escuro"
                          : "border-borda text-suave hover:bg-fundo"
                      }`}
                    >
                      {area.nome}
                    </button>
                  );
                })}
              </div>
            </fieldset>
          )}

          <div className="flex justify-end border-t border-borda pt-4">
            <Botao type="submit" carregando={salvando}>
              Salvar alterações
            </Botao>
          </div>
        </form>
      </section>
    </div>
  );
}

function SecaoSenha() {
  const [atual, setAtual] = useState("");
  const [nova, setNova] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [erros, setErros] = useState<{ atual?: string; nova?: string; confirmacao?: string }>({});
  const [aviso, setAviso] = useState<{ tipo: TipoAviso; texto: string } | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function salvar(evento: React.SyntheticEvent) {
    evento.preventDefault();
    setAviso(null);
    const encontrados: typeof erros = {};
    if (!atual) encontrados.atual = "Informe a senha atual.";
    if (!senhaValida(nova)) encontrados.nova = "A senha ainda não atende a todos os critérios abaixo.";
    else if (nova !== confirmacao) encontrados.confirmacao = "A confirmação é diferente da nova senha.";
    setErros(encontrados);
    if (Object.keys(encontrados).length) return;

    setEnviando(true);
    try {
      const r = await api<{ detail: string }>("/usuarios/me/senha", {
        metodo: "POST",
        corpo: { senha_atual: atual, nova_senha: nova },
      });
      setAviso({ tipo: "sucesso", texto: r.detail });
      setAtual("");
      setNova("");
      setConfirmacao("");
    } catch (e) {
      const erro = e as ErroApi;
      if (erro.campos?.senha_atual) setErros({ atual: erro.campos.senha_atual });
      else if (erro.criterios) {
        setErros({ nova: "Falta: " + erro.criterios.map((c) => c.descricao).join("; ") + "." });
      } else setAviso({ tipo: "erro", texto: erro.message });
    }
    setEnviando(false);
  }

  return (
    <section className={`${CARTAO} max-w-xl`}>
      <h2 className="mb-4 font-semibold">Alterar senha</h2>
      <form onSubmit={salvar} noValidate className="flex flex-col gap-5">
        {aviso && <Aviso tipo={aviso.tipo}>{aviso.texto}</Aviso>}
        <CampoSenha
          rotulo="Senha atual"
          valor={atual}
          aoMudar={setAtual}
          erro={erros.atual}
          autoComplete="current-password"
        />
        <CampoSenha
          rotulo="Nova senha"
          valor={nova}
          aoMudar={setNova}
          erro={erros.nova}
          autoComplete="new-password"
          mostrarCriterios
        />
        <CampoSenha
          rotulo="Confirmar nova senha"
          valor={confirmacao}
          aoMudar={setConfirmacao}
          erro={erros.confirmacao}
          autoComplete="new-password"
        />
        <p className="text-[13px] text-suave">
          Ao trocar a senha, as sessões abertas em outros navegadores ou aparelhos são encerradas.
        </p>
        <div className="flex justify-end">
          <Botao type="submit" carregando={enviando}>
            Alterar senha
          </Botao>
        </div>
      </form>
    </section>
  );
}
