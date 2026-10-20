"""Política de saída: evidências livres não são publicadas em diagnósticos."""
import re
from pathlib import Path

TIPOS_ERRO = {"AssertionError", "ImportError", "ModuleNotFoundError", "SyntaxError",
              "TypeError", "ValueError", "RuntimeError", "TimeoutError", "TestFailure"}


def tipo_erro_publico(texto: str) -> str:
    return next((tipo for tipo in sorted(TIPOS_ERRO) if re.search(r"\b" + tipo + r"\b", texto)), "TestFailure")


def arquivo_privado(caminho: Path) -> bool:
    nomes = {parte.lower() for parte in caminho.parts}
    return bool(nomes & {"prompts", "secrets", "credentials", ".ssh", ".aws"}) or (
        caminho.name.lower() in {"prompt.py", "prompts.py", "system_prompt.txt",
                                "credentials.json", "secrets.json"}
        or caminho.name.startswith(".env")
        or caminho.suffix.lower() in {".pem", ".key", ".p12"}
    )

def resumir_evidencia(texto: object) -> str:
    # Sem hash/tamanho: até esses metadados são desnecessários para o diagnóstico.
    return "[REDACTED] Evidência omitida pela política de divulgação do QA." if texto else "N/A"


def identificador_publico(texto: str) -> str:
    return texto if re.fullmatch(r"[A-Z]{2,12}-\d{1,8}", texto) else "QA-000"
