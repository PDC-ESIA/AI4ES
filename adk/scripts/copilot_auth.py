from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")


def _format_expiry(api_key_info: dict) -> str:
    exp = api_key_info.get("expires_at")
    if isinstance(exp, (int, float)):
        quando = datetime.fromtimestamp(exp)
        estado = "expirado" if exp < datetime.now().timestamp() else "válido"
        return f"{quando.isoformat()} ({estado})"
    return "desconhecido"


def main() -> int:
    """(Re)autentica o GitHub Copilot no LiteLLM e reporta o status.

    Lê/renova os tokens em ~/.config/litellm/github_copilot/. Se a credencial
    estiver expirada, força o refresh via access-token; se não houver
    access-token válido, dispara o device-flow (imprime URL + código para
    autorizar no navegador).
    """
    try:
        from litellm.llms.github_copilot.authenticator import Authenticator
    except Exception as exc:  # noqa: BLE001
        print(f"ERRO: não foi possível importar o Authenticator do LiteLLM: {exc}")
        return 1

    auth = Authenticator()
    print(f"Diretório de tokens: {auth.token_dir}")

    # Estado atual (antes de qualquer refresh).
    api_key_path = Path(auth.api_key_file)
    if api_key_path.exists():
        import json

        try:
            atual = json.loads(api_key_path.read_text(encoding="utf-8"))
            print(f"api-key.json atual: expira em {_format_expiry(atual)}")
        except (json.JSONDecodeError, OSError):
            print("api-key.json atual: presente, mas ilegível.")
    else:
        print("api-key.json atual: ausente.")

    print("\nValidando/renovando credencial do Copilot...")
    try:
        token = auth.get_api_key()
    except Exception as exc:  # noqa: BLE001
        print(f"FALHA: não foi possível obter a API key do Copilot: {exc}")
        print(
            "Verifique sua assinatura do GitHub Copilot e a conectividade com "
            "api.github.com."
        )
        return 1

    # Relê o api-key.json (agora possivelmente renovado) para reportar expiração.
    novo_estado = "desconhecido"
    if api_key_path.exists():
        import json

        try:
            novo = json.loads(api_key_path.read_text(encoding="utf-8"))
            novo_estado = _format_expiry(novo)
        except (json.JSONDecodeError, OSError):
            pass

    prefixo = token[:6] if token else ""
    print(f"\nSUCESSO: credencial válida (token {prefixo}...).")
    print(f"api-key.json: expira em {novo_estado}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
