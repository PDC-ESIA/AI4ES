import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool
from google.adk.tools.agent_tool import AgentTool

from shared.tools import (
    run_slicer,
    ler_chunk,
    extract_text,
    gerar_doubt_artifact,
    listar_duvidas_pendentes,
    tool_salvar_artefato_requisito,
    run_search,
    check_glossary,
    add_to_glossary,
    build_skill_toolset,
)
from .skills.hu_skill import hu_skill
from .skills.rf_skill import rf_skill
from .skills.rnf_skill import rnf_skill
from .skills.rn_skill import rn_skill
from .skills.uc_skill import uc_skill
from . import prompt

_DEFAULT_MODEL = os.environ.get("ADK_LLM_MODEL", "github_copilot/gpt-4")

artefatos_toolset = build_skill_toolset(
    [hu_skill, rf_skill, rnf_skill, rn_skill, uc_skill]
)
# ── Sub-Agente de Glossário ──────────────────────────────────────────────────
glossario_agent = LlmAgent(
    name="glossario_agent",
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", "github_copilot/gpt-4o")),
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

        ### ETAPA 1 - Leitura do documento-matriz
        Use a tool `extract_text` passando o caminho `data/matrix/` como argumento.
        A tool encontrará o arquivo automaticamente. Analise o conteúdo integralmente.

        ### ETAPA 2 - Identificação de termos técnicos
        A partir do texto completo, identifique TODOS os termos que podem
        enriquecer o contexto de uma especificação de requisitos:
        - Siglas técnicas (ex: LDAP, API, REST, SQL)
        - Nomes de tecnologias, protocolos ou padrões (ex: PostgreSQL, OAuth)
        - Conceitos de domínio técnico (ex: timeout, autenticação, middleware)
        - Termos específicos do negócio que precisem de definição formal

        NÃO inclua termos genéricos ou de uso comum que não precisem de definição.

        ### ETAPA 3 - Fatiamento do documento
        Use a tool `run_slicer` sem argumentos. Ela encontrará o arquivo automaticamente
        e criará os chunks em `data/chunks/`.

        ### ETAPA 4 - Busca de definições
        Para CADA termo identificado na Etapa 2:
        1. Use `check_glossary(termo)` para verificar se o termo já existe
        2. Se já existir, PULE para o próximo termo
        3. Se não existir, use `run_search(termo)` para encontrar trechos nos chunks
        4. Analise os trechos retornados e tente extrair uma DEFINIÇÃO FORMAL
        5. Uma definição formal deve explicar O QUE é o termo, não apenas citá-lo

        ### ETAPA 5 - Alimentação do glossário
        Para cada termo onde você CONSEGUIU extrair uma definição formal:
        - Use `add_to_glossary(term, definition, sources)`
        - Em `sources`, liste TODOS os chunks onde o termo foi encontrado, separados por vírgula

        Para termos onde NÃO foi possível extrair uma definição formal:
        - IGNORE o termo. Não o adicione ao glossário sem definição.

        ### ETAPA 6 - Verificação final
        Após processar todos os termos:
        - Se o glossário ficou COMPLETAMENTE VAZIO (nenhum termo foi adicionado),
          use `gerar_doubt_artifact` para registrar uma dúvida com os campos necessários.
        - Se pelo menos um termo foi adicionado, retorne um resumo dos termos encontrados.

        ## REGRAS IMPORTANTES:
        - Sempre siga as etapas na ordem (1 -> 2 -> 3 -> 4 -> 5 -> 6)
        - Nunca invente definições. Extraia APENAS do documento-matriz.
        - Seja criterioso: qualidade > quantidade.
    """,
    tools=[
        FunctionTool(extract_text),
        FunctionTool(run_slicer),
        FunctionTool(run_search),
        FunctionTool(add_to_glossary),
        FunctionTool(check_glossary),
        FunctionTool(gerar_doubt_artifact),
    ],
)
# ── Agente Principal de Requisitos ───────────────────────────────────────────
root_agent = LlmAgent(
    model=LiteLlm(_DEFAULT_MODEL),
    name="requirements_agent",
    description=prompt.description,
    instruction=prompt.instruction,
    output_key="analysis_result",
    tools=[
        artefatos_toolset,
        FunctionTool(run_slicer),
        FunctionTool(ler_chunk),
        FunctionTool(gerar_doubt_artifact),
        FunctionTool(tool_salvar_artefato_requisito),
        AgentTool(agent=glossario_agent),
    ],
)

agent = root_agent
