"""Executor como `BaseAgent` — a decisão de encerrar o loop vira código.

O fluxo que antes vivia em `prompt.py` (rodar o harness → acionar o validador →
obedecer ao veredito) passa a ser executado deterministicamente: sem LLM no
topo, não há o que reinterpretar. A "salvaguarda" em prosa do prompt existia
para impedir que o LLM decidisse sozinho; aqui ela é desnecessária, porque a
decisão é o próprio código.

Por iteração do loop `[coder → executor]`:

1. Roda o harness sobre o Work Item atual, persistindo o ExecutionReport.
2. Invoca o `implementation_validator` como SUB-AGENTE (`run_async`), que ao
   terminar já deixa `state['validation']` preenchido pela sua política
   determinística — o `after_agent_callback` dispara dentro do próprio
   `run_async`, sem chamada extra daqui.
3. Decide a partir de `ValidationVerdict.status`, e só dele:
   - `aprovado`  → encerra o loop (Event com `EventActions(escalate=True)`,
     equivalente ao `exit_loop` de quando isto era tool call);
   - `reprovado` → devolve ao coder o `ErrorReport` determinístico do hook
     injetado, SEM encerrar.

O `overall_status` técnico do harness nunca encerra o loop sozinho — como
antes, só o veredito encerra.

A única outra saída é a ESTAGNAÇÃO (ver `estagnacao.py`): quando o mesmo par
`(hash do código, blocking_reason)` se repete em 3 iterações consecutivas, o
loop encerra com o resumo `bloqueado` em vez do ErrorReport. Encerrar por
estagnação NÃO é aprovar — o veredito continua reprovado.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator, Callable, Optional

from google.adk.agents import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.genai import types
from pydantic import ConfigDict, PrivateAttr

from shared.tools.build_context import reunir_contexto_build
from shared.tools.coding_tools.harness_execucao import (
    executar_harness_validacao,
    ler_tech_stack,
)
from shared.workspace import get_agent_workspace

from .estagnacao import LIMITE_REPETICOES, hash_codigo, resumo_bloqueado

logger = logging.getLogger(__name__)

# Hook que monta o relatório devolvido ao coder quando o veredito é reprovado.
# Recebe um contexto com `.state` (o CallbackContext desta invocação) e devolve
# o Content a emitir, ou None quando não há relatório a emitir.
ErrorReportBuilder = Callable[[CallbackContext], Optional[types.Content]]

_CHAVE_ITERACAO = "executor_iteration"
_CHAVE_CONTAGEM_ESTAGNACAO = "stagnation_count"
_CHAVE_CHAVE_ESTAGNACAO = "stagnation_key"

# Estágio de testes no payload do harness (StageName.TESTES_AUTOMATIZADOS.value —
# usado como literal para não importar StageName daqui e reabrir o ciclo).
_STAGE_TESTES = "testes_automatizados"

# Filtro leve do comando de teste resolvido: recusa se contiver qualquer um destes
# como substring (instalar dependência é do Dockerfile/build, nunca do teste).
_PADROES_PERIGOSOS = (
    "rm -rf", "sudo", "curl", "wget", "apt install", "apt-get install",
    "pip install", "npm install", "npm ci", "yarn add", "chmod 777",
    "dd if=", "mkfs", "> /dev/",
)


class ExecutorOrchestrator(BaseAgent):
    """Orquestra harness → validador → decisão de encerramento, sem LLM."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Hook injetado por quem instancia — dependência de comportamento, não
    # configuração serializável do agente; por isso PrivateAttr.
    _error_report_builder: Optional[ErrorReportBuilder] = PrivateAttr(default=None)

    def __init__(
        self,
        *,
        validator: BaseAgent,
        dockerfile_resolver: BaseAgent,
        test_command_resolver: BaseAgent,
        error_report_builder: Optional[ErrorReportBuilder] = None,
        **kwargs: Any,
    ) -> None:
        """Args:
        validator: agente de validação a usar como sub-agente. É injetado, e
            não importado como singleton, porque o ADK exige parent ÚNICO em
            `sub_agents` — use `implementation_validator.agent.criar_agente()`
            para obter uma instância própria por orquestração.
        dockerfile_resolver: agente que resolve o Dockerfile quando o coder não
            traz um próprio (passo 0). Injetado como instância própria
            (`dockerfile_resolver.agent.criar_agente()`) pelo mesmo motivo do
            validador — `sub_agents` exige parent único.
        test_command_resolver: agente que resolve o comando de teste (Estágio 6).
            Injetado como instância própria, mesma obrigação de parent único.
        error_report_builder: hook que monta o `ErrorReport` do turno reprovado
            (ver `executor/error_report.py`). Sem ele, um veredito reprovado
            apenas registra o `blocking_reason` em texto — o loop continua
            igual, mas o coder não recebe a evidência bruta dos estágios.
        """
        super().__init__(
            sub_agents=[validator, dockerfile_resolver, test_command_resolver],
            **kwargs,
        )
        self._error_report_builder = error_report_builder

    @property
    def validator(self) -> BaseAgent:
        """O agente de validação — mesma instância passada ao construtor."""
        return self.sub_agents[0]

    @property
    def dockerfile_resolver(self) -> BaseAgent:
        """O agente resolvedor de Dockerfile — mesma instância passada ao construtor."""
        return self.sub_agents[1]

    @property
    def test_command_resolver(self) -> BaseAgent:
        """O agente resolvedor do comando de teste — mesma instância do construtor."""
        return self.sub_agents[2]

    # ------------------------------------------------------------------
    # Comando de teste — leitura do agente, filtro de segurança e cache
    # ------------------------------------------------------------------

    def _ler_comando_resolvido(
        self, ctx: InvocationContext
    ) -> tuple[Optional[str], Optional[str]]:
        """Lê o comando resolvido pelo agente (do state) e aplica o filtro leve.

        `(comando, "llm")` quando há comando não-vazio e seguro; senão
        `(None, None)` — o harness então pula o Estágio 6 honestamente.
        """
        resolucao = ctx.session.state.get("test_command_resolution") or {}
        comando = (resolucao.get("comando") or "").strip()
        if not comando:
            return None, None
        if not self._comando_seguro(comando):
            logger.warning("executor: comando de teste recusado pelo filtro: %r", comando)
            return None, None
        return comando, "llm"

    @staticmethod
    def _comando_seguro(comando: str) -> bool:
        """Recusa comando com padrão perigoso (instalar/apagar/baixar/etc.).

        Instalar dependência é problema do Dockerfile/build, nunca do comando de
        teste — mesma filosofia dos adapters aposentados.
        """
        alvo = comando.lower()
        return not any(padrao in alvo for padrao in _PADROES_PERIGOSOS)

    @staticmethod
    def _ler_cache_comando(cache_path) -> Optional[str]:
        """Comando cacheado por Task (`{task_id}.test_command.json`), ou None."""
        try:
            dados = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        comando = dados.get("comando") if isinstance(dados, dict) else None
        return comando if isinstance(comando, str) and comando.strip() else None

    @staticmethod
    def _atualizar_cache_comando(
        cache_path, comando: Optional[str], estagio6: Optional[dict]
    ) -> None:
        """Grava o cache quando o comando final RODOU (mesmo com testes falhando de
        verdade); invalida (remove) quando ainda deu COMANDO_NAO_ENCONTRADO — assim
        a próxima iteração resolve do zero."""
        error_code = (estagio6 or {}).get("error_code")
        if comando and estagio6 is not None and error_code != "COMANDO_NAO_ENCONTRADO":
            try:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(
                    json.dumps({"comando": comando}, ensure_ascii=False), encoding="utf-8"
                )
            except OSError:
                logger.warning("executor: falha ao gravar cache de comando em %s", cache_path)
        elif error_code == "COMANDO_NAO_ENCONTRADO":
            try:
                cache_path.unlink(missing_ok=True)
            except OSError:
                pass

    @staticmethod
    def _stage(payload: dict, nome: str) -> Optional[dict]:
        """O dict do StageResult com `stage == nome` no payload do harness, ou None."""
        for s in payload.get("stages", []) or []:
            if s.get("stage") == nome:
                return s
        return None

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # CallbackContext expõe o `.state` delta-aware desta invocação: as
        # escritas caem direto em ctx.session.state (visíveis já para o
        # validador, que compartilha a sessão) e ficam acumuladas em
        # `.actions.state_delta` para viajar nos Events que emitimos — é assim
        # que report_path/task_id chegam a ser persistidos.
        cb = CallbackContext(ctx)

        task_id = self._resolver_task_id(cb)
        if not task_id:
            logger.warning(
                "executor: nenhum task_id resolvível no state; harness não "
                "executado nesta iteração."
            )
            yield self._evento_texto(
                ctx,
                "Não foi possível identificar o Work Item a validar: nem "
                "`task_id` nem `tasks` estão no state da sessão.",
                cb,
            )
            return

        iteration = self._proxima_iteracao(cb)

        # tech_stack declarada, lida uma vez: vira DICA (não autoritativa) para os
        # dois resolvedores (Dockerfile e comando de teste).
        tech_stack = ler_tech_stack(cb)
        coder_dir = get_agent_workspace("cr_coder")

        # ---- 0. Dockerfile: prioriza o do coder; senão, resolve via LLM ----
        # O harness é função pura: RECEBE o Dockerfile pronto. Quem decide de onde
        # ele vem é aqui. O Dockerfile do coder SEMPRE vence — nem chama a LLM.
        dockerfile_path = coder_dir / "Dockerfile"
        if dockerfile_path.is_file():
            dockerfile_resolvido = dockerfile_path.read_text(encoding="utf-8")
            origem_dockerfile = "coder"
        else:
            # Sem Dockerfile do coder: reúne o contexto (determinístico, sem tool)
            # e o injeta na conversa do resolvedor — mesmo truque do REPORT_PATH,
            # mantendo o agente sem capacidade de vasculhar o filesystem.
            yield self._evento_texto(
                ctx,
                "Nenhum Dockerfile no workspace do coder. Resolva o Dockerfile a "
                "partir do CONTEXTO DO WORKSPACE a seguir.\n\n"
                + reunir_contexto_build(coder_dir, tech_stack=tech_stack),
                cb,
            )
            async for event in self.dockerfile_resolver.run_async(ctx):
                yield event
            resolucao = ctx.session.state.get("dockerfile_resolution") or {}
            dockerfile_resolvido = resolucao.get("dockerfile")
            # None quando a extração falhou: não passa Dockerfile ao harness, que
            # cai no próprio caminho honesto (DOCKERFILE_AUSENTE).
            origem_dockerfile = "llm" if dockerfile_resolvido else None

        # ---- 1. Comando de teste + Harness (com 1 retry se o comando não rodar) --
        # O comando é resolvido FORA do harness (aqui) e entregue pronto. Cache por
        # Task no workspace do executor: "qual ferramenta roda os testes" é estável
        # entre iterações do loop.
        exec_dir = get_agent_workspace("cr_executor")
        cache_path = exec_dir / f"{task_id}.test_command.json"

        comando = self._ler_cache_comando(cache_path)
        if comando:
            origem_comando = "cache"
        else:
            yield self._evento_texto(
                ctx,
                "Resolva o COMANDO que roda a suíte de testes já configurada neste "
                "projeto, a partir do CONTEXTO DO WORKSPACE a seguir.\n\n"
                + reunir_contexto_build(coder_dir, tech_stack=tech_stack),
                cb,
            )
            async for event in self.test_command_resolver.run_async(ctx):
                yield event
            comando, origem_comando = self._ler_comando_resolvido(ctx)

        payload = executar_harness_validacao(
            task_id,
            iteration,
            tool_context=cb,
            dockerfile=dockerfile_resolvido,
            dockerfile_origem=origem_dockerfile,
            comando_teste=comando,
            comando_teste_origem=origem_comando,
        )

        # Retry ÚNICO: só quando o comando RODOU e não foi encontrado/executável
        # (127/126), sinal de que a LLM (ou um cache stale) errou a invocação — NÃO
        # quando os testes rodaram e falharam de verdade. Roda o harness inteiro de
        # novo (rebuild incluso — Opção A), sem mecanismo novo de reuso de container.
        estagio6 = self._stage(payload, _STAGE_TESTES)
        if estagio6 and estagio6.get("error_code") == "COMANDO_NAO_ENCONTRADO":
            ev = estagio6.get("evidence") or {}
            yield self._evento_texto(
                ctx,
                "O comando de teste anterior NÃO foi encontrado/executável no "
                f"container. Comando: {ev.get('comando')!r}. Saída:\n"
                f"{ev.get('saida_tail', '')}\n\n"
                "Resolva um comando corrigido a partir do CONTEXTO a seguir.\n\n"
                + reunir_contexto_build(coder_dir, tech_stack=tech_stack),
                cb,
            )
            async for event in self.test_command_resolver.run_async(ctx):
                yield event
            comando, origem_comando = self._ler_comando_resolvido(ctx)
            payload = executar_harness_validacao(
                task_id,
                iteration,
                tool_context=cb,
                dockerfile=dockerfile_resolvido,
                dockerfile_origem=origem_dockerfile,
                comando_teste=comando,
                comando_teste_origem=origem_comando,
            )
            estagio6 = self._stage(payload, _STAGE_TESTES)

        # Cache: grava quando o comando final rodou (mesmo com testes falhando de
        # verdade); invalida quando ainda deu COMANDO_NAO_ENCONTRADO.
        self._atualizar_cache_comando(cache_path, comando, estagio6)

        report_path = payload.get("report_path", "")

        # O report_path vai no CONTEÚDO do turno porque é assim que ele entra no
        # contexto do validador — que antes o recebia como argumento da
        # AgentTool. A política do validador o lê do state (fonte determinística);
        # o LLM dele precisa vê-lo aqui para saber o que ler do disco.
        yield self._evento_texto(
            ctx,
            f"Harness executado para {task_id} (iteração {iteration}). "
            f"REPORT_PATH: {report_path}",
            cb,
        )

        # ---- 2. Validador como sub-agente ----
        # Ao final deste laço, `state['validation']` já está escrito pela
        # política determinística do validador (o after_agent_callback dele
        # dispara dentro do próprio run_async).
        async for event in self.validator.run_async(ctx):
            yield event

        # ---- 3. Decisão — obedece ao veredito, e só a ele ----
        validation = ctx.session.state.get("validation") or {}
        status = validation.get("status")

        if status == "aprovado":
            resumo_aprovado = (
                f"Veredito APROVADO para {task_id}. "
                f"{validation.get('summary') or ''}"
            ).rstrip()
            cb.state["execution_result"] = resumo_aprovado
            yield self._evento_texto(
                ctx,
                resumo_aprovado,
                cb,
                escalate=True,
            )
            return

        if status != "reprovado":
            # A política do validador nunca deixa de emitir veredito (o
            # fail-safe dela reprova). Um status ausente/inesperado aqui
            # significa que a propagação falhou — tratar como aprovação seria
            # exatamente o erro que a salvaguarda antiga existia para impedir.
            logger.warning(
                "executor: veredito ausente ou inesperado (%r); tratando como "
                "não-aprovação e mantendo o loop.",
                status,
            )

        # ---- 3a. Estagnação — avaliada ANTES de montar o ErrorReport ----
        # A ordem importa: no caminho de estagnação o builder nem chega a ser
        # chamado, então o resumo `bloqueado` é o que persiste em
        # `execution_result`. (O builder também reconhece o marcador e devolve
        # None, mas depender só disso deixaria a garantia num efeito colateral.)
        repeticoes = self._contar_estagnacao(cb, validation)
        if repeticoes >= LIMITE_REPETICOES:
            resumo = resumo_bloqueado(
                validation.get("blocking_reason") or "", repeticoes
            )
            cb.state["execution_result"] = resumo
            logger.info(
                "executor: estagnação em %s — mesmo (hash, blocking_reason) por "
                "%d iterações consecutivas; encerrando como bloqueado.",
                task_id,
                repeticoes,
            )
            yield self._evento_texto(ctx, resumo, cb, escalate=True)
            return

        conteudo = (
            self._error_report_builder(cb) if self._error_report_builder else None
        )
        if conteudo is not None:
            texto = "".join(
                part.text or "" for part in (conteudo.parts or []) if part.text is not None
            )
            # O evento mostrado no loop é Markdown, mas o contrato interno com
            # o coder permanece sendo o JSON estruturado do ErrorReport.
            # Isso separa apresentação de dados sem alterar a interpretação do
            # retry nem os placeholders já usados pelo prompt do coder.
            error_report = cb.state.get("error_report")
            cb.state["execution_result"] = (
                json.dumps(error_report, ensure_ascii=False)
                if isinstance(error_report, dict)
                else texto
            )
            yield Event(
                author=self.name,
                invocation_id=ctx.invocation_id,
                branch=ctx.branch,
                content=conteudo,
                actions=self._drenar_actions(cb),
            )
            return

        resumo_reprovado = (
            f"Veredito REPROVADO para {task_id}: "
            f"{validation.get('blocking_reason') or 'sem blocking_reason.'}"
        )
        cb.state["execution_result"] = resumo_reprovado
        yield self._evento_texto(ctx, resumo_reprovado, cb)

    # ------------------------------------------------------------------
    # Resolução determinística das entradas do harness
    # ------------------------------------------------------------------

    @staticmethod
    def _resolver_task_id(cb: CallbackContext) -> str:
        """Identifica o Work Item a validar, sem depender de LLM.

        Duas fontes, nesta ordem:
          1. `state['task_id']` — gravado pelo próprio harness numa iteração
             anterior, o que mantém o mesmo Work Item ao longo do loop;
          2. a primeira task de `state['tasks']`, a saída estruturada que o
             context_engineer já grava (`output_key="tasks"`) antes do loop
             começar.

        Devolve "" quando nenhuma das duas resolve — quem chama decide o que
        fazer (aqui: não rodar o harness e registrar o motivo).
        """
        do_state = cb.state.get("task_id")
        if isinstance(do_state, str) and do_state:
            return do_state

        try:
            task_id = cb.state["tasks"]["tasks"][0]["id"]
        except (KeyError, TypeError, IndexError):
            return ""

        return task_id if isinstance(task_id, str) else ""

    @staticmethod
    def _contar_estagnacao(cb: CallbackContext, validation: dict) -> int:
        """Repetições CONSECUTIVAS do par `(hash do código, blocking_reason)`.

        Devolve 1 na primeira reprovação de um par novo, e incrementa enquanto o
        par se repetir. Qualquer mudança em uma das metades zera a contagem —
        `LIMITE_REPETICOES` é sobre repetições seguidas, não acumuladas.

        Vive no state pelo mesmo motivo que `_proxima_iteracao`: acompanha a
        sessão, não o processo. A chave é gravada como lista porque é assim que
        ela sobrevive à serialização do session state.
        """
        par = [
            hash_codigo(get_agent_workspace("cr_coder")),
            validation.get("blocking_reason") or "",
        ]

        anterior = cb.state.get(_CHAVE_CHAVE_ESTAGNACAO)
        contagem = cb.state.get(_CHAVE_CONTAGEM_ESTAGNACAO)
        if par == anterior and isinstance(contagem, int):
            atual = contagem + 1
        else:
            atual = 1

        cb.state[_CHAVE_CHAVE_ESTAGNACAO] = par
        cb.state[_CHAVE_CONTAGEM_ESTAGNACAO] = atual
        return atual

    @staticmethod
    def _proxima_iteracao(cb: CallbackContext) -> int:
        """Conta as passagens do executor nesta sessão (1 na primeira).

        Vive no state, e não num atributo de instância, porque é o número que o
        harness registra no ExecutionReport — precisa acompanhar a sessão, não
        o processo.
        """
        anterior = cb.state.get(_CHAVE_ITERACAO)
        atual = (anterior + 1) if isinstance(anterior, int) else 1
        cb.state[_CHAVE_ITERACAO] = atual
        return atual

    # ------------------------------------------------------------------
    # Construção de eventos
    # ------------------------------------------------------------------

    @staticmethod
    def _drenar_actions(cb: CallbackContext, *, escalate: bool = False) -> EventActions:
        """Transfere o state_delta pendente para um `EventActions` do evento.

        Cada Event leva o seu próprio objeto de actions: reaproveitar
        `cb.actions` faria dois eventos compartilharem a mesma instância
        mutável, e as escritas posteriores alterariam retroativamente um evento
        já emitido.
        """
        delta = dict(cb.actions.state_delta)
        cb.actions.state_delta.clear()
        return EventActions(state_delta=delta, escalate=escalate)

    def _evento_texto(
        self,
        ctx: InvocationContext,
        texto: str,
        cb: CallbackContext,
        *,
        escalate: bool = False,
    ) -> Event:
        return Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=texto)]),
            actions=self._drenar_actions(cb, escalate=escalate),
        )
