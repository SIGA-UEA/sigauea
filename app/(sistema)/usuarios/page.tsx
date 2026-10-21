"use client";

// TEL02 · Usuários e perfis (HU01.01, HU01.03, HU01.05, HU01.08 e RBN01.02)
// Só a coordenação usa esta tela. A API responde 403 para os outros perfis.

import { useEffect, useState } from "react";
import { Avatar } from "@/components/avatar";
import { Aviso, Selo, type TipoAviso } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Entrada, Selecao } from "@/components/campo";
import { Icone } from "@/components/icone";
import { Modal } from "@/components/modal";
import { api, ErroApi } from "@/lib/api";
import { useSessao } from "@/lib/sessao";
import {
  NOME_CARGO,
  NOME_PERFIL,
  urlFoto,
  type Area,
  type Curso,
  type Situacao,
  type Usuario,
} from "@/lib/tipos";
import { FormularioUsuario } from "./formulario-usuario";
import { GestaoAreas } from "./gestao-areas";

type Aba = "docente" | "aluno" | "area";

const ABAS: Record<Aba, string> = { docente: "Docentes", aluno: "Alunos", area: "Áreas de interesse" };

const SITUACAO: Record<Situacao, { rotulo: string; cor: "verde" | "ambar" | "cinza" }> = {
  ativo: { rotulo: "Ativo", cor: "verde" },
  aguardando_ativacao: { rotulo: "Aguardando ativação", cor: "ambar" },
  inativo: { rotulo: "Inativo", cor: "cinza" },
};

export default function PaginaUsuarios() {
  const { usuario: eu, tem } = useSessao();
  const coordenador = tem("coordenador");

  const [aba, setAba] = useState<Aba>("docente");
  const [busca, setBusca] = useState("");
  const [curso, setCurso] = useState("");
  const [cargo, setCargo] = useState("");
  const [situacao, setSituacao] = useState("");

  const [lista, setLista] = useState<Usuario[] | null>(null);
  const [cursos, setCursos] = useState<Curso[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [versao, setVersao] = useState(0); // muda para recarregar a lista
  const [aviso, setAviso] = useState<{ tipo: TipoAviso; texto: string } | null>(null);

  // Janelas abertas: formulário (novo ou edição) e confirmação de inativar.
  const [formulario, setFormulario] = useState<{ usuario?: Usuario } | null>(null);
  const [inativando, setInativando] = useState<Usuario | null>(null);
  const [ocupado, setOcupado] = useState(false);

  // Cursos e áreas dos formulários: carregados uma vez.
  useEffect(() => {
    if (!coordenador) return;
    api<Curso[]>("/cursos").then(setCursos).catch(() => {});
    api<Area[]>("/areas").then(setAreas).catch(() => {});
  }, [coordenador]);

  // Lista: a busca e os filtros vão para a API. Espera 300 ms depois da última
  // tecla para não disparar uma requisição por letra digitada.
  useEffect(() => {
    if (!coordenador || aba === "area") return;
    let ativo = true;
    const espera = setTimeout(() => {
      const filtros = new URLSearchParams();
      if (busca.trim()) filtros.set("busca", busca.trim());
      if (curso) filtros.set("curso", curso);
      if (cargo && aba === "docente") filtros.set("cargo", cargo);
      api<Usuario[]>(`/${aba}s?${filtros}`)
        .then((dados) => ativo && setLista(dados))
        .catch((e: ErroApi) => ativo && setAviso({ tipo: "erro", texto: e.message }));
    }, 300);
    return () => {
      ativo = false;
      clearTimeout(espera);
    };
  }, [coordenador, aba, busca, curso, cargo, versao]);

  if (!coordenador) {
    return <Aviso tipo="alerta">Esta tela é exclusiva da coordenação.</Aviso>;
  }

  const recarregar = () => setVersao((v) => v + 1);
  const visiveis = lista?.filter((u) => !situacao || u.situacao === situacao);

  function trocarAba(nova: Aba) {
    setAba(nova);
    setAviso(null);
    if (nova === "area") return;
    // As áreas podem ter mudado na outra aba; o formulário de docente usa a lista nova.
    api<Area[]>("/areas").then(setAreas).catch(() => {});
    setLista(null);
    setBusca("");
    setCurso("");
    setCargo("");
    setSituacao("");
  }

  // Inativar, reativar e reenviar ativação seguem o mesmo roteiro.
  async function executar(caminho: string, metodo: "PATCH" | "POST", sucesso: string) {
    setOcupado(true);
    try {
      await api(caminho, { metodo });
      setAviso({ tipo: "sucesso", texto: sucesso });
      recarregar();
    } catch (e) {
      setAviso({ tipo: "erro", texto: (e as ErroApi).message });
    }
    setOcupado(false);
    setInativando(null);
  }

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Usuários e perfis</h1>
          <p className="mt-1 text-sm text-suave">
            Cadastre docentes e alunos. Cada pessoa recebe um link para ativar a conta e criar a própria
            senha.
          </p>
        </div>
        {aba !== "area" && (
          <Botao onClick={() => setFormulario({})}>
            <Icone nome="mais" className="size-4" />
            {aba === "docente" ? "Novo docente" : "Novo aluno"}
          </Botao>
        )}
      </header>

      {aviso && <Aviso tipo={aviso.tipo}>{aviso.texto}</Aviso>}

      <div role="tablist" aria-label="Tipo de cadastro" className="flex gap-1 overflow-x-auto border-b border-borda">
        {(Object.keys(ABAS) as Aba[]).map((opcao) => (
          <button
            key={opcao}
            type="button"
            role="tab"
            aria-selected={aba === opcao}
            onClick={() => trocarAba(opcao)}
            className={`-mb-px border-b-[3px] px-4 py-2.5 text-sm font-medium whitespace-nowrap ${
              aba === opcao
                ? "border-azul text-azul-forte"
                : "border-transparent text-suave hover:text-texto"
            }`}
          >
            {ABAS[opcao]}
          </button>
        ))}
      </div>

      {aba === "area" ? (
        <GestaoAreas />
      ) : (
        <>
          <div className="flex flex-wrap gap-3">
            <label className="relative min-w-0 flex-1 basis-64">
              <span className="sr-only">Buscar</span>
              <Icone nome="busca" className="pointer-events-none absolute top-3 left-3 size-5 text-suave" />
              <Entrada
                type="search"
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                placeholder={aba === "docente" ? "Buscar por nome ou e-mail" : "Buscar por nome, e-mail ou matrícula"}
                className="pl-10"
              />
            </label>
            <Selecao
              aria-label="Curso"
              value={curso}
              onChange={(e) => setCurso(e.target.value)}
              className="flex-1 basis-36 sm:w-auto sm:flex-none"
            >
              <option value="">Todos os cursos</option>
              {cursos.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nome}
                </option>
              ))}
            </Selecao>
            {aba === "docente" && (
              <Selecao
                aria-label="Cargo"
                value={cargo}
                onChange={(e) => setCargo(e.target.value)}
                className="flex-1 basis-36 sm:w-auto sm:flex-none"
              >
                <option value="">Todos os cargos</option>
                {Object.entries(NOME_CARGO).map(([valor, rotulo]) => (
                  <option key={valor} value={valor}>
                    {rotulo}
                  </option>
                ))}
              </Selecao>
            )}
            <Selecao
              aria-label="Situação"
              value={situacao}
              onChange={(e) => setSituacao(e.target.value)}
              className="flex-1 basis-36 sm:w-auto sm:flex-none"
            >
              <option value="">Todas as situações</option>
              {Object.entries(SITUACAO).map(([valor, { rotulo }]) => (
                <option key={valor} value={valor}>
                  {rotulo}
                </option>
              ))}
            </Selecao>
          </div>

          <section className="overflow-hidden rounded-xl border border-borda bg-superficie">
            {!visiveis ? (
              <p role="status" className="p-6 text-sm text-suave">
                Carregando…
              </p>
            ) : visiveis.length === 0 ? (
              <p className="p-6 text-sm text-suave">
                {lista?.length || busca || curso || cargo
                  ? "Ninguém encontrado com estes filtros."
                  : `Nenhum ${aba} cadastrado ainda.`}
              </p>
            ) : (
              <ul className="divide-y divide-borda">
                {visiveis.map((u) => (
                  <li
                    key={u.id}
                    // Telas largas: 4 colunas alinhadas entre as linhas. Telas estreitas: os blocos quebram.
                    className="flex flex-wrap items-center gap-x-4 gap-y-3 px-4 py-3.5 xl:grid xl:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)_minmax(0,1.2fr)_18rem]"
                  >
                    <div className="flex min-w-0 flex-1 basis-64 items-center gap-3">
                      <Avatar nome={u.nome} foto={urlFoto(u)} />
                      <div className="min-w-0">
                        <p className="truncate font-medium">{u.nome}</p>
                        <p className="truncate text-sm text-suave">{u.email}</p>
                      </div>
                    </div>

                    <div className="min-w-0 basis-52 text-sm">
                      <p>{u.curso?.nome ?? "Todos os cursos do núcleo"}</p>
                      <p className="text-suave">
                        {u.matricula ? `Matrícula ${u.matricula}` : u.cargo && NOME_CARGO[u.cargo]}
                      </p>
                    </div>

                    <div className="flex basis-56 flex-wrap gap-1.5 xl:basis-auto">
                      {u.tipo === "docente" && u.perfis.map((p) => <Selo key={p}>{NOME_PERFIL[p]}</Selo>)}
                      <Selo cor={SITUACAO[u.situacao].cor}>{SITUACAO[u.situacao].rotulo}</Selo>
                      {u.situacao === "aguardando_ativacao" && u.email_ativacao === "falha" && (
                        <Selo cor="vermelho">E-mail não enviado</Selo>
                      )}
                    </div>

                    {/* Não existe "excluir": o cadastro só pode ser inativado (HU01.08 R6). */}
                    <div className="ml-auto flex flex-wrap justify-end gap-1">
                      {u.situacao === "aguardando_ativacao" && (
                        <Botao
                          variante="texto"
                          pequeno
                          disabled={ocupado}
                          onClick={() =>
                            executar(
                              `/usuarios/${u.id}/reenviar-ativacao`,
                              "POST",
                              `Novo link de ativação enviado para ${u.email}.`,
                            )
                          }
                        >
                          Reenviar ativação
                        </Botao>
                      )}
                      <Botao variante="texto" pequeno onClick={() => setFormulario({ usuario: u })}>
                        Editar
                      </Botao>
                      {u.situacao === "inativo" ? (
                        <Botao
                          variante="texto"
                          pequeno
                          disabled={ocupado}
                          onClick={() => executar(`/usuarios/${u.id}/reativar`, "PATCH", `${u.nome} foi reativado(a).`)}
                        >
                          Reativar
                        </Botao>
                      ) : (
                        u.id !== eu.id && (
                          <Botao variante="perigo" pequeno onClick={() => setInativando(u)}>
                            Inativar
                          </Botao>
                        )
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}

      {formulario && aba !== "area" && (
        <FormularioUsuario
          tipo={formulario.usuario?.tipo ?? aba}
          usuario={formulario.usuario}
          cursos={cursos}
          areas={areas}
          euId={eu.id}
          aoFechar={() => setFormulario(null)}
          aoSalvar={(salvo, criado, fotoFalhou) => {
            setFormulario(null);
            const texto = criado
              ? `${salvo.nome} foi cadastrado(a). O link de ativação vai para ${salvo.email}.`
              : `Dados de ${salvo.nome} atualizados.`;
            setAviso(
              fotoFalhou
                ? { tipo: "alerta", texto: `${texto} A foto não foi enviada: abra Editar e tente de novo.` }
                : { tipo: "sucesso", texto },
            );
            recarregar();
          }}
        />
      )}

      {inativando && (
        <Modal titulo="Inativar cadastro" aoFechar={() => setInativando(null)}>
          <p className="text-sm">
            <strong>{inativando.nome}</strong> não poderá mais entrar no sistema nem receber novas
            atribuições. O cadastro e o histórico são mantidos, e você pode reativar depois.
          </p>
          <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Botao variante="texto" onClick={() => setInativando(null)}>
              Cancelar
            </Botao>
            <Botao
              variante="destrutivo"
              carregando={ocupado}
              onClick={() =>
                executar(`/usuarios/${inativando.id}/inativar`, "PATCH", `${inativando.nome} foi inativado(a).`)
              }
            >
              Inativar
            </Botao>
          </div>
        </Modal>
      )}
    </div>
  );
}
