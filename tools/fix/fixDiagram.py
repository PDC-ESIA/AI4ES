
from typing import Dict, List


class ContentFixer:
    @staticmethod
    def fix_diagram(content: str, file_type: str) -> Dict:
        """
        Tenta corrigir automaticamente o conteúdo de diagramas gerados pelo agente,
        com base em erros comuns de sintaxe para arquivos Markdown (.md) e PlantUML (.puml).

        Esta ferramenta deve ser utilizada SOMENTE quando a validação falhar,
        como etapa intermediária antes de uma nova tentativa de validação e salvamento.

        Objetivo:
            - Corrigir erros simples e previsíveis automaticamente
            - Melhorar a qualidade do conteúdo gerado pelo agente
            - Reduzir falhas de persistência por problemas sintáticos básicos

        Regras de correção:

        - Para arquivos `.puml` (PlantUML):
            - Adiciona @startuml no início se estiver ausente
            - Adiciona @enduml no final se estiver ausente
            - Corrige ordem caso @enduml apareça antes de @startuml
            - Remove duplicações simples de delimitadores

        - Para arquivos `.md` (Markdown):
            - Remove espaços excessivos
            - Garante que o conteúdo não esteja vazio
            - Pode adicionar estrutura mínima (ex: título padrão) se necessário

        Parâmetros:
            content (str):
                Conteúdo original gerado pelo agente

            file_type (str):
                Tipo do arquivo a ser corrigido. Valores esperados:
                - "puml"
                - "md"

        Retorno:
            Dict contendo:
                - fixed_content (str): Conteúdo corrigido
                - applied_fixes (List[str]): Lista de correções realizadas
                - warnings (List[str]): Avisos sobre possíveis limitações da correção

        Comportamento esperado:
            - O agente deve SEMPRE validar novamente após aplicar esta ferramenta
            - Esta ferramenta não garante correção completa, apenas melhorias heurísticas
            - Não deve ser usada como substituto da geração correta de conteúdo

        Exemplo de uso:
            fix_diagram(content, "puml")
            fix_diagram(content, "md")
        """

        applied_fixes: List[str] = []
        warnings: List[str] = []
        
        if not content or not isinstance(content, str):
            return {
                "fixed_content": "",
                "applied_fixes": [],
                "warnings": ["Conteúdo inválido/vazio — não foi possível corrigir"]
            }
        
        file_type = file_type.lower()
        fixed_content = content.strip()
        
        if file_type == "puml":
            has_start = ("@startuml" in fixed_content)
            has_end = ("@enduml" in fixed_content)
        
            #correção de ausência
            if not has_start:
                    fixed_content = "@startuml\n" + fixed_content
                    applied_fixes.append("Adicionado @startuml no início")
                    
            if not has_end:
                    fixed_content = fixed_content + "\n@enduml"
                    applied_fixes.append("Adicionado @enduml no final")
            #correção de ordem
            if has_start and has_end:
                if fixed_content.index("@startuml")>fixed_content.index("@enduml"):
                    fixed_content = fixed_content.replace("@startuml", "")
                    fixed_content = fixed_content.replace("@enduml", "")
                    fixed_content = "@startuml\n" + fixed_content + "\n@enduml"
                    applied_fixes.append("Correção da ordem dos delimitadores UML - @startuml e @enduml")
            
            #correção de duplicações
            if fixed_content.count("@startuml") > 1:
                fixed_content = fixed_content.replace("@startuml", "", fixed_content.count("@startuml")-1)
                fixed_content = "@startuml\n" + fixed_content
                applied_fixes.append("Removido multiplos @startuml")
                
            
            if fixed_content.count("@enduml") > 1:  
                fixed_content = fixed_content.replace("@enduml", "", fixed_content.count("@enduml")-1)
                fixed_content = "@enduml\n" + fixed_content
                applied_fixes.append("Removido multiplos @enduml")
                
        elif file_type == "md":
            #Remoção de espaços extras
            cleaned = "\n".join(line.strip() for line in fixed_content.splitlines() if line.strip())
            
            if cleaned != fixed_content:
                fixed_content = cleaned
                applied_fixes.append("Removidos espaços em branco desnecessários")

            if len(fixed_content) == 0:
                fixed_content = "# Documento  \n\nConteúdo não especificado"
                applied_fixes.append("Inserido conteúdo mínimo ao arquivo Markdown")
            
            if not any(token in fixed_content for token in["#", "-", "*", "```"]):
                fixed_content = "# Documento\n\n" +  fixed_content
                applied_fixes.append("Inserido título padrão ao arquivo Markdown")
        else:
            warnings.append(f"Tipo de arquivo não suportado para correção: {file_type}")
            
        return{
            "fixed_content": fixed_content,
            "applied_fixes": applied_fixes,
            "warnings": warnings
        }