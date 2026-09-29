"""Plugin do Runner, exclusivo do benchmark: guarda do ambiente e contagem de rodadas.

Registrado no `App` do benchmark (nunca na produção). O ADK executa os
callbacks de plugin ANTES dos callbacks do próprio agente, então, a cada turno
do `cr_executor_agent`, este plugin roda antes do gate de executabilidade e do
harness. Ele:

1. conta as rodadas do loop (um turno do executor = uma rodada, inclusive as
   recusadas pelo gate). É uma contagem mais confiável que o
   `progress_score_history`, que perde a rodada quando o `state['validation']`
   não é gravado;
2. restaura o ambiente do benchmark se o coder o desfez (ver
   `environment.ensure_benchmark_files`) e registra cada restauração como
   violação, com a rodada em que ocorreu;
3. soma o uso de LLM por agente no `after_model_callback`. O
   `implementation_validator` roda como `AgentTool`, num Runner interno cujos
   eventos não chegam ao loop externo; como o ADK propaga os plugins para esse
   Runner (`include_plugins=True`), só por aqui o consumo dele é contado.

O plugin nunca devolve conteúdo (não curto-circuita nenhum agente) e nunca
propaga exceção: uma falha aqui vira ocorrência registrada, não queda do run.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from google.adk.plugins.base_plugin import BasePlugin

from . import environment

logger = logging.getLogger(__name__)

EXECUTOR_AGENT_NAME = "cr_executor_agent"
CODER_AGENT_NAME = "cr_coder_agent"
OCORRENCIA_ERRO_GUARDA = "erro_na_guarda"


class BenchmarkGuardPlugin(BasePlugin):
    """Guarda do ambiente + contadores de turno, reiniciados por instância."""

    def __init__(self, workspace: Path, *, name: str = "swebench_benchmark_guard"):
        super().__init__(name=name)
        self._workspace = workspace
        self._image: Optional[str] = None
        self.executor_rounds = 0
        self.coder_turns = 0
        self.occurrences: list[dict[str, Any]] = []
        self.usage_by_agent: dict[str, dict[str, int]] = {}

    def start_instance(self, image: str) -> None:
        """Zera os contadores para uma nova instância."""
        self._image = image
        self.executor_rounds = 0
        self.coder_turns = 0
        self.occurrences = []
        self.usage_by_agent = {}

    async def after_model_callback(self, *, callback_context, llm_response):
        try:
            uso = getattr(llm_response, "usage_metadata", None)
            if uso is None or getattr(llm_response, "partial", False):
                return None
            agente = getattr(callback_context, "agent_name", None) or "desconhecido"
            linha = self.usage_by_agent.setdefault(
                agente, {"llm_interactions": 0, "prompt_tokens": 0, "completion_tokens": 0}
            )
            linha["llm_interactions"] += 1
            linha["prompt_tokens"] += getattr(uso, "prompt_token_count", None) or 0
            linha["completion_tokens"] += getattr(uso, "candidates_token_count", None) or 0
        except Exception:  # noqa: BLE001 — contabilidade não pode derrubar o loop
            logger.exception("[SWEBENCH_GUARD] Falha ao contabilizar uso de LLM.")
        return None

    def usage_totals(self) -> dict[str, Any]:
        """Uso somado de todos os agentes, com o detalhamento por agente."""
        totais = {"llm_interactions": 0, "prompt_tokens": 0, "completion_tokens": 0}
        for linha in self.usage_by_agent.values():
            for chave in totais:
                totais[chave] += linha[chave]
        return {**totais, "por_agente": {k: dict(v) for k, v in self.usage_by_agent.items()}}

    async def before_agent_callback(self, *, agent, callback_context):
        nome = getattr(agent, "name", "")
        if nome == CODER_AGENT_NAME:
            self.coder_turns += 1
        elif nome == EXECUTOR_AGENT_NAME:
            self.executor_rounds += 1
            self._guardar_ambiente()
        return None

    def _guardar_ambiente(self) -> None:
        if self._image is None:
            return
        try:
            tipos = environment.ensure_benchmark_files(self._workspace, self._image)
        except Exception as exc:  # noqa: BLE001 — a guarda não pode derrubar o loop
            logger.exception("[SWEBENCH_GUARD] Falha ao verificar o ambiente.")
            tipos = [OCORRENCIA_ERRO_GUARDA]
            self.occurrences.append(
                {"rodada": self.executor_rounds, "tipo": tipos[0], "detalhe": str(exc)}
            )
            return
        for tipo in tipos:
            self.occurrences.append({"rodada": self.executor_rounds, "tipo": tipo})
            if tipo in environment.VIOLACOES:
                logger.warning(
                    "[SWEBENCH_GUARD] Rodada %d: %s.", self.executor_rounds, tipo
                )

    def summary(self) -> dict[str, Any]:
        """Resumo serializável da instância corrente."""
        tipos = [o["tipo"] for o in self.occurrences]
        return {
            "rodadas_executor": self.executor_rounds,
            "turnos_coder": self.coder_turns,
            "ocorrencias": list(self.occurrences),
            "ambiente_violado": any(t in environment.VIOLACOES for t in tipos),
            "venv_no_manifesto": environment.OBSERVACAO_VENV in tipos,
            "erro_na_guarda": OCORRENCIA_ERRO_GUARDA in tipos,
        }
