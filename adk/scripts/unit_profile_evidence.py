"""CLI para preparar e coletar evidências dos perfis unitários."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_ADK_ROOT = Path(__file__).resolve().parents[1]
if str(_ADK_ROOT) not in sys.path:
    sys.path.insert(0, str(_ADK_ROOT))

from shared.testing.unit_evidence import (  # noqa: E402
    UNIT_EVIDENCE_CASES,
    collect_unit_profile_evidence,
    index_dev_ui_screenshots,
    prepare_unit_evidence_workspace,
)

_DEFAULT_EVIDENCE_ROOT = (
    _ADK_ROOT.parent
    / "docs"
    / "Time_3_Testes"
    / "evidencias"
    / "evidencias_unit_profiles"
)
_DEFAULT_WORKSPACE_ROOT = _ADK_ROOT / "evidencias_unit_profiles"


def _profile_ids(value: str) -> list[str]:
    if value == "all":
        return sorted(UNIT_EVIDENCE_CASES)
    if value not in UNIT_EVIDENCE_CASES:
        options = ", ".join(["all", *sorted(UNIT_EVIDENCE_CASES)])
        raise ValueError(f"Perfil inválido: '{value}'. Opções: {options}.")
    return [value]


def _write_summary(run_root: Path, evidence: list[dict]) -> Path:
    lines = [
        "# Evidências automatizadas — perfis unitários",
        "",
        "| Perfil | Detecção | Execução | Testes | Cobertura |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for item in evidence:
        inspection = item["inspection"]
        execution = item["execution"]
        normalized = item["normalized_result"]
        total = normalized["total"]
        percentage = normalized["cobertura_percentual"]
        lines.append(
            "| {profile} | {inspection} | {execution} | {total} | {coverage} |".format(
                profile=item["case"]["profile_id"],
                inspection=inspection.get("status"),
                execution=execution.get("status"),
                total=total,
                coverage="—" if percentage is None else f"{percentage}%",
            )
        )
    lines.extend(
        [
            "",
            "Os JSONs individuais preservam comando, runtime, hashes, inspeção e saída.",
        ]
    )
    summary_path = run_root / "SUMMARY.md"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary_path


def _collect(args: argparse.Namespace) -> int:
    profile_ids = _profile_ids(args.profile)
    if args.output:
        run_root = Path(args.output).expanduser().resolve()
    else:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        run_root = _DEFAULT_EVIDENCE_ROOT / "runs" / timestamp
    if run_root.exists() and any(run_root.iterdir()):
        raise FileExistsError(f"O diretório de saída deve estar vazio: {run_root}")
    run_root.mkdir(parents=True, exist_ok=True)

    evidence = [
        collect_unit_profile_evidence(
            profile_id,
            run_root,
            bootstrap_runtime=args.bootstrap_runtime,
            workspace_base=(Path(args.workspace_base) if args.workspace_base else None),
        )
        for profile_id in profile_ids
    ]
    summary_path = _write_summary(run_root, evidence)
    result = {
        "status": (
            "sucesso"
            if all(item["status"] == "sucesso" for item in evidence)
            else "falha"
        ),
        "run_root": str(run_root),
        "summary": str(summary_path),
        "profiles": {item["case"]["profile_id"]: item["status"] for item in evidence},
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "sucesso" else 1


def _prepare_dev_ui(args: argparse.Namespace) -> int:
    profile_ids = _profile_ids(args.profile)
    output_root = (
        Path(args.output).expanduser().resolve()
        if args.output
        else _DEFAULT_WORKSPACE_ROOT / "dev_ui_workspaces"
    )
    sessions = []
    for profile_id in profile_ids:
        workspace = output_root / profile_id / "workspace_output"
        sessions.append(
            prepare_unit_evidence_workspace(
                profile_id,
                workspace,
                include_reference_test=False,
            )
        )
    print(
        json.dumps(
            {"status": "pronto", "sessions": sessions}, ensure_ascii=False, indent=2
        )
    )
    return 0


def _index_screenshots(args: argparse.Namespace) -> int:
    profile_ids = _profile_ids(args.profile)
    root = (
        Path(args.root).expanduser().resolve() if args.root else _DEFAULT_EVIDENCE_ROOT
    )
    manifest = index_dev_ui_screenshots(
        root,
        profile_ids,
        minimum_per_profile=args.minimum,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["status"] == "completo" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepara fixtures e evidências dos perfis unitários prioritários."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser(
        "collect", help="Executa smokes e grava JSON/Markdown."
    )
    collect.add_argument("--profile", default="all")
    collect.add_argument("--output")
    collect.add_argument(
        "--workspace-base",
        help="Usa uma raiz curta/isolada para workspaces, separada das evidências.",
    )
    collect.add_argument(
        "--bootstrap-runtime",
        action="store_true",
        help="Prepara dependências/build apenas dos fixtures controlados antes do smoke.",
    )
    collect.set_defaults(handler=_collect)

    prepare = subparsers.add_parser(
        "prepare-dev-ui",
        help="Cria workspaces isolados, sem testes de referência.",
    )
    prepare.add_argument("--profile", default="all")
    prepare.add_argument("--output")
    prepare.set_defaults(handler=_prepare_dev_ui)

    screenshots = subparsers.add_parser(
        "index-screenshots",
        help="Valida e indexa prints PNG da Dev UI.",
    )
    screenshots.add_argument("--profile", default="all")
    screenshots.add_argument("--root")
    screenshots.add_argument("--minimum", type=int, default=3)
    screenshots.set_defaults(handler=_index_screenshots)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.handler(args)
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        print(json.dumps({"status": "erro", "mensagem": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
