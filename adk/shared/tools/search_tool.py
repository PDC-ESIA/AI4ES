import os
from pathlib import Path


def _base_dir() -> Path:
    env = os.environ.get("ADK_AGENT_DATA_DIR")
    return (Path.cwd() / env).resolve() if env else Path.cwd()


def run_search(term: str, context_lines: int = 3) -> str:
    """
    Busca o termo em todos os arquivos .txt dentro de data/chunks.
    Retorna trechos com contexto ao redor do termo.
    """
    chunk_dir = str(_base_dir() / "data" / "chunks")
    results = []

    if not os.path.exists(chunk_dir):
        return "Erro: Base de conhecimento não fatiada. Execute run_slicer primeiro."

    for file in sorted(os.listdir(chunk_dir)):
        path = os.path.join(chunk_dir, file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        if term.lower() not in content.lower():
            continue

        lines = content.split('\n')
        snippets = []
        for i, line in enumerate(lines):
            if term.lower() in line.lower():
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                snippets.append('\n'.join(lines[start:end]))

        if snippets:
            results.append(f"--- Fonte: {file} ---\n" + "\n[...]\n".join(snippets))

    return "\n\n".join(results) if results else "Termo não encontrado nos documentos."
