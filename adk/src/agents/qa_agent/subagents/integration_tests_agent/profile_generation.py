"""Adaptadores de geração de testes de integração por stack."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from shared.testing.integration_adapters import (
    detect_node_integration_framework,
    execute_integration_adapter,
)
from src.agents.qa_agent.subagents.unit_test_generator.profile_generation import (
    _artifact_requirement,
    _available_target,
    _completion_content,
    _materialize_inline_sources,
    _package_and_type,
    _select_primary_source,
    _slug,
    _source_context,
    _source_files,
)

_PROFILE_SUFFIXES = {
    "python-integration": (".py",),
    "node-integration": (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"),
    "java-integration": (".java",),
    "go-integration": (".go",),
}


def _test_target(
    profile_id: str,
    root: Path,
    artifact: dict[str, Any],
    sources: list[Path],
) -> Path:
    artifact_slug = _slug(str(artifact.get("id_artefato") or "artefato"))
    module = str(artifact.get("modulo") or artifact_slug)
    primary = _select_primary_source(sources, module)
    if profile_id == "python-integration":
        return _available_target(
            root / "tests" / "integration" / f"test_{artifact_slug}_integration.py"
        )
    if profile_id == "node-integration":
        extension = (
            "ts"
            if any(path.suffix.casefold() in {".ts", ".tsx"} for path in sources)
            else "js"
        )
        return _available_target(
            root
            / "tests"
            / "integration"
            / f"{artifact_slug}.integration.test.{extension}"
        )
    if profile_id == "java-integration":
        package, class_name = _package_and_type(primary, module)
        package_path = Path(*package.split(".")) if package else Path()
        return _available_target(
            root
            / "src"
            / "test"
            / "java"
            / package_path
            / f"{class_name}IntegrationTest.java"
        )
    if profile_id == "go-integration":
        preferred = (
            primary.with_name(f"{primary.stem}_integration_test.go")
            if primary
            else root / f"{artifact_slug}_integration_test.go"
        )
        return _available_target(preferred)
    raise ValueError(f"Perfil de integração não suportado: {profile_id}")


def _profile_contract(profile_id: str, root: Path) -> tuple[str, str, str]:
    if profile_id == "python-integration":
        return (
            "pytest",
            "Use pytest e as APIs reais dos componentes Python/FastAPI.",
            r"(?m)^\s*def\s+test_\w+\s*\(",
        )
    if profile_id == "node-integration":
        framework = detect_node_integration_framework(root)
        rules = {
            "vitest": "Use Vitest e importe describe, expect e test/it de `vitest`.",
            "jest": "Use Jest e não use APIs do Vitest.",
            "mocha": "Use Mocha com describe/it e `node:assert/strict`.",
            "node:test": "Use somente `node:test` e `node:assert/strict`.",
        }
        patterns = {
            "vitest": r"\b(?:describe|it|test)\s*\(",
            "jest": r"\b(?:describe|it|test)\s*\(",
            "mocha": r"(?s)\bdescribe\s*\(.*\bit\s*\(",
            "node:test": r"node:test|require\(['\"]node:test['\"]\)",
        }
        return framework, rules[framework], patterns[framework]
    if profile_id == "java-integration":
        return (
            "junit",
            "Use JUnit 5 e as classes reais do projeto Java/Spring.",
            r"@Test\b|org\.junit\.jupiter\.api\.Test",
        )
    if profile_id == "go-integration":
        return (
            "go-testing",
            "Use o pacote padrão `testing` e o mesmo package do código-fonte.",
            r"(?ms)^\s*package\s+\w+.*\btesting\b.*^\s*func\s+Test",
        )
    raise ValueError(f"Perfil de integração não suportado: {profile_id}")


def _sanitize_code(code: str, required_pattern: str) -> str:
    value = (code or "").strip()
    fenced = re.fullmatch(r"```(?:[\w+#.-]+)?\s*(.*?)\s*```", value, re.DOTALL)
    if fenced:
        value = fenced.group(1).strip()
    if not value or "\x00" in value or not re.search(required_pattern, value):
        raise ValueError("O gerador retornou código incompatível com o perfil.")
    return value + "\n"


def _generate_code(
    profile_id: str,
    framework: str,
    rule: str,
    artifact: dict[str, Any],
    root: Path,
    target: Path,
    sources: list[Path],
) -> str:
    source_rule = (
        "Gere um teste executável atravessando ao menos duas responsabilidades reais."
        if sources
        else "Gere um esqueleto explicitamente ignorado pelo framework."
    )
    prompt = f"""Gere o arquivo {target.relative_to(root).as_posix()}.
Artefato: {artifact.get('id_artefato', 'SEM_ID')}
Tipo: {artifact.get('tipo', 'RF')}
Módulo: {artifact.get('modulo', 'geral')}
Requisito: {_artifact_requirement(artifact)}

{source_rule}

Código-fonte do projeto:
{_source_context(root, sources)}

Contrato {profile_id}/{framework}:
- {rule}
- Exercite a colaboração entre dois ou mais componentes reais.
- Use doubles somente para fronteiras externas não controladas.
- Não altere produção, manifests, dependências ou ambiente.
- Cubra o caminho feliz e uma falha observável da integração.

Retorne exclusivamente o conteúdo do arquivo, sem Markdown.
"""
    return _completion_content(
        "Você gera exclusivamente testes de integração executáveis.",
        prompt,
    )


def run_integration_profile_adapter(
    profile_id: str,
    artifacts: list[dict[str, Any]],
    project_root: Path,
) -> dict[str, Any]:
    """Gera e executa testes, preservando a saída bruta de cada executor."""
    if profile_id not in _PROFILE_SUFFIXES:
        raise ValueError(f"Perfil de integração não implementado: {profile_id}")
    root = project_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    details: list[dict[str, Any]] = []

    for artifact in artifacts:
        artifact_id = str(artifact.get("id_artefato") or "SEM_ID")
        if not _artifact_requirement(artifact):
            details.append(
                {
                    "id_artefato": artifact_id,
                    "status": "bloqueado",
                    "arquivo_gerado": None,
                    "resultado_execucao": None,
                    "erro": (
                        "Nenhum requisito textual encontrado (campos aceitos: "
                        "conteudo, descricao, requisito, resumo, titulo, "
                        "criterios_aceite, criterios_verificaveis)."
                    ),
                }
            )
            continue
        try:
            _materialize_inline_sources(artifact, root)
            sources = _source_files(root, _PROFILE_SUFFIXES[profile_id])
            target = _test_target(profile_id, root, artifact, sources).resolve()
            if not target.is_relative_to(root):
                raise ValueError("O destino do teste saiu do projeto gerenciado.")
            framework, rule, required_pattern = _profile_contract(profile_id, root)
            generated = _generate_code(
                profile_id, framework, rule, artifact, root, target, sources
            )
            code = _sanitize_code(generated, required_pattern)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(code, encoding="utf-8")
            execution = (
                execute_integration_adapter(profile_id, root, target)
                if sources
                else None
            )
            details.append(
                {
                    "id_artefato": artifact_id,
                    "status": "gerado",
                    "fluxo": "A" if sources else "B",
                    "framework": framework,
                    "arquivo_gerado": str(target),
                    "arquivos_apoio": [str(path) for path in sources],
                    "resultado_execucao": execution,
                    "erro": None,
                }
            )
        except Exception as exc:
            details.append(
                {
                    "id_artefato": artifact_id,
                    "status": "falha",
                    "arquivo_gerado": None,
                    "resultado_execucao": None,
                    "erro": str(exc),
                }
            )

    return {
        "status": "concluido",
        "perfil": profile_id,
        "detalhes": details,
    }


__all__ = ["run_integration_profile_adapter"]
