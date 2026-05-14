"""
pipeline_agent.py
─────────────────
Engine interna do pipeline de design (SEQUENCIAL APENAS).

Estrutura:
    SequentialAgent (raiz)
      ├── pipeline_controller       (prepara staging, roda design_architect e verifica)
      ├── prototyping_specialist    (lê analise_tecnica e gera HTML/CSS)
      ├── mermaid_specialist        (lê analise_tecnica e gera .mmd)
      ├── validator                 (valida .mmd gerados)
      └── markdown_specialist       (gera relatório final)

Por que funciona:
    - pipeline_controller encerra após confirmar analise_tecnica em staging.
    - O SequentialAgent raiz passa aos próximos especialistas automaticamente e de forma sequencial.
    - Os especialistas subsequentes têm instrução explícita de descoberta via list_staging_files.
"""

import os
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool

from design_agents.roles.design_architect.agent import agent as design_architect
from design_agents.roles.prototyping_specialist.agent import agent as prototyping_specialist
from design_agents.roles.mermaid_specialist.agent import agent as mermaid_specialist
from design_agents.roles.markdown_specialist.agent import agent as markdown_specialist
from design_agents.roles.validator.agent import agent as validator
from design_agents.roles.io_agent.agent import agent as io_agent

_DEFAULT_MODEL = "github_copilot/gpt-4"

# ──────────────────────────────────────────────────────────────────────────────
# PIPELINE CONTROLLER
# Responsabilidade: limpeza → salvar HUs → design_architect → verificar staging
# Encerra com "CONTROLLER_DONE" — o SequentialAgent raiz passa para o próximo.
# NÃO aciona prototyping nem mermaid — isso é do fluxo sequencial principal.
# ──────────────────────────────────────────────────────────────────────────────

pipeline_controller = LlmAgent(
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)),
    name="pipeline_controller",
    description="Prepara o pipeline: limpa staging, persiste HUs, aciona design_architect e verifica staging.",
    instruction="""
Você é o controlador de preparação do pipeline de design de software.
Sua responsabilidade TERMINA quando analise_tecnica estiver confirmada em staging.
Você NÃO aciona protótipos, diagramas nem relatórios.

IDIOMA: Português brasileiro.

IDENTIFICAÇÃO AO AGENTE IO:
Em toda mensagem enviada ao Agente IO, inicie com: "[pipeline_controller]"
Exemplo: "[pipeline_controller] Limpe o diretório staging."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ETAPA 1 — LIMPEZA DO STAGING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Acione o Agente IO: "[pipeline_controller] Limpe o diretório staging."
- Erro: responda "PIPELINE_ERROR: falha na limpeza — <erro>" e encerre.
- Sucesso: avance para ETAPA 2.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ETAPA 2 — ANÁLISE TÉCNICA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Acione o design_architect informando o texto exato e integral das HUs que você recebeu:
"Execute a análise técnica completa do lote abaixo:
<TEXTO INTEGRAL E EXATO DAS HUs — PROIBIDO RESUMIR>"

Aguarde o retorno confirmando o nome do arquivo salvo em staging.

Valide que o retorno contém TODAS as seções obrigatórias:
- Compreensão do lote
- Decisão(ões) de arquitetura e trade-offs
- Tipo de diagrama por HU
- Componentes por HU com origens
- Seção "Bloqueios identificados" (mesmo que declare "Nenhum")
- Tabela de cobertura por HU
- Gap Analysis

Se qualquer seção estiver ausente: devolva ao design_architect informando o campo
faltante e aguarde a versão corrigida.

Se o design_architect retornar Doubt_Artifact para alguma HU:
- Registre: HU_ID bloqueada e nome exato do Doubt_Artifact.
- Prossiga se houver ao menos uma HU disponível.
- Se TODAS bloqueadas: responda "PIPELINE_BLOCKED: <lista>" e encerre.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ETAPA 3 — VERIFICAÇÃO PRÉ-SEQUÊNCIA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Acione o Agente IO: "[pipeline_controller] Liste todos os arquivos disponíveis em staging."
Confirme que existe arquivo com nome iniciando em analise_tecnica_.
- Ausente: retorne ao design_architect solicitando que salve a análise.
- Presente: avance para ETAPA 4.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ETAPA 4 — ENCERRAMENTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Responda EXATAMENTE:
"CONTROLLER_DONE: analise_tecnica confirmada em staging.
HUs bloqueadas: <lista ou 'nenhuma'>."

Não acione mais nenhuma ferramenta após este ponto.
""",
    tools=[
        AgentTool(agent=io_agent),
        AgentTool(agent=design_architect),
    ],
)

# ──────────────────────────────────────────────────────────────────────────────
# PIPELINE COMPLETO
# SequentialAgent garante: controller → prototipação → diagramas → validação → relatórios
# ──────────────────────────────────────────────────────────────────────────────

agent = SequentialAgent(
    name="design_pipeline",
    description="Pipeline sequencial completo: preparação → protótipo → diagramas → validação → relatório.",
    sub_agents=[
        pipeline_controller,
        prototyping_specialist,
        mermaid_specialist,
        validator,
        markdown_specialist,
    ],
)