"""TaskIterator — camada externa que itera as tasks, envolvendo o loop de correção.

Descoberta ao investigar um pipeline real: o `context_engineer` gera N tasks, mas
o `LoopAgent[coder, executor]` sempre foi um loop de CORREÇÃO de UMA implementação
(repete enquanto reprova, encerra ao aprovar/estagnar) — nunca houve uma camada
que iterasse sobre as tasks. Esta é essa camada.

NÃO toca o executor (Opção B): a lógica de avançar entre tasks fica AQUI, externa.
O executor continua validando a task que está em `state['task_id']`; quem troca a
task é esta camada. O executor não sabe que existe uma fila.

Determinístico, sem LLM — mesmo espírito do `ExecutorOrchestrator`. Para cada task,
em ordem topológica estável a partir da ordem canônica: prepara o state (seta
`task_id` e `current_task`, zera as chaves de ciclo-de-task) e chama primeiro o
executor sobre o sistema completo já construído. Apenas após reprovação roda o
`code_execute_loop[coder de correção, executor]`. Lê `state['validation']['status']`:
`aprovado` segue para a próxima; qualquer outro (teto/estagnação) interrompe o
processamento das tasks e entrega o resultado parcial ao reviewer.

O estado transitório canônico vive em `state['task_runtime']`, substituído por
inteiro na troca de task. As chaves planas são mantidas como ponte de
compatibilidade com coder/executor/validator. Cada desfecho entra em
`state['task_results']` e o agregado em `state['task_iteration_summary']`.
`failure_policy=fail_fast` é o padrão explícito; `continue_independent` permite
prosseguir apenas com tasks cujas dependências estejam aprovadas.

Sobre `escalate`: o executor emite `escalate=True` para encerrar o LoopAgent
interno (desejado, inalterado). Esse escalate borbulha, mas o `SequentialAgent` de
cima IGNORA escalate (só o LoopAgent o respeita) — então ele não pula o reviewer,
e a progressão entre tasks é decidida AQUI pela leitura do state, não pelo escalate.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.genai import types
from pydantic import ConfigDict, PrivateAttr

from shared.workspace import get_agent_workspace

logger = logging.getLogger(__name__)

_CHAVE_TASK_ID = "task_id"
_CHAVE_RUNTIME = "task_runtime"
_CHAVE_RESULTADOS = "task_results"
_CHAVE_RESUMO = "task_iteration_summary"
_POLITICAS_FALHA = {"fail_fast", "continue_independent"}
_TASK_ID_RE = re.compile(r"^TASK-\d{3,}$")
_MARCADOR_CONTEXTO_TASK = "[AI4ES_TASK_CONTEXT_START]"
_DIRETORIOS_IGNORADOS_SNAPSHOT = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}
_LIMITE_ARQUIVOS_SNAPSHOT = 200

# Chaves planas legadas de ciclo de task, limpas ao avançar (`task_id` é setada,
# não limpa). O runtime canônico é substituído integralmente; esta lista existe
# apenas enquanto coder/executor/validator ainda consomem as chaves históricas.
_CHAVES_LIMPAR = (
    "validation",                 # veredito da task anterior
    "validation_raw",             # saída crua do validador (output_key)
    "error_report",               # feedback de erro ao coder da task anterior
    "execution_result",           # resumo textual do desfecho anterior
    "report_path",                # caminho do report da task anterior
    "stagnation_key",             # _CHAVE_CHAVE_ESTAGNACAO
    "stagnation_count",           # _CHAVE_CONTAGEM_ESTAGNACAO  (PRECISA zerar)
    "executor_iteration",         # _CHAVE_ITERACAO (contador de iteração, por-task)
    "test_command_resolution",    # comando resolvido no state (NÃO o cache em disco)
    "test_command_resolution_raw",
    "dockerfile_resolution",
    "dockerfile_resolution_raw",
)


def _novo_runtime(task: dict[str, Any], indice: int, total: int) -> dict[str, Any]:
    """Cria todo o estado transitório de uma task em um único namespace.

    As chaves planas continuam sendo espelhadas temporariamente porque coder,
    executor e validator ainda as consomem. `task_runtime` é a fonte agregada e
    substituível; isso evita depender de uma blacklist para observar o ciclo.
    """
    return {
        "task_id": task["id"],
        "task": task,
        "index": indice,
        "total": total,
        "status": "executando",
        "attempts": 0,
        "validation": None,
        "execution_result": None,
        "error_report": None,
        "report_path": None,
        "stagnation": {"key": None, "count": None},
        "resolutions": {"dockerfile": None, "test_command": None},
    }


def _capturar_runtime(state: Any, status: str) -> dict[str, Any]:
    """Consolida no namespace da task os valores produzidos pelas peças legadas."""
    runtime = dict(state.get(_CHAVE_RUNTIME) or {})
    runtime.update(
        {
            "status": status,
            "attempts": state.get("executor_iteration") or 0,
            "validation": state.get("validation"),
            "execution_result": state.get("execution_result"),
            "error_report": state.get("error_report"),
            "report_path": state.get("report_path"),
            "stagnation": {
                "key": state.get("stagnation_key"),
                "count": state.get("stagnation_count"),
            },
            "resolutions": {
                "dockerfile": state.get("dockerfile_resolution"),
                "test_command": state.get("test_command_resolution"),
            },
        }
    )
    return runtime


def _resultado_da_task(runtime: dict[str, Any]) -> dict[str, Any]:
    """Projeção compacta e estável do runtime para observabilidade/review."""
    validation = runtime.get("validation") or {}
    return {
        "task_id": runtime.get("task_id"),
        "index": runtime.get("index"),
        "status": runtime.get("status"),
        "attempts": runtime.get("attempts", 0),
        "report_path": runtime.get("report_path"),
        "blocking_reason": validation.get("blocking_reason"),
    }


def _snapshot_workspace(workspace: Path) -> dict[str, Any]:
    """Lista o estado estrutural atual sem serializar conteúdo de arquivos."""
    if not workspace.exists():
        return {"root": str(workspace), "files": [], "omitted": 0}

    arquivos = sorted(
        str(path.relative_to(workspace))
        for path in workspace.rglob("*")
        if path.is_file()
        and not any(
            parte in _DIRETORIOS_IGNORADOS_SNAPSHOT
            for parte in path.relative_to(workspace).parts
        )
    )
    return {
        "root": str(workspace),
        "files": arquivos[:_LIMITE_ARQUIVOS_SNAPSHOT],
        "omitted": max(len(arquivos) - _LIMITE_ARQUIVOS_SNAPSHOT, 0),
    }


def _contexto_compacto_task(
    state: Any,
    task: dict[str, Any],
    tasks: list[dict[str, Any]],
) -> str:
    """Monta a âncora explícita que substitui a conversa de tasks anteriores."""
    saida = _como_dict(state.get("tasks")) or {}
    resultados = list(state.get(_CHAVE_RESULTADOS) or [])
    tasks_por_id = {item["id"]: item for item in tasks}
    anteriores = []
    for resultado in resultados:
        contrato = tasks_por_id.get(resultado.get("task_id"), {})
        anteriores.append(
            {
                **resultado,
                "description": contrato.get("description"),
                "outputs": (contrato.get("contract") or {}).get("outputs", []),
                "interfaces": (contrato.get("contract") or {}).get(
                    "interfaces", []
                ),
            }
        )

    contexto = {
        "current_task_contract": task,
        "previous_tasks_summary": anteriores,
        "workspace_snapshot": _snapshot_workspace(
            get_agent_workspace("cr_coder")
        ),
        "last_error_report_for_current_task": None,
        "architectural_context": {
            "macro_context": saida.get("macro_context") or {},
            "plan_file": "PLAN.md",
            "guidance": (
                "O workspace persiste entre tasks. Leia PLAN.md e somente os "
                "arquivos relevantes usando as tools disponíveis."
            ),
        },
    }
    return (
        f"{_MARCADOR_CONTEXTO_TASK}\n"
        + json.dumps(contexto, ensure_ascii=False, sort_keys=True)
    )


def _resumo(total: int, resultados: list[dict[str, Any]], outcome: str) -> dict[str, Any]:
    aprovadas = sum(item.get("status") == "aprovado" for item in resultados)
    bloqueadas = sum(item.get("status") != "aprovado" for item in resultados)
    return {
        "outcome": outcome,
        "total": total,
        "processed": len(resultados),
        "approved": aprovadas,
        "blocked": bloqueadas,
        "pending": max(total - len(resultados), 0),
    }

def _como_dict(valor: Any) -> dict[str, Any] | None:
    """Normaliza dict/Pydantic/JSON para dict sem assumir a forma do ADK."""
    if isinstance(valor, dict):
        return valor
    if hasattr(valor, "model_dump"):
        convertido = valor.model_dump()
        return convertido if isinstance(convertido, dict) else None
    if isinstance(valor, str):
        try:
            convertido = json.loads(valor)
        except ValueError:
            return None
        return convertido if isinstance(convertido, dict) else None
    return None


def _carregar_tasks(state: Any, tasks_dir: Path) -> list[dict[str, Any]]:
    """Carrega a fila canônica do state e valida os contratos persistidos.

    A ordem de `state['tasks']['tasks']` é preservada. O filesystem não define a
    fila: apenas comprova que cada contrato foi persistido e que o id interno
    coincide com o nome usado pelo harness (`{task_id}.json`).
    """
    saida = _como_dict(state.get("tasks"))
    if saida is None or not isinstance(saida.get("tasks"), list):
        raise ValueError("state['tasks']['tasks'] ausente ou inválido")

    tasks: list[dict[str, Any]] = []
    ids: set[str] = set()
    for posicao, valor in enumerate(saida["tasks"], start=1):
        task = _como_dict(valor)
        task_id = task.get("id") if task else None
        if not isinstance(task_id, str) or not task_id:
            raise ValueError(f"task na posição {posicao} possui id ausente ou inválido")
        if not _TASK_ID_RE.fullmatch(task_id):
            raise ValueError(
                f"task na posição {posicao} possui id fora do formato TASK-NNN: "
                f"{task_id!r}"
            )
        if task_id in ids:
            raise ValueError(f"id de task duplicado: {task_id}")
        ids.add(task_id)

        dependencias = task.get("depends_on", [])
        if not isinstance(dependencias, list):
            raise ValueError(f"depends_on de {task_id} deve ser uma lista")
        if len(dependencias) != len(set(dependencias)):
            raise ValueError(f"dependências duplicadas em {task_id}")
        for dependencia in dependencias:
            if not isinstance(dependencia, str) or not _TASK_ID_RE.fullmatch(dependencia):
                raise ValueError(
                    f"dependência de {task_id} fora do formato TASK-NNN: "
                    f"{dependencia!r}"
                )
            if dependencia == task_id:
                raise ValueError(f"task {task_id} não pode depender de si própria")
        task = {**task, "depends_on": dependencias}

        task_file = tasks_dir / f"{task_id}.json"
        try:
            persistida = json.loads(task_file.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ValueError(f"contrato não persistido para {task_id}: {task_file}") from exc
        except (OSError, ValueError) as exc:
            raise ValueError(f"contrato inválido para {task_id}: {task_file}") from exc
        if not isinstance(persistida, dict) or persistida.get("id") != task_id:
            recebido = persistida.get("id") if isinstance(persistida, dict) else None
            raise ValueError(
                f"id interno divergente em {task_file}: esperado {task_id}, "
                f"recebido {recebido}"
            )
        dependencias_persistidas = persistida.get("depends_on", [])
        if dependencias_persistidas != dependencias:
            raise ValueError(
                f"depends_on divergente em {task_file}: esperado {dependencias}, "
                f"recebido {dependencias_persistidas}"
            )
        tasks.append(task)

    por_id = {task["id"]: task for task in tasks}
    for task in tasks:
        ausentes = set(task["depends_on"]) - set(por_id)
        if ausentes:
            raise ValueError(
                f"task {task['id']} depende de IDs inexistentes: {sorted(ausentes)}"
            )

    # Ordenação topológica estável: respeita dependências e preserva a ordem
    # canônica original entre tasks sem relação entre si.
    ordenadas: list[dict[str, Any]] = []
    visitando: set[str] = set()
    visitados: set[str] = set()

    def visitar(task_id: str) -> None:
        if task_id in visitando:
            raise ValueError(f"ciclo de dependências detectado em {task_id}")
        if task_id in visitados:
            return
        visitando.add(task_id)
        for dependencia in por_id[task_id]["depends_on"]:
            visitar(dependencia)
        visitando.remove(task_id)
        visitados.add(task_id)
        ordenadas.append(por_id[task_id])

    for task in tasks:
        visitar(task["id"])
    return ordenadas


def _resolver_politica_falha(state: Any) -> str:
    """Lê a política explícita da saída; ausência mantém o contrato fail-fast."""
    saida = _como_dict(state.get("tasks")) or {}
    politica = saida.get("failure_policy", "fail_fast")
    if politica not in _POLITICAS_FALHA:
        raise ValueError(
            f"failure_policy inválida: {politica!r}; esperado "
            "'fail_fast' ou 'continue_independent'"
        )
    return politica


class TaskIterator(BaseAgent):
    """Itera a fila: executor primeiro; coder só entra após reprovação."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    _initial_executor: BaseAgent = PrivateAttr()
    _max_executor_attempts: int = PrivateAttr()

    def __init__(
        self,
        *,
        code_execute_loop: BaseAgent,
        initial_executor: BaseAgent,
        max_executor_attempts: int = 5,
        **kwargs,
    ) -> None:
        """`code_execute_loop`: o `LoopAgent[coder, executor]` já montado, INJETADO
        (não reconstruído). Vira o único sub-agente desta camada — o parent único
        que o ADK exige é satisfeito porque só esta camada o adota.

        `initial_executor` é a mesma instância do executor dentro do loop, usada
        diretamente para que cada task seja validada antes de qualquer correção.
        Ela não é readotada em `sub_agents`, preservando o parent único do ADK.
        """
        if max_executor_attempts < 1:
            raise ValueError("max_executor_attempts deve ser pelo menos 1")
        super().__init__(sub_agents=[code_execute_loop], **kwargs)
        self._initial_executor = initial_executor
        self._max_executor_attempts = max_executor_attempts

    @property
    def code_execute_loop(self) -> BaseAgent:
        return self.sub_agents[0]

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        cb = CallbackContext(ctx)

        tasks_dir = get_agent_workspace("cr_context_engineer")
        try:
            tasks = _carregar_tasks(cb.state, tasks_dir)
            politica_falha = _resolver_politica_falha(cb.state)
        except ValueError as exc:
            cb.state["task_iteration_status"] = "concluido"
            cb.state["task_iteration_outcome"] = "erro_configuracao"
            cb.state["task_iteration_error"] = str(exc)
            cb.state[_CHAVE_RUNTIME] = None
            cb.state[_CHAVE_RESULTADOS] = []
            cb.state[_CHAVE_RESUMO] = _resumo(0, [], "erro_configuracao")
            yield self._evento(
                ctx,
                f"Processamento de tasks não iniciado: {exc}. O reviewer receberá "
                "este bloqueio de configuração e o workspace disponível.",
                cb,
            )
            return
        if not tasks:
            cb.state["task_iteration_status"] = "concluido"
            cb.state["task_iteration_outcome"] = "sem_tasks"
            cb.state["task_iteration_error"] = "nenhuma task gerada"
            cb.state[_CHAVE_RUNTIME] = None
            cb.state[_CHAVE_RESULTADOS] = []
            cb.state[_CHAVE_RESUMO] = _resumo(0, [], "sem_tasks")
            yield self._evento(
                ctx,
                "Processamento de tasks não iniciado: nenhuma task foi gerada. O "
                "reviewer receberá este bloqueio e o workspace disponível.",
                cb,
            )
            return

        total = len(tasks)
        cb.state["project_initialized"] = bool(cb.state.get("project_initialized"))
        cb.state["task_iteration_status"] = "executando"
        cb.state["task_iteration_outcome"] = None
        cb.state["task_iteration_error"] = None
        cb.state["task_failure_policy"] = politica_falha
        cb.state[_CHAVE_RESULTADOS] = []
        cb.state[_CHAVE_RESUMO] = _resumo(total, [], "executando")
        for i, task in enumerate(tasks, start=1):
            task_id = task["id"]
            # Runtime canônico substituído integralmente a cada task. As chaves
            # planas abaixo são apenas a ponte de compatibilidade com os agentes.
            cb.state[_CHAVE_RUNTIME] = _novo_runtime(task, i, total)
            cb.state[_CHAVE_TASK_ID] = task_id
            cb.state["current_task"] = task
            cb.state["current_task_index"] = i
            cb.state["total_tasks"] = total
            for chave in _CHAVES_LIMPAR:
                cb.state[chave] = None

            # Na política de continuidade, uma task só executa quando TODAS as
            # dependências terminaram aprovadas. Independentes continuam.
            resultados_atuais = list(ctx.session.state.get(_CHAVE_RESULTADOS) or [])
            status_por_id = {
                item.get("task_id"): item.get("status") for item in resultados_atuais
            }
            dependencias_bloqueadas = [
                dependencia
                for dependencia in task.get("depends_on", [])
                if status_por_id.get(dependencia) != "aprovado"
            ]
            if dependencias_bloqueadas:
                motivo = (
                    "dependências não aprovadas: " + ", ".join(dependencias_bloqueadas)
                )
                validation = {
                    "status": "bloqueado_dependencia",
                    "blocking_reason": motivo,
                }
                cb.state["validation"] = validation
                runtime = dict(ctx.session.state[_CHAVE_RUNTIME])
                runtime.update(
                    {
                        "status": "bloqueado_dependencia",
                        "validation": validation,
                        "execution_result": motivo,
                    }
                )
                cb.state[_CHAVE_RUNTIME] = runtime
                resultados_atuais.append(_resultado_da_task(runtime))
                cb.state[_CHAVE_RESULTADOS] = resultados_atuais
                cb.state[_CHAVE_RESUMO] = _resumo(total, resultados_atuais, "executando")
                yield self._evento(
                    ctx,
                    f"Task {i}/{total}: {task_id} não executada — {motivo}.",
                    cb,
                )
                continue
            yield self._evento(
                self._contexto_da_task(ctx, task_id),
                (
                    f"Task {i}/{total}: {task_id} — iniciando loop de correção.\n"
                    + _contexto_compacto_task(ctx.session.state, task, tasks)
                ),
                cb,
                role="user",
            )

            # Primeira tentativa: o sistema já foi construído pelo coder inicial.
            # O harness precisa produzir evidência antes que o coder de correção
            # faça qualquer mudança.
            task_ctx = self._contexto_da_task(ctx, task_id)
            async for event in self._initial_executor.run_async(task_ctx):
                yield event

            # Reprovou: agora o ErrorReport orienta o coder. Cada iteração do
            # loop executa coder → executor; aprovação/estagnação do executor
            # emite escalate e encerra somente este loop interno.
            validation = ctx.session.state.get("validation") or {}
            if (
                validation.get("status") != "aprovado"
                and self._max_executor_attempts > 1
            ):
                async for event in self.code_execute_loop.run_async(task_ctx):
                    yield event

            # --- desfecho: só o veredito decide (como no executor) ---
            validation = ctx.session.state.get("validation") or {}
            if validation.get("status") == "aprovado":
                runtime = _capturar_runtime(ctx.session.state, "aprovado")
                cb.state[_CHAVE_RUNTIME] = runtime
                resultados = list(ctx.session.state.get(_CHAVE_RESULTADOS) or [])
                resultados.append(_resultado_da_task(runtime))
                cb.state[_CHAVE_RESULTADOS] = resultados
                cb.state[_CHAVE_RESUMO] = _resumo(total, resultados, "executando")
                cb.state["project_initialized"] = True
                continue

            motivo = validation.get("blocking_reason") or ""
            status_task = validation.get("status") or "inconclusivo"
            runtime = _capturar_runtime(ctx.session.state, status_task)
            cb.state[_CHAVE_RUNTIME] = runtime
            resultados = list(ctx.session.state.get(_CHAVE_RESULTADOS) or [])
            resultados.append(_resultado_da_task(runtime))
            cb.state[_CHAVE_RESULTADOS] = resultados
            cb.state["project_initialized"] = True
            if politica_falha == "fail_fast":
                cb.state["task_iteration_status"] = "concluido"
                cb.state["task_iteration_outcome"] = "parcial"
                cb.state["task_iteration_error"] = motivo or "task não aprovada"
                cb.state[_CHAVE_RESUMO] = _resumo(total, resultados, "parcial")
                yield self._evento(
                    ctx,
                    (
                        f"Processamento das tasks interrompido em {task_id} pela "
                        f"política fail_fast: task não aprovada após o loop de "
                        f"correção. {motivo} As tasks seguintes ficaram pendentes; "
                        f"o reviewer analisará o resultado parcial."
                    ).rstrip(),
                    cb,
                )
                return

            yield self._evento(
                ctx,
                (
                    f"Task {task_id} não aprovada. Pela política "
                    "continue_independent, apenas tasks independentes continuarão."
                ),
                cb,
            )

        resultados = list(ctx.session.state.get(_CHAVE_RESULTADOS) or [])
        cb.state["task_iteration_status"] = "concluido"
        todas_aprovadas = len(resultados) == total and all(
            item.get("status") == "aprovado" for item in resultados
        )
        outcome = "aprovado" if todas_aprovadas else "parcial"
        cb.state["task_iteration_outcome"] = outcome
        cb.state["task_iteration_error"] = (
            None if todas_aprovadas else "uma ou mais tasks não foram aprovadas"
        )
        cb.state[_CHAVE_RESUMO] = _resumo(total, resultados, outcome)
        texto = (
            f"Todas as {total} tasks foram aprovadas."
            if todas_aprovadas
            else "Processamento concluído parcialmente: tasks independentes foram "
            "avaliadas e dependentes de falhas foram bloqueadas; o reviewer "
            "analisará o resultado agregado."
        )
        yield self._evento(ctx, texto, cb)

    # ------------------------------------------------------------------
    # Eventos (mesmo padrão do ExecutorOrchestrator: o state_delta viaja neles)
    # ------------------------------------------------------------------

    @staticmethod
    def _drenar_state_delta(cb: CallbackContext) -> EventActions:
        delta = dict(cb.actions.state_delta)
        cb.actions.state_delta.clear()
        return EventActions(state_delta=delta)

    def _evento(
        self,
        ctx: InvocationContext,
        texto: str,
        cb: CallbackContext,
        *,
        role: str = "model",
    ) -> Event:
        return Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            branch=ctx.branch,
            content=types.Content(role=role, parts=[types.Part(text=texto)]),
            actions=self._drenar_state_delta(cb),
        )

    @staticmethod
    def _contexto_da_task(
        ctx: InvocationContext, task_id: str
    ) -> InvocationContext:
        """Cria uma branch irmã por task mantendo sessão e state compartilhados."""
        sufixo = f"task_iterator.task_{task_id.replace('-', '_')}"
        branch = f"{ctx.branch}.{sufixo}" if ctx.branch else sufixo
        return ctx.model_copy(update={"branch": branch})
