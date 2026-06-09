"""Workflow de QA / Testes (Time 3).

Orquestrador que conduz o ciclo completo de QA do PDC-AI4SE:
planejamento → geração de testes pytest → autocorreção em caso de falha.
Composto sobre os sub-agentes especialistas do qa_agent.
"""

import os

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool, LongRunningFunctionTool
from google.adk.tools.agent_tool import AgentTool

from src.agents.qa_agent.subagents.code_fix_agent.agent import agent as code_fix_agent
from src.agents.qa_agent.subagents.receive_requirements import agent as receber_requisitos_agent
from adk.shared.tools.hitl_tool import aguardar_aprovacao_humana
from adk.shared.tools.pytest_runner import executar_pytest_tool
from adk.shared.tools.doubt_tool import DoubtArtifactGenerator
from src.agents.workflow_qa.tools.planner_wrapper import invocar_planejamento_qa

_DEFAULT_MODEL = "gemini-2.5-flash"

_INSTRUCTION = """
Você é o pipeline de QA / Testes do Time 3.

PAPEL:
Receber artefatos de requisito (RF, HU, UC, RNF, RN) — opcionalmente
acompanhados de código fonte — e produzir uma suíte pytest executável,
corrigindo automaticamente as falhas detectadas.

FLUXO OBRIGATÓRIO:

1. PLANEJAMENTO
   Chame `invocar_planejamento_qa(request=<entrada original>)`.
   Essa função roda o planner com retry automático e GARANTE retorno
   de JSON estruturado (nunca empty). O JSON contém: tipos de teste,
   dependências, pontos de validação humana (HITL) e relatório de
   compliance preliminar.

   → Se `lifecycle.status == "bloqueado"` no JSON retornado:
        Encerre com Doubt_Artifact citando `erro` do JSON.
        Esse caminho só é acionado quando o action_planner não
        conseguiu produzir plano nem com retry — bloqueio legítimo.

   → Se o plano retornar com `hitl_checkpoint.required=true`:
        CHAME OBRIGATORIAMENTE a tool `aguardar_aprovacao_humana`
        passando checkpoint_id, approval_question, allowed_decisions e
        pause_reason extraídos do plano. NÃO emita texto pedindo
        aprovação — a tool faz a pausa real.
        Quando a tool retornar, leia o campo `decision`:
          - "aprovar"           → prossiga para a etapa 2 (geração).
          - "rejeitar"          → encerre com Doubt_Artifact citando
                                  `comments`; não gere testes.
          - "solicitar_ajustes" → encerre devolvendo `comments` ao
                                  solicitante; não gere testes.

2. GERAÇÃO DE TESTES
   Encaminhe o(s) artefato(s) ao receber_requisitos_agent.
   Esse subagente:
   - normaliza a entrada em JSON com id_artefato, tipo, conteúdo, módulo, criticidade;
   - inclui anexos no campo `arquivos_apoio` quando houver código-fonte;
   - gera arquivos pytest em artefactsTests/<slug>/test_<slug>.py;
   - retorna {status, resumo, detalhes} com sucessos, bloqueados e falhas.
   → Para cada artefato bloqueado (status "bloqueado"): registre o Doubt_Artifact
     gerado e prossiga com os demais.

3. EXECUÇÃO
   Após a geração, invoque a tool `executar_pytest_tool` apontando para
   a pasta dos testes gerados. Colete o relatório (status, saída pytest,
   cobertura, falhas).
   → Se TODOS os testes passaram: vá direto para a entrega final.
   → Se houver falhas: vá para a etapa 4.

4. AUTOCORREÇÃO (Code Fix)
   Encaminhe o relatório de falhas ao code_fix_agent.
   Ele analisa o log do pytest e produz um prompt de correção dirigido
   ao agente responsável pela mudança (ex.: coder).
   → Aplique a correção sugerida (ou devolva o prompt ao solicitante).
   → Volte para a etapa 3 (re-execução), com no máximo 2 ciclos de
     autocorreção antes de bloquear e gerar Doubt_Artifact.

5. DOUBT ARTIFACT (fallback)
   Em qualquer etapa, se faltar contexto crítico, use a tool
   `DoubtArtifactGenerator.generate` para registrar o bloqueio e
   devolver ao solicitante.

REGRAS:
- Nunca pule a etapa de planejamento (1).
- Nunca tente corrigir código de produção — sua atuação é restrita ao
  código de TESTES.
- Idioma: Português brasileiro.
- Limite a autocorreção a 2 ciclos para evitar loops infinitos.

ENTREGA FINAL AO SOLICITANTE:
- Resumo: {total, sucessos, bloqueados, falhas}.
- Lista de arquivos pytest gerados, com caminhos.
- Relatório de execução do pytest (saída + cobertura).
- Doubt_Artifacts gerados (se houver), com caminho.
- Prompts de correção produzidos pelo code_fix (se houver), com destinatário.
"""

agent = LlmAgent(
    model=os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL),
    name="qa_pipeline",
    description=(
        "Pipeline completo de QA: planejamento, geração pytest a partir de "
        "requisitos, execução e autocorreção. Compõe action_planner, "
        "receber_requisitos e code_fix sobre as tools do qa_agent."
    ),
    instruction=_INSTRUCTION,
    tools=[
        FunctionTool(invocar_planejamento_qa),
        AgentTool(agent=receber_requisitos_agent),
        AgentTool(agent=code_fix_agent),
        FunctionTool(executar_pytest_tool),
        FunctionTool(DoubtArtifactGenerator.generate),
        LongRunningFunctionTool(aguardar_aprovacao_humana),
    ],
)
