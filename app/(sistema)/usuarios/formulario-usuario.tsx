"use client";

// Formulário de cadastro e de edição de docente (HU01.01) e de aluno (HU01.03).
// Em edição (HU01.08) os mesmos campos são enviados por PUT /usuarios/{id}.

import { useEffect, useMemo, useState } from "react";
import { Aviso } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Avatar } from "@/components/avatar";
import { Campo, Entrada, Selecao } from "@/components/campo";
import { Modal } from "@/components/modal";
import { api, ErroApi } from "@/lib/api";
import { MENSAGEM_TELEFONE, soTelefone, telefoneValido } from "@/lib/telefone";
import {
  FOTO_TIPOS,
  NOME_CARGO,
  NOME_PERFIL,
  PERFIS_DOCENTE,
  problemaNaFoto,
  urlFoto,
  type Area,
  type Cargo,
  type Curso,
  type Perfil,
  type Usuario,
} from "@/lib/tipos";

type Props = {
  tipo: "docente" | "aluno";
  usuario?: Usuario; // preenchido = edição
  cursos: Curso[];
  areas: Area[];
  euId: number;
  // fotoFalhou: os dados foram salvos, mas a foto não chegou à API.
  aoSalvar: (salvo: Usuario, criado: boolean, fotoFalhou?: boolean) => void;
  aoFechar: () => void;
};

type Erros = Record<string, string>;

export function FormularioUsuario({ tipo, usuario, cursos, areas, euId, aoSalvar, aoFechar }: Props) {
  const docente = tipo === "docente";
  const editando = usuario !== undefined;
  const souEu = usuario?.id === euId;

  const [nome, setNome] = useState(usuario?.nome ?? "");
  const [email, setEmail] = useState(usuario?.email ?? "");
  const [telefone, setTelefone] = useState(usuario?.telefone ?? "");
  const [matricula, setMatricula] = useState(usuario?.matricula ?? "");
  const [cursoId, setCursoId] = useState(usuario?.curso ? String(usuario.curso.id) : "");
  const [cargo, setCargo] = useState<Cargo>(usuario?.cargo ?? "professor");
  const [perfis, setPerfis] = useState<Perfil[]>(usuario?.perfis ?? ["orientador"]);
  const [areasIds, setAreasIds] = useState<number[]>(usuario?.areas.map((a) => a.id) ?? []);
  const [foto, setFoto] = useState<File | null>(null);
  // Pré-visualização da foto escolhida, antes de enviar. Liberada quando troca ou fecha.
  const previa = useMemo(() => (foto ? URL.createObjectURL(foto) : null), [foto]);
  useEffect(() => () => {
    if (previa) URL.revokeObjectURL(previa);
  }, [previa]);
  const [erros, setErros] = useState<Erros>({});
  const [erroGeral, setErroGeral] = useState("");
  const [enviando, setEnviando] = useState(false);

  // HU01.01 A2: com o perfil coordenador marcado, o curso deixa de ser obrigatório.
  const cursoObrigatorio = !docente || !perfis.includes("coordenador");

  function alternar<T>(lista: T[], item: T) {
    return lista.includes(item) ? lista.filter((x) => x !== item) : [...lista, item];
  }

  function validar(): Erros {
    const e: Erros = {};
    if (nome.trim().length < 3) e.nome = "Informe o nome completo.";
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) e.email = "Informe um e-mail válido.";
    if (docente && !telefoneValido(telefone)) e.telefone = MENSAGEM_TELEFONE;
    if (cursoObrigatorio && !cursoId) e.curso_id = "Escolha o curso.";
    if (docente && perfis.length === 0) e.perfis = "Marque ao menos um perfil.";
    if (!docente && !/^\d{6,20}$/.test(matricula)) e.matricula = "Use só números (6 a 20 dígitos).";
    return e;
  }

  async function salvar(evento: React.SyntheticEvent) {
    evento.preventDefault();
    setErroGeral("");
    const encontrados = validar();
    setErros(encontrados);
    if (Object.keys(encontrados).length) return; // E1: destaca os campos e não salva

    const corpo = docente
      ? {
          nome,
          email,
          telefone,
          cargo,
          curso_id: cursoId ? Number(cursoId) : null,
          areas: areasIds,
          // Ninguém altera os próprios perfis (HU01.01 R2), então nem enviamos.
          ...(souEu ? {} : { perfis }),
        }
      : { nome, email, matricula, curso_id: Number(cursoId) };

    setEnviando(true);
    try {
      let salvo = editando
        ? await api<Usuario>(`/usuarios/${usuario.id}`, { metodo: "PUT", corpo })
        : await api<Usuario>(docente ? "/docentes" : "/alunos", { metodo: "POST", corpo });
      let fotoFalhou = false;
      if (foto) {
        // A foto vai depois dos dados: se falhar, o cadastro já está salvo e dá para tentar de novo.
        const formulario = new FormData();
        formulario.append("foto", foto);
        try {
          salvo = await api<Usuario>(`/usuarios/${salvo.id}/foto`, { metodo: "PUT", corpo: formulario });
        } catch {
          fotoFalhou = true;
        }
      }
      aoSalvar(salvo, !editando, fotoFalhou);
    } catch (e) {
      const erro = e as ErroApi;
      // O formulário continua preenchido; só marcamos o que a API recusou.
      if (erro.campos) setErros(erro.campos);
      else if (erro.campo) setErros({ [erro.campo]: erro.message });
      else setErroGeral(erro.message);
      setEnviando(false);
    }
  }

  const titulo = `${editando ? "Editar" : "Novo"} ${docente ? "docente" : "aluno"}`;

  return (
    <Modal titulo={titulo} aoFechar={aoFechar} largo>
      <form onSubmit={salvar} noValidate className="flex flex-col gap-5">
        {erroGeral && <Aviso tipo="erro">{erroGeral}</Aviso>}

        <div className="grid gap-4 sm:grid-cols-2">
          <Campo rotulo="Nome completo" obrigatorio erro={erros.nome} className="sm:col-span-2">
            <Entrada value={nome} onChange={(e) => setNome(e.target.value)} erro={erros.nome} maxLength={150} />
          </Campo>

          <Campo rotulo="E-mail" obrigatorio erro={erros.email}>
            <Entrada
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              erro={erros.email}
              placeholder="nome@exemplo.com"
            />
          </Campo>

          {docente ? (
            <Campo rotulo="Telefone" dica="opcional" erro={erros.telefone}>
              <Entrada
                type="tel"
                inputMode="tel"
                value={telefone}
                onChange={(e) => setTelefone(soTelefone(e.target.value))}
                erro={erros.telefone}
                placeholder="(92) 90000-0000"
                maxLength={20}
              />
            </Campo>
          ) : (
            <Campo rotulo="Matrícula" obrigatorio erro={erros.matricula}>
              <Entrada
                inputMode="numeric"
                value={matricula}
                // Máscara simples: só aceita dígitos.
                onChange={(e) => setMatricula(e.target.value.replace(/\D/g, "").slice(0, 20))}
                erro={erros.matricula}
              />
            </Campo>
          )}

          {docente && (
            <Campo rotulo="Cargo" obrigatorio erro={erros.cargo}>
              <Selecao value={cargo} onChange={(e) => setCargo(e.target.value as Cargo)}>
                {Object.entries(NOME_CARGO).map(([valor, rotulo]) => (
                  <option key={valor} value={valor}>
                    {rotulo}
                  </option>
                ))}
              </Selecao>
            </Campo>
          )}

          <Campo
            rotulo="Curso"
            obrigatorio={cursoObrigatorio}
            dica="opcional para coordenador"
            erro={erros.curso_id}
          >
            <Selecao value={cursoId} onChange={(e) => setCursoId(e.target.value)} erro={erros.curso_id}>
              <option value="">{cursoObrigatorio ? "Escolha…" : "Todos os cursos do núcleo"}</option>
              {cursos.map((curso) => (
                <option key={curso.id} value={curso.id}>
                  {curso.nome}
                </option>
              ))}
            </Selecao>
          </Campo>
        </div>

        {docente && (
          <>
            <div className="flex items-center gap-4 text-sm">
              <Avatar
                nome={nome || "?"}
                foto={previa ?? (usuario ? urlFoto(usuario) : null)}
                tamanho="grande"
              />
              <div className="flex min-w-0 flex-col gap-1">
                <label className="w-fit cursor-pointer font-medium text-azul-forte hover:underline">
                  {foto || usuario?.foto_versao ? "Trocar foto" : "Adicionar foto"}
                  <input
                    type="file"
                    accept={FOTO_TIPOS.join(",")}
                    className="sr-only"
                    onChange={(e) => {
                      const arquivo = e.target.files?.[0];
                      if (!arquivo) return;
                      const problema = problemaNaFoto(arquivo);
                      setErros({ ...erros, foto: problema ?? "" });
                      setFoto(problema ? null : arquivo);
                    }}
                  />
                </label>
                {erros.foto ? (
                  <span role="alert" className="text-[13px] font-medium text-vermelho">
                    {erros.foto}
                  </span>
                ) : (
                  <span className="text-[13px] text-suave">Opcional. JPG, PNG ou WebP, até 5 MB.</span>
                )}
              </div>
            </div>

            <fieldset className="flex flex-col gap-2 text-sm" disabled={souEu}>
              <legend className="mb-2 font-medium">
                Perfis de acesso <span className="text-vermelho">*</span>
              </legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {PERFIS_DOCENTE.map((perfil) => (
                  <label
                    key={perfil}
                    className="flex cursor-pointer items-center gap-2.5 rounded-lg border border-borda px-3 py-2.5 has-checked:border-azul has-checked:bg-azul-claro has-disabled:cursor-not-allowed has-disabled:opacity-60"
                  >
                    <input
                      type="checkbox"
                      checked={perfis.includes(perfil)}
                      onChange={() => setPerfis(alternar(perfis, perfil))}
                      className="size-4 accent-azul"
                    />
                    {NOME_PERFIL[perfil]}
                  </label>
                ))}
              </div>
              {souEu && <p className="text-[13px] text-suave">Você não pode alterar os seus próprios perfis.</p>}
              {erros.perfis && (
                <p role="alert" className="text-[13px] font-medium text-vermelho">
                  {erros.perfis}
                </p>
              )}
            </fieldset>

            <fieldset className="text-sm">
              <legend className="mb-2 font-medium">
                Áreas de interesse <span className="font-normal text-suave">(opcional)</span>
              </legend>
              <div className="flex flex-wrap gap-2">
                {areas.map((area) => {
                  const marcada = areasIds.includes(area.id);
                  return (
                    <button
                      key={area.id}
                      type="button"
                      aria-pressed={marcada}
                      onClick={() => setAreasIds(alternar(areasIds, area.id))}
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
          </>
        )}

        {!editando && (
          <p className="text-[13px] text-suave">
            A conta é criada sem senha. A pessoa recebe por e-mail um link de ativação, válido por 48
            horas, e define a própria senha.
          </p>
        )}

        <div className="flex flex-col-reverse gap-2 border-t border-borda pt-4 sm:flex-row sm:justify-end">
          <Botao variante="texto" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao type="submit" carregando={enviando}>
            {editando ? "Salvar alterações" : "Salvar e enviar ativação"}
          </Botao>
        </div>
      </form>
    </Modal>
  );
}
