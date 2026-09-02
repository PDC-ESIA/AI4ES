"""Executa as matrizes reais de integração e E2E e grava evidências."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_ADK_ROOT = Path(__file__).resolve().parents[1]
if str(_ADK_ROOT) not in sys.path:
    sys.path.insert(0, str(_ADK_ROOT))

from shared.testing.multilevel_evidence import (  # noqa: E402
    E2E_EVIDENCE_PROFILES,
    INTEGRATION_EVIDENCE_CASES,
    collect_e2e_profile_evidence,
    collect_integration_profile_evidence,
)

_DEFAULT_ROOT = (
    _ADK_ROOT.parent
    / "docs"
    / "Time_3_Testes"
    / "evidencias"
    / "evidencias_multilevel"
)


def _selected(level: str, profile: str) -> list[tuple[str, str]]:
    available = {
        **{name: "integration" for name in INTEGRATION_EVIDENCE_CASES},
        **{name: "e2e" for name in E2E_EVIDENCE_PROFILES},
    }
    if profile != "all":
        selected_level = available.get(profile)
        if selected_level is None or level not in {"all", selected_level}:
            raise ValueError(f"Perfil incompatível ou desconhecido: {profile}")
        return [(selected_level, profile)]
    return [
        (case_level, name)
        for name, case_level in available.items()
        if level in {"all", case_level}
    ]


def _summary(run_root: Path, evidence: list[dict]) -> Path:
    lines = [
        "# Evidências automáticas — integração e E2E",
        "",
        "| Nível | Perfil | Status | Testes executados |",
        "| --- | --- | --- | ---: |",
    ]
    for item in evidence:
        normalized = item["normalized_result"]
        level = normalized["tipo_teste"]
        raw_profile = normalized.get("perfil")
        profile = (
            raw_profile.get("profile_id")
            if isinstance(raw_profile, dict)
            else raw_profile
        )
        executed = normalized.get("testes", normalized.get("resumo", {})).get(
            "total", 0
        )
        if level == "e2e":
            executed = normalized["resumo"]["executados"]
        lines.append(f"| {level} | {profile} | {item['status']} | {executed} |")
    lines.extend(
        [
            "",
            "Cada JSON preserva comando, runtime, hashes, logs e resultado bruto.",
            "A única validação restante é a captura visual pela Dev UI.",
        ]
    )
    path = run_root / "SUMMARY.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def collect(args: argparse.Namespace) -> int:
    if args.output:
        run_root = Path(args.output).expanduser().resolve()
    else:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_root = _DEFAULT_ROOT / "runs" / timestamp
    if run_root.exists() and any(run_root.iterdir()):
        raise FileExistsError(f"O diretório deve estar vazio: {run_root}")
    run_root.mkdir(parents=True, exist_ok=True)

    evidence = []
    for level, profile in _selected(args.level, args.profile):
        collector = (
            collect_integration_profile_evidence
            if level == "integration"
            else collect_e2e_profile_evidence
        )
        evidence.append(collector(profile, run_root))
    summary = _summary(run_root, evidence)
    result = {
        "status": (
            "sucesso"
            if evidence and all(item["status"] == "sucesso" for item in evidence)
            else "falha"
        ),
        "run_root": str(run_root),
        "summary": str(summary),
        "profiles": {
            (
                item.get("case", {}).get("profile_id")
                or item.get("profile", {}).get("profile_id")
            ): item["status"]
            for item in evidence
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "sucesso" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--level", choices=("all", "integration", "e2e"), default="all")
    parser.add_argument("--profile", default="all")
    parser.add_argument("--output")
    return parser


def main() -> int:
    try:
        return collect(build_parser().parse_args())
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        print(json.dumps({"status": "erro", "mensagem": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
