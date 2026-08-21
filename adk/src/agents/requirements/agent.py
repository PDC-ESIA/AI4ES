import os
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools.agent_tool import AgentTool

from shared.agent_factory import _bind_tool_to_workspace
from shared.tools import (
    run_slicer,
    extract_text,
    gerar_doubt_artifact,
    listar_duvidas_pendentes,
    tool_salvar_artefato_requisito,
    run_search,
    check_glossary,
    add_to_glossary,
    ler_artefatos_gerados,
)
from shared.workspace import get_agent_workspace, get_workspace_root
from . import prompt
from .validation import (
    auditar_saida_final,
    rebaixar_duvida_de_glossario,
    registrar_artefato_persistido,
    validar_antes_de_salvar,
)

_DEFAULT_MODEL = os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash")

# Workspace binding (resolvido no import-time, igual ao workflow_coding_review).
_WS_ROOT = str(get_workspace_root())
_REQ_WS = str(get_agent_workspace("requirements_agent"))
_GLOS_WS = str(get_agent_workspace("glossario_agent"))


def _bind(tool, agent_ws):
    return _bind_tool_to_workspace(tool, agent_ws, _WS_ROOT)

# ── Sub-Agente de Glossário (DESLIGADO DO PIPELINE) ──────────────────────────
# Fora do fluxo temporariamente: as ETAPAS 1 e 3 dependem de `data/matrix/`, que
# não existe no layout atual, e o erro delas fazia o agente pai abortar a análise
# antes de gravar qualquer artefato. Definição preservada — para religar, basta
# devolver `AgentTool(agent=glossario_agent)` à lista de tools do agente.

glossario_agent = LlmAgent(
    name="glossario_agent",
    model=os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash"),
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
        4. Analise os trechos retornados e tente extrair uma DEFINIÇÃO FORMAL
        5. Uma definição formal deve explicar O QUE é o termo, não apenas citá-lo

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
          use `gerar_doubt_artifact` para registrar uma dúvida:
            - id_duvida: "D-GLOSSARIO"
            - id_artefato_afetado: "Glossário"
            - duvida_descricao: "Nenhum termo técnico com definição formal foi encontrado no documento-matriz"
            - motivo: Explique por que não foi possível extrair definições
            - impacto: "Glossário da especificação ficará vazio, prejudicando a compreensão dos termos técnicos"
            - trecho_contexto: "Documento-matriz completo"
        - Se pelo menos um termo foi adicionado, retorne um resumo dos termos encontrados.

        ## REGRAS IMPORTANTES:
        - Sempre siga as etapas na ordem (1 → 2 → 3 → 4 → 5 → 6)
        - Nunca invente definições. Extraia APENAS do documento-matriz.
        - Se um mesmo termo aparece em múltiplos chunks, liste todos na coluna Fontes.
        - Seja criterioso: qualidade > quantidade.
    """,
    tools=[
        FunctionTool(extract_text),
        FunctionTool(run_slicer),
        FunctionTool(run_search),
        FunctionTool(add_to_glossary),
        FunctionTool(check_glossary),
        _bind(FunctionTool(gerar_doubt_artifact), _GLOS_WS),
    ],
)

# ── Sub-Agente de Validação ──────────────────────────────────────────────────

validacao_agent = LlmAgent(
    name="validacao_agent",
    model=_DEFAULT_MODEL,
    description=(
        "Sub-agente especializado em validação de requisitos. "
        "Analisa os artefatos gerados (HUs, RFs, RNFs, RNs, UCs) em busca de "
        "ambiguidades, contradições, inconsistências e violações dos critérios SMART."
    ),
    instruction=prompt.validacao_instruction,
    output_key="validation_result",
    tools=[
        _bind(FunctionTool(ler_artefatos_gerados), _REQ_WS),
        FunctionTool(check_glossary),
        _bind(FunctionTool(gerar_doubt_artifact), _REQ_WS),
    ],
)

# ── Agente Principal de Requisitos ───────────────────────────────────────────

agent = LlmAgent(
    model=_DEFAULT_MODEL,
    name="requirements_agent",
    description=prompt.description,
    instruction=prompt.instruction,
    output_key="analysis_result",
    # C1: rejeita artefato malformado antes de ele tocar o disco e impede que
    # uma dúvida sobre o glossário nasça bloqueante. Ambos retornam None para
    # as tools que não lhes dizem respeito, então a ordem é indiferente.
    before_tool_callback=[rebaixar_duvida_de_glossario, validar_antes_de_salvar],
    # C2: registra em state o que foi realmente gravado.
    after_tool_callback=registrar_artefato_persistido,
    # C3: audita a saída final contra o que foi persistido.
    after_agent_callback=auditar_saida_final,
    # `run_slicer` e `ler_chunk` ficaram de fora: resolvem caminho contra
    # ADK_AGENT_DATA_DIR, que aponta para um layout inexistente, e devolvem
    # string de erro em vez de exceção — falha silenciosa que o agente lia como
    # "documento indisponível" e usava para abortar a análise.
    tools=[
        _bind(FunctionTool(gerar_doubt_artifact), _REQ_WS),
        _bind(FunctionTool(tool_salvar_artefato_requisito), _REQ_WS),
        AgentTool(agent=validacao_agent),
    ],
)
