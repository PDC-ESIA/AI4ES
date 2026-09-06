"""Congela o workspace_output da execução recém-terminada em benchmark/runs/.

Precisa rodar ANTES de disparar a execução seguinte: init_workspace() apaga o
workspace_output inteiro no início de cada run, então o que não for copiado
agora é perdido.

Uso:
    adk/.venv/bin/python benchmark/collect.py \
        --modelo claude-sonnet-4.5 --caso RE-07 --execucao 1
"""

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone

from config import CANDIDATOS, RUNS, WORKSPACE_OUTPUT
from metrics import extrair_metricas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modelo", required=True, choices=CANDIDATOS)
    parser.add_argument("--caso", required=True, help="identificador do caso, ex.: RE-07")
    parser.add_argument("--execucao", required=True, type=int)
    args = parser.parse_args()

    if not WORKSPACE_OUTPUT.is_dir():
        sys.exit(f"erro: {WORKSPACE_OUTPUT} não existe")

    artefatos = sorted(WORKSPACE_OUTPUT.rglob("*.md"))
    if not artefatos:
        sys.exit(
            "erro: nenhum artefato .md em workspace_output — a execução falhou "
            "ou o workspace já foi limpo por uma execução posterior"
        )

    destino = RUNS / args.modelo / args.caso / f"exec-{args.execucao:02d}"
    if destino.exists():
        sys.exit(f"erro: {destino} já existe; remova-o antes de regravar")

    destino.mkdir(parents=True)
    shutil.copytree(WORKSPACE_OUTPUT, destino / "artifacts")

    mtimes = [a.stat().st_mtime for a in artefatos]
    duvidas = [a.name for a in artefatos if a.name.startswith("Doubt_Artifact")]

    meta = {
        "modelo": args.modelo,
        "caso": args.caso,
        "execucao": args.execucao,
        "coletado_em": datetime.now(timezone.utc).isoformat(),
        "n_artefatos": len(artefatos),
        "n_doubt_artifacts": len(duvidas),
        "caracteres": sum(a.stat().st_size for a in artefatos),
        # Piso do tempo real: intervalo entre a gravação do primeiro e do último
        # artefato. Não inclui o boot, a chamada final nem a validação. Para o
        # tempo verdadeiro exigido pela RQ4, use o MetricsPlugin.
        "duracao_artefatos_s": round(max(mtimes) - min(mtimes), 2),
    }
    log_adk = WORKSPACE_OUTPUT / "adk_debug.yaml"
    if log_adk.is_file():
        meta["metricas_adk"] = extrair_metricas(log_adk)
    (destino / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"{len(artefatos)} artefatos copiados para {destino}")
    if duvidas:
        print(f"  atenção: {len(duvidas)} doubt artifact(s) nesta execução")


if __name__ == "__main__":
    main()
