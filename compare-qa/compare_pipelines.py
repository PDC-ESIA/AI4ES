#!/usr/bin/env python3
"""Primitivas compartilhadas pelo benchmark robusto TACO vs. TACO + QA."""

from __future__ import annotations

import json
import shutil
import statistics
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (ROOT, ROOT / "adk"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


@dataclass
class Oracle:
    passed: int
    failed: int
    covered: list[int]
    statements: list[int]
    failures: list[str] = field(default_factory=list)

    @property
    def coverage(self) -> float:
        return round(100 * len(set(self.covered)) / len(self.statements), 2) if self.statements else 0.0


@dataclass
class Qa:
    status: str
    passed: int
    failed: int
    skipped: int
    covered: list[int]
    source_coverage: float
    errors: list[str]


def clean(path: Path, allowed_root: Path) -> None:
    path, allowed_root = path.resolve(), allowed_root.resolve()
    if path != allowed_root and not path.is_relative_to(allowed_root):
        raise RuntimeError(f"caminho fora do benchmark: {path}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def configure(agent: Any, model: str) -> None:
    agent.model = model
    config = getattr(agent, "generate_content_config", None)
    if config is not None and hasattr(config, "temperature"):
        config.temperature = 0.0


async def invoke(agent: Any, message: str, usage: Any, stage: str) -> str:
    from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.genai import types
    from shared.token_usage import bind_stage, token_usage_plugin

    bind_stage(usage, stage)
    runner = Runner(
        app_name=agent.name,
        agent=agent,
        plugins=[token_usage_plugin],
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
    )
    session = await runner.session_service.create_session(
        app_name=agent.name, user_id=f"compare-{stage}", state={}
    )
    content = types.Content(role="user", parts=[types.Part.from_text(text=message)])
    last = ""
    try:
        async for event in runner.run_async(
            user_id=session.user_id, session_id=session.id, new_message=content
        ):
            for part in getattr(getattr(event, "content", None), "parts", []) or []:
                if getattr(part, "text", None):
                    last = part.text
    finally:
        await runner.close()
    return last


def run_oracle(source: Path, examples: list[dict], timeout: int, workspace: Path) -> Oracle:
    data = workspace / ".coverage.common"
    data.unlink(missing_ok=True)
    passed, failures = 0, []
    for index, example in enumerate(examples):
        command = [sys.executable, "-m", "coverage", "run", "--branch", f"--data-file={data}"]
        if index:
            command.append("--append")
        command.append(str(source))
        try:
            result = subprocess.run(
                command,
                input=str(example.get("input", "")),
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=source.parent,
            )
            actual = result.stdout.rstrip("\n")
            expected = str(example.get("expected_output", "")).rstrip("\n")
            if result.returncode == 0 and actual == expected:
                passed += 1
            else:
                failures.append(
                    f"exemplo {index + 1}: esperado={expected!r}, obtido={actual!r}, "
                    f"exit={result.returncode}, stderr={result.stderr[-600:]!r}"
                )
        except subprocess.TimeoutExpired:
            failures.append(f"exemplo {index + 1}: timeout de {timeout}s")
    covered: list[int] = []
    statements: list[int] = []
    try:
        import coverage

        cov = coverage.Coverage(data_file=str(data))
        cov.load()
        _, statements, _, missing, _ = cov.analysis2(str(source))
        covered = sorted(set(statements) - set(missing))
    except Exception as exc:
        failures.append(f"cobertura indisponível: {type(exc).__name__}: {exc}")
    return Oracle(passed, len(examples) - passed, covered, statements, failures)


def source_coverage(test_file: Path, source_name: str) -> tuple[list[int], float]:
    path = test_file.parent / "coverage.json"
    if not path.is_file():
        return [], 0.0
    payload = json.loads(path.read_text(encoding="utf-8"))
    executed: set[int] = set()
    total = covered = 0
    for name, item in payload.get("files", {}).items():
        if Path(name).name == source_name:
            executed.update(item.get("executed_lines", []))
            total += int(item.get("summary", {}).get("num_statements", 0) or 0)
            covered += int(item.get("summary", {}).get("covered_lines", 0) or 0)
    return sorted(executed), round(100 * covered / total, 2) if total else 0.0


def run_qa(case: dict, source: Path, usage: Any, workspace: Path) -> Qa:
    from shared.token_usage import bind_stage
    from shared.workspace import get_agent_workspace
    from src.agents.qa_agent.subagents.unit_test_generator.orchestration import gerar_testes_unitarios

    clean(get_agent_workspace("receive_requirements"), workspace)
    artifact = {
        "id_artefato": f"RF-{case['_id']}",
        "tipo": "RF",
        "conteudo": (
            f"{case['challenge']['title']}. {case['challenge']['description']} "
            f"Gere testes contra solve no arquivo {source.name}; importe a função, "
            "cubra casos felizes e bordas e não reimplemente a solução no teste."
        ),
        "modulo": source.stem,
        "criticidade": "alta",
        "arquivos_apoio": [{"path": source.resolve().relative_to(workspace.resolve()).as_posix()}],
    }
    bind_stage(usage, "qa_agent")
    result = gerar_testes_unitarios(
        json.dumps([artifact], ensure_ascii=False),
        workspace_projeto=str(source.parent),
        stack_declarada="python",
    )
    passed = failed = skipped = 0
    errors: list[str] = []
    lines: set[int] = set()
    percentages: list[float] = []
    for detail in result.get("detalhes", []):
        execution = detail.get("resultado_execucao") or {}
        passed += int(execution.get("testes_passaram", 0) or 0)
        failed += int(execution.get("testes_falharam", 0) or 0)
        skipped += int(execution.get("testes_ignorados", 0) or 0)
        errors.extend(str(e.get("log") or e)[-3000:] for e in execution.get("erros", []))
        generated = detail.get("arquivo_gerado")
        if generated:
            found, percentage = source_coverage(Path(generated), source.name)
            lines.update(found)
            percentages.append(percentage)
    errors.extend(str(b.get("mensagem") or b) for b in result.get("bloqueios", []))
    if not result.get("detalhes") and result.get("status") != "sucesso":
        errors.append(json.dumps(result, ensure_ascii=False)[-3000:])
    return Qa(
        str(result.get("status", "desconhecido")), passed, failed, skipped,
        sorted(lines), round(statistics.fmean(percentages), 2) if percentages else 0.0, errors,
    )


def validation_ok(validation: dict[str, dict]) -> bool:
    return bool(validation) and all(
        item.get("syntax_ok") and item.get("examples_run")
        and all(example.get("passed") for example in item["examples_run"])
        for item in validation.values()
    )


def feedback(validation: dict[str, dict], qa: Qa | None) -> str:
    lines: list[str] = []
    for label, item in validation.items():
        if not item.get("syntax_ok"):
            lines.append(f"{label}: {item.get('status')}")
        for example in item.get("examples_run", []):
            if not example.get("passed"):
                lines.append(
                    f"{label}: input={example.get('input')!r}; esperado={example.get('expected')!r}; "
                    f"obtido={example.get('actual')!r}"
                )
    if qa and (qa.status != "sucesso" or qa.failed or not qa.passed):
        lines.append(f"QA: status={qa.status}, passou={qa.passed}, falhou={qa.failed}, skip={qa.skipped}")
        lines.extend(error[-2000:] for error in qa.errors[:2])
    return "\n\n".join(lines) or "A suíte não convergiu."
