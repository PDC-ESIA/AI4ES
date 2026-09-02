"""Geração por perfis não Python do subagente de testes unitários."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path, PurePosixPath
from typing import Any

import litellm
from litellm import completion

from shared.llm import copilot_completion_kwargs
from shared.testing import executar_teste_unitario, get_unit_test_profile

litellm.drop_params = True

_IGNORED_PARTS = {
    ".git",
    ".gradle",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
}
_TEST_DIR_NAMES = {"__tests__", "spec", "specs", "test", "tests"}
_MAX_SOURCE_FILES = 30
_MAX_SOURCE_BYTES = 500_000

_PROFILE_RULES = {
    "node-vitest": "Use Vitest e importe describe, expect e it/test de `vitest`.",
    "node-jest": "Use Jest, seus globals ou `@jest/globals`; não use APIs do Vitest.",
    "node-node-test": "Use somente `node:test` e `node:assert/strict`, sem dependências externas.",
    "node-mocha": "Use Mocha com describe/it e `node:assert/strict`; não use Jest ou Vitest.",
    "java-junit": "Use JUnit 5 (`org.junit.jupiter.api.Test`) e Assertions estáticas.",
    "go-testing": "Use somente o pacote padrão `testing` e o mesmo package do fonte.",
}

_REQUIRED_PATTERNS = {
    "node-vitest": r"\b(?:describe|it|test)\s*\(",
    "node-jest": r"\b(?:describe|it|test)\s*\(",
    "node-node-test": r"(?:node:test|require\(['\"]node:test['\"]\))",
    "node-mocha": r"\bdescribe\s*\(.*\bit\s*\(",
    "java-junit": r"@Test\b|org\.junit\.jupiter\.api\.Test",
    "go-testing": r"(?m)^\s*package\s+\w+.*\btesting\b",
}


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value or "artefato").strip("_")
    return normalized.casefold() or "artefato"


def _camel(value: str) -> str:
    parts = re.findall(r"[a-zA-Z0-9]+", value or "Artefato")
    result = "".join(part[:1].upper() + part[1:] for part in parts)
    if not result or result[0].isdigit():
        result = f"Artefato{result}"
    return result


def _safe_relative_path(value: str) -> Path | None:
    normalized = PurePosixPath(value.replace("\\", "/"))
    if normalized.is_absolute() or not normalized.parts or ".." in normalized.parts:
        return None
    if normalized.parts[0].casefold() in {"workspace_output", "coder"}:
        return Path(normalized.name)
    return Path(*normalized.parts)


def _materialize_inline_sources(artifact: dict[str, Any], root: Path) -> list[Path]:
    materialized: list[Path] = []
    support_files = artifact.get("arquivos_apoio", [])
    if not isinstance(support_files, list):
        return materialized
    for item in support_files:
        if not isinstance(item, dict):
            continue
        raw_path = item.get("path")
        if isinstance(raw_path, str) and raw_path.strip():
            existing = Path(raw_path).expanduser()
            if not existing.is_absolute():
                existing = root / existing
            existing = existing.resolve()
            if existing.is_file() and existing.is_relative_to(root):
                materialized.append(existing)
                continue
        content = item.get("conteudo")
        name = item.get("nome") or item.get("filename") or raw_path
        if (
            not isinstance(content, str)
            or not isinstance(name, str)
            or not name.strip()
        ):
            continue
        relative = _safe_relative_path(name.strip())
        if relative is None:
            continue
        target = (root / relative).resolve()
        if not target.is_relative_to(root):
            continue
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        if target.is_file():
            materialized.append(target)
    return materialized


def _looks_like_test(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if {part.casefold() for part in relative.parts[:-1]} & _TEST_DIR_NAMES:
        return True
    name = path.name.casefold()
    return bool(
        re.search(
            r"(?:^test_|_test\.|_spec\.|\.test\.|\.spec\.|tests?\.java$)",
            name,
        )
    )


def _source_files(root: Path, suffixes: tuple[str, ...]) -> list[Path]:
    sources: list[Path] = []
    if not root.is_dir():
        return sources
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.casefold() not in suffixes:
            continue
        relative_parts = {part.casefold() for part in path.relative_to(root).parts}
        if relative_parts & _IGNORED_PARTS or _looks_like_test(path, root):
            continue
        name = path.name.casefold()
        if name.startswith(("vitest.config.", "jest.config.", ".mocharc.")):
            continue
        if name == "module-info.java":
            continue
        sources.append(path)
        if len(sources) >= _MAX_SOURCE_FILES:
            break
    return sources


def _select_primary_source(sources: list[Path], module: str) -> Path | None:
    key = _slug(module)
    for source in sources:
        if _slug(source.stem) == key or key in _slug(source.as_posix()):
            return source
    return sources[0] if sources else None


def _package_and_type(source: Path | None, fallback: str) -> tuple[str, str]:
    if source is None:
        return "", _camel(fallback)
    text = source.read_text(encoding="utf-8", errors="replace")
    package_match = re.search(
        r"^\s*(?:package|namespace)\s+([\w.]+)\s*;?", text, re.MULTILINE
    )
    type_match = re.search(
        r"\b(?:public\s+)?(?:class|interface|record|struct|enum|object)\s+(\w+)",
        text,
    )
    return (
        package_match.group(1) if package_match else "",
        type_match.group(1) if type_match else source.stem,
    )


def _available_target(preferred: Path) -> Path:
    """Mantém o helper genérico usado pelos adaptadores de integração."""
    if not preferred.exists():
        return preferred
    return preferred.with_name(f"{preferred.stem}.generated{preferred.suffix}")


def _available_java_target(preferred: Path) -> Path:
    if not preferred.exists():
        return preferred
    component = preferred.stem.removesuffix("Test")
    candidate = preferred.with_name(f"{component}GeneratedTest.java")
    index = 2
    while candidate.exists():
        candidate = preferred.with_name(f"{component}Generated{index}Test.java")
        index += 1
    return candidate


def _available_go_target(preferred: Path) -> Path:
    if not preferred.exists():
        return preferred
    component = preferred.name.removesuffix("_test.go")
    candidate = preferred.with_name(f"{component}_generated_test.go")
    index = 2
    while candidate.exists():
        candidate = preferred.with_name(f"{component}_generated{index}_test.go")
        index += 1
    return candidate


def _node_test_convention(root: Path, extension: str) -> tuple[Path, str]:
    """Reaproveita diretório e sufixo dos testes Node já existentes."""
    for path in sorted(root.rglob(f"*.{extension}")):
        if not path.is_file() or not _looks_like_test(path, root):
            continue
        relative_parts = {part.casefold() for part in path.relative_to(root).parts}
        if relative_parts & _IGNORED_PARTS:
            continue
        name = path.name.casefold()
        for marker in (".unit.test", ".spec", ".test"):
            if f"{marker}.{extension}" in name:
                return path.parent, marker
    return root / "tests" / "unit", ".test"


def _available_node_target(
    directory: Path, artifact_slug: str, marker: str, extension: str
) -> Path:
    preferred = directory / f"{artifact_slug}{marker}.{extension}"
    if not preferred.exists():
        return preferred
    return directory / f"{artifact_slug}.generated{marker}.{extension}"


def _test_target(
    profile_id: str,
    root: Path,
    artifact: dict[str, Any],
    sources: list[Path],
) -> Path:
    artifact_slug = _slug(str(artifact.get("id_artefato") or "artefato"))
    module = str(artifact.get("modulo") or artifact_slug)
    primary = _select_primary_source(sources, module)

    if profile_id.startswith("node-"):
        extension = (
            "ts"
            if any(path.suffix.casefold() in {".ts", ".tsx"} for path in sources)
            else "js"
        )
        directory, marker = _node_test_convention(root, extension)
        return _available_node_target(
            directory,
            artifact_slug,
            marker,
            extension,
        )
    if profile_id == "java-junit":
        package, class_name = _package_and_type(primary, module)
        package_path = Path(*package.split(".")) if package else Path()
        return _available_java_target(
            root / "src" / "test" / "java" / package_path / f"{class_name}Test.java"
        )
    if profile_id == "go-testing":
        preferred = (
            primary.with_name(f"{primary.stem}_test.go")
            if primary
            else root / f"{artifact_slug}_test.go"
        )
        return _available_go_target(preferred)
    raise ValueError(f"Perfil de geração não suportado: {profile_id}")


def _source_context(root: Path, sources: list[Path]) -> str:
    parts: list[str] = []
    used_bytes = 0
    for source in sources:
        try:
            content = source.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        encoded_size = len(content.encode("utf-8"))
        if used_bytes + encoded_size > _MAX_SOURCE_BYTES:
            continue
        used_bytes += encoded_size
        parts.append(f"--- {source.relative_to(root).as_posix()} ---\n{content}")
    return "\n\n".join(parts) or "Nenhum código-fonte foi encontrado."


def _artifact_requirement(artifact: dict[str, Any]) -> str:
    """Extrai requisito textual sem exigir um envelope específico de origem."""
    for field in ("conteudo", "descricao", "requisito", "resumo", "titulo"):
        value = artifact.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()

    criteria = artifact.get("criterios_aceite") or artifact.get(
        "criterios_verificaveis"
    )
    if isinstance(criteria, list):
        values = [str(item).strip() for item in criteria if str(item).strip()]
        if values:
            return "; ".join(values)
    return ""


def _declared_node_module_type(root: Path) -> str:
    package_json = root / "package.json"
    if not package_json.is_file():
        return ""
    try:
        package = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    value = package.get("type") if isinstance(package, dict) else None
    return value.strip().casefold() if isinstance(value, str) else ""


def _node_module_instruction(profile_id: str, root: Path, target: Path) -> str:
    if profile_id not in {"node-node-test", "node-mocha"}:
        return ""
    module_type = _declared_node_module_type(root)
    if target.suffix.casefold() in {".js", ".cjs"} and module_type != "module":
        return (
            "- O projeto executa JavaScript como CommonJS. Use exclusivamente "
            "`require(...)`; não use declarações `import` ou `export`."
        )
    return (
        "- O projeto executa o teste como ES Module. Use `import` e não use "
        "`require(...)`."
    )


def _requires_explicit_commonjs(
    profile_id: str, root: Path, target: Path
) -> bool:
    return (
        profile_id in {"node-node-test", "node-mocha"}
        and target.suffix.casefold() in {".js", ".cjs"}
        and _declared_node_module_type(root) == "commonjs"
    )


def _repair_commonjs_test(code: str) -> str:
    return _completion_content(
        (
            "Você corrige somente a sintaxe de módulos de um teste Node.js e "
            "preserva integralmente seus cenários e asserts."
        ),
        f"""O projeto está declarado como CommonJS, mas o teste abaixo usa ESM.
Reescreva todas as importações para `require(...)`. Não use `import` nem `export`.
Retorne exclusivamente o arquivo JavaScript corrigido, sem Markdown.

Teste:
{code}
""",
    )


def _completion_content(system_prompt: str, user_prompt: str) -> str:
    model_name = os.environ.get("ADK_LLM_MODEL", "gemini-2.5-flash")
    llm_kwargs = copilot_completion_kwargs(model_name)
    if "/" not in model_name:
        model_name = f"gemini/{model_name}"
        llm_kwargs["api_key"] = os.environ.get("GOOGLE_API_KEY")
    response = completion(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0,
        **llm_kwargs,
    )
    choices = getattr(response, "choices", None)
    if choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", "") if message else ""
        if isinstance(content, str):
            return content
    if isinstance(response, dict):
        response_choices = response.get("choices", [])
        if response_choices:
            return str(response_choices[0].get("message", {}).get("content", ""))
    return ""


def _sanitize_code(profile_id: str, code: str) -> str:
    value = (code or "").strip()
    fenced = re.fullmatch(r"```(?:[\w+#.-]+)?\s*(.*?)\s*```", value, re.DOTALL)
    if fenced:
        value = fenced.group(1).strip()
    if not value or "\x00" in value:
        raise ValueError("O modelo retornou código de teste vazio ou inválido.")
    pattern = _REQUIRED_PATTERNS.get(profile_id)
    if pattern is None or not re.search(pattern, value, re.DOTALL):
        raise ValueError(
            f"O código gerado não atende ao contrato do perfil '{profile_id}'."
        )
    return value + "\n"


def _align_java_test_class(code: str, target: Path) -> str:
    """Alinha a classe JUnit ao nome físico exigido pelo compilador Java."""
    match = re.search(r"\bclass\s+(\w+)", code)
    if match is None or match.group(1) == target.stem:
        return code
    return re.sub(
        rf"\b{re.escape(match.group(1))}\b",
        target.stem,
        code,
    )


def _deduplicate_go_test_names(code: str, root: Path, target: Path) -> str:
    """Evita colisões de funções Test* com testes Go preexistentes."""
    existing: set[str] = set()
    for path in root.rglob("*_test.go"):
        if not path.is_file() or path.resolve() == target.resolve():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        existing.update(re.findall(r"\bfunc\s+(Test\w+)\s*\(", text))

    replacements: dict[str, str] = {}
    reserved = set(existing)
    for name in re.findall(r"\bfunc\s+(Test\w+)\s*\(", code):
        if name not in reserved:
            reserved.add(name)
            continue
        candidate = f"{name}Generated"
        index = 2
        while candidate in reserved:
            candidate = f"{name}Generated{index}"
            index += 1
        replacements[name] = candidate
        reserved.add(candidate)
    for original, replacement in replacements.items():
        code = re.sub(rf"\b{re.escape(original)}\b", replacement, code)
    return code


def _normalize_generated_code(
    profile_id: str,
    code: str,
    root: Path,
    target: Path,
) -> str:
    if profile_id == "java-junit":
        return _align_java_test_class(code, target)
    if profile_id == "go-testing":
        return _deduplicate_go_test_names(code, root, target)
    return code


def _generate_test_code(
    profile_id: str,
    artifact: dict[str, Any],
    root: Path,
    target: Path,
    sources: list[Path],
) -> str:
    requirement = _artifact_requirement(artifact)
    if not requirement and sources:
        requirement = (
            "Inferir e validar os comportamentos observáveis do código-fonte "
            "persistido, cobrindo sucesso, erros e limites."
        )
    no_source_rule = (
        "Há código-fonte: gere testes completos contra as APIs reais."
        if sources
        else "Não há código-fonte: gere um esqueleto marcado como ignorado pelo framework."
    )
    module_instruction = _node_module_instruction(profile_id, root, target)
    prompt = f"""Gere o arquivo {target.relative_to(root).as_posix()}.
Artefato: {artifact.get("id_artefato", "SEM_ID")}
Tipo: {artifact.get("tipo", "RF")}
Módulo: {artifact.get("modulo", "geral")}
Requisito: {requirement}

{no_source_rule}

Código-fonte do projeto:
{_source_context(root, sources)}

Regras do perfil:
{_PROFILE_RULES[profile_id]}
{module_instruction}
- Importe o código real pelo caminho/package/module correto do projeto.
- Não altere configuração, manifestos, dependências ou código de produção.
- Cubra caminho feliz, entradas inválidas e limites observáveis.

Retorne exclusivamente o conteúdo do arquivo, sem Markdown.
"""
    return _completion_content(
        "Você gera exclusivamente testes unitários executáveis e não altera código de produção.",
        prompt,
    )


def gerar_testes_do_perfil(
    profile_id: str,
    artifacts: list[dict[str, Any]],
    project_root: Path,
) -> dict[str, Any]:
    """Gera e executa os artefatos de um perfil não Python implementado."""
    profile = get_unit_test_profile(profile_id)
    if profile_id not in _PROFILE_RULES:
        raise ValueError(f"Perfil de geração não implementado: {profile_id}")
    root = project_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    details: list[dict[str, Any]] = []

    for artifact in artifacts:
        artifact_id = str(
            artifact.get("id_artefato") or artifact.get("id") or "SEM_ID"
        )
        try:
            _materialize_inline_sources(artifact, root)
            sources = _source_files(root, profile.source_suffixes)
            if not _artifact_requirement(artifact) and not sources:
                details.append(
                    {
                        "id_artefato": artifact_id,
                        "status": "bloqueado",
                        "mensagem": (
                            "Nenhum requisito textual nem código-fonte foi "
                            "encontrado para gerar o teste."
                        ),
                        "arquivo_gerado": None,
                        "resultado_execucao": None,
                    }
                )
                continue

            normalized_artifact = dict(artifact)
            normalized_artifact.setdefault("id_artefato", artifact_id)
            target = _test_target(
                profile_id, root, normalized_artifact, sources
            ).resolve()
            if not target.is_relative_to(root):
                raise ValueError("O destino do teste saiu do projeto gerenciado.")
            generated = _generate_test_code(
                profile_id,
                normalized_artifact,
                root,
                target,
                sources,
            )
            if (
                _requires_explicit_commonjs(profile_id, root, target)
                and re.search(r"(?m)^\s*import\s", generated)
            ):
                generated = _repair_commonjs_test(generated)
            code = _sanitize_code(profile_id, generated)
            code = _normalize_generated_code(profile_id, code, root, target)
            if (
                _requires_explicit_commonjs(profile_id, root, target)
                and re.search(r"(?m)^\s*(?:import|export)\s", code)
            ):
                raise ValueError(
                    "O teste gerado permaneceu incompatível com CommonJS após correção."
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(code, encoding="utf-8")
            execution = (
                executar_teste_unitario(profile_id, root, target) if sources else None
            )
            details.append(
                {
                    "id_artefato": artifact_id,
                    "status": "sucesso",
                    "fluxo": "A" if sources else "B",
                    "pasta_gerada": str(target.parent),
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
        "resumo": {
            "total": len(details),
            "sucessos": sum(item["status"] == "sucesso" for item in details),
            "bloqueados": sum(item["status"] == "bloqueado" for item in details),
            "falhas": sum(item["status"] == "falha" for item in details),
        },
        "detalhes": details,
    }
