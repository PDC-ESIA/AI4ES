"""Escritor da memória incremental — 4º e último passo do coding_review_pipeline.

É o passo que fecha o ciclo: tudo que o pipeline aprendeu nesta run vira item de
memória para a próxima. Roda **uma vez por run**, depois do reviewer, quando o
veredito e o `ExecutionReport` já estão no estado da sessão.

## Por que um BaseAgent custom, e não um LlmAgent

Um `LlmAgent` aqui reproduziria os dois modos de falha que já derrubaram este
pipeline em execuções reais:

1. *"o agente anuncia a ação e encerra o turno"* — o LlmAgent termina a vez ao
   devolver texto sem function call, e a escrita nunca aconteceria;
2. *"`output_schema` é decorativo neste provedor"* — sob Copilot o
   `response_format` é descartado e a validação Pydantic derruba a run.

Aqui o controle de fluxo é Python puro: só a **destilação** consulta o LLM, e
mesmo ela degrada para lista vazia em qualquer falha. Julgamento e escrita são
determinísticos. É a mesma escolha que o `cr_reviewer` já fez ao persistir por
`after_agent_callback` em vez de por tool ("elimina o risco de modo narrador").

## Contrato de entrada (tudo já existe no estado, nada é recalculado)

- `state['validation']` — `ValidationVerdict` do `implementation_validator`
- `state['report_path']` — `ExecutionReport` gravado pelo harness
- `coder/tasks/_macro_context.json` — de onde sai a `tech_stack` (escopo do item)
"""

from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.genai import types

from shared.memory import (
    MemoryOutcome,
    MemoryProvenance,
    MemoryStore,
    carregar_report,
    destilar,
    error_codes_do_report,
    julgar_lote,
    memoria_habilitada,
    montar_trajetoria,
    normalizar_status,
)
from shared.workspace import get_agent_workspace

logger = logging.getLogger(__name__)


def _normalizar_stack(bruto) -> str:
    """Coage o `tech_stack` do contrato a uma string única.

    O schema permite lista (`["Python", "FastAPI", ...]`) ou string; o escopo do
    item de memória precisa de uma forma canônica para comparar.
    """
    if isinstance(bruto, (list, tuple)):
        return ", ".join(str(s) for s in bruto).strip()
    return str(bruto or "").strip()


def _do_macro_context() -> tuple[str, str]:
    """Fonte primária: o `_macro_context.json` gravado pelo context engineer."""
    try:
        macro = get_agent_workspace("cr_context_engineer") / "_macro_context.json"
        if not macro.is_file():
            return "", ""
        dados = json.loads(macro.read_text(encoding="utf-8"))
        return (
            _normalizar_stack(dados.get("tech_stack")),
            str(dados.get("summary") or "").strip(),
        )
    except Exception:
        logger.warning("[MEMORY] _macro_context.json ilegível.")
        return "", ""


def _do_state(state) -> tuple[str, str]:
    """Fonte de reserva: o `TasksOutput` que o context engineer deixou no estado.

    Existe por causa de um modo de falha real, observado em 13/08: o
    `cr_context_engineer` **narrou** o `TasksOutput` como texto em vez de chamar
    `tool_salvar_task_cr`, então `_macro_context.json` nunca foi para o disco —
    mas o JSON, com `tech_stack` e `summary`, ficou em `state['tasks']` pelo
    `output_key`.

    Sem esta reserva, toda lição de uma run assim vai para quarentena por falta
    de escopo, e a memória fica cega justamente nas runs que mais têm a ensinar.
    """
    bruto = state.get("tasks") if hasattr(state, "get") else None
    if not bruto:
        return "", ""

    if isinstance(bruto, str):
        # O texto pode vir cercado em ```json — o mesmo motivo pelo qual o
        # parser de `extract.py` é tolerante.
        texto = bruto.strip()
        if texto.startswith("```"):
            texto = texto.split("```")[1] if "```" in texto[3:] else texto[3:]
            texto = texto.lstrip("json").strip()
        try:
            bruto = json.loads(texto)
        except Exception:
            return "", ""

    if not isinstance(bruto, dict):
        return "", ""

    macro = bruto.get("macro_context") or {}
    if not isinstance(macro, dict):
        return "", ""

    return (
        _normalizar_stack(macro.get("tech_stack")),
        str(macro.get("summary") or "").strip(),
    )


def _tech_stack_e_objetivo(state) -> tuple[str, str]:
    """Resolve o escopo (`tech_stack`) e o objetivo da run.

    A `tech_stack` vira o **escopo** do item de memória — sem ela o `judge` não
    promove, porque um item sem escopo seria injetado em qualquer projeto.
    Tenta o disco primeiro e o estado da sessão depois; devolve vazio só quando
    nenhuma das duas fontes tem o contrato, e aí a quarentena é a resposta certa.
    """
    stack, objetivo = _do_macro_context()
    if stack:
        return stack, objetivo

    stack_state, objetivo_state = _do_state(state)
    if stack_state:
        logger.info(
            "[MEMORY] tech_stack veio de state['tasks'] — o context engineer não "
            "gravou o _macro_context.json nesta run."
        )
    return stack_state, objetivo or objetivo_state


def _criterios_reprovados(validation: dict) -> list[str]:
    """Critérios de aceite que não ficaram 'atendido' no veredito.

    É o segundo sinal de verdade de campo, ao lado do `error_code` — e o único
    disponível na **reprovação semântica**, em que o harness passa em todos os
    estágios e quem reprova é o `implementation_validator`, nos critérios.
    Emitido por `montar_veredito()`, sem LLM no caminho.
    """
    if not validation:
        return []
    return [
        str(cv.get("criterion", "")).strip()
        for cv in validation.get("criteria_verdicts", [])
        if normalizar_status(cv.get("status")) != "atendido"
        and str(cv.get("criterion", "")).strip()
    ]


class _MemoryWriter(BaseAgent):
    """Destila, julga e grava a memória da run corrente."""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        resumo = self._executar(ctx)
        yield Event(
            author=self.name,
            invocation_id=ctx.invocation_id,
            content=types.Content(role="model", parts=[types.Part(text=resumo)]),
        )

    def _executar(self, ctx: InvocationContext) -> str:
        """Todo o trabalho, em Python. Devolve o texto de resumo do turno.

        Nunca levanta: a memória é um acessório do pipeline. Uma run que
        produziu código bom não pode ser marcada como falha porque a
        destilação não respondeu.
        """
        if not memoria_habilitada():
            return "[memória] Desabilitada por AI4ES_MEMORY_ENABLED=0 — nada gravado."

        try:
            return self._ciclo(ctx)
        except Exception as exc:  # noqa: BLE001 — ver docstring
            logger.exception("[MEMORY] Falha no ciclo de escrita da memória.")
            return f"[memória] Falhou sem afetar o pipeline: {exc}"

    def _ciclo(self, ctx: InvocationContext) -> str:
        state = ctx.session.state
        validation = state.get("validation") or {}
        report_path = state.get("report_path")
        report = carregar_report(report_path)

        if not report and not validation:
            return (
                "[memória] Nada a aprender: a run não produziu ExecutionReport "
                "nem veredito (provavelmente parou antes da execução)."
            )

        # O desfecho vem do veredito determinístico, não da opinião do LLM.
        # Sem veredito, cai no status técnico do harness. `normalizar_status`
        # é obrigatório aqui: no estado VIVO da sessão o campo é o Enum, e
        # comparar sem normalizar classificava run aprovada como falha.
        status_veredito = normalizar_status(validation.get("status"))
        if status_veredito:
            aprovado = status_veredito == "aprovado"
        else:
            aprovado = normalizar_status(report.get("overall_status")) == "sucesso"

        outcome = MemoryOutcome.SUCESSO if aprovado else MemoryOutcome.FALHA
        codigos = error_codes_do_report(report)
        criterios = _criterios_reprovados(validation)
        stack, objetivo = _tech_stack_e_objetivo(state)

        trajetoria = montar_trajetoria(
            report, validation, tech_stack=stack, objetivo=objetivo
        )

        provenance = MemoryProvenance(
            run_id=str(getattr(ctx.session, "id", "") or "desconhecida"),
            task_id=str(state.get("task_id") or report.get("work_item_id") or ""),
            iteration=report.get("iteration"),
            report_path=str(report_path) if report_path else None,
            model=str(state.get("_memory_model") or ""),
        )

        # Única chamada de LLM do passo. Prompts verbatim do ReasoningBank.
        candidatos = destilar(
            trajetoria,
            outcome,
            error_codes=codigos,
            unmet_criteria=criterios,
            tech_stack=stack,
            provenance=provenance,
        )
        if not candidatos:
            return "[memória] O destilador não produziu nenhum item para esta run."

        julgados = julgar_lote(candidatos, veredito_status=status_veredito)

        store = MemoryStore()
        novos = store.append(julgados)
        stats = store.stats()

        promovidos = sum(1 for i in novos if i.status.value == "promovido")
        linhas = [
            f"[memória] Run {outcome.value} · {len(candidatos)} item(ns) destilado(s), "
            f"{len(novos)} novo(s), {promovidos} promovido(s).",
            f"[memória] Banco: {store.path} — {stats}",
        ]
        for item in novos:
            linhas.append(f"  · [{item.status.value}] {item.title} — {item.judge_reason}")

        resumo = "\n".join(linhas)
        logger.info(resumo)
        return resumo


agent = _MemoryWriter(
    name="cr_memory_writer",
    description=(
        "Destila a trajetória desta run em itens de memória (protocolo "
        "ReasoningBank), julga cada um contra a evidência do harness e grava "
        "os aprovados fora do repositório, para as runs seguintes."
    ),
)
