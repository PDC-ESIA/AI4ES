"""Schemas Pydantic do Context Engineer do workflow coding_review.

Define MacroContext (contexto global do épico), Contract (fronteiras de I/O
de cada task) e Task (Context Window completo para o coder), além de TasksOutput
(saída estruturada do agente). Autocontido para o workflow coding_review.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class MacroContext(BaseModel):
    """Contexto global — compartilhado por todas as tasks da sessão."""

    summary: str = Field(description="Resumo de 1 linha do objetivo maior")
    product_type: str = Field(
        default="a definir",
        description=(
            "Tipo de produto final inferido dos artefatos, orienta stack e "
            "critérios do Coder. Vocabulário recomendado (aberto): "
            "web_app | api_service | cli | library | mobile_app | "
            "desktop_app | data_pipeline | outro. Use 'a definir' se não "
            "for possível inferir. Outro valor é permitido quando o produto "
            "não se encaixar na lista."
        ),
    )
    tech_stack: list[str] = Field(
        description=(
            "Stack obrigatória inferida dos artefatos, coerente com o "
            "product_type (ex: Java/Spring, Node/Express, Python/FastAPI, "
            "Go). Use ['a definir'] se não for possível inferir."
        )
    )
    global_rules: list[str] = Field(
        description=(
            "Restrições arquiteturais que o Coder DEVE respeitar, derivadas "
            "dos artefatos (ex: convenções de camadas, padrão de API, "
            "estratégia de persistência). Neutras quanto à tecnologia."
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
            "Pontos de contato públicos que devem ser respeitados, conforme o "
            "product_type (rota HTTP, comando CLI, assinatura de função/módulo, "
            "evento…). Aceita str única, dict (chave: valor) ou list[str] na "
            "entrada; sempre normalizado para list[str] internamente."
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
    type: str = Field(
        description=(
            "Categoria da task, coerente com o product_type. Vocabulário "
            "recomendado (aberto): component | interface | data | infra | "
            "test | docs. Outro valor é permitido quando o produto exigir."
        )
    )
    complexity: str = Field(description="Complexidade: low | medium | high")
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

    requirement_refs: list[str] = Field(
        default_factory=list,
        description=(
            "IDs de todos os artefatos de requirements que contribuíram para "
            "esta task — RNFs, RNs, HUs e outros além do RF de origem. "
            "requirement_id é o RF principal; requirement_refs complementa "
            "com todos os demais que enriqueceram o contexto."
        ),
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
    """Saída completa do Context Engineer — inclui o caminho BLOQUEADO.

    O prompt manda PARAR e gerar Doubt Artifact quando faltam artefatos mínimos
    de requisitos ou design ("PARE IMEDIATAMENTE. Não gere nenhuma task"). Com
    `macro_context` e `tasks` obrigatórios, essa resposta legítima violava o
    schema, e a `ValidationError` levantada pelo ADK em
    `__maybe_save_output_to_state` derrubava a invocação inteira — o pipeline
    morria com stack trace em vez de reportar o bloqueio.

    Por isso todos os campos têm default: uma resposta bloqueada é um resultado
    VÁLIDO. O envelope vazio é então tratado a jusante pelo TaskIterator, que o
    classifica como `lista_vazia` (input inválido), zera a cobertura e faz o
    reviewer bloquear com relatório — o mesmo caminho fail-closed de qualquer
    outra entrada insuficiente.

    `status` é texto livre de propósito: o modelo não enxerga este schema
    (o provedor descarta `response_format`), então recusar um valor fora de um
    enum apenas recriaria o crash que este desenho existe para eliminar.
    """

    status: str = Field(
        default="concluido",
        description=(
            "'concluido' quando há tasks; 'bloqueado' quando o fluxo parou por "
            "falta de artefatos. Texto livre — nunca invalida a resposta."
        ),
    )
    bloqueio: Optional[str] = Field(
        default=None,
        description=(
            "Quando bloqueado: o que faltou e qual fase precisa ser reprocessada."
        ),
    )
    macro_context: Optional[MacroContext] = Field(
        default=None,
        description=(
            "Contexto global do épico — compartilhado por todas as tasks. "
            "Ausente quando o fluxo foi bloqueado antes de gerar tasks."
        ),
    )
    tasks: list[Task] = Field(
        default_factory=list,
        description=(
            "Tasks contextualizadas para o Agente Coder. Lista VAZIA é a "
            "resposta correta no caminho bloqueado — não invente tasks para "
            "preencher o schema."
        ),
    )

    @property
    def bloqueado(self) -> bool:
        """Sem tasks não há o que codificar, qualquer que seja o `status`."""
        return not self.tasks
