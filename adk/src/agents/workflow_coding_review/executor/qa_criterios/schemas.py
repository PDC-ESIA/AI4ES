"""Contratos do QA de critérios de aceite dentro do loop (PoC issue #394).

O agente de QA responde a UMA pergunta por critério: "a aplicação, navegada de
verdade, faz o que este critério pede?". A resposta não é prosa — é um teste
Playwright que passa ou falha contra a aplicação no ar.

Por que o contrato é ESTE, e não o `EntradaAutonomaE2E` do `e2e_test_generator`
existente: aquele contrato exige `rotas_ou_telas` com `passos_automacao`
estruturados (ação + localizador tipado), produzidos por um `action_planner`
upstream. É um planejamento de jornada completo, montado antes de o agente
rodar. Aqui a entrada é a lista de critérios da Task e o HTML da aplicação viva;
o que se pede ao LLM é bem menor — o corpo de um teste por critério — e o que
sobra de garantia vem de checagem determinística sobre o que ele escreveu (ver
`spec.py`), não de um schema de planejamento.
"""

from __future__ import annotations

from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from shared.tools.coding_tools.harness_schemas import CriterionEvidence

# Chave de ciclo publicada no session state: o que o QA fez nesta rodada, para
# auditoria. Exportada para o `TaskIterator` limpá-la entre tasks — sem isso, uma
# task cujo QA não rodou herdaria o registro da task anterior e a auditoria
# apontaria uma verificação que nunca aconteceu.
CHAVE_QA = "qa_criterios_resultado"

# Evidência por critério que o QA produziu na rodada. Fica no state, e não no
# report em disco, porque o report pertence ao harness — sobrescrevê-lo com a
# saída de outro produtor apagaria a fronteira que faz dele um sensor confiável.
# É desta chave que sai o que o coder recebe sobre os critérios reprovados.
CHAVE_QA_EVIDENCIAS = "qa_criterios_evidencias"

CHAVES_DE_CICLO: tuple[str, ...] = (CHAVE_QA, CHAVE_QA_EVIDENCIAS)


class TesteDeCriterio(BaseModel):
    """Um teste Playwright que comprova (ou refuta) UM critério de aceite.

    Os aliases e o default de `titulo` não são generosidade: numa execução real
    o modelo devolveu `{"id": ..., "corpo": ...}` — sem `criterion_id` e sem
    `titulo` —, o `output_schema` do ADK levantou `ValidationError` DENTRO do
    runner, e a rodada inteira de QA virou um no-op silencioso. Um campo com
    nome quase certo não pode custar a verificação toda.

    É a mesma tolerância que `criterios_aceite` aplica a `description`/
    `criterion` e que `Contract._coerce_interfaces` aplica às chaves traduzidas:
    a forma é normalizada aqui; o que não dá para aproveitar cai no portão de
    `spec.validar_corpo`, que é onde a recusa tem significado.
    """

    model_config = ConfigDict(populate_by_name=True)

    criterion_id: str = Field(
        validation_alias=AliasChoices(
            "criterion_id", "id", "criterio_id", "criterionId"
        ),
        description="Id do critério na Task que este teste comprova (ex.: CA-01).",
    )
    titulo: str = Field(
        default="",
        validation_alias=AliasChoices("titulo", "title", "nome", "name"),
        description=(
            "Descrição curta do que o teste verifica, em português. Não repetir "
            "o id — ele é prefixado automaticamente."
        ),
    )
    corpo: str = Field(
        validation_alias=AliasChoices("corpo", "body", "codigo", "code"),
        description=(
            "Corpo do teste em TypeScript, usando `page` e `expect` do "
            "Playwright. SEM import, SEM a declaração `test(...)` em volta: "
            "apenas as instruções de dentro do teste."
        ),
    )


class CriterioNaoVerificavel(BaseModel):
    """Um critério que o QA declara não conseguir comprovar navegando a app.

    Existe para que "não dá para verificar" seja uma resposta explícita e barata,
    em vez de um teste inventado que passa sem provar nada. Um critério estético
    ("visual minimalista") ou que dependa de estado externo cai aqui — e vira
    `NAO_AUTOMATIZAVEL` na evidência, nunca `nao_atendido`.
    """

    model_config = ConfigDict(populate_by_name=True)

    criterion_id: str = Field(
        validation_alias=AliasChoices(
            "criterion_id", "id", "criterio_id", "criterionId"
        ),
        description="Id do critério na Task (ex.: CA-01).",
    )
    motivo: str = Field(
        default="",
        validation_alias=AliasChoices("motivo", "reason", "justificativa"),
        description="Por que este critério não é comprovável navegando a aplicação.",
    )


class EspecificacaoCriterios(BaseModel):
    """A saída do agente de QA: o que ele consegue testar, e o que não consegue."""

    testes: list[TesteDeCriterio] = Field(
        default_factory=list,
        description="Um teste por critério que o QA consegue comprovar navegando.",
    )
    nao_verificaveis: list[CriterioNaoVerificavel] = Field(
        default_factory=list,
        description="Critérios que o QA declara fora do alcance da navegação.",
    )

    @field_validator("nao_verificaveis", mode="before")
    @classmethod
    def _aceitar_lista_de_ids(cls, valor: Any) -> Any:
        """Absorve `["CA-03", "CA-04"]` além da lista de objetos.

        Numa execução real o modelo devolveu exatamente isso, e o
        `ValidationError` resultante derrubou a rodada inteira de QA. O id
        sozinho é aproveitável — só falta o motivo, que é texto de auditoria e
        não muda decisão nenhuma.
        """
        if not isinstance(valor, list):
            return valor
        return [
            {"criterion_id": item, "motivo": "(motivo não informado pelo QA)"}
            if isinstance(item, str)
            else item
            for item in valor
        ]


class ResultadoQA(BaseModel):
    """O que a verificação por QA produziu nesta rodada.

    Attributes:
        executado: Se a verificação chegou a rodar testes contra a aplicação.
            `False` cobre todos os motivos de não ter rodado — artefato sem
            interface, app que não subiu, runtime Playwright ausente — e nesse
            caso `evidencias` vem VAZIA, para que quem consome caia na evidência
            do harness em vez de registrar reprovação por ausência de medida.
        motivo: Por que não executou; vazio quando executou.
        evidencias: Uma `CriterionEvidence` por critério verificado.
        spec_path: Caminho do `.spec.ts` gerado, para auditoria.
    """

    executado: bool = False
    motivo: str = ""
    evidencias: list[CriterionEvidence] = Field(default_factory=list)
    spec_path: str | None = None

    def como_dict(self) -> dict:
        """Forma serializável para o session state (auditoria da rodada)."""
        return {
            "executado": self.executado,
            "motivo": self.motivo,
            "spec_path": self.spec_path,
            "criterios_verificados": len(self.evidencias),
            "por_resultado": {
                resultado: sum(
                    1 for e in self.evidencias if e.outcome.value == resultado
                )
                for resultado in sorted({e.outcome.value for e in self.evidencias})
            },
        }
