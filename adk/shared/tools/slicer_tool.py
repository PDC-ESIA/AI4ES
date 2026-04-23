import os
import re

try:
    import fitz
except ImportError:
    fitz = None

def extract_text(file_path):
    """Extrai texto de diferentes formatos (PDF, TXT, MD)."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.pdf':
        if fitz is None:
            raise ImportError(
                "Suporte a PDF requer PyMuPDF. Instale com `pip install pymupdf`."
            )
        text = ""
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()
        return text
    elif ext in ('.txt', '.md'):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        raise ValueError(f"Extensão {ext} não suportada.")

def run_slicer(filename: str, paragraphs_per_chunk: int = 2, overlap_count: int = 1):
    """
    Fatia o documento matriz por PARÁGRAFOS com overlap.
    
    Args:
        filename: Nome do arquivo em data/matrix/
        paragraphs_per_chunk: Quantos parágrafos cada arquivo .txt terá.
        overlap_count: Quantos parágrafos do final do chunk anterior serão repetidos no próximo.
    """
    input_path = os.path.join("data", "matrix", filename) # @todo avaliar se o contexto esta sendo sempre salvo como matrix
    output_dir = os.path.join("data", "chunks")
    
    os.makedirs(output_dir, exist_ok=True)

    try:
        # 1. Extração do texto completo
        content = extract_text(input_path)
        if not content.strip():
            return "Erro: Nenhum texto encontrado no arquivo."

        # 2. Divisão em parágrafos 
        # (Usa regex para capturar quebras de linha duplas ou múltiplas, comum em documentos)
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', content) if p.strip()]
        chunks = []
        start = 0
        
        # 3. Lógica de Janela Deslizante por LISTA de parágrafos
        while start < len(paragraphs):
            end = start + paragraphs_per_chunk
            
            # Pega o subconjunto de parágrafos e junta-os com quebra de linha dupla
            chunk_content = "\n\n".join(paragraphs[start:end])
            chunks.append(chunk_content)
            
            if end >= len(paragraphs): break
            
             # O índice de início avança o tamanho do chunk menos o overlap
            start += (paragraphs_per_chunk - overlap_count)

        # 4. Salvamento em .txt
        for i, text in enumerate(chunks):
            chunk_name = f"chunk_{i:03d}.txt"
            with open(os.path.join(output_dir, chunk_name), 'w', encoding='utf-8') as out:
                out.write(text)
        
        return f"Sucesso: {filename} fatiado em {len(chunks)} arquivos (por parágrafo com overlap)."

    except Exception as e:
        return f"Erro no fatiamento: {str(e)}"
    
    
    

def ler_chunk(index: int):
    """Lê um chunk específico já gerado."""
    chunk_path = os.path.join("data", "chunks", f"chunk_{index:03d}.txt")
    if not os.path.exists(chunk_path):
        return f"Erro: Chunk {index} não encontrado."
    with open(chunk_path, "r", encoding="utf-8") as f:
        return f.read()

