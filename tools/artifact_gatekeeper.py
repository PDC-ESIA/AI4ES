"""
artifact_gatekeeper.py
──────────────────────
Parser / Validator — Gatekeeper  (ferramenta determinística)
Camada GUARDRAIL da arquitetura A2A.
 
Responsabilidade:
    Recebe o artefato bruto do Agente Arquiteto, delega a validação ao
    ContentValidator e devolve um GatekeeperResult padronizado para o
    Supervisor / loop de auto-correção.
 
Separação de papéis:
    ┌─────────────────────┐      invoca      ┌──────────────────────┐
    │  ArtifactGatekeeper │ ───────────────► │   ContentValidator   │
    │  (decisão / contrato│ ◄─────────────── │   (regras / parsing) │
    └─────────────────────┘   errors/warnings└──────────────────────┘
             │
             ▼ GatekeeperResult
    { valid, error_type, error_message, line_number, suggested_fix }
 
Payload de saída espelha exatamente o diagrama de arquitetura:
    { valid, error_type, error_message, line_number, suggested_fix }
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
#Função local
from contentValidator import ContentValidator

# ──────────────────────────────────────────────────────────────────────────────
# Tipos de erro 
# ──────────────────────────────────────────────────────────────────────────────
 
class ErrorType(str, Enum):
    EMPTY_CONTENT       = "EMPTY_CONTENT"       # conteúdo vazio / None
    UNSUPPORTED_FORMAT  = "UNSUPPORTED_FORMAT"  # extensão desconhecida
    MISSING_DELIMITER   = "MISSING_DELIMITER"   # @startuml/@enduml ausente
    INVALID_STRUCTURE   = "INVALID_STRUCTURE"   # bloco malformado
    UNKNOWN_DIAGRAM     = "UNKNOWN_DIAGRAM"     # tipo Mermaid não reconhecido
    INVALID_GRAMMAR     = "INVALID_GRAMMAR"     # gramática inválida (aspas, fences…)
    MULTIPLE_ERRORS     = "MULTIPLE_ERRORS"     # mais de um erro — ver error_message
 
 
 
# ──────────────────────────────────────────────────────────────────────────────
# Resultado — contrato público do Gatekeeper
# ──────────────────────────────────────────────────────────────────────────────
 
@dataclass
class GatekeeperResult:
    """
    Payload estruturado devolvido ao Supervisor / Arquiteto.
    Campos opcionais ficam None quando valid=True.
    """
    #Atributos da raiz da classe (self)
    valid:          bool
    error_type:     Optional[ErrorType] = None
    error_message:  Optional[str]       = None
    line_number:    Optional[int]       = None
    suggested_fix:  Optional[str]       = None
 
    # Campos extras (não exibidos ao LLM, úteis para logging/métricas)
    warnings:       list[str]           = field(default_factory=list)
    format_detected:   Optional[str]       = None
 
    def to_dict(self) -> dict:
        """Serialização da resposta, padrão para envio entre agentes."""
        return {
            "valid":         self.valid,
            "error_type":    self.error_type.value if self.error_type else None,
            "error_message": self.error_message,
            "line_number":   self.line_number,
            "suggested_fix": self.suggested_fix,
        }
 
    def to_feedback_prompt(self) -> str:
        """
        Texto pronto para ser injetado como feedback no próximo prompt do Arquiteto.
        Usado pelo Supervisor no loop de auto-correção.
        """
        if self.valid:
            return "✅ Artefato validado com sucesso. Prossiga para persistência."
 
        parts = [
            f"❌ Artefato inválido [{self.error_type.value if self.error_type else 'ERRO'}]",
            f"Problema: {self.error_message}",
        ]
        if self.line_number:
            parts.append(f"Linha aproximada: {self.line_number}")
        if self.suggested_fix:
            parts.append(f"Correção sugerida: {self.suggested_fix}")
        if self.warnings:
            parts.append("Avisos adicionais:\n" + "\n".join(f"  • {w}" for w in self.warnings))
 
        return "\n".join(parts)
 

# ──────────────────────────────────────────────────────────────────────────────
# Mapeamento: mensagem de erro → ErrorType + sugestão
# ──────────────────────────────────────────────────────────────────────────────
 
# Cada entrada: (padrão regex, ErrorType, sugestão de correção)
_ERROR_CLASSIFIER: list[tuple[re.Pattern, ErrorType, str]] = [
    # PlantUML
    (re.compile(r"@startuml|@enduml", re.I),
     ErrorType.MISSING_DELIMITER,
     "Certifique-se de que o diagrama começa com '@startuml' e termina com '@enduml'."),
 
    (re.compile(r"ordem inválida|enduml.*antes", re.I),
     ErrorType.INVALID_STRUCTURE,
     "Inverta a ordem: '@startuml' deve vir antes de '@enduml'."),
 
    (re.compile(r"corpo.*vazio|vazio.*corpo", re.I),
     ErrorType.INVALID_STRUCTURE,
     "Adicione pelo menos um elemento entre os delimitadores do diagrama."),
 
    # Mermaid
    (re.compile(r"tipo de diagrama.*ausente|declaração.*inválida", re.I),
     ErrorType.UNKNOWN_DIAGRAM,
     "A primeira linha deve declarar o tipo: 'flowchart TD', 'sequenceDiagram', 'classDiagram'…"),
 
    (re.compile(r"aspas não fechadas|aspas.*linha", re.I),
     ErrorType.INVALID_GRAMMAR,
     "Feche todas as aspas duplas na linha indicada."),
 
    (re.compile(r"nenhum nó|corpo.*mermaid.*vazio", re.I),
     ErrorType.INVALID_STRUCTURE,
     "Defina pelo menos um nó e uma relação no diagrama."),
 
    # Markdown
    (re.compile(r"bloco de código não fechado|desbalanceados|sem fechamento", re.I),
     ErrorType.INVALID_GRAMMAR,
     "Adicione os delimitadores de fechamento (``` ou ~~~) dos blocos de código abertos."),
 
    (re.compile(r"link.*malformado|parêntese.*ausente", re.I),
     ErrorType.INVALID_STRUCTURE,
     "Corrija os links Markdown: o formato correto é [texto](url)."),
 
    (re.compile(r"vazio|inválido", re.I),
     ErrorType.EMPTY_CONTENT,
     "O conteúdo não pode ser vazio."),
 
    # Formato não suportado
    (re.compile(r"não suportado", re.I),
     ErrorType.UNSUPPORTED_FORMAT,
     "Use um dos formatos suportados: 'puml', 'mmd' ou 'md'."),
]
 
 
def _classify_error(error_msg: str) -> tuple[ErrorType, str]:
    """
    Converte a mensagem de texto do ContentValidator em um ErrorType
    e retorna uma sugestão de correção padronizada.
    """
    for pattern, error_type, suggestion in _ERROR_CLASSIFIER:
        if pattern.search(error_msg):
            return error_type, suggestion
    
    return ErrorType.INVALID_STRUCTURE, "Revise o conteúdo gerado e corrija o problema indicado."
 
 
def _extract_line_number(error_msg: str) -> Optional[int]:
    """Tenta extrair número de linha de mensagens como 'linha 5' ou 'line 5'."""
    match = re.search(r'\blinha\s+(\d+)\b|\bline\s+(\d+)\b', error_msg, re.I)
    if match:
        return int(match.group(1) or match.group(2))
    return None

# ──────────────────────────────────────────────────────────────────────────────
# Gatekeeper — classe principal
# ──────────────────────────────────────────────────────────────────────────────
 
class ArtifactGatekeeper:
    """
    Ferramenta determinística de guardrail.
 
    Uso típico (chamado pelo Supervisor ou diretamente pelo Arquiteto):
 
        result = ArtifactGatekeeper.check(content="@startuml\\n...\\n@enduml", format="puml")
        if not result.valid:
            # Reinjeta result.to_feedback_prompt() no próximo turno do Arquiteto
            ...
    """
 
    @staticmethod
    def check(content: str, format: str) -> GatekeeperResult:
        """
        Ponto de entrada único do Gatekeeper.
 
        Parâmetros
        ----------
        content : str   Texto bruto do artefato gerado pelo Agente Arquiteto.
        format  : str   Formato declarado: 'puml' | 'mmd' | 'md'
 
        Retorna
        -------
        GatekeeperResult
            .to_dict()             → payload A2A  { valid, error_type, … }
            .to_feedback_prompt()  → texto pronto para reinjetar no Arquiteto
        """
 
        # 1. Valida se o content está vazio
        if not content or not isinstance(content, str) or not content.strip():
            return GatekeeperResult(
                valid=False,
                error_type=ErrorType.EMPTY_CONTENT,
                error_message="Conteúdo vazio ou ausente recebido pelo Gatekeeper.",
                suggested_fix="O Agente Arquiteto deve gerar conteúdo não-vazio antes de invocar o Gatekeeper.",
            )
 
        format_clean = format.lower().strip()
 
        # 2. Valida formatos aceitos
        if format_clean not in ("puml", "mmd", "md"):
            return GatekeeperResult(
                valid=False,
                error_type=ErrorType.UNSUPPORTED_FORMAT,
                error_message=f"Formato '{format}' não suportado. Aceitos: 'puml', 'mmd', 'md'.",
                suggested_fix="Verifique a extensão do arquivo gerado pelo Agente Arquiteto.",
                format_detected=format_clean,
            )
 
        # 3. Chamada da tool ContentValidator
        validation_result: dict = ContentValidator.validate_diagram(content, format_clean)
 
        errors:   list[str] = validation_result.get("errors",   [])
        warnings: list[str] = validation_result.get("warnings", [])
 
        # 4. Artefato válido → passa para persistência
        if validation_result.get("valid"):
            return GatekeeperResult(
                valid=True,
                warnings=warnings,
                format_detected=format_clean,
            )
 
        # 5. Artefato inválido → classifica e monta resultado
        if len(errors) == 1:
            error_type, suggested_fix = _classify_error(errors[0])
            line_number = _extract_line_number(errors[0])
            error_message = errors[0]
        else:
            # Múltiplos erros: classifica pelo primeiro, lista todos na mensagem
            error_type, suggested_fix = _classify_error(errors[0])
            line_number = _extract_line_number(errors[0])
            error_type = ErrorType.MULTIPLE_ERRORS
            error_message = f"{len(errors)} erro(s) encontrado(s):\n" + "\n".join(
                f"  [{i+1}] {e}" for i, e in enumerate(errors)
            )
 
        return GatekeeperResult(
            valid=False,
            error_type=error_type,
            error_message=error_message,
            line_number=line_number,
            suggested_fix=suggested_fix,
            warnings=warnings,
            format_detected=format_clean,
        )
 
 
 
 
# ──────────────────────────────────────────────────────────────────────────────
# Testes - Ao rodar diretamente o arquivo
# ──────────────────────────────────────────────────────────────────────────────
 
if __name__ == "__main__":
    import json
 
    cases = [
        # ── PlantUML ──────────────────────────────────────────────────────────
        ("@startuml\nclass User {\n  +name: String\n}\n@enduml",           "puml", "PlantUML válido"),
        ("@startuml\nclass User {}\n",                                      "puml", "PlantUML sem @enduml"),
        ("@enduml\nclass User {}\n@startuml",                               "puml", "PlantUML ordem errada"),
        ("@startuml\n@enduml",                                              "puml", "PlantUML corpo vazio"),
        # ── Mermaid ──────────────────────────────────────────────────────────
        ("flowchart TD\n  A[Start] --> B[End]",                             "mmd", "Mermaid válido"),
        ("unknownDiagram\n  A --> B",                                       "mmd", "Mermaid tipo desconhecido"),
        ('flowchart TD\n  A["label] --> B',                                 "mmd", "Mermaid aspas desbalanceadas"),
        ("flowchart TD",                                                    "mmd", "Mermaid sem corpo"),
        # ── Markdown ─────────────────────────────────────────────────────────
        ("# Título\n\nTexto normal.\n\n```python\nprint('ok')\n```",        "md",  "Markdown válido"),
        ("# Título\n\n```python\nprint('ok')\n",                            "md",  "Markdown fence aberto"),
        ("[link quebrado](url sem fechar",                                  "md",  "Markdown link malformado"),
        # ── Edge cases ───────────────────────────────────────────────────────
        ("",                                                                "puml", "Conteúdo vazio"),
        ("qualquer coisa",                                                  "svg",  "Formato não suportado"),
    ]
 
    for content, fmt, label in cases:
        result = ArtifactGatekeeper.check(content, fmt)
        print(f"\n{'═'*60}")
        print(f"  {label}  [{fmt}]")
        print(f"{'─'*60}")
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        if not result.valid:
            print("\n📋 Feedback para o Arquiteto:")
            print(result.to_feedback_prompt())
        if result.warnings:
            print(f"\n⚠️  Warnings: {result.warnings}")
 