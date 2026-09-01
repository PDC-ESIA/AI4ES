"""Smokes reais e evidências reproduzíveis para integração e E2E."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any, Iterator

from .e2e_profiles import E2E_TEST_PROFILES
from .integration_adapters import execute_integration_adapter
from .integration_profiles import INTEGRATION_TEST_PROFILES
from .profile_inspector import inspect_test_project
from .result_normalization import (
    normalize_e2e_result,
    normalize_integration_execution,
)

_ADK_ROOT = Path(__file__).resolve().parents[2]
_FIXTURES_ROOT = _ADK_ROOT / "tests" / "fixtures"


@dataclass(frozen=True)
class IntegrationEvidenceCase:
    profile_id: str
    stack: str
    title: str
    test_relative_path: str
    reference_test: str
    runtime_command: tuple[str, ...]

    @property
    def fixture_root(self) -> Path:
        return _FIXTURES_ROOT / "integration_profiles" / self.profile_id

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["fixture_root"] = str(self.fixture_root)
        return result


INTEGRATION_EVIDENCE_CASES = {
    case.profile_id: case
    for case in (
        IntegrationEvidenceCase(
            "python-integration",
            "Python/FastAPI",
            "Python/FastAPI com pytest",
            "tests/integration/test_checkout_integration.py",
            "test_checkout_integration.py",
            ("python", "--version"),
        ),
        IntegrationEvidenceCase(
            "node-integration",
            "TypeScript",
            "Node/Express TypeScript com node:test",
            "tests/integration/checkout.integration.test.ts",
            "checkout.integration.test.ts",
            ("node", "--version"),
        ),
        IntegrationEvidenceCase(
            "java-integration",
            "Java/Spring",
            "Java/Spring com JUnit/Maven",
            "src/test/java/com/example/CheckoutIntegrationTest.java",
            "CheckoutIntegrationTest.java",
            ("java", "--version"),
        ),
        IntegrationEvidenceCase(
            "go-integration",
            "Go",
            "Go com testing",
            "checkout_integration_test.go",
            "checkout_integration_test.go",
            ("go", "version"),
        ),
    )
}

E2E_EVIDENCE_PROFILES = (
    "python-e2e",
    "node-e2e",
    "java-e2e",
    "go-e2e",
)


def _sha256_files(root: Path) -> dict[str, str]:
    ignored = {"target", "test-results", "__pycache__", ".pytest_cache"}
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and not any(part in ignored for part in path.relative_to(root).parts)
    }


def _runtime_version(command: tuple[str, ...]) -> dict[str, Any]:
    executable = shutil.which(command[0])
    if command[0] == "python":
        executable = shutil.which("python") or os.sys.executable
    if executable is None:
        return {"available": False, "command": list(command), "output": None}
    resolved = [executable, *command[1:]]
    process = subprocess.run(
        resolved,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
        shell=False,
    )
    output = "\n".join(
        part.strip() for part in (process.stdout, process.stderr) if part.strip()
    )
    return {
        "available": process.returncode == 0,
        "command": resolved,
        "output": output,
    }


def _write_evidence(path: Path, evidence: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=False)
    path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def collect_integration_profile_evidence(
    profile_id: str, run_root: Path
) -> dict[str, Any]:
    """Executa detector, comando real e normalizador de um perfil de integração."""
    try:
        case = INTEGRATION_EVIDENCE_CASES[profile_id]
    except KeyError:
        raise ValueError(f"Perfil de integração desconhecido: {profile_id}") from None

    output_root = run_root.resolve()
    workspace = output_root / "workspaces" / profile_id / "workspace_output"
    workspace.mkdir(parents=True, exist_ok=False)
    (workspace / ".ai4se_workspace").write_text("qa evidence\n", encoding="utf-8")
    project = workspace / "coder" / "src"
    shutil.copytree(case.fixture_root / "project", project)
    test_path = project / case.test_relative_path
    test_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(case.fixture_root / "reference" / case.reference_test, test_path)

    inspection = inspect_test_project(
        project,
        INTEGRATION_TEST_PROFILES,
        declared_stack=case.stack,
    )
    raw = execute_integration_adapter(profile_id, project, test_path)
    normalized = normalize_integration_execution(raw)
    counts = normalized["testes"]
    passed = (
        inspection.get("status") == "suportado"
        and (inspection.get("perfil") or {}).get("profile_id") == profile_id
        and normalized["status"] == "sucesso"
        and counts["total"] >= 2
        and counts["falhas"] == 0
    )
    evidence = {
        "schema_version": "1.0",
        "evidence_type": "integration-profile-smoke",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "status": "sucesso" if passed else "falha",
        "case": case.to_dict(),
        "runtime": _runtime_version(case.runtime_command),
        "workspace": str(workspace),
        "source_sha256": _sha256_files(project),
        "inspection": inspection,
        "execution": raw,
        "normalized_result": normalized,
    }
    evidence_file = output_root / "results" / "integration" / profile_id / "evidence.json"
    _write_evidence(evidence_file, evidence)
    evidence["evidence_file"] = str(evidence_file)
    return evidence


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return


@contextmanager
def _fixture_server() -> Iterator[str]:
    directory = _FIXTURES_ROOT / "e2e_profiles"
    handler = partial(_QuietHandler, directory=str(directory))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/index.html"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _e2e_spec(base_url: str) -> str:
    return f"""import {{ test, expect }} from '@playwright/test';

test('fluxo de confirmação funciona', async ({{ page }}) => {{
  await page.goto('{base_url}');
  await expect(page.getByRole('heading', {{ name: 'Aplicação pronta' }})).toBeVisible();
  await page.getByLabel('Nome').fill('QA');
  await page.getByRole('button', {{ name: 'Confirmar' }}).click();
  await expect(page.getByText('Olá, QA!')).toBeVisible();
}});
"""


def collect_e2e_profile_evidence(profile_id: str, run_root: Path) -> dict[str, Any]:
    """Executa Chromium real para um perfil E2E sobre servidor loopback."""
    profile = E2E_TEST_PROFILES.get(profile_id)
    if profile is None or profile_id not in E2E_EVIDENCE_PROFILES:
        raise ValueError(f"Perfil E2E desconhecido: {profile_id}")

    from src.agents.qa_agent.subagents.e2e_test_generator.schemas import (
        EntradaE2ENormalizada,
    )
    from src.agents.qa_agent.subagents.e2e_test_generator.tools.executar_playwright import (
        executar_playwright,
    )

    output_root = run_root.resolve()
    workspace = output_root / "workspaces" / profile_id / "workspace_output"
    destination = workspace / "tests" / "e2e"
    destination.mkdir(parents=True, exist_ok=False)
    (workspace / ".ai4se_workspace").write_text("qa evidence\n", encoding="utf-8")
    spec_path = destination / f"{profile_id}.spec.ts"

    previous_workspace = os.environ.get("WORKSPACE_OUTPUT_DIR")
    os.environ["WORKSPACE_OUTPUT_DIR"] = str(workspace)
    try:
        with _fixture_server() as base_url:
            spec_path.write_text(_e2e_spec(base_url), encoding="utf-8")
            execution_model = executar_playwright(
                EntradaE2ENormalizada(
                    ambiente_execucao={
                        "tipo": "local",
                        "browser": "chromium",
                        "timeout_segundos": 90,
                        "timeout_teste_ms": 30_000,
                        "auto_instalar_runtime": False,
                    },
                    comando_execucao="npx playwright test",
                ),
                str(spec_path),
            )
    finally:
        if previous_workspace is None:
            os.environ.pop("WORKSPACE_OUTPUT_DIR", None)
        else:
            os.environ["WORKSPACE_OUTPUT_DIR"] = previous_workspace

    execution = execution_model.model_dump(mode="json")
    raw = {
        "tipo_saida": "executado",
        "arquivos_gerados": [str(spec_path)],
        "resultado_execucao": execution,
        "bloqueios": [],
    }
    normalized = normalize_e2e_result(
        {"status": "suportado"},
        profile.to_dict(),
        raw,
        [{"id_artefato": "RF-E2E-001"}],
    )
    passed = execution["status"] == "aprovado" and normalized["status"] == "sucesso"
    evidence = {
        "schema_version": "1.0",
        "evidence_type": "e2e-profile-smoke",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "status": "sucesso" if passed else "falha",
        "profile": profile.to_dict(),
        "runtime": _runtime_version(("node", "--version")),
        "workspace": str(workspace),
        "source_sha256": _sha256_files(workspace),
        "execution": execution,
        "normalized_result": normalized,
    }
    evidence_file = output_root / "results" / "e2e" / profile_id / "evidence.json"
    _write_evidence(evidence_file, evidence)
    evidence["evidence_file"] = str(evidence_file)
    return evidence


__all__ = [
    "E2E_EVIDENCE_PROFILES",
    "INTEGRATION_EVIDENCE_CASES",
    "collect_e2e_profile_evidence",
    "collect_integration_profile_evidence",
]
