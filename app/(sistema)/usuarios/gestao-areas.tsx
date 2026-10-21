"use client";

// RBN01.02: a coordenação adiciona, renomeia e exclui áreas de interesse.
// Excluir uma área em uso tira a área dos docentes que a tinham marcado (a API registra quem).

import { useEffect, useState } from "react";
import { Aviso, Selo, type TipoAviso } from "@/components/aviso";
import { Botao } from "@/components/botao";
import { Campo, Entrada } from "@/components/campo";
import { Icone } from "@/components/icone";
import { Modal } from "@/components/modal";
import { api, ErroApi } from "@/lib/api";
import type { AreaUso } from "@/lib/tipos";

export function GestaoAreas() {
  const [areas, setAreas] = useState<AreaUso[] | null>(null);
  const [versao, setVersao] = useState(0);
  const [aviso, setAviso] = useState<{ tipo: TipoAviso; texto: string } | null>(null);
  // Janelas: nova área / renomear (com a área) e confirmação de exclusão.
  const [editando, setEditando] = useState<{ area?: AreaUso } | null>(null);
  const [excluindo, setExcluindo] = useState<AreaUso | null>(null);
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => {
    let ativo = true;
    api<AreaUso[]>("/areas/gestao")
      .then((dados) => ativo && setAreas(dados))
      .catch((e: ErroApi) => ativo && setAviso({ tipo: "erro", texto: e.message }));
    return () => {
      ativo = false;
    };
  }, [versao]);

  async function excluir(area: AreaUso) {
    setOcupado(true);
    try {
      await api(`/areas/${area.id}`, { metodo: "DELETE" });
      setAviso({ tipo: "sucesso", texto: `Área "${area.nome}" excluída.` });
      setVersao((v) => v + 1);
    } catch (e) {
      setAviso({ tipo: "erro", texto: (e as ErroApi).message });
    }
    setOcupado(false);
    setExcluindo(null);
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-suave">
          Docentes escolhem entre estas áreas; propostas de TCC podem ser enviadas para uma área.
        </p>
        <Botao variante="contorno" onClick={() => setEditando({})}>
          <Icone nome="mais" className="size-4" />
          Nova área
        </Botao>
      </div>

      {aviso && <Aviso tipo={aviso.tipo}>{aviso.texto}</Aviso>}

      <section className="overflow-hidden rounded-xl border border-borda bg-superficie">
        {!areas ? (
          <p role="status" className="p-6 text-sm text-suave">
            Carregando…
          </p>
        ) : areas.length === 0 ? (
          <p className="p-6 text-sm text-suave">Nenhuma área cadastrada ainda.</p>
        ) : (
          <ul className="divide-y divide-borda">
            {areas.map((area) => (
              <li key={area.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
                <p className="min-w-0 flex-1 basis-48 font-medium">{area.nome}</p>
                <Selo cor={area.docentes ? "azul" : "cinza"}>
                  {area.docentes === 1 ? "1 docente" : `${area.docentes} docentes`}
                </Selo>
                <div className="ml-auto flex gap-1">
                  <Botao variante="texto" pequeno onClick={() => setEditando({ area })}>
                    Renomear
                  </Botao>
                  <Botao variante="perigo" pequeno onClick={() => setExcluindo(area)}>
                    Excluir
                  </Botao>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {editando && (
        <FormularioArea
          area={editando.area}
          aoFechar={() => setEditando(null)}
          aoSalvar={(salva, criada) => {
            setEditando(null);
            setAviso({
              tipo: "sucesso",
              texto: criada ? `Área "${salva.nome}" criada.` : `Área renomeada para "${salva.nome}".`,
            });
            setVersao((v) => v + 1);
          }}
        />
      )}

      {excluindo && (
        <Modal titulo="Excluir área de interesse" aoFechar={() => setExcluindo(null)}>
          <p className="text-sm">
            A área <strong>{excluindo.nome}</strong> deixará de aparecer nos formulários.
            {excluindo.docentes > 0 &&
              ` Ela será retirada ${
                excluindo.docentes === 1 ? "do docente que a tinha" : `dos ${excluindo.docentes} docentes que a tinham`
              } marcada.`}{" "}
            A exclusão fica registrada no log.
          </p>
          <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
            <Botao variante="texto" onClick={() => setExcluindo(null)}>
              Cancelar
            </Botao>
            <Botao variante="destrutivo" carregando={ocupado} onClick={() => excluir(excluindo)}>
              Excluir
            </Botao>
          </div>
        </Modal>
      )}
    </div>
  );
}

type PropsFormulario = {
  area?: AreaUso; // preenchida = renomear
  aoSalvar: (salva: AreaUso, criada: boolean) => void;
  aoFechar: () => void;
};

function FormularioArea({ area, aoSalvar, aoFechar }: PropsFormulario) {
  const [nome, setNome] = useState(area?.nome ?? "");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function salvar(evento: React.SyntheticEvent) {
    evento.preventDefault();
    if (nome.trim().length < 2) return setErro("Informe o nome da área.");
    setErro("");
    setEnviando(true);
    try {
      const salva = area
        ? await api<AreaUso>(`/areas/${area.id}`, { metodo: "PUT", corpo: { nome } })
        : await api<AreaUso>("/areas", { metodo: "POST", corpo: { nome } });
      aoSalvar(salva, !area);
    } catch (e) {
      const falha = e as ErroApi;
      setErro(falha.campos?.nome ?? falha.message);
      setEnviando(false);
    }
  }

  return (
    <Modal titulo={area ? "Renomear área" : "Nova área de interesse"} aoFechar={aoFechar}>
      <form onSubmit={salvar} noValidate className="flex flex-col gap-5">
        <Campo rotulo="Nome da área" obrigatorio erro={erro}>
          <Entrada
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            erro={erro}
            maxLength={100}
            placeholder="Ex.: Computação Gráfica"
            autoFocus
          />
        </Campo>
        <div className="flex flex-col-reverse gap-2 border-t border-borda pt-4 sm:flex-row sm:justify-end">
          <Botao variante="texto" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao type="submit" carregando={enviando}>
            {area ? "Salvar" : "Criar área"}
          </Botao>
        </div>
      </form>
    </Modal>
  );
}
