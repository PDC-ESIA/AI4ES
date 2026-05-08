import os
from pathlib import Path


def _base_dir() -> Path:
    env = os.environ.get("ADK_AGENT_DATA_DIR")
    return (Path.cwd() / env).resolve() if env else Path.cwd()


def check_glossary(term: str) -> str:
    """
    Verifica se um termo já existe no glossário com status Válido.

    Args:
        term: O termo a verificar.

    Returns:
        Mensagem indicando se o termo existe (com definição vigente) ou não.
    """
    glossary_path = str(_base_dir() / "knowledge" / "glossario.md")

    if not os.path.exists(glossary_path):
        return "Erro: Arquivo glossario.md não encontrado em knowledge/."

    with open(glossary_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.split('|')]
        # cells: ['', Termo, Definição, Fontes, Status, '']
        if len(cells) >= 5 and cells[1].lower() == term.strip().lower():
            status = cells[4] if len(cells) > 4 else ""
            if status.lower() == "válido":
                return f"Termo '{term}' já existe no glossário. Definição atual: {cells[2]}"

    return f"Termo '{term}' não encontrado no glossário."


def add_to_glossary(term: str, definition: str, sources: str):
    """
    Adiciona um termo técnico ao glossário em knowledge/glossario.md.
    Se o termo já existir com status Válido, marca a versão anterior como
    Substituído e adiciona uma nova linha com status Válido.
    Se a definição for idêntica à vigente, não faz alterações.

    Args:
        term: O termo técnico a ser adicionado.
        definition: A definição formal extraída do documento.
        sources: As fontes (nomes dos chunks separados por vírgula, ex: "chunk_001.txt, chunk_003.txt").

    Returns:
        Mensagem de sucesso ou erro.
    """
    glossary_path = str(_base_dir() / "knowledge" / "glossario.md")

    if not os.path.exists(glossary_path):
        return "Erro: Arquivo glossario.md não encontrado em knowledge/."

    try:
        with open(glossary_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Escapa pipes dentro da definição para não quebrar a tabela markdown
        definition_clean = definition.replace('|', '\\|').strip()
        sources_clean = sources.replace('|', '\\|').strip()
        term_clean = term.strip()

        new_row = f"| {term_clean} | {definition_clean} | {sources_clean} | Válido |"

        lines = content.split('\n')
        term_found = False
        existing_definition = ""

        # Procura linha válida existente do mesmo termo
        for i, line in enumerate(lines):
            if not line.startswith('|'):
                continue
            cells = [c.strip() for c in line.split('|')]
            if len(cells) >= 5 and cells[1].lower() == term_clean.lower():
                status = cells[4] if len(cells) > 4 else ""
                if status.lower() == "válido":
                    existing_definition = cells[2]
                    # Se a definição é idêntica, não faz nada
                    if existing_definition == definition_clean:
                        return f"Termo '{term_clean}' já existe com definição idêntica. Nenhuma alteração feita."
                    # Marca a linha atual como Substituído (preserva conteúdo original)
                    lines[i] = f"| {cells[1]} | {cells[2]} | {cells[3]} | Substituído |"
                    term_found = True
                    break

        # Reconstrói o conteúdo e adiciona a nova linha ao final
        content = '\n'.join(lines)
        content = content.rstrip('\n') + '\n' + new_row + '\n'

        with open(glossary_path, 'w', encoding='utf-8') as f:
            f.write(content)

        action = "atualizado (versão anterior preservada como Substituído)" if term_found else "adicionado"
        return f"Sucesso: Termo '{term_clean}' {action} no glossário."

    except Exception as e:
        return f"Erro ao escrever no glossário: {str(e)}"
