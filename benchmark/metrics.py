"""Extrai tempo, chamadas e tokens do YAML nativo do DebugLoggingPlugin do ADK.

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


def extrair_metricas(caminho: Path) -> dict:
    documentos = [d for d in yaml.safe_load_all(caminho.read_text(encoding="utf-8")) if d]
    if not documentos:
        raise ValueError(f"nenhuma invocação em {caminho}")

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
    args = parser.parse_args()
    print(json.dumps(extrair_metricas(args.yaml), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
