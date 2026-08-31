"""QA de critérios de aceite dentro do loop coder ↔ executor (PoC issue #394).

Exporta a verificação e o seu resultado. Importar este pacote CONSTRÓI o
`LlmAgent` do QA, porque `verificacao` o referencia no topo — mesmo
comportamento do `executor/agent.py`, que constrói o validador ao ser
importado. Nenhum workspace é criado no import (`get_agent_workspace` só é
chamado em tempo de execução), que é a parte que realmente importa: fazê-lo no
import criaria diretórios sem o marcador `.ai4se_workspace` e impediria
`init_workspace()` de limpar o workspace depois.
"""

from .schemas import CHAVE_QA, CHAVE_QA_EVIDENCIAS, CHAVES_DE_CICLO, ResultadoQA
from .verificacao import base_tecnica_comprovada, verificar_criterios_por_e2e

__all__ = [
    "CHAVE_QA",
    "CHAVE_QA_EVIDENCIAS",
    "CHAVES_DE_CICLO",
    "ResultadoQA",
    "base_tecnica_comprovada",
    "verificar_criterios_por_e2e",
]
