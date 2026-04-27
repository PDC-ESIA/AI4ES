import re
from typing import Dict, List

class ContentValidator:
    """
    Valida o conteúdo de diagramas e documentos antes de serem persistidos.
    Suporta: Mermaid (.mmd) e Markdown (.md).
    """
    
    MERMAID_DIAGRAM_TYPES = [
            "graph", "flowchart", "sequenceDiagram", "classDiagram",
            "stateDiagram", "stateDiagram-v2", "erDiagram", "gantt",
            "pie", "gitGraph", "journey", "mindmap", "timeline",
            "quadrantChart", "requirementDiagram", "C4Context",
        ]
            
    MD_SPECIAL_ESCAPE_CHARS = r'\\`*_{}[]<>()#+-.!'    
    
    # ---------------------------------------------------------------------------
    # Função raíz de validação
    # ---------------------------------------------------------------------------
    @staticmethod
    def validate_diagram(content: str, file_type: str) -> Dict:
        """
        Valida o conteúdo gerado pelo agente antes do salvamento.
 
        Parâmetros:
            content   (str): Conteúdo bruto a ser validado.
            file_type (str): "mmd" | "md"
 
        Retorno:
            Dict com:
                - valid    (bool)
                - errors   (List[str])
                - warnings (List[str])
        """
        errors: List[str] = []
        warnings: List[str] = []
 
        #1. Guarda de entrada 
        if not content or not isinstance(content, str):
            return {"valid": False, "errors": ["Conteúdo vazio ou inválido"], "warnings": []}
 
        file_type = file_type.lower().strip()
 
        #2.  Destinação ao validador específico 
        
        if file_type == "mmd":
            errors, warnings = ContentValidator._validate_mermaid(content)
        elif file_type == "md":
            errors, warnings = ContentValidator._validate_markdown(content)
        else:
            errors.append(f"Tipo de arquivo não suportado: '{file_type}'. Use 'mmd' ou 'md'.")
 
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
    
    # ---------------------------------------------------------------------------
    # Validador Mermaid
    # ---------------------------------------------------------------------------
    @staticmethod
    def _validate_mermaid(content: str):
        errors: List[str] = []
        warnings: List[str] = []
 
        stripped = content.strip()
 
        # 1. Detecção de tipo de diagrama obrigatória
        first_token = stripped.split()[0] if stripped.split() else ""
        known = ContentValidator.MERMAID_DIAGRAM_TYPES
        found_type = next((t for t in known if stripped.lower().startswith(t.lower())), None)
 
        if not found_type:
            errors.append(
                f"Declaração de tipo de diagrama Mermaid ausente ou inválida. "
                f"Primeiro token encontrado: '{first_token}'. "
                f"Tipos válidos: {', '.join(known[:8])}..."
            )
 
        # 2. Corpo não pode estar vazio após o tipo
        lines = [l for l in stripped.splitlines() if l.strip()]
        if len(lines) < 2:
            errors.append("Corpo do diagrama Mermaid está vazio — nenhum nó ou relação definida")
 
        # 3. Heurística: verifica se há pelo menos um conector/relação
        has_relation = bool(
            re.search(r'(-->|->|--\|>|==|:::|-\.-|<-->|\|)', stripped)
            or re.search(r'(\w+\s*:\s*\w+)', stripped)   # gantt / pie / erDiagram
        )
        if not has_relation and len(lines) >= 2:
            warnings.append("Nenhum conector ou relação detectado no diagrama Mermaid — verifique se há nós isolados")
 
        # 4. Aspas não fechadas
        for i, line in enumerate(stripped.splitlines(), 1):
            if line.count('"') % 2 != 0:
                errors.append(f"Aspas não fechadas na linha {i}: {line.strip()[:60]}")
 
        # 5. Blocos de código Markdown envolvendo Mermaid (deve estar limpo para .mmd)
        if "```" in stripped:
            warnings.append(
                "Delimitadores de bloco de código Markdown (```) encontrados em arquivo .mmd — "
                "remova-os, pois o arquivo já é o código Mermaid puro"
            )
 
        return errors, warnings
       
    
    # ---------------------------------------------------------------------------
    # Validador Markdown
    # ---------------------------------------------------------------------------
    @staticmethod
    def _validate_markdown(content: str):
        errors: List[str] = []
        warnings: List[str] = []
 
        stripped = content.strip()
 
        # 1. Conteúdo vazio
        if not stripped:
            errors.append("Documento Markdown vazio")
            return errors, warnings
 
        # 2. Estrutura mínima
        has_structure = any(tok in stripped for tok in ["#", "-", "*", "```", ">", "|"])
        if not has_structure:
            warnings.append("Markdown sem estrutura detectável (títulos, listas, tabelas ou blocos de código)")
 
        # 3. ── Integridade de blocos de código ──────────────────────────────
        fence_pattern = re.compile(r'^(`{3,}|~{3,})', re.MULTILINE)
        fences = fence_pattern.findall(stripped)
 
        # Cada bloco exige abertura + fechamento
        if len(fences) % 2 != 0:
            errors.append(
                f"Bloco de código não fechado: {len(fences)} delimitador(es) encontrado(s) "
                f"(esperava-se número par). Verifique blocos ``` ou ~~~ sem fechamento."
            )
 
        # Valida pares de fences correspondentes
        fence_stack = []
        for match in re.finditer(r'^(`{3,}|~{3,})', stripped, re.MULTILINE):
            token = match.group(1)
            char = token[0]
            length = len(token)
            if not fence_stack:
                fence_stack.append((char, length, match.start()))
            else:
                top_char, top_len, top_pos = fence_stack[-1]
                if top_char == char and top_len == length:
                    fence_stack.pop()  # fechou corretamente
                else:
                    fence_stack.append((char, length, match.start()))
 
        if fence_stack:
            positions = [pos for _, _, pos in fence_stack]
            errors.append(
                f"Blocos de código desbalanceados: {len(fence_stack)} bloco(s) aberto(s) sem fechamento. "
                f"Posições aproximadas (char offset): {positions}"
            )
 
        # 4. ── Caracteres especiais sem escape ────────────────────────────────
        # Detecta < e > fora de blocos de código (pode quebrar renderização HTML)
        outside_code = re.sub(r'`{3,}[\s\S]*?`{3,}', '', stripped)   # remove blocos
        outside_code = re.sub(r'`[^`\n]+`', '', outside_code)          # remove inline code
 
        raw_html_pattern = re.compile(r'<(?![\!/-])[a-zA-Z][^>]{0,80}>')
        html_matches = raw_html_pattern.findall(outside_code)
        if html_matches:
            warnings.append(
                f"Tags HTML brutas detectadas fora de blocos de código: {html_matches[:3]}. "
                f"Considere escapar com &lt; &gt; ou envolver em bloco de código."
            )
 
        # 5. Links e imagens malformados
        broken_links = re.findall(r'\[([^\]]*)\]\s*\([^)]*$', stripped, re.MULTILINE)
        if broken_links:
            errors.append(
                f"Link(s) Markdown malformado(s) — parêntese de fechamento ausente: {broken_links[:3]}"
            )
 
        # 6. Heading sem espaço após #
        bad_headings = re.findall(r'^#{1,6}[^ #\n]', stripped, re.MULTILINE)
        if bad_headings:
            warnings.append(
                f"Heading(s) sem espaço após '#': {bad_headings[:3]} — pode não renderizar corretamente"
            )
 
        # 7. Tabelas desbalanceadas
        table_rows = [l for l in stripped.splitlines() if l.strip().startswith("|")]
        if table_rows:
            col_counts = [len(re.findall(r'\|', row)) for row in table_rows]
            if len(set(col_counts)) > 1:
                warnings.append(
                    f"Tabela Markdown com número inconsistente de colunas por linha: {set(col_counts)}"
                )
 
        return errors, warnings
    
    
