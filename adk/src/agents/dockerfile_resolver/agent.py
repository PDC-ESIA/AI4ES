"""Agente Resolvedor de Dockerfile.

Segue o MESMO contorno do `implementation_validator` (achado ao pesquisar a
F1): `create_se_agent` normal, SEM `output_schema` (GAP-00: schema desliga
function calling, e a factory sempre injeta `tool_ask_clarification_adk`), saída
em TEXTO LIVRE com marcação fixa, extraída por um `after_agent_callback`
determinístico. A única diferença pro validador é o formato da marcação: um bloco
delimitado (`DOCKERFILE_INICIO`/`DOCKERFILE_FIM`), não texto+regex por critério.

O agente NÃO recebe tool de leitura/filesystem — o contexto (manifestos, README,
CI) é reunido FORA, por `shared.tools.build_context`, e injetado na conversa pelo
`ExecutorOrchestrator`. Aqui o agente só "lê o que foi dado e devolve um
Dockerfile".
"""

import logging
import re

from google.adk.agents import LlmAgent

from shared.agent_factory import create_se_agent

from . import prompt

logger = logging.getLogger(__name__)

# Extrai o Dockerfile entre as marcações fixas do prompt (cada uma em sua linha).
_DOCKERFILE_RE = re.compile(
    r"DOCKERFILE_INICIO[ \t]*\n(?P<corpo>.*?)\nDOCKERFILE_FIM",
    re.DOTALL,
)

# Cerca de código markdown: ``` (opcionalmente com um identificador de linguagem,
# ex. ```dockerfile) na 1ª linha e ``` sozinho na última.
_CERCA_ABRE_RE = re.compile(r"^```[\w.+-]*$")
_CERCA_FECHA_RE = re.compile(r"^```$")


def _remover_cerca_markdown(texto: str) -> str:
    """Remove uma cerca de código markdown que envolva o conteúdo INTEIRO.

    Casa quando a primeira linha é ``` (opcionalmente com um identificador de
    linguagem) e a última linha é ``` sozinho — nesse caso remove as duas linhas.
    Não mexe em nada quando o padrão não bate (caso comum: o prompt já pede pra
    não usar crase). NÃO tenta corrigir outros desvios de formato do LLM.
    """
    linhas = texto.split("\n")
    if (
        len(linhas) >= 2
        and _CERCA_ABRE_RE.match(linhas[0].strip())
        and _CERCA_FECHA_RE.match(linhas[-1].strip())
    ):
        return "\n".join(linhas[1:-1]).strip()
    return texto


def _extrair_dockerfile(callback_context):
    """`after_agent_callback`: extrai o Dockerfile do texto livre do LLM.

    Grava `state["dockerfile_resolution"] = {"dockerfile": <texto ou None>}`.
    `None` quando a extração falha (LLM não seguiu o formato) — o Orchestrator
    trata isso EXATAMENTE como "nenhum Dockerfile resolvido" (mesmo caminho
    honesto que já existe para ausência de Dockerfile do coder), sem inventar um
    estado de erro novo. Retorna None: a saída crua do LLM permanece o conteúdo
    do turno; o dado que importa vai para o state.
    """
    raw = callback_context.state.get("dockerfile_resolution_raw", "") or ""
    m = _DOCKERFILE_RE.search(raw)
    dockerfile = _remover_cerca_markdown(m.group("corpo").strip()) if m else None
    if not dockerfile:  # marcações ausentes ou corpo vazio
        dockerfile = None
        logger.warning(
            "dockerfile_resolver: não foi possível extrair um Dockerfile da "
            "resposta do LLM (marcações ausentes/vazias)."
        )
    callback_context.state["dockerfile_resolution"] = {"dockerfile": dockerfile}
    return None


def criar_agente() -> LlmAgent:
    """Constrói uma instância NOVA do resolvedor, já com a extração acoplada.

    Instância própria a cada chamada porque `sub_agents` do ADK exige parent
    ÚNICO, e o `ExecutorOrchestrator` é instanciado em DOIS lugares (executor
    consolidado e o do workflow) — mesma obrigação que o validador já resolve
    assim.
    """
    novo = create_se_agent(
        name="dockerfile_resolver",
        description=prompt.description,
        instruction=prompt.instruction,
        output_key="dockerfile_resolution_raw",
        # SEM output_schema (GAP-00) e SEM tools próprias — só a
        # tool_ask_clarification que a factory injeta.
    )
    novo.after_agent_callback = _extrair_dockerfile
    return novo


agent = criar_agente()

# ADK CLI busca por `root_agent` ao carregar um app diretamente.
root_agent = agent
