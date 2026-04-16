import os
import fitz  
import re

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
        text = ""
        with fitz.open(file_path) as doc:
            for page in doc:
                text += page.get_text()
        return text
    elif ext in ('.txt', '.md'):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return f"Erro: extensão '{ext}' não suportada."

def run_slicer(filename: str = "", paragraphs_per_chunk: int = 2, overlap_count: int = 1) -> str:
    """
    Fatia o documento matriz por parágrafos com overlap.
    Se filename não for informado, usa o primeiro arquivo encontrado em data/matrix/.
    """
    matrix_dir = os.path.join("data", "matrix")

    if not filename:
        supported = ('.pdf', '.txt', '.md')
        files = [f for f in sorted(os.listdir(matrix_dir)) if f.endswith(supported)]
        if not files:
            return "Erro: nenhum arquivo encontrado em data/matrix/."
        filename = files[0]

    # Aceita tanto nome simples quanto caminho completo
    input_path = filename if os.path.isabs(filename) else os.path.join(matrix_dir, os.path.basename(filename))
    output_dir = os.path.join("data", "chunks")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        # Limpa chunks antigos
        for file in os.listdir(output_dir):
            os.remove(os.path.join(output_dir, file))

    try:
        # 1. Extração do texto completo
        content = extract_text(input_path)

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
            
            if end >= len(paragraphs):
                break
            
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