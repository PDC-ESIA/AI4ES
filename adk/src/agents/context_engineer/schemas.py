"""Schemas Pydantic do Context Engineer.

Define MacroContext (contexto global do épico), Contract (fronteiras de I/O
de cada task) e Task (Context Window completo para o coder).

Portado de feat/me2/coding_squad (Time 4).
"""

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class MacroContext(BaseModel):
    """Contexto global — compartilhado por todas as tasks da sessão."""

    summary: str = Field(description="Resumo de 1 linha do objetivo maior")
    tech_stack: list[str] = Field(
        description="Stack obrigatória (ex: ['Python', 'FastAPI', 'PostgreSQL'])"
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
    interfaces: Optional[list[str | dict[str, Any]]] = Field(
        default=None,
        description=(
            "Assinatura de interface/contrato que deve ser respeitado. "
            "Aceita lista de assinaturas em texto e/ou objetos estruturados."
        ),
    )

    @field_validator("interfaces", mode="before")
    @classmethod
    def normalize_interfaces(cls, value: Any) -> Any:
        """Normaliza entrada única (string/objeto) para lista."""
        if isinstance(value, (str, dict)):
            return [value]
        return value


class Task(BaseModel):
    """Uma tarefa de codificação contextualizada (Context Window) para o Coder."""

    id: str = Field(description="Identificador da task (ex: TASK-001)")
    type: str = Field(description="Tipo: frontend | backend | database | infra | test")
    complexity: str = Field(description="Complexidade: low | medium | high")
    description: str = Field(description="Descrição clara do que codificar")
    business_rules: list[str] = Field(
        default_factory=list,
        description="Regras de negócio específicas desta task",
    )
    acceptance_criteria: list[str] = Field(
        description="Critérios de aceitação verificáveis (checklist)"
    )
    contract: Contract = Field(
        description="Fronteiras: o que ler e o que produzir"
    )


class TasksOutput(BaseModel):
    """Saída completa do Context Engineer."""

    macro_context: MacroContext = Field(
        description="Contexto global do épico — compartilhado por todas as tasks"
    )
    tasks: list[Task] = Field(
        description="Lista de tasks contextualizadas para o Agente Coder"
    )
