from pydantic import BaseModel, Field
from typing import Optional


class MacroContext(BaseModel):
    """Contexto global — compartilhado por todas as tasks da sessão."""

    summary: str = Field(
        description="Resumo de 1 linha do objetivo maior"
    )
    tech_stack: list[str] = Field(
        description="Stack obrigatória (ex: ['Python', 'FastAPI', 'PostgreSQL'])"
    )
    global_rules: list[str] = Field(
        description=(
            "Restrições arquiteturais que o Coder DEVE respeitar "
            "(ex: ['Usar SQLAlchemy', 'API RESTful', 'Sem estado local no frontend'])"
        )
    )


class Contract(BaseModel):
    """Fronteiras: o que o Coder pode consumir e o que deve produzir."""

    inputs: list[str] = Field(
        default_factory=list,
        description=(
            "Arquivos, funções ou módulos que o Coder pode LER "
            "mas NÃO deve modificar (ex: 'src/utils/auth.py')"
        ),
    )
    outputs: list[str] = Field(
        default_factory=list,
        description=(
            "Arquivos que o Coder deve CRIAR ou MODIFICAR "
            "(ex: 'src/components/SubmitButton.tsx')"
        ),
    )
    interfaces: Optional[str] = Field(
        default=None,
        description=(
            "Assinatura de interface/contrato que deve ser respeitado "
            "(ex: 'interface SubmitProps { isLoading: boolean; onClick: () => void; }')"
        ),
    )


class Task(BaseModel):
    """Uma tarefa de codificação contextualizada (Context Window) para o Agente Coder."""

    id: str = Field(description="Identificador da task (ex: TASK-001)")
    type: str = Field(
        description="Tipo da task: frontend | backend | database | infra | test"
    )
    complexity: str = Field(
        description="Complexidade estimada: low | medium | high"
    )
    description: str = Field(
        description="Descrição clara e objetiva do que deve ser codificado"
    )
    business_rules: list[str] = Field(
        default_factory=list,
        description="Regras de negócio específicas desta task"
    )
    acceptance_criteria: list[str] = Field(
        description="Critérios de aceitação verificáveis (checklist)"
    )
    contract: Contract = Field(
        description="Fronteiras: o que o Coder pode ler e o que deve produzir"
    )


class TasksOutput(BaseModel):
    """Saída completa do Context Engineer: contexto macro + lista de tasks."""

    macro_context: MacroContext = Field(
        description="Contexto global do épico — compartilhado por todas as tasks"
    )
    tasks: list[Task] = Field(
        description="Lista de tasks contextualizadas para o Agente Coder"
    )
