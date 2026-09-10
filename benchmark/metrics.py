"""Extrai tempo, chamadas e tokens do YAML nativo do DebugLoggingPlugin do ADK.

O plugin escreve em modo append e o arquivo acumula execuções de dias diferentes,
então por padrão só a execução mais recente é considerada.

Uso isolado:
    adk/.venv/bin/python benchmark/metrics.py adk/workspace_output/adk_debug.yaml

O collect.py usa este módulo automaticamente quando o YAML existe.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import yaml


def _instante(valor: str | datetime) -> datetime:
    if isinstance(valor, datetime):
        return valor
    return datetime.fromisoformat(valor.replace("Z", "+00:00"))


def _intervalo(doc: dict) -> tuple[datetime, datetime]:
    inicio = _instante(doc["start_time"])
    marcas = [
        _instante(e["timestamp"]) for e in doc.get("entries", []) if e.get("timestamp")
    ]
    return inicio, max(marcas) if marcas else inicio


def _ultima_execucao(documentos: list[dict]) -> list[dict]:
    """Documentos da execução mais recente.

    O DebugLoggingPlugin abre o arquivo em modo append e o workspace nem sempre
    é limpo entre runs, então o YAML acumula execuções de dias diferentes. Uma
    única run gera vários documentos (o agente raiz e cada sub-agente invocado
    via AgentTool), cujos intervalos se sobrepõem porque os filhos rodam dentro
    do pai. Agrupar por sobreposição separa as runs sem depender de limiar.
    """
    ordenados = sorted(documentos, key=lambda d: _intervalo(d)[0])
    grupos: list[list[dict]] = []
    fim_grupo = None
    for doc in ordenados:
        inicio, fim = _intervalo(doc)
        if fim_grupo is None or inicio > fim_grupo:
            grupos.append([doc])
            fim_grupo = fim
        else:
            grupos[-1].append(doc)
            fim_grupo = max(fim_grupo, fim)
    return grupos[-1]


def extrair_metricas(caminho: Path, apenas_ultima: bool = True) -> dict:
    documentos = [d for d in yaml.safe_load_all(caminho.read_text(encoding="utf-8")) if d]
    if not documentos:
        raise ValueError(f"nenhuma invocação em {caminho}")

    n_total = len(documentos)
    if apenas_ultima:
        documentos = _ultima_execucao(documentos)

    inicios = []
    fins = []
    chamadas = []
    erros = 0

    for doc in documentos:
        inicios.append(_instante(doc["start_time"]))
        for entrada in doc.get("entries", []):
            timestamp = entrada.get("timestamp")
            if timestamp:
                fins.append(_instante(timestamp))
            if entrada.get("entry_type") == "llm_response":
                dados = entrada.get("data", {})
                uso = dados.get("usage_metadata") or {}
                chamadas.append(
                    {
                        "agente": entrada.get("agent_name"),
                        "timestamp": timestamp,
                        "modelo_versao": dados.get("model_version"),
                        "tokens_prompt": uso.get("prompt_token_count") or 0,
                        "tokens_resposta": uso.get("candidates_token_count") or 0,
                        "tokens_total": uso.get("total_token_count") or 0,
                        "tokens_cache": uso.get("cached_content_token_count") or 0,
                        "erro": dados.get("error_code"),
                    }
                )
                erros += int(bool(dados.get("error_code")))

    inicio = min(inicios)
    fim = max(fins) if fins else inicio
    return {
        "duracao_total_s": round((fim - inicio).total_seconds(), 3),
        "n_invocacoes_adk": len(documentos),
        "n_invocacoes_ignoradas": n_total - len(documentos),
        "n_chamadas_llm": len(chamadas),
        "n_erros_llm": erros,
        "tokens_prompt": sum(c["tokens_prompt"] for c in chamadas),
        "tokens_resposta": sum(c["tokens_resposta"] for c in chamadas),
        "tokens_total": sum(c["tokens_total"] for c in chamadas),
        "tokens_cache": sum(c["tokens_cache"] for c in chamadas),
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "chamadas": chamadas,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("yaml", type=Path)
    parser.add_argument(
        "--todas",
        action="store_true",
        help="agrega o arquivo inteiro em vez de só a última execução",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            extrair_metricas(args.yaml, apenas_ultima=not args.todas),
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
