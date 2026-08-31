"""Preflight de credenciais dos modelos do piloto.

1. Gemini: exige GOOGLE_API_KEY (ou GEMINI_API_KEY) em benchmark/.env ou ambiente.
2. Copilot: usa o Authenticator do LiteLLM (~/.config/litellm/github_copilot/).
   Sem credencial válida, dispara o device-flow: imprime URL + código para
   autorizar no navegador e aguarda a conclusão.

Ao final, executa um ping mínimo de completion em cada modelo configurado.

Uso:
    python preflight_models.py [--model gemini/gemini-2.5-flash]
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / "benchmark" / ".env")

if os.environ.get("GOOGLE_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]


def preflight_gemini(model: str) -> bool:
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        print("[gemini] SEM CHAVE: adicione GOOGLE_API_KEY=... em benchmark/.env")
        return False
    import litellm

    try:
        resp = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=8,
            timeout=30,
        )
        print(f"[{model}] OK — respondeu: {resp.choices[0].message.content!r:.40}")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[{model}] FALHOU: {str(exc)[:300]}")
        return False


def preflight_copilot(model: str) -> bool:
    try:
        from litellm.llms.github_copilot.authenticator import Authenticator
    except ImportError as exc:
        print(f"[copilot] Authenticator indisponível no venv: {exc}")
        return False

    auth = Authenticator()
    print(f"[copilot] diretório de credenciais: {auth.token_dir}")
    try:
        token = auth.get_api_key()
    except Exception as exc:  # noqa: BLE001
        print(f"[copilot] device-flow necessário/aguardando autorização: {type(exc).__name__}")
        print(f"          detalhe: {str(exc)[:300]}")
        return False
    if not token:
        print("[copilot] token vazio após autenticação.")
        return False
    print(f"[copilot] credencial obtida ({token[:6]}...). Testando {model}...")
    import litellm
    from run_benchmark import copilot_extra_headers

    try:
        resp = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=16,
            timeout=60,
            drop_params=True,
            extra_headers=copilot_extra_headers() | {"x-request-id": os.urandom(8).hex()},
        )
        texto = (resp.choices[0].message.content or "").strip()[:40]
        print(f"[{model}] OK — respondeu: {texto!r}")
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[{model}] FALHOU: {str(exc)[:400]}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rodada", default="fase3-piloto")
    parser.add_argument("--model", default="", help="valida apenas este(s) modelo(s), vírgula")
    args = parser.parse_args()

    import yaml

    cfg_path = ROOT / "benchmarks" / "rodadas" / args.rodada / "config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    modelos_cfg = [m.strip() for m in args.model.split(",") if m.strip()] or cfg["models"]

    resultados = {}
    for modelo in modelos_cfg:
        fn = preflight_gemini if modelo.startswith(("gemini/", "vertex_", "google/")) else preflight_copilot
        resultados[modelo] = fn(modelo)

    print("\n=== RESUMO PREFLIGHT ===")
    for modelo, ok in resultados.items():
        print(f"  {'OK ' if ok else 'FALHA'} {modelo}")
    return 0 if all(resultados.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
