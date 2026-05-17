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
    """Extrai texto de um documento PDF, TXT ou MD.

    Use quando precisar do conteúdo bruto de um documento de
    requisitos ou referência para análise textual. Suporta PDF (via
    PyMuPDF), TXT e Markdown. Se `file_path` for um diretório,
    automaticamente lê o primeiro arquivo suportado encontrado em
    ordem alfabética.

    Args:
        file_path: Caminho de arquivo (.pdf, .txt, .md) ou diretório
            contendo um arquivo suportado. Caminhos relativos são
            resolvidos contra ADK_AGENT_DATA_DIR (se definido) ou
            CWD.

    Returns:
        str com o conteúdo textual extraído, ou string iniciada por
        "Erro:" descrevendo extensão não suportada, diretório vazio
        ou falha de leitura. Pode levantar ImportError se PDF for
        solicitado sem PyMuPDF instalado.
    """
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
        return f"Erro: extensão '{ext}' não suportada (esperado .pdf, .txt ou .md) — file_path='{file_path}'."


def run_slicer(filename: str = "", paragraphs_per_chunk: int = 2, overlap_count: int = 1) -> str:
    """Fragmenta um documento extenso em partes processáveis com overlap.

    Use quando precisar analisar um documento de requisitos cujo
    tamanho excede uma janela de leitura razoável. O documento é
    quebrado em chunks de N parágrafos com sobreposição configurável,
    salvos em `data/chunks/chunk_NNN.txt`. Chunks antigos do diretório
    são limpos antes de gerar os novos.

    Após fatiar, use a capacidade de leitura de chunk individual para
    consumir cada parte por demanda, e a capacidade de busca para
    localizar termos.

    Args:
        filename: Nome do arquivo na pasta `data/matrix/` (ou caminho
            absoluto). Se vazio, usa o primeiro arquivo encontrado em
            `data/matrix/`.
        paragraphs_per_chunk: Tamanho do chunk em parágrafos. Default
            2. Deve ser > 0.
        overlap_count: Número de parágrafos compartilhados entre
            chunks consecutivos. Default 1. Deve ser >= 0 e estritamente
            menor que `paragraphs_per_chunk`.

    Returns:
        str com mensagem "Sucesso: <filename> fatiado em N arquivos
        ..." ou "Erro: ..." em caso de validação inválida, diretório
        inexistente ou falha de extração.
    """
    if paragraphs_per_chunk <= 0:
        return "Erro: paragraphs_per_chunk deve ser maior que 0."
    if not (0 <= overlap_count < paragraphs_per_chunk):
        return f"Erro: overlap_count deve ser entre 0 e {paragraphs_per_chunk - 1} (menor que paragraphs_per_chunk)."

    matrix_dir = str(_base_dir() / "data" / "matrix")

    if not filename:
        if not os.path.isdir(matrix_dir):
            return f"Erro: diretório '{matrix_dir}' não existe — informe explicitamente um filename ou crie o diretório com o documento matriz."
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
    """Lê um chunk individual previamente gerado pela fragmentação.

    Use depois de fragmentar um documento para acessar uma parte
    específica por índice. Os chunks são arquivos `chunk_NNN.txt` em
    `data/chunks/`, gerados pela capacidade de fragmentação.

    Args:
        index: Índice numérico do chunk (0-based). Equivale ao número
            no nome do arquivo (chunk_000.txt -> index=0).

    Returns:
        str com o conteúdo do chunk, ou string "Erro: Chunk N não
        encontrado." se o índice for inválido ou os chunks não tiverem
        sido gerados ainda.
    """
    chunk_path = str(_base_dir() / "data" / "chunks" / f"chunk_{index:03d}.txt")
    if not os.path.exists(chunk_path):
        return f"Erro: Chunk {index} não encontrado."
    with open(chunk_path, "r", encoding="utf-8") as f:
        return f.read()
