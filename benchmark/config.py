"""Configuração central do benchmark de LLMs para o Agente de Requisitos.

Implementa as decisões do protocolo.md (seções 4, 8, 13 e 14). Todo script do
benchmark lê daqui — nenhum valor experimental deve ser redefinido localmente,
sob pena de invalidar a comparabilidade entre execuções.
"""

from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ADK = RAIZ.parent / "adk"

WORKSPACE_OUTPUT = ADK / "workspace_output"
RUNS = RAIZ / "runs"
JUDGMENTS = RAIZ / "judgments"
RESULTS = RAIZ / "results"

PROVIDER = "github_copilot"

# Modelos avaliados: produzem os artefatos que serão pontuados.
# Todos verificados em 2026-09-10. Constar em /models não basta:
# "claude-sonnet-4.5" está no catálogo mas o endpoint o recusa, e "gpt-5.6-terra"
# só aceita /responses — como candidato ele roda via ADK_LLM_MODEL com o prefixo
# da ponte (github_copilot/responses/gpt-5.6-terra), então aqui vale só o rótulo.
CANDIDATOS = [
    "gpt-4o-mini",
    "gpt-5-mini",
    "gpt-5.4",
    "gpt-5.6-terra",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "claude-haiku-4.5",
    "claude-opus-5",
]

# Modelos que aplicam a rubrica. Independente de CANDIDATOS: os conjuntos podem
# ser disjuntos, parcialmente sobrepostos ou idênticos.
JUIZES = [
    "gpt-5-mini",
    "gemini-3.6-flash",
]

# Teste piloto: a autoavaliação é permitida e mantém o desenho balanceado (todo
# candidato recebe os mesmos dois juízes). O cegamento de montar_resposta() faz
# o juiz desconhecer a autoria, mas não impede que ele reconheça o próprio
# estilo — viés de auto-preferência continua sendo ameaça à validade.
# Ative para o experimento definitivo.
EXCLUIR_AUTOAVALIACAO = False


def juizes_de(candidato: str) -> list[str]:
    """Juízes elegíveis para avaliar um dado candidato."""
    if not EXCLUIR_AUTOAVALIACAO:
        return list(JUIZES)
    return [j for j in JUIZES if j != candidato]


def intersecao() -> list[str]:
    """Modelos que atuam nos dois papéis — sujeitos a autoavaliação."""
    return [m for m in CANDIDATOS if m in JUIZES]


# Protocolo §8. A ordem é fixa e usada tanto no prompt quanto nas tabelas.
CRITERIOS = [
    "correcao_tecnica",
    "completude",
    "clareza",
    "consistencia",
    "verificabilidade",
    "ausencia_ambiguidades",
    "organizacao",
    "conformidade_29148",
]

ROTULOS = {
    "correcao_tecnica": "Correção técnica",
    "completude": "Completude",
    "clareza": "Clareza",
    "consistencia": "Consistência",
    "verificabilidade": "Verificabilidade",
    "ausencia_ambiguidades": "Ausência de ambiguidades",
    "organizacao": "Organização",
    "conformidade_29148": "Conformidade com a ISO/IEC/IEEE 29148",
}

# Ordem canônica de concatenação dos artefatos. Precisa ser idêntica para todos
# os modelos: se variasse, a nota de "organização" refletiria a ordem de leitura
# do script em vez da qualidade da entrega.
ORDEM_PASTAS = ["HUs", "RFs", "RNFs", "RNs", "UCs", "Outros"]

# Juiz determinístico. Sem isto, reexecutar o julgamento produziria notas
# diferentes para a mesma resposta e a RQ3 mediria ruído do juiz.
TEMPERATURA_JUIZ = 0.0
TIMEOUT_S = 600
MAX_TENTATIVAS_JSON = 3

ALFA = 0.05


def modelo_litellm(nome: str) -> str:
    return f"{PROVIDER}/{nome}"
