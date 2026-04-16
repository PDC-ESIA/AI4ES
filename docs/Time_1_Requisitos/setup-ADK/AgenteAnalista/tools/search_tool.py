import os

def run_search(term: str, context_lines: int = 3):
    """
    Busca o termo em todos os arquivos .txt dentro de data/chunks.
    Retorna trechos com contexto ao redor do termo (±context_lines linhas),
    facilitando a análise do LLM para extração de definições.

    Args:
        term: Termo a buscar nos chunks.
        context_lines: Quantidade de linhas de contexto ao redor de cada ocorrência.

    Returns:
        String com os trechos encontrados e suas fontes, ou mensagem de erro.
    """
    chunk_dir = "data/chunks"
    results = []

    if not os.path.exists(chunk_dir):
        return "Erro: Base de conhecimento não fatiada. Execute run_slicer primeiro."

    for file in sorted(os.listdir(chunk_dir)):
        path = os.path.join(chunk_dir, file)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        if term.lower() not in content.lower():
            continue

        # Extrai trechos com contexto ao redor do termo
        lines = content.split('\n')
        snippets = []

        for i, line in enumerate(lines):
            if term.lower() in line.lower():
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                snippet = '\n'.join(lines[start:end])
                snippets.append(snippet)

        if snippets:
            chunk_result = f"--- Fonte: {file} ---\n"
            chunk_result += "\n[...]\n".join(snippets)
            results.append(chunk_result)

    return "\n\n".join(results) if results else "Termo não encontrado nos documentos."