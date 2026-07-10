import os
from pathlib import Path


def _base_dir() -> Path:
    env = os.environ.get("ADK_AGENT_DATA_DIR")
    return (Path.cwd() / env).resolve() if env else Path.cwd()


def run_search(term: str, context_lines: int = 3) -> str:
    """Busca um termo nos chunks fragmentados de um documento.

    Use após fragmentar o documento (capacidade de fragmentação) para
    localizar referências a um termo específico ao longo das partes.
    Faz match case-insensitive e devolve trechos com contexto antes e
    depois de cada ocorrência, agrupados por arquivo de chunk.

    Pré-requisito: o documento precisa ter sido fragmentado antes;
    se `data/chunks/` não existir, esta tool retorna erro pedindo a
    fragmentação primeiro.

    Args:
        term: Termo a buscar. Match é case-insensitive sobre o conteúdo
            dos chunks.
        context_lines: Quantas linhas de contexto antes e depois de
            cada ocorrência. Default 3.

    Returns:
        str com os trechos casados, separados por marcador
        "--- Fonte: chunk_NNN.txt ---" e "[...]" entre ocorrências
        múltiplas no mesmo chunk. "Termo não encontrado nos documentos."
        se zero matches. "Erro: ..." se chunks não existem.
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
