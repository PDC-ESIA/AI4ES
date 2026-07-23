"""Camada extensível de capacidades de análise estática para o reviewer.

Uso:
    from shared.review import run_capabilities, Finding
    findings = run_capabilities(Path("/path/to/code"))
"""

from __future__ import annotations

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel


class Finding(BaseModel):
    """Achado de análise estática normalizado entre ferramentas."""

    origem: str
    regra: str
    severidade: Literal["critical", "warning", "info"]
    arquivo: str
    linha: int | None = None
    mensagem: str
    sugestao: str | None = None


class ReviewCapability(Protocol):
    """Protocolo para ferramentas de análise estática plugáveis."""

    name: str

    def run(self, target_dir: Path) -> list[Finding]: ...


_SEVERITY_ORDER: dict[str, int] = {"critical": 0, "warning": 1, "info": 2}


class RuffCapability:
    """Linting e estilo via Ruff."""

    name = "ruff"

    def run(self, target_dir: Path) -> list[Finding]:
        try:
            proc = subprocess.run(
                ["ruff", "check", "--output-format", "json", str(target_dir)],
                capture_output=True,
                text=True,
            )
            if not proc.stdout.strip():
                return []
            items = json.loads(proc.stdout)
        except Exception:
            return []

        findings = []
        for item in items:
            fix = item.get("fix")
            findings.append(Finding(
                origem=self.name,
                regra=item.get("code", ""),
                severidade="warning",
                arquivo=item.get("filename", ""),
                linha=(item.get("location") or {}).get("row"),
                mensagem=item.get("message", ""),
                sugestao=fix.get("message") if fix else None,
            ))
        return findings


class BanditCapability:
    """Análise de segurança via Bandit."""

    name = "bandit"

    _SEVERITY_MAP: dict[str, str] = {
        "HIGH": "critical",
        "MEDIUM": "warning",
        "LOW": "info",
    }

    def run(self, target_dir: Path) -> list[Finding]:
        try:
            proc = subprocess.run(
                ["bandit", "-r", "--format", "json", "-q", str(target_dir)],
                capture_output=True,
                text=True,
            )
            if not proc.stdout.strip():
                return []
            data = json.loads(proc.stdout)
        except Exception:
            return []

        findings = []
        for issue in data.get("results", []):
            findings.append(Finding(
                origem=self.name,
                regra=issue.get("test_id", ""),
                severidade=self._SEVERITY_MAP.get(
                    issue.get("issue_severity", ""), "info"
                ),
                arquivo=issue.get("filename", ""),
                linha=issue.get("line_number"),
                mensagem=issue.get("issue_text", ""),
                sugestao=issue.get("more_info"),
            ))
        return findings


REGISTRY: list[ReviewCapability] = [RuffCapability(), BanditCapability()]


def run_capabilities(
    target_dir: Path,
    registry: list[ReviewCapability] | None = None,
) -> list[Finding]:
    """Executa capacidades em paralelo com isolamento de falhas por ferramenta.

    Falhas individuais são silenciadas — a capacidade com erro retorna lista
    vazia em vez de propagar a exceção. Resultados são ordenados por
    severidade: critical → warning → info.
    """
    _registry = registry if registry is not None else REGISTRY
    if not _registry:
        return []

    all_findings: list[Finding] = []

    with ThreadPoolExecutor(max_workers=len(_registry)) as executor:
        futures = {executor.submit(cap.run, target_dir): cap.name for cap in _registry}
        for future in as_completed(futures):
            try:
                all_findings.extend(future.result())
            except Exception:
                pass

    return sorted(all_findings, key=lambda f: _SEVERITY_ORDER[f.severidade])
