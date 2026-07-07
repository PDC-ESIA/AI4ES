"""
pipeline_agent.py
─────────────────
Engine interna do pipeline de design.

Estrutura:
    SequentialAgent (raiz)
      ├── pipeline_controller  LlmAgent — limpeza + design_architect + verificação
      └── parallel_branch      ParallelAgent DIRETO (não AgentTool)
           ├── prototyping_specialist  autodescobre analise_tecnica via list_design_files
           └── diagram_flow           SequentialAgent: mermaid → validator → markdown
"""

import os
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool

from src.agents.design_architect.agent import agent as design_architect
from src.agents.mermaid_specialist.agent import agent as mermaid_specialist
from src.agents.markdown_specialist.agent import agent as markdown_specialist
from src.agents.prototyping_specialist.agent import agent as prototyping_specialist
from src.agents.validator.agent import agent as validator
from src.agents.io_agent.agent import agent as io_agent

_DEFAULT_MODEL = "github_copilot/gpt-4"

# ──────────────────────────────────────────────────────────────────────────────
# PIPELINE CONTROLLER
# Responsabilidade: limpeza → salvar HUs → design_architect → verificar design_dir
# Encerra com "CONTROLLER_DONE" — o SequentialAgent raiz passa para o próximo.
# NÃO aciona prototyping nem mermaid — isso é do fluxo sequencial principal.
# ──────────────────────────────────────────────────────────────────────────────

pipeline_controller = LlmAgent(
    model=LiteLlm(os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)),
    name="pipeline_controller",
    description="PASSO_OBRIGATORIO_1: Único agente que gera a 'analise_tecnica.md'. O pipeline INTEIRO para aqui até que este arquivo seja confirmado.",
    instruction="""
Você é o controlador de preparação do pipeline de design de software.
Sua responsabilidade TERMINA quando analise_tecnica estiver confirmada em design_dir E não houver bloqueios ativos.
Você NÃO aciona protótipos, diagramas nem relatórios.

IDIOMA: Português brasileiro.

IDENTIFICAÇÃO AO AGENTE IO:
Em toda mensagem enviada ao Agente IO, inicie com: "[pipeline_controller]"
Exemplo: "[pipeline_controller] Limpe o diretório design_dir."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REGRA DE OURO DE SEQUENCIAMENTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Você é o detentor do token de execução.
1. Enquanto o design_architect não entregar o arquivo 'analise_tecnica_*.md', você NÃO PODE emitir nenhuma mensagem final.
2. Se o design_architect demorar, você deve continuar monitorando o design_dir.
3. Se houver Doubt_Artifacts com status Bloqueado, você NÃO PODE emitir PIPELINE_STAGE_1_COMPLETE.
   O lote inteiro aguarda resolução — não há execução parcial.
4. Somente quando o arquivo estiver validado E não houver bloqueios ativos, responda exatamente:
   "PIPELINE_STAGE_1_COMPLETE: A análise técnica foi gerada com sucesso. O controle de execução pode agora ser transferido para os especialistas."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ETAPA 1 — LIMPEZA DO DESIGN_DIR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Acione o Agente IO: "[pipeline_controller] Limpe o diretório design_dir."
- Erro: responda "PIPELINE_ERROR: falha na limpeza — <erro>" e encerre.
- Sucesso: avance para ETAPA 2.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ETAPA 2 — ANÁLISE TÉCNICA (BLOQUEANTE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Acione o design_architect com o comando: 'Analise o seguinte conteúdo de HUs e gere a análise técnica em analysis_dir: '. Deixe claro que não há arquivo de origem e que ele deve usar este texto como fonte única.
2. APÓS o retorno do design_architect, você DEVE obrigatoriamente executar a ferramenta list_design_files do Agente IO.
3. Se o arquivo 'analise_tecnica_*.md' NÃO aparecer na lista, você deve perguntar ao design_architect: "Onde está o arquivo de análise técnica? Confirme o salvamento."
4. Repita a verificação de listagem até que o arquivo esteja presente.

⚠️ VOCÊ SÓ PODE AVANÇAR PARA A ETAPA 3 APÓS VER O ARQUIVO NA LISTA DO AGENTE IO.

Valide que o CONTEÚDO DO ARQUIVO SALVO contém TODAS as seções obrigatórias.
Peça ao Agente IO para ler o arquivo confirmado e verifique:
- Compreensão do lote
- Decisão(ões) de arquitetura e trade-offs
- Tipo de diagrama por HU
- Componentes por HU com origens
- Seção "Bloqueios identificados" (mesmo que declare "Nenhum")
- Tabela de cobertura por HU
- Gap Analysis
- Plano de Prototipação (seção 8): deve conter "Tela Central" declarada e tabela com ao menos uma linha de arquivo HTML
Uma seção é válida somente se contiver conteúdo além do título.
Não confie apenas no nome do arquivo ou na mensagem de confirmação do design_architect.

Se qualquer seção estiver ausente: devolva ao design_architect informando o campo
faltante e aguarde a versão corrigida.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ETAPA 3 — VERIFICAÇÃO DE BLOQUEIOS (HITL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Após validar o conteúdo da análise técnica, verifique bloqueios:

Acione o Agente IO: "[pipeline_controller] Verifique se há Doubt_Artifacts bloqueados em doubt_dir."

SE não houver bloqueios (has_blocks: false):
→ Avance diretamente para ETAPA 4.

SE houver bloqueios (has_blocks: true):
1. NÃO encerre. NÃO emita PIPELINE_STAGE_1_COMPLETE. NÃO avance para os especialistas.
2. Informe o orquestrador com EXATAMENTE este formato:
   "PIPELINE_BLOCKED: O lote está suspenso aguardando resolução humana.
   Bloqueios ativos:
   - <HU_ID>: <nome_do_doubt_artifact>
   [repita para cada bloqueio]
   O pipeline só continuará após todos os Doubt_Artifacts serem resolvidos.
   Instrução ao solicitante: edite cada Doubt_Artifact alterando o status de 'Bloqueado' para 'Resolvido' e solicite a retomada."

3. Entre em loop de espera:
   a. Aguarde mensagem de retomada do orquestrador.
   b. Ao receber retomada: acione o Agente IO para verificar bloqueios novamente.
   c. SE ainda houver bloqueios: informe quais permanecem e volte ao passo (a).
   d. SE não houver mais bloqueios: avance para ETAPA 4.

⚠️ NUNCA saia do loop de espera por iniciativa própria.
⚠️ NUNCA emita PIPELINE_STAGE_1_COMPLETE enquanto has_blocks for true.
⚠️ O lote é indivisível — todas as HUs avançam juntas ou nenhuma avança.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ETAPA 4 — VERIFICAÇÃO PRÉ-SEQUÊNCIA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Acione o Agente IO: "[pipeline_controller] Liste todos os arquivos disponíveis em design_dir."
Confirme que existe arquivo com nome iniciando em analise_tecnica_.
- Ausente: retorne ao design_architect solicitando que salve a análise.
- Presente: leia o arquivo via Agente IO e valide que TODAS as seções obrigatórias possuem conteúdo além do título:
  - Compreensão do lote
  - Decisão de Arquitetura e Trade-Offs
  - Tipo de Diagrama Escolhido e Justificativa
  - Identificação de Componentes por HU
  - Bloqueios Identificados
  - Tabela de Cobertura por HU
  - Gap Analysis
  - Plano de Prototipação: deve conter "Tela Central" e tabela de arquivos HTML com ao menos uma linha. Se ausente ou contiver apenas o título sem tabela: devolva ao design_architect informando que a seção 8 está incompleta.
  Se qualquer seção existir mas estiver vazia (apenas título sem conteúdo): devolva ao design_architect informando as seções vazias e aguarde versão corrigida.
  Somente avance para ETAPA 5 após confirmar conteúdo real em todas as seções.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ETAPA 5 — ENCERRAMENTO OBRIGATÓRIO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Você é o porteiro do pipeline. Enquanto o design_architect trabalha (mesmo que demore minutos), você deve manter o foco na resposta dele.
NÃO finalize sua execução e não responda ao orquestrador até que você tenha lido o conteúdo do arquivo gerado e confirmado que ele não está vazio.
Sua resposta final deve ser EXATAMENTE e NADA MAIS:
"PIPELINE_STAGE_1_COMPLETE: A análise técnica foi gerada com sucesso. O controle de execução pode agora ser transferido para os especialistas."
""",
    tools=[
        AgentTool(agent=io_agent),
        AgentTool(agent=design_architect),
    ],
)

diagram_flow = SequentialAgent(
    name="diagram_flow",
    description="FASE_FINAL: Processamento de diagramas e relatório. SÓ PODE RODAR APÓS A ANALISE_TECNICA ESTAR PRONTA.",
    sub_agents=[
        mermaid_specialist,
        validator,
        markdown_specialist,
    ],
)

parallel_branch = ParallelAgent(
    name="parallel_branch",
    description="ERRO_SE_ACESSADO_AGORA: Este bloco contém especialistas que dependem CRITICAMENTE da saída do PASSO_OBRIGATORIO_1. Não ativar enquanto o status não for PIPELINE_STAGE_1_COMPLETE.",
    sub_agents=[
        prototyping_specialist,
        diagram_flow,
    ],
)

agent = SequentialAgent(
    name="design_pipeline",
    description="PIPELINE_MESTRE: 1. Controller (OBRIGATÓRIO) -> 2. Execução (SÓ APÓS O 1).",
    sub_agents=[
        pipeline_controller,
        parallel_branch,
    ],
)