import os
import re
from pathlib import Path

try:
    import fitz
except ImportError:
    fitz = None


def _base_dir() -> Path:
    """Retorna o diretório base absoluto para resolução de caminhos das tools."""
    env = os.environ.get("ADK_AGENT_DATA_DIR")
    return (Path.cwd() / env).resolve() if env else Path.cwd()


def _resolve(path: str) -> str:
    """Resolve um caminho relativo contra _base_dir(), absolutos passam direto."""
    p = Path(path)
    return str(p) if p.is_absolute() else str(_base_dir() / p)


def extract_text(file_path: str) -> str:
    """Extrai texto de um arquivo PDF, TXT ou MD. Se file_path for um diretório, lê o primeiro arquivo encontrado."""
    file_path = _resolve(file_path)
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

    matrix_dir = str(_base_dir() / "data" / "matrix")

    if not filename:
        supported = ('.pdf', '.txt', '.md')
        files = [f for f in sorted(os.listdir(matrix_dir)) if f.endswith(supported)]
        if not files:
            return "Erro: nenhum arquivo encontrado em data/matrix/."
        filename = files[0]

    input_path = filename if os.path.isabs(filename) else os.path.join(matrix_dir, os.path.basename(filename))
    output_dir = str(_base_dir() / "data" / "chunks")

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


def ler_chunk(index: int):
    """Lê um chunk específico já gerado."""
    chunk_path = str(_base_dir() / "data" / "chunks" / f"chunk_{index:03d}.txt")
    if not os.path.exists(chunk_path):
        return f"Erro: Chunk {index} não encontrado."
    with open(chunk_path, "r", encoding="utf-8") as f:
        return f.read()
