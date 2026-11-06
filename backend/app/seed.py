"""Carga inicial mínima para desenvolvimento: python -m app.seed

Aplica as migrações (cria ou atualiza as tabelas), depois cria o núcleo, os três
cursos, as áreas de interesse, os perfis e o primeiro coordenador. Pode ser
rodado mais de uma vez.

Com --demo, cria também uma conta pronta por perfil (já ativa, senha Siga@2026),
para testar e apresentar sem depender do link de ativação:
    python -m app.seed --demo
Não use --demo no servidor de produção.

O primeiro coordenador nasce como qualquer usuário: sem senha. O script imprime
o link de ativação para você abrir no navegador e definir a senha.

O esquema do banco vem das migrações em migrations/ (Alembic), e não de
create_all, para o PostgreSQL de produção e o SQLite de desenvolvimento terem
exatamente as mesmas tabelas.
"""

import os
import sys

from sqlalchemy import select

from app import config
from app.database import SessionLocal
from app.migracoes import atualizar_banco
from app.security import gerar_hash_senha
from app.models import (
    PERFIL_ALUNO,
    PERFIL_BANCA,
    PERFIL_COORDENADOR,
    PERFIL_ORIENTADOR,
    PERFIL_PROFESSOR,
    PERFIS,
    TOKEN_ATIVACAO,
    MATRICULADO,
    PONTOS_ESCRITA,
    PONTOS_ORAL,
    Aluno,
    AreaInteresse,
    ComponenteAvaliacao,
    CriterioAvaliacao,
    Curso,
    Docente,
    InstrumentoAvaliacao,
    MatriculaTurma,
    Nucleo,
    Perfil,
    PeriodoLetivo,
    Turma,
    Usuario,
    UsuarioPerfil,
)
from app.services import tokens
from app.services.usuarios import buscar_por_email

CURSOS = [
    ("EC", "Engenharia de Computação"),
    ("LC", "Licenciatura em Computação"),
    ("SI", "Sistemas de Informação"),
]
AREAS = [
    "IA",
    "Engenharia de Software",
    "Governança de TI",
    "Ciência de Dados",
    "Segurança da Informação",
    "Sistemas de Informação",
]


def carregar_base(db) -> Nucleo:
    """Núcleo, cursos, áreas e perfis. Só insere o que ainda não existe."""
    nucleo = db.scalar(select(Nucleo).where(Nucleo.sigla == "NUCOMP"))
    if nucleo is None:
        nucleo = Nucleo(sigla="NUCOMP", nome="Núcleo de Computação")
        db.add(nucleo)
        db.flush()
    for sigla, nome in CURSOS:
        if not db.scalar(select(Curso).where(Curso.sigla == sigla)):
            db.add(Curso(sigla=sigla, nome=nome, nucleo_id=nucleo.id))
    for nome in AREAS:
        if not db.scalar(select(AreaInteresse).where(AreaInteresse.nome == nome)):
            db.add(AreaInteresse(nome=nome))
    for codigo, nome in PERFIS.items():
        if not db.scalar(select(Perfil).where(Perfil.codigo == codigo)):
            db.add(Perfil(codigo=codigo, nome=nome))
    db.flush()
    return nucleo


def criar_coordenador(db, nucleo: Nucleo, nome: str, email: str) -> Usuario:
    usuario = Usuario(nome=nome, email=email.lower())
    db.add(usuario)
    db.flush()
    db.add(Docente(usuario_id=usuario.id, cargo="coordenador", nucleo_id=nucleo.id))
    for codigo in (PERFIL_COORDENADOR, PERFIL_PROFESSOR):
        perfil = db.scalar(select(Perfil).where(Perfil.codigo == codigo))
        db.add(UsuarioPerfil(usuario_id=usuario.id, perfil_id=perfil.id))
    return usuario


# Versão 1 do instrumento de avaliação (RBN10.01): a planilha de avaliação de TCC usada pela
# coordenação (abas Avaliação_Orientador e Nome_Avaliador), com os erros de digitação corrigidos.
# (componente, pontos, [(critério, peso, texto Exemplar, texto Competente, texto Necessita de Trabalho)])
INSTRUMENTO_V1 = [
    (
        "Parte escrita",
        PONTOS_ESCRITA,
        [
            (
                "Relevância do tema",
                0.5,
                (
                    "1. O tema tem relevância científica e aborda conteúdos e/ou pesquisas relacionadas ao estado da arte na área da Computação;\n"
                    "2. O conteúdo do trabalho foi focado no tema e com profundidade adequada para um pleno entendimento do problema abordado;\n"
                    "3. O tema conjuga de maneira não-trivial diferentes habilidades desenvolvidas pelo estudante ao longo do curso."
                ),
                (
                    "1. A apresentação do tema não é embasada por argumentos que permitam destacar a sua relevância nem tampouco sua relação com a área da Computação;\n"
                    "2. Em algumas ocasiões, não ficou clara a relação entre o conteúdo do trabalho e o tema proposto, podendo esta apresentação ter sido superficial ou pouco coesa para prover um bom entendimento do problema abordado;\n"
                    "3. O tema conjuga múltiplas habilidades desenvolvidas pelo estudante ao longo do curso;"
                ),
                (
                    "1. Há uma dissociação entre o tema e o seu embasamento, de tal modo que não é possível identificar sua relevância e possíveis contribuições para a área da Computação;\n"
                    "2. O conteúdo do trabalho foge ao tema proposto;\n"
                    "3. O tema conjuga superficialmente habilidades pontuais desenvolvidas pelo estudante ao longo do curso."
                ),
            ),
            (
                "Metodologia",
                2.0,
                (
                    "Metodologia está bem descrita, aderente aos objetivos propostos e com justificativas pautadas em critérios técnico-científicos."
                ),
                (
                    "Metodologia está regular, pouco aderente aos objetivos propostos e com significativa necessidade de melhorias nas justificativas."
                ),
                (
                    "Metodologia está severamente aquém da qualidade necessária e incompatível com o nível de formação almejado."
                ),
            ),
            (
                "Revisão da literatura (referencial teórico, trabalhos correlatos, referências bibliográficas)",
                1.0,
                (
                    "1. O documento apresenta revisão bibliográfica focada no tema e de profundidade adequada para o entendimento do trabalho;\n"
                    "2. Apresenta seção de trabalhos relacionados, em quantidade adequada e comparando qualitativa e quantitativamente as características e resultados dos trabalhos correlatos;\n"
                    "3. Há entendimento das normas de ABNT, sobretudo é possível verificar o emprego correto para citações e indicações de referências correlatas."
                ),
                (
                    "1. Demonstra fundamento, porém a capacidade conceitual e articulação teórico-metodológica (ou teórico-prática) carece de melhorias;\n"
                    "2. Apresenta seção de trabalhos relacionados, com quantidade adequada, porém necessita de um aprofundamento nos aspectos comparativos de ordem qualitativa e quantitativa;\n"
                    "3. As referências adotadas, em certa medida, são adequadas e com certa atualidade, mas não foram muito além em termos de representatividade."
                ),
                (
                    "1. A revisão bibliográfica é superficial ao tema, carecendo de conceitos elementares para o entendimento do trabalho;\n"
                    "2. Compreende poucos trabalhos correlatos ou é inexistente, sendo insuficiente para o tema considerado;\n"
                    "3. As referências adotadas são pouco adequadas, antigas e/ou insuficientes para sustentar o trabalho. Também há indícios de desleixo com relação às normas da ABNT."
                ),
            ),
            (
                "Resultados e discussões",
                2.0,
                (
                    "Os resultados estão detalhados, mostram-se compatíveis com o prazo de desenvolvimento e condizentes com a metodologia apresentada."
                ),
                (
                    "Os resultados apresentados são regulares, mostrando-se limitados dado o prazo de desenvolvimento e/ou a metodologia apresentados."
                ),
                (
                    "Não há evidências da obtenção dos resultados propostos para o prazo de desenvolvimento."
                ),
            ),
            (
                "Conclusões",
                0.5,
                (
                    "As conclusões apresentadas são fortemente coerentes com o trabalho desenvolvido e contemplam uma análise crítica e comparativa das suas vantagens e limitações.\n"
                    "\n"
                    "As sugestões para as próximas etapas do trabalho ou pesquisas futuras são resultado de uma reflexão bem pautada em critérios técnico-científicos."
                ),
                (
                    "As conclusões apresentadas são limitadas para descrever o trabalho desenvolvido, com grande potencial de melhoria na análise crítica e comparativa das vantagens e limitações.\n"
                    "\n"
                    "As próximas etapas do trabalho precisam ser delicadamente revistas em face do cronograma disponível e/ou de critérios técnico-científicos."
                ),
                (
                    "As considerações estão severamente aquém da qualidade necessária e são incompatíveis com o nível de formação almejado."
                ),
            ),
            (
                "Redação",
                1.0,
                (
                    "1. Escrito de forma organizada e sistemática, e há evidências de esforço dos autores para a elaboração de um texto que se preocupa com a compreensão do leitor;\n"
                    "2. As informações são apresentadas de forma clara e explicitamente relacionadas aos aspectos que o texto dá suporte;\n"
                    "3. Atende às boas práticas de comunicação escrita (linguagem, pontuação, ortografia, encadeamento das ideias, etc.); é organizado de forma lógica, facilitando a leitura, compreensão e localização de informações;\n"
                    "4. Há aspectos a serem corrigidos e melhorados, mas o trabalho demonstra habilidade acima da média e atenção aos detalhes."
                ),
                (
                    "1. O texto possui uma organização, porém apresenta algumas imprecisões que dificultam a compreensão do leitor;\n"
                    "2. É possível observar qualidade técnica no texto, mas há perdas de conexões entre os aspectos que deveriam sustentar o trabalho;\n"
                    "3. A apresentação das informações carece de melhorias, ou porque faltou clareza ou porque apresentou algumas lacunas na forma de relacionar explicitamente as informações aos aspectos estabelecidos na análise.\n"
                    "4. O trabalho está na média, mas exigirá um pouco mais de esforço para deixá-lo no nível Exemplar."
                ),
                (
                    "1. A escrita apresenta muitas faltas, dificultando a compreensão do leitor;\n"
                    "2. O texto possui baixa qualidade técnica, com frequentes perdas de conexões entre os aspectos que deveriam sustentar o trabalho, podendo ser impreciso até mesmo no foco adotado;\n"
                    "3. É pouco fundamentado, e demonstra muitas carências na capacidade conceitual e articulação teórico-metodológica (ou teórico-prática).\n"
                    "4. O trabalho está severamente aquém da qualidade necessária para o nível de formação almejado."
                ),
            ),
        ],
    ),
    (
        "Parte oral",
        PONTOS_ORAL,
        [
            (
                "Organização (sequência lógica, qualidade do material e da apresentação, aproveitamento do tempo)",
                1.0,
                (
                    "1. Organizou e encadeou as ideias com conectores adequados e diversificados, sem repetições;\n"
                    "2. Apresentou conjunto de slides com adequado conteúdo de informações a serem comunicadas, ótima qualidade e padronização dos textos e imagens;\n"
                    "3. A apresentação fluiu conforme uma ótima sequência lógica de apresentação das informações;\n"
                    "4. Realizou a apresentação em tempo igual ou muito próximo ao tempo total disponível."
                ),
                (
                    "1. Organizou e encadeou as ideias com poucos conectores e/ou com repetições, mas sem comprometer a compreensão do conteúdo;\n"
                    "2. Apesar de alguns slides com problemas de qualidade visual e padronização, não houve prejuízo à compreensão do conteúdo;\n"
                    "3. Houve desvios na sua sequência lógica, mas o entendimento não foi prejudicado. Eventualmente houve desproporcionalidade na exposição de alguns conteúdos;\n"
                    "4. A apresentação foi além ou aquém do tempo disponível, eventualmente houve leitura do conteúdo dos slides, mas tais aspectos não comprometeram a apresentação como um todo."
                ),
                (
                    "1. Não organizou nem encadeou as ideias com uso de conectores, limitando-se a justapor ideias de forma desarticulada e confusa;\n"
                    "2. Apresentou conjunto de slides com total ausência de qualidade visual e padronização, contendo excesso de texto e incluindo imagens de baixa qualidade ou ilegíveis. Houve grave prejuízo ao acompanhamento da apresentação e ao entendimento do conteúdo;\n"
                    "3. A apresentação oral deu-se majoritariamente por meio da leitura dos slides. Houve ausência de proporcionalidade entre a importância e volume de cada assunto;\n"
                    "4. Realizou a apresentação de forma negligente, subutilizando o tempo disponível ou extrapolando-o, o que neste segundo caso impediu a conclusão da apresentação."
                ),
            ),
            (
                "Domínio do assunto",
                1.5,
                (
                    "1. Organiza e encadeia as ideias com conectores adequados e diversificados, sem repetições.\n"
                    "2. Expressa-se oralmente sem recurso à leitura dos slides.\n"
                    "\n"
                    "1. Adota uma atitude adequada, com gestos e expressões faciais coerentes e expressivos, que cativam a atenção do auditório e que reforçam a mensagem transmitida.\n"
                    "2. Emprega um tom de voz audível e com entoação expressiva.\n"
                    "3. Utiliza um estilo de linguagem (coloquial, literário ou técnico) adequado à (ao) situação/tema."
                ),
                (
                    "1. Organiza e encadeia as ideias com recurso a conectores geralmente adequados, embora pouco diversificados e com repetições.\n"
                    "2. Expressa-se oralmente recorrendo algumas vezes à leitura dos slides.\n"
                    "\n"
                    "1. Adota uma atitude geralmente adequada, com gestos e expressões faciais coerentes, ainda que pouco expressivas, que cativam pontualmente a atenção do auditório.\n"
                    "2. Emprega um tom de voz audível e, pontualmente, com entoação expressiva.\n"
                    "3. Utiliza um estilo de linguagem (coloquial, literário ou técnico) globalmente adequado à(ao) situação/tema, ainda que com falhas pontuais."
                ),
                (
                    "1. Não organiza nem encadeia as ideias com recurso a conectores, limitando-se a justapor ideias de forma desarticulada e confusa.\n"
                    "2. Expressa-se oralmente com recurso exclusivo à leitura dos slides.\n"
                    "\n"
                    "Adota uma atitude não adequada, negligente ou provocadora; ou emprega um tom de voz imperceptível ou estridente; ou utiliza um estilo de linguagem (coloquial, literário ou técnico) inadequado à(ao) situação/tema."
                ),
            ),
            (
                "Postura perante a banca",
                0.5,
                (
                    "1. Compreendeu perfeitamente as arguições conseguindo respondê-las de imediato com propriedade, segurança, usando termos técnico-científicos corretos e adequados;\n"
                    "\n"
                    "2. Demonstrou atitude positiva perante a banca, colocando-se à disposição para responder questionamentos de forma coerente e respeitosa;\n"
                    "\n"
                    "3. Demonstrou maturidade em compreender as sugestões de melhorias e/ou apontamento de erros feitos pela banca;\n"
                    "\n"
                    "4. Aceitou as considerações dos avaliadores de maneira respeitosa e esclareceu suas dúvidas de forma clara, objetiva e com segurança;\n"
                    "\n"
                    "5. Não realizou interrupções fora do tempo;"
                ),
                (
                    "1. Precisou de intervenção do orientador para compreender algumas arguições, mas conseguiu responder de forma satisfatória;\n"
                    "\n"
                    "2. Demonstrou pouca resistência em aceitar as considerações da banca;\n"
                    "\n"
                    "3. Demonstrou compreender a maioria das sugestões de melhorias e possíveis erros apontados pela banca.\n"
                    "\n"
                    "4. Realizou mais de uma interrupção fora do tempo."
                ),
                (
                    "1. Apesar da intervenção do orientador para compreender todas as arguições, não conseguiu respondê-las;\n"
                    "\n"
                    "2. Demonstrou atitude negativa perante a banca, colocando-se em posição defensiva e/ou agressiva;\n"
                    "\n"
                    "3. Interrompeu diversas vezes os arguidores de forma desrespeitosa;\n"
                    "\n"
                    "4. Insistiu em defender suas ideias em relação ao trabalho, ainda que a banca tenha considerado insatisfatório."
                ),
            ),
        ],
    ),
]


def carregar_instrumento(db, autor: Usuario) -> InstrumentoAvaliacao:
    """Versão 1 do instrumento, vigente, com o primeiro coordenador como autor (criado_por é
    obrigatório, por isso a carga fica aqui e não na migração). Só cria se não houver nenhuma versão."""
    instrumento = db.scalar(
        select(InstrumentoAvaliacao).order_by(InstrumentoAvaliacao.versao))
    if instrumento is not None:
        return instrumento
    instrumento = InstrumentoAvaliacao(
        versao=1, vigente=True, criado_por=autor.id)
    db.add(instrumento)
    db.flush()
    for ordem_c, (nome, pontos, criterios) in enumerate(INSTRUMENTO_V1, start=1):
        componente = ComponenteAvaliacao(
            instrumento_id=instrumento.id, nome=nome, pontos=pontos, ordem=ordem_c)
        db.add(componente)
        db.flush()
        for ordem, (criterio, peso, exemplar, competente, necessita) in enumerate(criterios, start=1):
            db.add(
                CriterioAvaliacao(
                    componente_id=componente.id,
                    nome=criterio,
                    peso=peso,
                    texto_exemplar=exemplar,
                    texto_competente=competente,
                    texto_necessita=necessita,
                    ordem=ordem,
                )
            )
    db.flush()
    return instrumento


SENHA_DEMO = "Siga@2026"
# (nome, e-mail, cargo do docente ou None para aluno, perfis)
CONTAS_DEMO = [
    ("Carla Coordenadora", "coordenador@exemplo.com",
     "coordenador", [PERFIL_COORDENADOR]),
    ("Paulo Professor", "professor@exemplo.com",
     "professor", [PERFIL_PROFESSOR]),
    ("Olga Orientadora", "orientador@exemplo.com",
     "orientador", [PERFIL_ORIENTADOR]),
    ("Bruno Banca", "banca@exemplo.com", "professor", [PERFIL_BANCA]),
    ("Ana Aluna", "aluno@exemplo.com", None, [PERFIL_ALUNO]),
]


def criar_contas_demo(db, nucleo: Nucleo) -> None:
    curso = db.scalar(select(Curso).where(Curso.sigla == "EC"))
    senha_hash = gerar_hash_senha(SENHA_DEMO)
    print(f"Contas de demonstração (senha de todas: {SENHA_DEMO}):")
    for nome, email, cargo, perfis in CONTAS_DEMO:
        if buscar_por_email(db, email) is None:
            usuario = Usuario(nome=nome, email=email,
                              senha_hash=senha_hash, ativo=True)
            db.add(usuario)
            db.flush()
            if cargo:
                # Coordenador acessa todos os cursos; os demais docentes ficam em EC.
                curso_id = None if cargo == "coordenador" else curso.id
                db.add(
                    Docente(
                        usuario_id=usuario.id, cargo=cargo, nucleo_id=nucleo.id, curso_id=curso_id
                    )
                )
            else:
                db.add(Aluno(usuario_id=usuario.id,
                       matricula="2026000001", curso_id=curso.id))
            for codigo in perfis:
                perfil = db.scalar(
                    select(Perfil).where(Perfil.codigo == codigo))
                db.add(UsuarioPerfil(usuario_id=usuario.id, perfil_id=perfil.id))
        print(f"  {email:<26} {', '.join(PERFIS[p] for p in perfis)}")
    db.flush()
    criar_turma_demo(db, curso)
    print()


def criar_turma_demo(db, curso: Curso) -> None:
    """Período 2026/2, turma TCC1 do professor de demonstração e a aluna matriculada,
    para o cadastro de TCC (Sprint S03) já poder ser testado."""
    from datetime import date

    periodo = db.scalar(select(PeriodoLetivo).where(
        PeriodoLetivo.codigo == "2026/2"))
    if periodo is None:
        periodo = PeriodoLetivo(codigo="2026/2", inicio=date(2026, 8, 1), fim=date(2026, 12, 20),
                                prazo_versao_final=date(2026, 12, 11))
        db.add(periodo)
        db.flush()
    professor = buscar_por_email(db, "professor@exemplo.com")
    aluno = buscar_por_email(db, "aluno@exemplo.com")
    codigo = f"TCC1-{curso.sigla}-{periodo.codigo}-1"
    turma = db.scalar(select(Turma).where(Turma.codigo == codigo))
    if turma is None:
        turma = Turma(codigo=codigo, disciplina="TCC1", curso_id=curso.id, periodo_id=periodo.id,
                      professor_id=professor.id)
        db.add(turma)
        db.flush()
    if not db.scalar(select(MatriculaTurma).where(MatriculaTurma.turma_id == turma.id,
                                                  MatriculaTurma.aluno_id == aluno.id)):
        db.add(MatriculaTurma(turma_id=turma.id, aluno_id=aluno.id,
               situacao=MATRICULADO, incluido_por=professor.id))
    print(
        f"  Turma {codigo} (período {periodo.codigo}) com aluno@exemplo.com matriculada.")


def main() -> None:
    atualizar_banco()
    nome = os.environ.get("SEED_COORDENADOR_NOME", "Coordenação NUCOMP")
    email = os.environ.get("SEED_COORDENADOR_EMAIL", "coordenacao@uea.edu.br")

    with SessionLocal() as db:
        nucleo = carregar_base(db)
        usuario = buscar_por_email(db, email)
        if usuario is None:
            usuario = criar_coordenador(db, nucleo, nome, email)
        carregar_instrumento(db, usuario)
        if usuario.senha_hash is None:
            token = tokens.criar(db, usuario, TOKEN_ATIVACAO)
            print(f"\nPrimeiro coordenador: {usuario.email}")
            print("Abra o link abaixo para definir a senha (vale 48 horas):")
            print(f"{config.FRONTEND_URL}/ativar?token={token}\n")
        else:
            print(
                f"\nCarga inicial conferida. Coordenador já ativo: {usuario.email}\n")
        if "--demo" in sys.argv:
            criar_contas_demo(db, nucleo)
        db.commit()


if __name__ == "__main__":
    main()
