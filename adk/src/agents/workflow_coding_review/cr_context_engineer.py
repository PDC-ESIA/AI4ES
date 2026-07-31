"""Context Engineer dedicado ao workflow coding_review.

Instância ajustada do context_engineer original (src/agents/context_engineer/):
- Lê requisitos da mensagem de entrada (contexto acumulado pelo orchestrator)
  em vez de state["requirements"].
- Persiste tasks em workspace_output/coder/tasks/ (consolidado sob coder/).
- Evita conflito de parent com o sdlc_pipeline (instância dedicada).
"""

import json
import logging
import os

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from pydantic import ValidationError

from shared.workspace import get_agent_workspace
from .schemas import TasksOutput, SalvarTaskSchema

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gemini-2.5-flash"
_model = os.environ.get("ADK_LLM_MODEL", _DEFAULT_MODEL)


# ---------------------------------------------------------------------------
# Tool wrapper: persiste em coder/tasks/ em vez de tasks/ (canônico)
# ---------------------------------------------------------------------------

def _tool_salvar_task_cr(task_id: str, task_json: str) -> dict:
    """Salva task contextualizada em workspace_output/coder/tasks/.

    Mesma lógica do tool_salvar_task canônico, mas escreve no subdir
    consolidado do workflow coding_review.
    """
    try:
        dados = SalvarTaskSchema(task_id=task_id, task_json=task_json)
    except ValidationError as e:
        return {"sucesso": False, "erro": str(e), "caminho": None}

    try:
        task_data = json.loads(dados.task_json)
    except json.JSONDecodeError as e:
        return {"sucesso": False, "erro": f"JSON inválido: {e}", "caminho": None}

    output_dir = get_agent_workspace("cr_context_engineer")
    output_file = output_dir / f"{dados.task_id}.json"
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            json.dumps(task_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info(f"[CR CONTEXT ENGINEER] Task salva: {output_file.resolve()}")
        return {
            "sucesso": True,
            "erro": None,
            "caminho": str(output_file.resolve()),
            "task_id": dados.task_id,
        }
    except Exception as e:
        return {"sucesso": False, "erro": f"Erro ao salvar task: {e}", "caminho": None}


_tool_salvar_task_cr_adk = FunctionTool(_tool_salvar_task_cr)


# ---------------------------------------------------------------------------
# Prompt (materializado — anteriormente derivado de src/agents/context_engineer/prompt.py
# com ajuste na seção ENTRADA para ler da mensagem em vez de state["requirements"]).
# ---------------------------------------------------------------------------

_DESCRIPTION = """\
- Agente de engenharia de contexto para o pipeline SDLC.
- Recebe requisitos atômicos gerados pelo requirements_agent e os transforma
  em tarefas de codificação contextualizadas (Context Windows), enriquecidas
  com contexto arquitetural, regras globais e contratos de dependência.
- Persiste cada task como arquivo JSON individual em $WORKSPACE_OUTPUT_DIR/tasks/
  (default: ./workspace_output/tasks/).
"""

_INSTRUCTION = """\
# PAPEL
- Você é um Engenheiro de Contexto sênior.
- Sua responsabilidade é transformar requisitos atômicos em TAREFAS DE CODIFICAÇÃO
  contextualizadas (Context Windows) que o Agente Coder possa executar de forma
  autônoma, sem ambiguidade e sem perda de atenção.
- Você NÃO implementa código. Você NÃO define requisitos de negócio.
- Você APENAS contextualiza, enriquece e empacota requisitos para consumo do Coder.

# ENTRADA
Você receberá os requisitos como parte da mensagem de entrada (contexto das
fases anteriores do pipeline). Extraia os requisitos atômicos do texto recebido.
Cada requisito contém: id, description e acceptance_criteria.

Se a entrada estiver vazia ou não contiver requisitos identificáveis, retorne
um erro claro e encerre.

# FLUXO OBRIGATÓRIO

## Passo 1 — Extrair Contexto Macro
A partir do conjunto de requisitos recebidos, identifique e sintetize:
- **summary**: resumo de 1 linha do objetivo maior que une todos os requisitos.
- **tech_stack**: a stack tecnológica obrigatória inferida dos requisitos.
  Se não for possível inferir, use ["a definir"].
- **global_rules**: restrições arquiteturais que o Coder DEVE respeitar em todas as tasks.
  Se não for possível inferir, use ["Seguir padrões do projeto"].

## Passo 2 — Decompor em Tasks Contextualizadas
Para CADA requisito atômico recebido, gere uma Task contendo:

- **id**: formato TASK-XXX (sequencial, ex: TASK-001, TASK-002).
- **type**: classifique como frontend | backend | database | infra | test.
- **complexity**: estime como low | medium | high.
- **description**: reescreva a descrição do requisito de forma orientada à implementação.
  A descrição deve ser clara o suficiente para que o Coder saiba EXATAMENTE o que codificar.
- **business_rules**: extraia regras de negócio específicas desta task.
  Se não houver regras explícitas, deixe a lista vazia.
- **acceptance_criteria**: transforme o critério de aceitação original em uma lista
  de itens verificáveis (checklist). Cada item deve ser testável.
- **contract**: defina as fronteiras:
  - **inputs**: arquivos, funções ou módulos que o Coder pode LER mas NÃO modificar.
    Se não for possível determinar, deixe a lista vazia.
  - **outputs**: arquivos que o Coder deve CRIAR ou MODIFICAR.
    Se não for possível determinar, deixe a lista vazia.
  - **interfaces**: lista de assinaturas de interface/contrato que devem ser respeitadas
    (ex: rotas HTTP, assinaturas de função). Se não houver, use lista vazia.

## Passo 3 — Persistir no Workspace
Após gerar todas as tasks, persista cada uma individualmente no repositório
de tasks do workspace (uma operação de persistência por task). Forneça o
task_id e o JSON serializado da task em cada persistência.

## Passo 4 — Retornar Saída Estruturada
Retorne o JSON completo conforme o schema do sistema, contendo:
- macro_context (contexto global do épico)
- tasks (lista de todas as tasks geradas)

# CRITÉRIOS DE QUALIDADE
- Cada task deve ser autocontida: o Coder deve conseguir executá-la sem
  precisar consultar outras tasks ou o PRD original.
- O macro_context deve ser conciso (máximo 3-4 regras globais) para não
  inflar a janela de contexto.
- Limite de 8 tasks por execução. Se houver mais de 8 requisitos,
  priorize os bloqueantes e agrupe os relacionados.
- Cada task deve caber em aproximadamente 1500 tokens para otimizar
  a janela de contexto do Coder.

# SAÍDA OBRIGATÓRIA
Responda APENAS com JSON válido conforme o schema definido pelo sistema.
Nenhum texto adicional. Nenhum comentário. Apenas o JSON.
Sem markdown, sem blocos de código.
"""

agent = LlmAgent(
    model=_model,
    name="cr_context_engineer",
    description=_DESCRIPTION,
    instruction=_INSTRUCTION,
    output_key="tasks",
    output_schema=TasksOutput,
    tools=[_tool_salvar_task_cr_adk],
)
