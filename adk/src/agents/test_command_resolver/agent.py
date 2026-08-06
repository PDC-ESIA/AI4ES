"""Agente Resolvedor do Comando de Teste.

Mesmo padrão exato do `dockerfile_resolver` (F1): `create_se_agent` sem
`output_schema`, saída em TEXTO LIVRE com bloco delimitado
(`COMANDO_INICIO`/`COMANDO_FIM`) extraído por um `after_agent_callback`
determinístico, `criar_agente()` com instância nova por chamada (parent único do
ADK). Sem tool de filesystem — o contexto é reunido FORA (build_context) e
injetado na conversa pelo `ExecutorOrchestrator`.
"""

import logging
import re

from google.adk.agents import LlmAgent

from shared.agent_factory import create_se_agent

from . import prompt

logger = logging.getLogger(__name__)

# Extrai o comando entre as marcações fixas do prompt (cada uma em sua linha).
_COMANDO_RE = re.compile(
    r"COMANDO_INICIO[ \t]*\n(?P<corpo>.*?)\nCOMANDO_FIM",
    re.DOTALL,
)

# Cerca de código markdown que o LLM às vezes envolve mesmo instruído a não usar.
_CERCA_ABRE_RE = re.compile(r"^```[\w.+-]*$")
_CERCA_FECHA_RE = re.compile(r"^```$")


def _remover_cerca_markdown(texto: str) -> str:
    """Remove uma cerca de código markdown que envolva o conteúdo INTEIRO.

    Casa quando a primeira linha é ``` (opcionalmente com um identificador de
    linguagem) e a última é ``` sozinho — nesse caso remove as duas linhas. Não
    mexe em nada quando o padrão não bate. NÃO tenta corrigir outros desvios.
    """
    linhas = texto.split("\n")
    if (
        len(linhas) >= 2
        and _CERCA_ABRE_RE.match(linhas[0].strip())
        and _CERCA_FECHA_RE.match(linhas[-1].strip())
    ):
        return "\n".join(linhas[1:-1]).strip()
    return texto


def _extrair_comando(callback_context):
    """`after_agent_callback`: extrai o comando do texto livre do LLM.

    Grava `state["test_command_resolution"] = {"comando": <texto ou None>}`.
    `None` quando a extração falha — o Orchestrator trata como "nenhum comando
    resolvido" (harness pula o Estágio 6 honestamente), sem estado de erro novo.
    """
    raw = callback_context.state.get("test_command_resolution_raw", "") or ""
    m = _COMANDO_RE.search(raw)
    comando = _remover_cerca_markdown(m.group("corpo").strip()) if m else None
    if not comando:
        comando = None
        logger.warning(
            "test_command_resolver: não foi possível extrair um comando da "
            "resposta do LLM (marcações ausentes/vazias)."
        )
    callback_context.state["test_command_resolution"] = {"comando": comando}
    return None


def criar_agente() -> LlmAgent:
    """Instância NOVA do resolvedor por chamada (parent único do ADK em sub_agents)."""
    novo = create_se_agent(
        name="test_command_resolver",
        description=prompt.description,
        instruction=prompt.instruction,
        output_key="test_command_resolution_raw",
        # SEM output_schema (GAP-00) e SEM tools próprias.
    )
    novo.after_agent_callback = _extrair_comando
    return novo


agent = criar_agente()

# ADK CLI busca por `root_agent` ao carregar um app diretamente.
root_agent = agent
