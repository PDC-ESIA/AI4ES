import re
from typing import Dict, List

class ContentValidator:
    @staticmethod
    def validate_diagram(content: str, file_type: str) -> Dict:
        """
        Valida o conteúdo de diagramas antes de serem persistidos no repositório.

        Esta ferramenta deve ser utilizada pelo agente sempre que for necessário
        garantir que o conteúdo gerado esteja sintaticamente correto antes de salvar
        arquivos do tipo Markdown (.md) ou PlantUML (.puml).

        Regras de validação:

        - Para arquivos `.puml` (PlantUML):
            - Deve conter obrigatoriamente os delimitadores:
                @startuml e @enduml
            - @startuml deve aparecer antes de @enduml
            - Não pode haver múltiplos blocos conflitantes

        - Para arquivos `.md` (Markdown):
            - O conteúdo não pode estar vazio
            - Deve ser texto válido (string não nula)
            - Opcionalmente pode conter títulos (#), listas ou blocos de código

        Parâmetros:
            content (str):
                Conteúdo gerado pelo agente que será validado.

            file_type (str):
                Tipo do arquivo a ser validado. Valores esperados:
                - "puml"
                - "md"

        Retorno:
            Dict contendo:
                - valid (bool): Indica se o conteúdo é válido
                - errors (List[str]): Lista de erros encontrados
                - warnings (List[str]): Lista de avisos (opcional)

        Comportamento esperado:
            - Se `valid` for False, o agente NÃO deve prosseguir com o salvamento.
            - O agente pode tentar corrigir o conteúdo com base nos erros retornados.

        Exemplos de uso:
            validate_diagram_content(content, "puml")
            validate_diagram_content(content, "md")
        """
        
        errors: List[str] = []
        warnings: List[str] = []
        
        if not content or not isinstance(content, str):
            return {
                "valid": False,
                "errors": ["Conteúdo vazio ou inválido"],
                "warnings": []
            }
            
        file_type = file_type.lower()
        
        if file_type == "puml":
            if "@startuml" not in content:
                errors.append("Falta o marcador @startuml")
                
            if "@enduml" not in content:
                errors.append("Falta o marcador @enduml")
                
            if "@startuml" in content and "@enduml" in content:
                if content.index("@startuml") > content.index("@enduml"):
                    errors.append("@startuml deve vir antes de @enduml")
            
            if content.count("@startuml") > 1 or content.count("@enduml") > 1:
                warnings.append("Múltiplos blocos UML detectados")  
                      
        elif file_type=="md":
            if len(content.strip()) == 0:
                errors.append("Markdown vazio")
                
            if not any(token in content for token in ["#", "-", "*", "```"]):
                warnings.append("Markdown sem estrutura comum - Títulos, Listas ou código")
            
        else:
            errors.append(f"Tipo de arquivo não suportado: {file_type}")
            
        return{
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }