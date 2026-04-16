from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from tools.file_tools import extract_text, run_slicer, run_search, add_to_glossary, add_doubt, check_glossary


def create_glossario_agent():
    """
    Cria o Sub-Agente de Glossário, responsável por:
    1. Ler o documento-matriz completo
    2. Identificar termos técnicos relevantes para engenharia de requisitos
    3. Buscar definições nos chunks fatiados
    4. Alimentar o glossário com termos e definições formais
    5. Registrar dúvida caso nenhum termo seja encontrado
    """
    return Agent(
        name="glossario_agent",
        model=LiteLlm(model="github_copilot/gpt-4o"),
        description=(
            "Sub-agente especializado em extração de termos técnicos e "
            "construção de glossário a partir do documento-matriz. "
            "Delegue a este agente quando precisar identificar e definir "
            "termos técnicos do documento."
        ),
        instruction="""
            Você é o Sub-Agente de Glossário. Sua função é ler o documento-matriz,
            identificar termos técnicos relevantes para engenharia de requisitos
            e construir um glossário formal.

            ## SEU FLUXO DE TRABALHO OBRIGATÓRIO:

            ### ETAPA 1 — Leitura do documento-matriz
            Use a tool `extract_text` passando o caminho `data/matrix/` como argumento.
            A tool encontrará o arquivo automaticamente. Analise o conteúdo integralmente.

            ### ETAPA 2 — Identificação de termos técnicos
            A partir do texto completo, identifique TODOS os termos que podem
            enriquecer o contexto de uma especificação de requisitos:
            - Siglas técnicas (ex: LDAP, API, REST, SQL)
            - Nomes de tecnologias, protocolos ou padrões (ex: PostgreSQL, OAuth)
            - Conceitos de domínio técnico (ex: timeout, autenticação, middleware)
            - Termos específicos do negócio que precisem de definição formal

            NÃO inclua termos genéricos ou de uso comum que não precisem de definição.

            ### ETAPA 3 — Fatiamento do documento
            Use a tool `run_slicer` sem argumentos. Ela encontrará o arquivo automaticamente
            e criará os chunks em `data/chunks/`.

            ### ETAPA 4 — Busca de definições
            Para CADA termo identificado na Etapa 2:
            1. Use `check_glossary(termo)` para verificar se o termo já existe
            2. Se já existir, PULE para o próximo termo
            3. Se não existir, use `run_search(termo)` para encontrar trechos nos chunks
            2. Analise os trechos retornados e tente extrair uma DEFINIÇÃO FORMAL
            3. Uma definição formal deve explicar O QUE é o termo, não apenas citá-lo

            Exemplos de definição formal:
            - "LDAP: Lightweight Directory Access Protocol, protocolo utilizado para autenticação e consulta de diretórios de usuários"
            - "Timeout: Tempo máximo de espera para uma resposta do sistema antes de encerrar a conexão"

            ### ETAPA 5 — Alimentação do glossário
            Para cada termo onde você CONSEGUIU extrair uma definição formal:
            - Use `add_to_glossary(term, definition, sources)`
            - Em `sources`, liste TODOS os chunks onde o termo foi encontrado, separados por vírgula

            Para termos onde NÃO foi possível extrair uma definição formal:
            - IGNORE o termo. Não o adicione ao glossário sem definição.

            ### ETAPA 6 — Verificação final
            Após processar todos os termos:
            - Se o glossário ficou COMPLETAMENTE VAZIO (nenhum termo foi adicionado),
              use `add_doubt` para registrar uma dúvida no Doubt_Artifact.md:
                - affected_artifact: "Glossário"
                - doubt_description: "Nenhum termo técnico com definição formal foi encontrado no documento-matriz"
                - reason: Explique por que não foi possível extrair definições
                - impact: "Glossário da especificação ficará vazio, prejudicando a compreensão dos termos técnicos"
            - Se pelo menos um termo foi adicionado, retorne um resumo dos termos encontrados.

            ## REGRAS IMPORTANTES:
            - Sempre siga as etapas na ordem (1 → 2 → 3 → 4 → 5 → 6)
            - Nunca invente definições. Extraia APENAS do documento-matriz.
            - Se um mesmo termo aparece em múltiplos chunks, liste todos na coluna Fontes.
            - Seja criterioso: qualidade > quantidade.
        """,
        tools=[extract_text, run_slicer, run_search, add_to_glossary, add_doubt, check_glossary]
    )


glossario_agent = create_glossario_agent()