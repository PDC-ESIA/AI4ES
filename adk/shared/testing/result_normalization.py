"""Normalização comum dos resultados de integração e E2E."""

from __future__ import annotations

import json
import re
from typing import Any


def _counts(total: int, failed: int = 0, skipped: int = 0) -> dict[str, int]:
    return {
        "total": total,
        "sucessos": max(0, total - failed - skipped),
        "falhas": failed,
        "ignorados": skipped,
    }


def _go_counts(output: str) -> dict[str, int]:
    observed: dict[str, str] = {}
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        test_name = event.get("Test")
        action = event.get("Action")
        if isinstance(test_name, str) and action in {"pass", "fail", "skip"}:
            observed[test_name] = action
    return {
        "total": len(observed),
        "sucessos": sum(value == "pass" for value in observed.values()),
        "falhas": sum(value == "fail" for value in observed.values()),
        "ignorados": sum(value == "skip" for value in observed.values()),
    }


def parse_integration_counts(framework: str, output: str) -> dict[str, int]:
    """Converte os formatos conhecidos para contagens comuns."""
    if framework == "go-testing":
        return _go_counts(output)
    if framework == "pytest":
        passed = int((re.search(r"(\d+) passed", output) or [0, 0])[1])
        failed = int((re.search(r"(\d+) failed", output) or [0, 0])[1])
        skipped = int((re.search(r"(\d+) skipped", output) or [0, 0])[1])
        return _counts(passed + failed + skipped, failed, skipped)
    if framework == "vitest":
        summary = next(
            (
                line
                for line in output.splitlines()
                if re.search(r"\bTests\b", line, re.IGNORECASE)
            ),
            "",
        )
        passed = int((re.search(r"(\d+)\s+passed", summary) or [0, 0])[1])
        failed = int((re.search(r"(\d+)\s+failed", summary) or [0, 0])[1])
        skipped = int((re.search(r"(\d+)\s+skipped", summary) or [0, 0])[1])
        return _counts(passed + failed + skipped, failed, skipped)
    if framework == "jest":
        match = re.search(
            r"Tests:\s*(?:(\d+) failed,\s*)?(?:(\d+) skipped,\s*)?"
            r"(?:(\d+) passed,\s*)?(\d+) total",
            output,
            re.IGNORECASE,
        )
        if match:
            failed, skipped, _passed, total = (
                int(value or 0) for value in match.groups()
            )
            return _counts(total, failed, skipped)
    if framework == "mocha":
        passed = int((re.search(r"(\d+) passing", output) or [0, 0])[1])
        failed = int((re.search(r"(\d+) failing", output) or [0, 0])[1])
        skipped = int((re.search(r"(\d+) pending", output) or [0, 0])[1])
        return _counts(passed + failed + skipped, failed, skipped)
    if framework == "node:test":
        values = {
            key: (
                int(match.group(1))
                if (
                    match := re.search(
                        rf"^.*?\b{key}\s+(\d+)\s*$",
                        output,
                        re.MULTILINE | re.IGNORECASE,
                    )
                )
                else 0
            )
            for key in ("tests", "pass", "fail", "skipped")
        }
        return _counts(values["tests"], values["fail"], values["skipped"])
    if framework.startswith("junit"):
        matches = re.findall(
            r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*"
            r"Errors:\s*(\d+),\s*Skipped:\s*(\d+)",
            output,
        )
        if matches:
            total, failures, errors, skipped = map(int, matches[-1])
            return _counts(total, failures + errors, skipped)
        gradle = re.search(
            r"(\d+) tests completed(?:, (\d+) failed)?(?:, (\d+) skipped)?",
            output,
        )
        if gradle:
            total, failed, skipped = (int(value or 0) for value in gradle.groups())
            return _counts(total, failed, skipped)
        statuses = re.findall(
            r"^.+\s>\s.+\s(PASSED|FAILED|SKIPPED)\s*$",
            output,
            re.MULTILINE,
        )
        if statuses:
            return _counts(
                len(statuses), statuses.count("FAILED"), statuses.count("SKIPPED")
            )
    return _counts(0)


def normalize_integration_execution(raw: dict[str, Any]) -> dict[str, Any]:
    """Normaliza uma execução bruta sem descartar stdout/stderr."""
    framework = str(raw.get("framework") or "desconhecido")
    stdout = str(raw.get("stdout") or "")
    stderr = str(raw.get("stderr") or "")
    output = "\n".join(part for part in (stdout, stderr) if part).strip()
    blocked = raw.get("status") == "bloqueado"
    counts = _counts(0) if blocked else parse_integration_counts(framework, output)
    return_code = raw.get("codigo_saida")
    no_tests = not blocked and return_code == 0 and counts["total"] == 0
    if blocked:
        status = "bloqueado"
    elif return_code == 0 and not no_tests:
        status = "sucesso"
    else:
        status = "falha"

    errors: list[dict[str, Any]] = []
    if blocked:
        errors.extend(raw.get("bloqueios") or [])
    elif no_tests:
        errors.append(
            {
                "codigo": "NENHUM_TESTE_EXECUTADO",
                "mensagem": "O executor terminou sem descobrir testes de integração.",
            }
        )
    elif return_code != 0:
        errors.append(
            {
                "codigo": "TESTES_INTEGRACAO_FALHARAM",
                "mensagem": f"O executor terminou com código {return_code}.",
            }
        )
    return {
        "status": status,
        "tipo_teste": "integracao",
        "perfil": raw.get("perfil"),
        "framework": framework,
        "comando": raw.get("comando") or [],
        "codigo_saida": return_code,
        "testes": counts,
        "saida": output,
        "erros": errors,
        "resultado_bruto": raw,
    }


def _overall_status(successes: int, blocked: int, failures: int) -> str:
    if successes and (blocked or failures):
        return "parcial"
    if failures:
        return "falha"
    if blocked and not successes:
        return "bloqueado"
    if successes:
        return "sucesso"
    return "falha"


def normalize_integration_result(
    inspection: dict[str, Any],
    profile: dict[str, Any],
    raw: dict[str, Any],
) -> dict[str, Any]:
    """Consolida geração e execução de integração no envelope do QA."""
    details: list[dict[str, Any]] = []
    generated_files: list[str] = []
    blockers: list[dict[str, Any]] = []
    executions = 0

    for raw_detail in raw.get("detalhes", []):
        detail = dict(raw_detail)
        generated_path = detail.get("arquivo_gerado")
        if isinstance(generated_path, str) and generated_path:
            generated_files.append(generated_path)
        raw_execution = detail.get("resultado_execucao")
        normalized_execution = (
            normalize_integration_execution(raw_execution)
            if isinstance(raw_execution, dict)
            else None
        )
        if normalized_execution is not None and normalized_execution["status"] != "bloqueado":
            executions += 1

        raw_status = detail.get("status")
        if raw_status == "gerado":
            normalized_status = (
                normalized_execution["status"] if normalized_execution else "sucesso"
            )
        elif raw_status == "bloqueado":
            normalized_status = "bloqueado"
        else:
            normalized_status = "falha"

        if normalized_status == "bloqueado":
            execution_errors = (
                normalized_execution.get("erros", []) if normalized_execution else []
            )
            blockers.extend(
                execution_errors
                or [
                    {
                        "codigo": "ARTEFATO_INTEGRACAO_BLOQUEADO",
                        "mensagem": detail.get("erro") or "Artefato bloqueado.",
                    }
                ]
            )
        details.append(
            {
                **detail,
                "status": normalized_status,
                "resultado_execucao": normalized_execution,
                "resultado_bruto": raw_detail,
            }
        )

    successes = sum(detail["status"] == "sucesso" for detail in details)
    blocked = sum(detail["status"] == "bloqueado" for detail in details)
    failures = sum(detail["status"] == "falha" for detail in details)
    return {
        "status": _overall_status(successes, blocked, failures),
        "tipo_teste": "integracao",
        "inspecao": inspection,
        "perfil": profile,
        "resumo": {
            "total": len(details),
            "sucessos": successes,
            "bloqueados": blocked,
            "falhas": failures,
            "executados": executions,
        },
        "arquivos_gerados": list(dict.fromkeys(generated_files)),
        "detalhes": details,
        "bloqueios": blockers,
        "resultado_bruto": raw,
    }


def _normalize_e2e_execution(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    if not raw:
        return None
    raw_status = str(raw.get("status") or "desconhecido")
    if raw_status == "aprovado":
        status = "sucesso"
    elif raw_status in {"bloqueado_infraestrutura", "timeout", "erro_execucao"}:
        status = "bloqueado"
    else:
        status = "falha"
    failed = int(raw.get("testes_falhos", 0) or 0)
    skipped = int(raw.get("testes_pulados", 0) or 0)
    total = int(raw.get("testes_executados", 0) or 0)
    passed = int(raw.get("testes_aprovados", 0) or 0)
    errors = list(raw.get("falhas") or [])
    if status == "bloqueado" and not errors:
        errors = [
            {
                "codigo": "RUNTIME_E2E_BLOQUEADO",
                "mensagem": " ".join(raw.get("logs_resumidos") or []),
            }
        ]
    return {
        "status": status,
        "tipo_teste": "e2e",
        "framework": "playwright-typescript",
        "comando": raw.get("comando"),
        "codigo_saida": raw.get("codigo_saida"),
        "duracao_ms": int(raw.get("duracao_ms", 0) or 0),
        "testes": {
            "total": total,
            "sucessos": passed,
            "falhas": failed,
            "ignorados": skipped,
        },
        "arquivo_relatorio": raw.get("arquivo_relatorio"),
        "diretorio_artefatos": raw.get("diretorio_artefatos"),
        "saida": "\n".join(raw.get("logs_resumidos") or []),
        "erros": errors,
        "resultado_bruto": raw,
    }


def normalize_e2e_result(
    inspection: dict[str, Any],
    profile: dict[str, Any],
    raw: dict[str, Any],
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Converte o retorno Playwright para o envelope comum do QA."""
    blockers = list(raw.get("bloqueios") or [])
    generated_files = [
        value
        for value in raw.get("arquivos_gerados", [])
        if isinstance(value, str) and value
    ]
    execution = _normalize_e2e_execution(raw.get("resultado_execucao"))
    if execution is not None and execution["status"] == "bloqueado" and not blockers:
        blockers.extend(execution["erros"])
    output_type = str(raw.get("tipo_saida") or "bloqueado")
    artifact_total = len(artifacts)
    scope_count = max(1, artifact_total)

    if execution is not None:
        status = execution["status"]
        successes = artifact_total if status == "sucesso" else 0
        failures = scope_count if status == "falha" else 0
        blocked = scope_count if status == "bloqueado" else 0
        if status == "sucesso" and blockers:
            status = "parcial"
        elif status == "bloqueado" and generated_files:
            status = "parcial"
    elif generated_files:
        status = "parcial" if blockers else "sucesso"
        successes = artifact_total
        failures = 0
        blocked = 0
    elif output_type == "plano_e2e":
        status = "parcial"
        successes = failures = 0
        blocked = scope_count
    else:
        status = "bloqueado"
        successes = failures = 0
        blocked = scope_count

    artifact_ids = [
        str(item.get("id_artefato") or item.get("id") or "SEM_ID")
        for item in artifacts
    ] or ["SEM_ID"]
    if execution is not None:
        detail_status = execution["status"]
    elif generated_files:
        detail_status = "sucesso"
    else:
        detail_status = "bloqueado"
    generated_path = generated_files[0] if generated_files else None
    details = [
        {
            "id_artefato": artifact_id,
            "status": detail_status,
            "fluxo": "A",
            "framework": "playwright-typescript",
            "arquivo_gerado": generated_path,
            "resultado_execucao": execution,
            "resultado_bruto": raw,
        }
        for artifact_id in artifact_ids
    ]
    return {
        "status": status,
        "tipo_teste": "e2e",
        "inspecao": inspection,
        "perfil": profile,
        "resumo": {
            "total": artifact_total,
            "sucessos": successes,
            "bloqueados": blocked,
            "falhas": failures,
            "executados": (
                execution["testes"]["total"] if execution is not None else 0
            ),
        },
        "arquivos_gerados": generated_files,
        "detalhes": details,
        "bloqueios": blockers,
        "resultado_bruto": raw,
        "cenarios": raw.get("cenarios") or [],
        "nivel_confianca": raw.get("nivel_confianca"),
        "tipo_sistema": raw.get("tipo_sistema"),
        "arquivos_sugeridos": raw.get("arquivos_sugeridos") or [],
    }


__all__ = [
    "normalize_e2e_result",
    "normalize_integration_execution",
    "normalize_integration_result",
    "parse_integration_counts",
]
