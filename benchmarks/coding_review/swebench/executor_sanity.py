"""Sanidade do ambiente do EXECUTOR com a solução oficial — sem LLM.

Pergunta que responde: "se o coder acertasse tudo, o harness do executor
conseguiria comprovar?". Para cada instância:

1. prepara o workspace exatamente como o run (imagem oficial, fotografia,
   `Dockerfile`/`.dockerignore`/`run.json` do benchmark);
2. aplica o patch OFICIAL e o `test_patch` oficial — o coder perfeito;
3. declara no `run.json` o comando de teste oficial, extraído do `eval_script`
   do dataset (o mesmo que o harness oficial usa);
4. roda o harness de PRODUÇÃO do executor (`executar_harness_validacao`).

Com a solução certa, `overall_status == "sucesso"` é o que o validador precisaria
para aprovar. Quando não sai sucesso, a causa é o AMBIENTE do executor (limite de
memória, timeout de 120 s por comando, teste que já falha naquele arquivo) — e
não o LLM. O resultado mostra quantas aprovações corretas o executor consegue
dar, no máximo, e separa esse ruído das métricas do run.

Nada disto chega ao loop: é uma checagem do ambiente, fora do benchmark medido.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from . import environment, snapshot
from .contract import TASK_ID
from .dataset import SWEInstance

_INICIO_TESTES = ": '>>>>> Start Test Output'"
_FIM_TESTES = ": '>>>>> End Test Output'"

RESULTADO_SUCESSO = "sucesso"
RESULTADO_TIMEOUT = "timeout_do_comando_de_teste"
RESULTADO_MEMORIA = "sem_memoria"
RESULTADO_TESTES_FALHARAM = "testes_falharam"
RESULTADO_BUILD = "falha_no_build"
RESULTADO_OUTRO = "outra_falha"
RESULTADO_PREPARACAO = "falha_na_preparacao"
RESULTADO_SEM_COMANDO = "sem_comando_de_teste"

# `timeout(1)` sai com 124; o kernel mata por falta de memória com SIGKILL (137).
_EXIT_OOM = 137
_TAMANHO_SAIDA = 3000


def official_test_command(eval_script: str) -> str | None:
    """Comando de teste oficial: a linha entre os marcadores do `eval_script`."""
    linhas = eval_script.splitlines()
    for indice, linha in enumerate(linhas):
        if linha.strip() == _INICIO_TESTES:
            for seguinte in linhas[indice + 1:]:
                if seguinte.strip() == _FIM_TESTES:
                    return None
                if seguinte.strip():
                    return seguinte.strip()
    return None


def classify_report(report: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Classifica o `ExecutionReport` do harness e extrai o detalhe útil."""
    estagios = {s.get("stage"): s for s in report.get("stages") or [] if isinstance(s, dict)}
    testes = estagios.get("testes_automatizados") or {}
    resultados = (testes.get("evidence") or {}).get("resultados") or []
    detalhe = {
        "overall_status": report.get("overall_status"),
        "status_testes": testes.get("status"),
        "exit_codes": [r.get("exit_code") for r in resultados if isinstance(r, dict)],
        "falhas_de_estagio": {
            nome: s.get("error_code")
            for nome, s in estagios.items()
            if s.get("status") in ("falha", "erro")
        },
        # Final da saída de cada comando de teste que falhou: sem isso não dá
        # para distinguir teste reprovado de erro de coleta ou de ambiente.
        "saidas_com_falha": [
            {
                "comando": r.get("comando"),
                "exit_code": r.get("exit_code"),
                "saida_tail": str(r.get("saida_tail") or "")[-_TAMANHO_SAIDA:],
            }
            for r in resultados
            if isinstance(r, dict) and r.get("exit_code") not in (0, None)
        ],
    }
    implantacao_ev = (estagios.get("implantacao_artefato") or {}).get("evidence") or {}
    if (estagios.get("implantacao_artefato") or {}).get("status") in ("falha", "erro"):
        detalhe["build_logs_tail"] = str(implantacao_ev.get("build_logs_tail") or "")[-_TAMANHO_SAIDA:]
    if report.get("overall_status") == "sucesso":
        return RESULTADO_SUCESSO, detalhe
    if any(isinstance(r, dict) and r.get("timed_out") for r in resultados):
        return RESULTADO_TIMEOUT, detalhe
    if _EXIT_OOM in detalhe["exit_codes"]:
        return RESULTADO_MEMORIA, detalhe
    if testes.get("status") == "falha":
        return RESULTADO_TESTES_FALHARAM, detalhe
    implantacao = estagios.get("implantacao_artefato") or {}
    if implantacao.get("status") in ("falha", "erro"):
        return RESULTADO_BUILD, detalhe
    return RESULTADO_OUTRO, detalhe


def check_instance(
    instance: SWEInstance,
    *,
    coder_src: Path,
    tasks_dir: Path,
    harness: Callable[..., dict],
    write_task: Callable[[Path, SWEInstance], Path],
    client=None,
) -> dict[str, Any]:
    """Roda a sanidade numa instância e devolve o registro (nunca levanta)."""
    registro: dict[str, Any] = {"instance_id": instance.instance_id, "repo": instance.repo}
    comando = official_test_command(instance.eval_script)
    registro["comando_de_teste"] = comando
    if not comando:
        return {**registro, "resultado": RESULTADO_SEM_COMANDO}

    try:
        environment.clear_directory(coder_src.parent)
        environment.seed_workspace(coder_src, instance.image, client=client)
        snapshot.apply_patch(coder_src, instance.patch)
        snapshot.apply_patch(coder_src, instance.test_patch)
        manifesto_path = coder_src / environment.MANIFEST_NAME
        manifesto = json.loads(manifesto_path.read_text(encoding="utf-8"))
        manifesto["test"] = [comando]
        manifesto_path.write_text(json.dumps(manifesto, indent=2) + "\n", encoding="utf-8")
        write_task(tasks_dir, instance)
    except Exception as exc:  # noqa: BLE001 — falha vira dado
        return {**registro, "resultado": RESULTADO_PREPARACAO, "erro": f"{type(exc).__name__}: {exc}"}

    try:
        report = harness(TASK_ID, 1)
    except Exception as exc:  # noqa: BLE001
        return {**registro, "resultado": RESULTADO_OUTRO, "erro": f"{type(exc).__name__}: {exc}"}
    resultado, detalhe = classify_report(report)
    return {**registro, "resultado": resultado, **detalhe}
