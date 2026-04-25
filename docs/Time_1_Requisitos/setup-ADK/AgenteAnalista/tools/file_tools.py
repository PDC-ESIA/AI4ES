import os
import re

try:
    import fitz
except ImportError:
    fitz = None


def extract_text(file_path: str) -> str:
    """Extrai texto de um arquivo PDF, TXT ou MD. Se file_path for um diretório, lê o primeiro arquivo encontrado."""
    if os.path.isdir(file_path):
        supported = ('.pdf', '.txt', '.md')
        files = [f for f in sorted(os.listdir(file_path)) if f.endswith(supported)]
        if not files:
            return f"Erro: nenhum arquivo suportado encontrado em '{file_path}'."
        file_path = os.path.join(file_path, files[0])

    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf':
        if fitz is None:
            raise ImportError("Suporte a PDF requer PyMuPDF. Instale com `pip install pymupdf`.")
        text = ""
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()
        return text
    elif ext in ('.txt', '.md'):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        raise ValueError(f"Extensão '{ext}' não suportada.")


def run_slicer(filename: str = "", paragraphs_per_chunk: int = 2, overlap_count: int = 1) -> str:
    """
    Fatia o documento matriz por parágrafos com overlap.
    Se filename não for informado, usa o primeiro arquivo encontrado em data/matrix/.
    """
    if paragraphs_per_chunk <= 0:
        return "Erro: paragraphs_per_chunk deve ser maior que 0."
    if not (0 <= overlap_count < paragraphs_per_chunk):
        return f"Erro: overlap_count deve ser entre 0 e {paragraphs_per_chunk - 1} (menor que paragraphs_per_chunk)."

    matrix_dir = os.path.join("data", "matrix")

    if not filename:
        supported = ('.pdf', '.txt', '.md')
        files = [f for f in sorted(os.listdir(matrix_dir)) if f.endswith(supported)]
        if not files:
            return "Erro: nenhum arquivo encontrado em data/matrix/."
        filename = files[0]

    input_path = filename if os.path.isabs(filename) else os.path.join(matrix_dir, os.path.basename(filename))
    output_dir = os.path.join("data", "chunks")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        for file in os.listdir(output_dir):
            file_path = os.path.join(output_dir, file)
            if file.startswith("chunk_") and file.endswith(".txt") and os.path.isfile(file_path):
                os.remove(file_path)

    try:
        content = extract_text(input_path)
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', content) if p.strip()]
        chunks = []
        start = 0

        while start < len(paragraphs):
            end = start + paragraphs_per_chunk
            chunks.append("\n\n".join(paragraphs[start:end]))
            if end >= len(paragraphs):
                break
            start += (paragraphs_per_chunk - overlap_count)

        for i, text in enumerate(chunks):
            with open(os.path.join(output_dir, f"chunk_{i:03d}.txt"), 'w', encoding='utf-8') as out:
                out.write(text)

        return f"Sucesso: {filename} fatiado em {len(chunks)} arquivos (por parágrafo com overlap)."
    except Exception as e:
        return f"Erro no fatiamento: {str(e)}"


def run_search(term: str, context_lines: int = 3) -> str:
    """
    Busca o termo em todos os arquivos .txt dentro de data/chunks.
    Retorna trechos com contexto ao redor do termo.
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


def check_glossary(term: str) -> str:
    """
    Verifica se um termo já existe no glossário.

    Args:
        term: O termo a verificar.

    Returns:
        Mensagem indicando se o termo existe ou não, com sua definição atual se existir.
    """
    glossary_path = os.path.join("knowledge", "glossario.md")

    if not os.path.exists(glossary_path):
        return "Erro: Arquivo glossario.md não encontrado em knowledge/."

    with open(glossary_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.split('|')]
        if len(cells) >= 4 and cells[1].lower() == term.strip().lower():
            return f"Termo '{term}' já existe no glossário. Definição atual: {cells[2]}"

    return f"Termo '{term}' não encontrado no glossário."


def add_to_glossary(term: str, definition: str, sources: str):
    """
    Adiciona um termo técnico ao glossário em knowledge/glossario.md.
    Se o termo já existir, atualiza a definição e as fontes.

    Args:
        term: O termo técnico a ser adicionado.
        definition: A definição formal extraída do documento.
        sources: As fontes (nomes dos chunks separados por vírgula, ex: "chunk_001.txt, chunk_003.txt").

    Returns:
        Mensagem de sucesso ou erro.
    """
    glossary_path = os.path.join("knowledge", "glossario.md")

    if not os.path.exists(glossary_path):
        return "Erro: Arquivo glossario.md não encontrado em knowledge/."

    try:
        with open(glossary_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Escapa pipes dentro da definição para não quebrar a tabela markdown
        definition_clean = definition.replace('|', '\\|').strip()
        sources_clean = sources.replace('|', '\\|').strip()
        term_clean = term.strip()

        new_row = f"| {term_clean} | {definition_clean} | {sources_clean} |"

        # Verifica se o termo já existe na tabela (case-insensitive)
        lines = content.split('\n')
        term_found = False
        for i, line in enumerate(lines):
            # Procura por linhas da tabela que começam com | Termo |
            if line.startswith('|'):
                cells = [c.strip() for c in line.split('|')]
                # cells[0] é vazio (antes do primeiro |), cells[1] é o termo
                if len(cells) >= 4 and cells[1].lower() == term_clean.lower():
                    lines[i] = new_row
                    term_found = True
                    break

        if term_found:
            content = '\n'.join(lines)
        else:
            # Adiciona nova linha ao final da tabela
            content = content.rstrip('\n') + '\n' + new_row + '\n'

        with open(glossary_path, 'w', encoding='utf-8') as f:
            f.write(content)

        action = "atualizado" if term_found else "adicionado"
        return f"Sucesso: Termo '{term_clean}' {action} no glossário."

    except Exception as e:
        return f"Erro ao escrever no glossário: {str(e)}"


