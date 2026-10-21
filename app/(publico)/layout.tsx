import { Marca } from "@/components/marca";

const CURSOS = ["Engenharia de Computação", "Licenciatura em Computação", "Sistemas de Informação"];

// Moldura das telas de acesso (TEL01): faixa azul de apresentação + formulário.
export default function LayoutPublico({ children }: { children: React.ReactNode }) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-azul p-12 text-white lg:flex">
        {/* Círculos decorativos, no espírito dos cabeçalhos do Google Sala de Aula */}
        <span aria-hidden="true" className="absolute -right-24 -bottom-32 size-96 rounded-full bg-white/10" />
        <span aria-hidden="true" className="absolute right-28 bottom-36 size-40 rounded-full bg-white/10" />
        <span aria-hidden="true" className="absolute -top-16 -left-16 size-56 rounded-full bg-azul-forte/60" />

        <div className="relative">
          <Marca clara />
        </div>
        <div className="relative max-w-md">
          <h1 className="text-4xl leading-tight font-semibold text-balance">
            O TCC inteiro em um só lugar, do cadastro à defesa.
          </h1>
          <p className="mt-4 text-white/85">
            Sistema de gestão de Trabalhos de Conclusão de Curso do NUCOMP, na Escola Superior de
            Tecnologia da UEA.
          </p>
          <ul className="mt-6 flex flex-wrap gap-2 text-sm">
            {CURSOS.map((curso) => (
              <li key={curso} className="rounded-full bg-white/15 px-3 py-1">
                {curso}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-sm text-white/75">Universidade do Estado do Amazonas · Manaus</p>
      </aside>

      <main className="flex flex-col items-center justify-center px-4 py-10">
        <div className="mb-8 lg:hidden">
          <Marca />
        </div>
        <div className="w-full max-w-sm">{children}</div>
      </main>
    </div>
  );
}
