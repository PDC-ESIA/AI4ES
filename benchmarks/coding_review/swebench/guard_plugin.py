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
   Runner (`include_plugins=True`), só por aqui o consumo dele é contado;
4. PAUSA a instância quando o provedor limita o ritmo (rate limit): no
   `on_model_error_callback`, espera e repete a MESMA chamada (backoff
   dobrando, até um teto), e o loop segue de onde estava. Refazer a instância
   do zero desperdiçaria as chamadas já feitas — que consomem o mesmo limite.
   Estouro de contexto e outros erros não são tocados: são resultado do loop;
5. CONTROLA O RITMO antes de cada chamada ao modelo (`before_model_callback`):
   com um teto de tokens por minuto, a chamada espera até o consumo recente
   caber nele. O provedor limita a VAZÃO (tokens numa janela de tempo), não o
   total do mês; respeitar o ritmo evita os bloqueios longos que o rate limit
   impõe depois de estourado.

O plugin não curto-circuita nenhum agente e não propaga falhas próprias: uma
falha da guarda vira ocorrência registrada, não queda do run.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

from google.adk.plugins.base_plugin import BasePlugin

from . import environment
from .loop_runner import is_context_overflow

logger = logging.getLogger(__name__)

EXECUTOR_AGENT_NAME = "cr_executor_agent"
CODER_AGENT_NAME = "cr_coder_agent"
OCORRENCIA_ERRO_GUARDA = "erro_na_guarda"

_HTTP_429 = re.compile(r"(?<!\d)429(?!\d)")
# Folga do controle de ritmo: quanto consumo (em segundos de teto) pode ficar
# "a pagar" antes de a próxima chamada esperar. Permite pequenas rajadas.
_RAJADA_S = 60.0
_AVISO_ESPERA_S = 5.0


def is_rate_limit(erro: BaseException | str) -> bool:
    """Se o erro é o provedor limitando o ritmo (e não estouro de contexto)."""
    texto = erro if isinstance(erro, str) else f"{type(erro).__name__}: {erro}"
    if is_context_overflow(texto):
        return False
    minusculo = texto.lower()
    return (
        "ratelimiterror" in minusculo
        or "rate limit" in minusculo
        or bool(_HTTP_429.search(minusculo))
    )


class BenchmarkGuardPlugin(BasePlugin):
    """Guarda do ambiente + contadores de turno, reiniciados por instância."""

    def __init__(
        self,
        workspace: Path,
        *,
        name: str = "swebench_benchmark_guard",
        rate_limit_initial_wait: float = 60.0,
        rate_limit_max_wait: float = 3600.0,
        max_tokens_per_minute: int = 0,
        sleep: Callable[[float], Awaitable[Any]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        super().__init__(name=name)
        self._workspace = workspace
        self._image: Optional[str] = None
        self._espera_inicial = rate_limit_initial_wait
        self._espera_maxima = rate_limit_max_wait
        self._sleep = sleep
        self._clock = clock
        self._tpm = max(0, int(max_tokens_per_minute or 0))
        # Instante em que todo o consumo registrado estará dentro do teto. NÃO
        # zera entre instâncias: o provedor não zera o limite dele.
        self._pago_ate = 0.0
        self.throttle_waits: list[float] = []
        self.executor_rounds = 0
        self.coder_turns = 0
        self.occurrences: list[dict[str, Any]] = []
        self.usage_by_agent: dict[str, dict[str, int]] = {}
        self.rate_limit_waits: list[float] = []

    def start_instance(self, image: str) -> None:
        """Zera os contadores para uma nova instância."""
        self._image = image
        self.executor_rounds = 0
        self.coder_turns = 0
        self.occurrences = []
        self.usage_by_agent = {}
        self.rate_limit_waits = []
        self.throttle_waits = []

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
            self._registrar_consumo(
                (getattr(uso, "prompt_token_count", None) or 0)
                + (getattr(uso, "candidates_token_count", None) or 0)
            )
        except Exception:  # noqa: BLE001 — contabilidade não pode derrubar o loop
            logger.exception("[SWEBENCH_GUARD] Falha ao contabilizar uso de LLM.")
        return None

    def _registrar_consumo(self, tokens: int) -> None:
        """Acrescenta o consumo à "dívida" do controle de ritmo."""
        if self._tpm <= 0 or tokens <= 0:
            return
        agora = self._clock()
        self._pago_ate = max(self._pago_ate, agora) + tokens / self._tpm * 60.0

    async def before_model_callback(self, *, callback_context, llm_request):
        """Espera, se preciso, para o consumo médio caber no teto por minuto."""
        if self._tpm <= 0:
            return None
        espera = self._pago_ate - _RAJADA_S - self._clock()
        if espera > 0:
            if espera >= _AVISO_ESPERA_S:
                print(f"[guarda] ritmo: aguardando {espera:.0f}s para respeitar "
                      f"{self._tpm} tokens/min", flush=True)
            self.throttle_waits.append(espera)
            await self._sleep(espera)
        return None

    async def on_model_error_callback(self, *, callback_context, llm_request, error):
        """Rate limit: espera e repete a mesma chamada; o resto segue intocado."""
        if not is_rate_limit(error):
            return None
        contexto = getattr(callback_context, "_invocation_context", None)
        modelo = getattr(getattr(contexto, "agent", None), "canonical_model", None)
        if modelo is None:
            return None

        espera, acumulado = self._espera_inicial, 0.0
        print(f"[guarda] erro do provedor: {type(error).__name__}: {error}", flush=True)
        while acumulado + espera <= self._espera_maxima:
            logger.warning(
                "[SWEBENCH_GUARD] Rate limit do provedor; pausando %.0fs antes de "
                "repetir a chamada.", espera,
            )
            print(f"[guarda] rate limit do provedor: pausa de {espera / 60:.0f} min "
                  "antes de repetir a chamada", flush=True)
            self.rate_limit_waits.append(espera)
            await self._sleep(espera)
            acumulado += espera
            try:
                resposta = None
                async for parcial in modelo.generate_content_async(llm_request, stream=False):
                    resposta = parcial
                return resposta
            except Exception as novo_erro:  # noqa: BLE001
                if not is_rate_limit(novo_erro):
                    raise
            espera *= 2
        return None  # teto esgotado: o erro original segue para o loop

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
            "pausas_rate_limit_s": list(self.rate_limit_waits),
            "pausa_ritmo_s": round(sum(self.throttle_waits), 2),
        }
