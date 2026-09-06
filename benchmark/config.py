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

CANDIDATOS = [
    "gpt-5-mini",
    "gemini-3.5-flash",
    "gemini-3.8-flash",
]


# Protocolo §14: o mesmo modelo nunca avalia a própria resposta. Com três
# candidatos, cada resposta recebe dois juízes independentes.
JUIZES = {c: [j for j in CANDIDATOS if j != c] for c in CANDIDATOS}

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
