import os
from google.adk.agents import LlmAgent, SequentialAgent, ParallelAgent
from google.adk.tools import LongRunningFunctionTool
from google.adk.tools.agent_tool import AgentTool

from src.agents.design_architect.agent import agent as design_architect
from src.agents.mermaid_specialist.agent import agent as mermaid_specialist
from src.agents.markdown_specialist.agent import agent as markdown_specialist
from src.agents.prototyping_specialist.agent import agent as prototyping_specialist
from src.agents.validator.agent import agent as validator
from src.agents.io_agent.agent import agent as io_agent
from shared.tools.design_hitl_tool import aguardar_resolucao_doubt

_DEFAULT_MODEL = "github_copilot/gpt-4"

# ──────────────────────────────────────────────────────────────────────────────
# PIPELINE CONTROLLER
# Responsabilidade: limpeza → salvar HUs → design_architect → verificar design_dir
# Encerra com "CONTROLLER_DONE" — o SequentialAgent raiz passa para o próximo.
# NÃO aciona prototyping nem mermaid — isso é do fluxo sequencial principal.
# ──────────────────────────────────────────────────────────────────────────────

_INSTRUCTION = """
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
⛔ ESTA VALIDAÇÃO É DETERMINÍSTICA, NÃO NARRATIVA: acione o Agente IO para pedir a
verificação estrutural de completude do arquivo confirmado (a checagem que conta
os marcadores de fim de seção e reporta quais seções estão ausentes ou vazias) —
NÃO tente avaliar completude apenas lendo o texto e "achando" que está completo.
Uma autoavaliação textual já falhou uma vez em pegar um arquivo com só a Seção 1
(ver DIAGNOSTICO_BLOQUEIO_HITL_2026-07.md, Bug B) — por isso a checagem estrutural
é obrigatória e substitui qualquer inspeção manual.

Leia o retorno dessa verificação:
- "complete": true  → avance para ETAPA 3.
- "complete": false → NÃO avance. Informe ao design_architect exatamente quais
  seções estão em "missing_sections" (nunca persistidas) e "empty_sections"
  (persistidas só com título) e aguarde a versão corrigida. Após a correção,
  repita a verificação estrutural — não aceite a palavra do design_architect
  de que corrigiu sem essa confirmação.

As 8 seções esperadas (para referência, mas a fonte de verdade é a verificação estrutural):
- 1. Compreensão do lote
- 2. Decisão(ões) de arquitetura e trade-offs
- 3. Tipo de diagrama por HU
- 4. Componentes por HU com origens
- 5. Bloqueios identificados (mesmo que declare "Nenhum")
- 6. Tabela de cobertura por HU
- 7. Gap Analysis
- 8. Plano de Prototipação: deve conter "Tela Central" declarada e tabela com ao menos uma linha de arquivo HTML

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ETAPA 3 — VERIFICAÇÃO DE BLOQUEIOS (HITL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Após validar o conteúdo da análise técnica, verifique bloqueios:

Acione o Agente IO: "[pipeline_controller] Verifique se há Doubt_Artifacts bloqueados em doubt_dir."

SE não houver bloqueios (has_blocks: false):
→ Avance diretamente para ETAPA 4.

SE houver bloqueios (has_blocks: true):
1. NÃO encerre com texto de bloqueio. NÃO emita PIPELINE_STAGE_1_COMPLETE.
   NÃO avance para os especialistas. CHAME OBRIGATORIAMENTE a tool
   `aguardar_resolucao_doubt`, passando:
   - checkpoint_id: hu_ids bloqueados, unidos por vírgula
   - approval_question: cite cada bloco (filename + hu_id) e peça para
     resolver (Status: Bloqueado → Resolvido) e responder "retomar" ou
     "cancelar"
   - allowed_decisions: ["retomar", "cancelar"]
   - pause_reason: motivo do bloqueio
2. NÃO emita nenhum texto além da chamada da tool.
3. Quando a tool retornar, leia `decision`:
   - "cancelar" → encerre com "PIPELINE_ERROR: lote cancelado pelo solicitante."
   - "retomar"  → chame check_active_blocks novamente via Agente IO.
       - Se ainda houver bloqueios: chame `aguardar_resolucao_doubt`
         de novo com os bloqueios remanescentes (pausa encadeada — já
         suportada pelo orchestrator).
       - Se não houver mais bloqueios: avance para ETAPA 4.

⚠️ NUNCA emita PIPELINE_STAGE_1_COMPLETE enquanto has_blocks for true.
⚠️ O lote é indivisível — todas as HUs avançam juntas ou nenhuma avança.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ETAPA 4 — VERIFICAÇÃO PRÉ-SEQUÊNCIA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Acione o Agente IO: "[pipeline_controller] Liste todos os arquivos disponíveis em design_dir."
Confirme que existe arquivo com nome iniciando em analise_tecnica_.
- Ausente: retorne ao design_architect solicitando que salve a análise.
- Presente: acione o Agente IO para repetir a verificação estrutural de
  completude neste ponto (o mesmo gate determinístico da ETAPA 2) — isto
  confirma que nenhuma seção foi corrompida ou perdida entre a ETAPA 2 e o
  retorno do parallel_branch.
  - "complete": true  → avance para ETAPA 5.
  - "complete": false → devolva ao design_architect informando "missing_sections"
    e "empty_sections" retornados pela ferramenta, e aguarde a versão corrigida.
    Repita a chamada após a correção. Não avance para ETAPA 5 sem "complete": true.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ETAPA 5 — ENCERRAMENTO OBRIGATÓRIO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Você é o porteiro do pipeline. Enquanto o design_architect trabalha (mesmo que demore minutos), você deve manter o foco na resposta dele.
NÃO finalize sua execução e não responda ao orquestrador até que você tenha lido o conteúdo do arquivo gerado e confirmado que ele não está vazio.
Sua resposta final deve ser EXATAMENTE e NADA MAIS:
"PIPELINE_STAGE_1_COMPLETE: A análise técnica foi gerada com sucesso. O controle de execução pode agora ser transferido para os especialistas."
"""

pipeline_controller = LlmAgent(
    model=os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL),
    name="pipeline_controller",
    description="PASSO_OBRIGATORIO_1: Único agente que gera a 'analise_tecnica.md'. O pipeline INTEIRO para aqui até que este arquivo seja confirmado.",
    instruction=_INSTRUCTION,
    tools=[
        AgentTool(agent=io_agent),
        AgentTool(agent=design_architect),
        LongRunningFunctionTool(aguardar_resolucao_doubt),
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
    description="Pipeline completo de design: transforma HUs em protótipos, diagramas Mermaid e relatórios Markdown validados e persistidos.",
    sub_agents=[
        pipeline_controller,
        parallel_branch,
    ],
)