"""Regressão: subpastas de design nunca devem se aninhar dentro de si mesmas.

Contexto histórico: uma run real gerou `workspace_output/design/diagrams/diagrams/`,
`design/diagrams/{analysis,doubts,entrega_final,prototypes,reports}` e
`design/staging/{analysis,diagrams,doubts,entrega_final,prototypes,reports}`
— uma árvore inteira de subpastas oficiais recriada um nível abaixo do
correto, dentro da própria pasta de diagramas e dentro de uma pasta
"staging" que nunca deveria existir.

Causa raiz histórica: `_FILESYSTEM_TOOL_NAMES` incluía "save_artifact" ao
mesmo tempo em que `AGENT_DIRS["mermaid_specialist"]` apontava para
"design/diagrams" (uma subpasta, não a raiz "design") — o binding injetava
essa subpasta como base_dir, e design_filesystem.py trata base_dir como a
RAIZ de uma árvore completa (analysis/, diagrams/, prototypes/, reports/,
doubts/, entrega_final/), recriando a árvore inteira um nível abaixo.

Correção definitiva (roadmap "Integrar design_filesystem.py ao
agent_factory.py"): duas mudanças em conjunto eliminam o incidente sem
abrir mão do binding centralizado:
1. `AGENT_DIRS` unifica os 6 agentes de Time 2 em uma única raiz "design"
   (nunca mais uma subpasta por agente) — pré-condição verificada abaixo em
   `test_agent_dirs_time_2_aponta_para_raiz_design_unica`.
2. `save_artifact` (e as demais tools de design_filesystem.py) voltam a
   estar em `_FILESYSTEM_TOOL_NAMES`, recebendo base_dir=<raiz "design">
   via closure — respeitando WORKSPACE_OUTPUT_DIR como os demais times.

Os testes abaixo replicam o caminho real: criar o agente via
`create_se_agent(agent_subdir=...)` como os arquivos de produção fazem, e
confirmar que uma chamada de `save_artifact` cai na raiz compartilhada
"design", nunca em uma subpasta dela — o invariante de fundo (sem
aninhamento) é o mesmo de antes; só a causa que o garante mudou.
"""

from pathlib import Path

from google.adk.tools import FunctionTool

from shared.agent_factory import create_se_agent, _bind_tool_to_workspace, _FILESYSTEM_TOOL_NAMES
from shared.tools.design_filesystem import save_artifact
from shared.workspace import AGENT_DIRS


def test_save_artifact_esta_em_filesystem_tool_names_com_binding_para_raiz_unica():
    """Pós-roadmap: save_artifact DEVE ser bound por agent_subdir — a causa
    raiz do incidente não era o binding em si, e sim o binding apontar para
    uma subpasta ("design/diagrams") em vez da raiz compartilhada
    ("design"). Com AGENT_DIRS unificado (verificado no teste seguinte),
    o binding é seguro."""
    assert "save_artifact" in _FILESYSTEM_TOOL_NAMES
    assert "list_staging_files" not in _FILESYSTEM_TOOL_NAMES


def test_agent_dirs_time_2_aponta_para_raiz_design_unica():
    """Nenhum agente do Time 2 deve mapear para uma subpasta de 'design' —
    todos compartilham a mesma raiz."""
    agentes_time2 = [
        "design_architect",
        "design_orchestrator",
        "mermaid_specialist",
        "markdown_specialist",
        "validator",
        "io_agent",
    ]
    for agente in agentes_time2:
        assert AGENT_DIRS[agente] == "design", (
            f"AGENT_DIRS['{agente}'] = {AGENT_DIRS[agente]!r} — deveria ser "
            f"'design' (raiz compartilhada), nunca uma subpasta dela."
        )


def test_bind_tool_to_workspace_injeta_base_dir_em_save_artifact(tmp_path):
    """Pós-roadmap: _bind_tool_to_workspace DEVE criar uma nova FunctionTool
    para save_artifact, injetando base_dir=agent_workspace via closure —
    invisível ao LLM. Chamamos a tool resultante e confirmamos que o
    arquivo é escrito exatamente dentro do agent_workspace informado
    (aqui, uma raiz "design" simulada — a garantia de que essa raiz é
    sempre a raiz compartilhada, e não uma subpasta por agente, vem de
    AGENT_DIRS/get_agent_workspace, testado separadamente)."""
    design_root_simulada = tmp_path / "design"
    design_root_simulada.mkdir(parents=True)

    tool = FunctionTool(save_artifact)
    result = _bind_tool_to_workspace(
        tool,
        agent_workspace=str(design_root_simulada),
        workspace_root=str(tmp_path),
    )
    # Tool reconhecida (save_artifact está em _FILESYSTEM_TOOL_NAMES) ->
    # binding cria uma NOVA FunctionTool, nunca retorna a mesma instância.
    assert result is not tool

    fn = getattr(result, "func", result)
    saved = fn(filename="_teste.md", content="# x")
    assert saved["status"] == "ok"
    assert Path(saved["path"]).resolve() == (design_root_simulada / "analysis" / "_teste.md").resolve()


def test_regressao_incidente_mermaid_specialist_via_create_se_agent(monkeypatch, tmp_path):
    """Reproduz o caminho real de produção: cria o agente exatamente como
    src/agents/mermaid_specialist/agent.py faz (create_se_agent com
    agent_subdir='mermaid_specialist'), chama a save_artifact resultante, e
    confirma que o arquivo cai em <design_root>/diagrams/, nunca em
    <design_root>/diagrams/diagrams/.

    Pós-roadmap: `agent_subdir='mermaid_specialist'` é resolvido via
    AGENT_DIRS -> "design" -> get_agent_workspace() ->
    WORKSPACE_OUTPUT_DIR/design. Isolamos WORKSPACE_OUTPUT_DIR para
    tmp_path (não mais para um caminho decorrelacionado), de forma que
    design_root abaixo seja exatamente a raiz que create_se_agent vai
    injetar via binding.
    """
    design_root = tmp_path / "design"
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))

    agent = create_se_agent(
        name="mermaid_specialist_teste",
        description="d",
        instruction="i",
        tools=[save_artifact],
        agent_subdir="mermaid_specialist",
    )

    # Localiza a tool save_artifact entre as tools do agente construído.
    save_tool = None
    for t in agent.tools:
        fn = getattr(t, "func", t)
        if getattr(fn, "__name__", None) == "save_artifact":
            save_tool = fn
            break
    assert save_tool is not None, "save_artifact deveria estar entre as tools do agente"

    result = save_tool(filename="diagrama_HU-001_login.mmd", content="flowchart TD\n")

    assert result["status"] == "ok"
    esperado = design_root / "diagrams" / "diagrama_HU-001_login.mmd"
    nao_deveria_existir = design_root / "diagrams" / "diagrams"

    assert esperado.exists(), f"arquivo deveria estar em {esperado}"
    assert not nao_deveria_existir.exists(), (
        "não deveria existir uma subpasta 'diagrams' dentro de 'diagrams' — "
        "esse é exatamente o incidente reportado."
    )
    # Nenhuma outra subpasta oficial (analysis, doubts, entrega_final,
    # prototypes, reports) deveria ter sido recriada dentro de diagrams/.
    for indevida in ("analysis", "doubts", "entrega_final", "prototypes", "reports"):
        assert not (design_root / "diagrams" / indevida).exists()
