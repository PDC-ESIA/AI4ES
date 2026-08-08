"""Schemas Pydantic do Context Engineer.
 
Define MacroContext (contexto global do épico), Contract (fronteiras de I/O
de cada task) e Task (Context Window completo para o coder).
 
Atualizado para incluir rastreabilidade entre requisitos, design e tasks
conforme issue #299.
"""
 
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator
 
 
class MacroContext(BaseModel):
    """Contexto global — compartilhado por todas as tasks da sessão."""
 
    summary: str = Field(description="Resumo de 1 linha do objetivo maior")
    tech_stack: list[str] = Field(
        description=(
            "Stack/linguagem decidida pelo arquiteto a partir dos artefatos de "
            "requisitos e arquitetura/design (ex: ['Python', 'FastAPI', "
            "'PostgreSQL'], ['Rust'], ['C']). NÃO é imposição do sistema: quando "
            "não for possível inferir dos artefatos, use ['a definir'] — nesse "
            "caso o Coder escolhe a stack conforme a natureza da task."
        )
    )
    global_rules: list[str] = Field(
        description=(
            "Restrições arquiteturais que o Coder DEVE respeitar "
            "(ex: ['Usar SQLAlchemy', 'API RESTful'])"
        )
    )
 
 
class Contract(BaseModel):
    """Fronteiras: o que o Coder pode consumir e o que deve produzir."""
 
    inputs: list[str] = Field(
        default_factory=list,
        description="Arquivos, funções ou módulos que o Coder pode LER mas NÃO deve modificar",
    )
    outputs: list[str] = Field(
        default_factory=list,
        description="Arquivos que o Coder deve CRIAR ou MODIFICAR",
    )
    interfaces: list[str] = Field(
        default_factory=list,
        description=(
            "Assinatura(s) de interface/contrato que devem ser respeitadas. "
            "Aceita str única, dict (chave: valor) ou list[str] na entrada; "
            "sempre normalizado para list[str] internamente."
        ),
    )
 
    @field_validator("interfaces", mode="before")
    @classmethod
    def _coerce_interfaces(cls, v: Any) -> list[str]:
        """Normaliza str/dict/list em list[str] antes da validação de tipo."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        if isinstance(v, dict):
            resultado = []
            for chave, valor in v.items():
                if isinstance(valor, dict):
                    import json
                    resultado.append(str(chave) + ": " + json.dumps(valor, ensure_ascii=False))
                else:
                    resultado.append(str(chave) + ": " + str(valor))
            return resultado
        if isinstance(v, list):
            resultado = []
            for item in v:
                if isinstance(item, str):
                    resultado.append(item)
                elif isinstance(item, dict):
                    import json
                    resultado.append(json.dumps(item, ensure_ascii=False))
                else:
                    resultado.append(str(item))
            return resultado
        raise TypeError(
            "interfaces deve ser str, dict, list[str] ou None — "
            "recebido " + type(v).__name__
        )
 
 
class Task(BaseModel):
    """Uma tarefa de codificação contextualizada (Context Window) para o Coder."""
 
    id: str = Field(description="Identificador da task (ex: TASK-001)")
    type: str = Field(description="Tipo: frontend | backend | database | infra | test")
    complexity: str = Field(description="Complexidade: low | medium | high")
    delivery_mode: Literal["service", "command"] = Field(
        default="service",
        description=(
            "Como a entrega é validada pelo harness. "
            "'service': a solução sobe e fica ouvindo (web app, API) — validada "
            "por healthcheck HTTP. "
            "'command': a solução roda e termina (função, benchmark, algoritmo, "
            "CLI, biblioteca) — validada por exit code e saída/testes. "
            "Inferido pelo arquiteto a partir dos artefatos: RF de serviço/API "
            "→ 'service'; pedido de função/algoritmo/benchmark → 'command'."
        ),
    )
    description: str = Field(description="Descrição clara do que codificar")
    business_rules: list[str] = Field(
        default_factory=list,
        description="Regras de negócio específicas desta task",
    )
    acceptance_criteria: list[str] = Field(
        description=(
            "Critérios de aceitação verificáveis derivados dos RFs, RNFs "
            "e decisões de design disponíveis no workspace"
        )
    )
    contract: Contract = Field(
        description="Fronteiras: o que ler e o que produzir"
    )

    requirement_id: str = Field(
        description=(
            "ID do requisito funcional de origem desta task "
            "(ex: RF-001). Garante rastreabilidade até o Time 1."
        )
    )
    design_refs: list[str] = Field(
        default_factory=list,
        description=(
            "Referências aos artefatos de design que motivaram esta task. "
            "Pode incluir análises técnicas e diagramas por HU. "
            "Lista vazia quando o RF não tem HU associada e não há "
            "artefatos de design relevantes disponíveis no workspace."
        )
    )
 
    @field_validator("design_refs")
    @classmethod
    def validar_design_refs(cls, v: list[str]) -> list[str]:
        """Permite lista vazia apenas para RFs sem HU associada (caso legítimo)."""
        return v
 
 
class TasksOutput(BaseModel):
    """Saída completa do Context Engineer."""
 
    macro_context: MacroContext = Field(
        description="Contexto global do épico — compartilhado por todas as tasks"
    )
    tasks: list[Task] = Field(
        description="Lista de tasks contextualizadas para o Agente Coder"
    )