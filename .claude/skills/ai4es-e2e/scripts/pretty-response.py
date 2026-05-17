#!/usr/bin/env python3
"""Lê JSON do /run no stdin e imprime resumo legível.

Formato esperado: array de eventos ADK, cada um com content.parts contendo
text, functionCall ou functionResponse.
"""
import json
import sys


_TRUNC = 1200


def render_part(part: dict, idx: int) -> None:
    if "text" in part and part["text"]:
        print(f"\n--- [{idx}] TEXT ---")
        print(part["text"])
        return
    if "functionCall" in part:
        fc = part["functionCall"]
        print(f"\n--- [{idx}] CALL → {fc.get('name', '?')} ---")
        args = json.dumps(fc.get("args", {}), indent=2, ensure_ascii=False)
        if len(args) > _TRUNC:
            args = args[:_TRUNC] + "\n...(truncado)"
        print(args)
        return
    if "functionResponse" in part:
        fr = part["functionResponse"]
        print(f"\n--- [{idx}] RESULT ← {fr.get('name', '?')} ---")
        resp = json.dumps(fr.get("response", {}), indent=2, ensure_ascii=False)
        if len(resp) > _TRUNC:
            resp = resp[:_TRUNC] + "\n...(truncado)"
        print(resp)


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"ERRO: stdin não é JSON: {e}", file=sys.stderr)
        print(f"Conteúdo (500 chars): {raw[:500]}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, list):
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    print(f"==> {len(data)} eventos\n")
    for i, event in enumerate(data, 1):
        author = event.get("author", "?")
        content = event.get("content", {})
        parts = content.get("parts", [])
        if parts:
            for part in parts:
                render_part(part, i)
            print(f"   (author: {author})")
        elif event.get("errorCode"):
            print(f"\n--- [{i}] ERROR ---")
            print(f"   code: {event.get('errorCode')}")
            print(f"   msg:  {event.get('errorMessage', '')[:_TRUNC]}")


if __name__ == "__main__":
    main()
