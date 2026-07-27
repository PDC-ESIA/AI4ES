"""Schemas Pydantic do Context Engineer.

Define MacroContext (contexto global do épico), Contract (fronteiras de I/O
de cada task) e Task (Context Window completo para o coder).

Atualizado para incluir a rastreabilidade entre requisitos, designe e tasks
para o enriquecimento de contexto.
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
        if v is None:
            return None
        if isinstance(v, str):
            return [v]
        if isinstance(v, dict):
            resultado = []
            for chave, valor in v.items():
                if isinstance(valor, dict):
                    # serializa dicts aninhados como JSON string
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
    description: str = Field(description="Descrição clara do que codificar")
    business_rules: list[str] = Field(
        default_factory=list,
        description="Regras de negócio específicas desta task",
    )
    acceptance_criteria: list[str] = Field(
        description="Critérios de aceitação verificáveis derivados dps RFs, RNFs e decisões de designe"
    )
    contract: Contract = Field(
        description="Fronteiras: o que ler e o que produzir"
    )
    requirement_id: str = Field(
        description=(
            "ID do requisito funcional de origem desta task "
            "(ex: RF-001). Garante a rastreabilidade até o time de Requisitos."
        )
    )
    design_refs: list[str] = Field(
        description=(
            "Referência aos artefatos de design e arquitetura que motivara, essa esta task. "
            "Pode incluir nomes de diagramas, relatórios de arquitetura mínima e análises técnicas por HU. "
            "Deve conter ao menos uma referência."
        )
    )

class TasksOutput(BaseModel):
    """Saída completa do Context Engineer."""

    macro_context: MacroContext = Field(
        description="Contexto global do épico — compartilhado por todas as tasks"
    )
    tasks: list[Task] = Field(
        description="Lista de tasks contextualizadas para o Agente Coder"
    )
