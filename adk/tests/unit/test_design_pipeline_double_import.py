"""Regressão: o módulo do design_pipeline precisa suportar carga DUPLA.

Contexto do incidente: no `adk web`, o agent_loader importa a pasta como módulo
de topo `workflow_design_pipeline` (agents_dir=src/agents), enquanto
design_orchestrator e orchestrator importam o MESMO arquivo como
`src.agents.workflow_design_pipeline.agent`. São duas entradas distintas em
sys.modules, logo o corpo do módulo executa duas vezes — mas os especialistas
(`mermaid_specialist`, `validator`, ...) são singletons compartilhados. Como
SequentialAgent/ParallelAgent gravam `parent_agent` no sub_agent, a segunda
execução estourava com:

    Agent `mermaid_specialist` already has a parent agent, current parent:
    `diagram_flow`, trying to add: `diagram_flow`

derrubando /run_sse e /dev/build_graph com HTTP 500 para o pipeline de design.
"""

import importlib
import sys
from pathlib import Path

from src.agents.workflow_design_pipeline.agent import agent as design_pipeline

_AGENTS_DIR = Path(__file__).resolve().parents[2] / "src/agents"


def _load_como_agent_loader(nome: str = "workflow_design_pipeline"):
    """Importa a pasta como módulo de topo, igual ao agent_loader do `adk web`.

    O conftest já importou `src.agents.workflow_design_pipeline.agent`; esta
    segunda entrada em sys.modules reexecuta o corpo do módulo, que é
    exatamente o cenário que quebrava. Limpa os módulos criados no fim para não
    contaminar os outros testes.
    """
    inserido = str(_AGENTS_DIR) not in sys.path
    if inserido:
        sys.path.insert(0, str(_AGENTS_DIR))
    try:
        return importlib.import_module(nome)
    finally:
        for modulo in [m for m in list(sys.modules) if m == nome or m.startswith(f"{nome}.")]:
            sys.modules.pop(modulo, None)
        if inserido:
            sys.path.remove(str(_AGENTS_DIR))


def test_segunda_carga_do_modulo_nao_estoura_parent_agent():
    segunda = _load_como_agent_loader()

    assert segunda.root_agent.name == design_pipeline.name
    # Cada carga monta sua própria árvore: instâncias distintas, mesma forma.
    assert segunda.root_agent is not design_pipeline


def test_sub_agents_sao_copias_sem_parent_compartilhado():
    from src.agents.mermaid_specialist.agent import agent as mermaid_specialist

    diagram_flow = design_pipeline.sub_agents[1].sub_agents[1]
    mermaid_no_pipeline = diagram_flow.sub_agents[0]

    assert mermaid_no_pipeline.name == "mermaid_specialist"
    # O singleton global nunca é adotado pela árvore — quem entra é o clone.
    assert mermaid_no_pipeline is not mermaid_specialist
    assert mermaid_specialist.parent_agent is None
    assert mermaid_no_pipeline.parent_agent is diagram_flow
