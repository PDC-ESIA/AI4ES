"""Schemas Pydantic do workflow coding_review.

Define os modelos de saída do cr_context_engineer (TasksOutput) e o schema
de validação da tool de persistência de tasks (SalvarTaskSchema).
"""

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Schemas de saída do cr_context_engineer
# ---------------------------------------------------------------------------


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
    interfaces: Optional[list[str]] = Field(
        default=None,
        description=(
            "Assinatura(s) de interface/contrato que devem ser respeitadas. "
            "Aceita str única, dict (chave: valor) ou list[str] na entrada; "
            "sempre normalizado para list[str] internamente."
        ),
    )

    @field_validator("interfaces", mode="before")
    @classmethod
    def _coerce_interfaces(cls, v: Any) -> Optional[list[str]]:
        """Normaliza str/dict/list em list[str] antes da validação de tipo."""
        if v is None:
            return None
        if isinstance(v, str):
            return [v]
        if isinstance(v, dict):
            return [f"{chave}: {valor}" for chave, valor in v.items()]
        if isinstance(v, list):
            return [item if isinstance(item, str) else str(item) for item in v]
        raise TypeError(
            f"interfaces deve ser str, dict, list[str] ou None — "
            f"recebido {type(v).__name__}"
        )


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
    """Saída completa do cr_context_engineer."""

    macro_context: MacroContext = Field(
        description="Contexto global do épico — compartilhado por todas as tasks"
    )
    tasks: list[Task] = Field(
        description="Lista de tasks contextualizadas para o Agente Coder"
    )


# ---------------------------------------------------------------------------
# Schema de validação da tool de persistência
# ---------------------------------------------------------------------------


class SalvarTaskSchema(BaseModel):
    task_id: str = Field(..., description="ID da task (ex: 'TASK-001')")
    task_json: str = Field(..., description="Conteúdo JSON serializado da task")

    @field_validator("task_id")
    @classmethod
    def validar_task_id(cls, v):
        if not v.startswith("TASK-"):
            raise ValueError(f"task_id deve iniciar com 'TASK-'. Recebido: '{v}'")
        return v
