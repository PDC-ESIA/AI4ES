"""Exporta os dados de execução de uma sessão do ADK (dev-ui / api_server).

Lê a sessão pela API do servidor ADK e grava, numa pasta:

    session.json        sessão bruta (eventos + state), como a API devolve
    llm_calls.csv       uma linha por chamada ao LLM: agente, branch, modelo,
                        tokens de entrada (com e sem cache), saída, raciocínio
                        e as ferramentas que a resposta pediu
    agentes.csv         totais por agente, com a taxa de cache
    token_usage.json    cópia do contador do orchestrator, quando existe
    resumo.md           visão geral em Markdown

Os eventos só trazem as chamadas que ficaram gravadas na sessão: agentes que
rodam como ``AgentTool`` em sessão própria (ex.: ``requirements_agent``) não
aparecem em ``llm_calls.csv``, mas entram no ``token_usage.json``.

Uso:
    python scripts/export_session.py <session_id>
    python scripts/export_session.py <session_id> --url http://localhost:8081 \
        --app orchestrator --user user --out /tmp/export --zip
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ADK_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_OUTPUT = ADK_DIR / "workspace_output"

CALL_FIELDS = [
    "n",
    "timestamp",
    "author",
    "branch",
    "invocation_id",
    "model",
    "input",
    "input_cached",
    "input_uncached",
    "output",
    "thoughts",
    "total",
    "tool_calls",
    "finish_reason",
]


def fetch_session(url: str, app: str, user: str, session_id: str) -> dict:
    endpoint = f"{url.rstrip('/')}/apps/{app}/users/{user}/sessions/{session_id}"
    with urllib.request.urlopen(endpoint, timeout=60) as resp:
        return json.load(resp)


def session_workspace(root: Path, session_id: str) -> Path | None:
    """Pasta da sessão em workspace_output (``<data>-<session_id>``), se houver."""
    matches = sorted(root.glob(f"*{session_id}"))
    return matches[-1] if matches else None


def llm_calls(session: dict) -> list[dict]:
    rows = []
    for event in session.get("events", []):
        usage = event.get("usageMetadata")
        if not usage:
            continue
        prompt = usage.get("promptTokenCount") or 0
        cached = usage.get("cachedContentTokenCount") or 0
        parts = (event.get("content") or {}).get("parts") or []
        tools = [p["functionCall"]["name"] for p in parts if p.get("functionCall")]
        rows.append(
            {
                "n": len(rows) + 1,
                "timestamp": datetime.fromtimestamp(
                    event.get("timestamp", 0), tz=timezone.utc
                ).isoformat(timespec="seconds"),
                "author": event.get("author", ""),
                "branch": event.get("branch") or "",
                "invocation_id": event.get("invocationId", ""),
                "model": event.get("modelVersion") or "",
                "input": prompt,
                "input_cached": cached,
                "input_uncached": prompt - cached,
                "output": usage.get("candidatesTokenCount") or 0,
                "thoughts": usage.get("thoughtsTokenCount") or 0,
                "total": usage.get("totalTokenCount") or 0,
                "tool_calls": " ".join(tools),
                "finish_reason": event.get("finishReason") or "",
            }
        )
    return rows


def per_agent(rows: list[dict]) -> list[dict]:
    acc: dict[str, dict] = defaultdict(
        lambda: {"calls": 0, "input": 0, "input_cached": 0, "output": 0, "thoughts": 0}
    )
    for row in rows:
        agg = acc[row["author"]]
        agg["calls"] += 1
        for key in ("input", "input_cached", "output", "thoughts"):
            agg[key] += row[key]
    out = []
    for author, agg in sorted(acc.items(), key=lambda kv: -kv[1]["input"]):
        out.append(
            {
                "author": author,
                **agg,
                "input_per_call": agg["input"] // max(agg["calls"], 1),
                "cache_pct": round(100 * agg["input_cached"] / agg["input"], 1)
                if agg["input"]
                else 0.0,
            }
        )
    return out


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def fmt(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def write_summary(path: Path, session: dict, rows: list[dict], agents: list[dict],
                  token_usage: dict | None) -> None:
    total_in = sum(r["input"] for r in rows)
    total_cached = sum(r["input_cached"] for r in rows)
    total_out = sum(r["output"] for r in rows)
    lines = [
        f"# Sessão {session.get('id', '')}",
        "",
        f"- App: `{session.get('appName', '')}` · usuário: `{session.get('userId', '')}`",
        f"- Eventos: {len(session.get('events', []))} · chamadas ao LLM gravadas: {len(rows)}",
    ]
    if rows:
        lines.append(f"- Período: {rows[0]['timestamp']} → {rows[-1]['timestamp']}")
    lines += [
        "",
        "## Tokens nos eventos da sessão",
        "",
        f"- Entrada: {fmt(total_in)} (em cache: {fmt(total_cached)}, "
        f"{100 * total_cached / total_in:.1f}%)" if total_in else "- Entrada: 0",
        f"- Saída: {fmt(total_out)}",
        "",
        "| Agente | Chamadas | Entrada | Por chamada | Cache | Saída |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for a in agents:
        lines.append(
            f"| {a['author']} | {a['calls']} | {fmt(a['input'])} | "
            f"{fmt(a['input_per_call'])} | {a['cache_pct']}% | {fmt(a['output'])} |"
        )
    if token_usage:
        cur = token_usage.get("current_run", {})
        lines += [
            "",
            "## Contador do orchestrator (token_usage.json)",
            "",
            f"- Status: {token_usage.get('status', '?')} · execução {token_usage.get('run', '?')}",
            f"- Total: entrada {fmt(cur.get('total', {}).get('input', 0))}, "
            f"saída {fmt(cur.get('total', {}).get('output', 0))}",
            "",
            "| Workflow | Entrada | Saída |",
            "|---|---:|---:|",
        ]
        for wf, u in cur.get("workflows", {}).items():
            lines.append(f"| {wf} | {fmt(u.get('input', 0))} | {fmt(u.get('output', 0))} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("session_id")
    parser.add_argument("--url", default="http://localhost:8081")
    parser.add_argument("--app", default="orchestrator")
    parser.add_argument("--user", default="user")
    parser.add_argument(
        "--out",
        type=Path,
        help="pasta de saída (padrão: <workspace da sessão>/export, ou ./export-<id>)",
    )
    parser.add_argument(
        "--workspace-output",
        type=Path,
        default=WORKSPACE_OUTPUT,
        help="raiz dos workspaces das sessões (padrão: adk/workspace_output)",
    )
    parser.add_argument("--zip", action="store_true", help="gera também um .zip da pasta")
    args = parser.parse_args(argv)

    session = fetch_session(args.url, args.app, args.user, args.session_id)
    workspace = session_workspace(args.workspace_output, args.session_id)
    out = args.out or (workspace / "export" if workspace else Path(f"export-{args.session_id}"))
    out.mkdir(parents=True, exist_ok=True)

    (out / "session.json").write_text(
        json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    rows = llm_calls(session)
    agents = per_agent(rows)
    write_csv(out / "llm_calls.csv", rows, CALL_FIELDS)
    write_csv(out / "agentes.csv", agents, list(agents[0]) if agents else ["author"])

    token_usage = None
    if workspace and (workspace / "token_usage.json").exists():
        shutil.copy(workspace / "token_usage.json", out / "token_usage.json")
        token_usage = json.loads((workspace / "token_usage.json").read_text(encoding="utf-8"))

    write_summary(out / "resumo.md", session, rows, agents, token_usage)

    if args.zip:
        archive = shutil.make_archive(str(out), "zip", root_dir=out)
        print(f"zip: {archive}")
    print(f"exportado em: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
