"""Regressão: subpastas de design nunca devem se aninhar dentro de si mesmas.

Contexto: uma run real gerou `workspace_output/design/diagrams/diagrams/`,
`design/diagrams/{analysis,doubts,entrega_final,prototypes,reports}` e
`design/staging/{analysis,diagrams,doubts,entrega_final,prototypes,reports}`
— uma árvore inteira de subpastas oficiais recriada um nível abaixo do
correto, dentro da própria pasta de diagramas e dentro de uma pasta
"staging" que nunca deveria existir.

Causa raiz (confirmada lendo shared/agent_factory.py e shared/workspace.py):
`_FILESYSTEM_TOOL_NAMES` incluía "save_artifact" (tool de
shared/tools/design_filesystem.py), fazendo `create_se_agent(...,
agent_subdir="mermaid_specialist")` injetar `base_dir=<workspace do
agente>` nessa tool via closure. Só que `AGENT_DIRS["mermaid_specialist"]`
apontava para "design/diagrams" (não para a raiz "design"), e
design_filesystem.py trata `base_dir` como a RAIZ de uma árvore completa de
subpastas (analysis/, diagrams/, prototypes/, reports/, doubts/,
entrega_final/) — então "design/diagrams" virava a raiz, e a árvore
inteira era recriada dentro dela.

Os testes abaixo replicam o caminho real: criar o agente via
`create_se_agent(agent_subdir=...)` como os arquivos de produção fazem, e
confirmar que uma chamada de `save_artifact` cai na raiz compartilhada
"design", nunca em uma subpasta dela.
"""

from google.adk.tools import FunctionTool

from shared.agent_factory import create_se_agent, _bind_tool_to_workspace, _FILESYSTEM_TOOL_NAMES
from shared.tools.design_filesystem import save_artifact
from shared.workspace import AGENT_DIRS


def test_save_artifact_nao_esta_mais_em_filesystem_tool_names():
    """A causa raiz do incidente: save_artifact nunca deve ser bound por
    agent_subdir, porque design_filesystem.py já tem seu próprio sistema de
    alias de pasta com uma única raiz compartilhada."""
    assert "save_artifact" not in _FILESYSTEM_TOOL_NAMES
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


def test_bind_tool_to_workspace_nao_altera_save_artifact(tmp_path):
    """Mesmo passando explicitamente um workspace de agente 'errado' (uma
    subpasta), _bind_tool_to_workspace não deve mais tocar em save_artifact —
    ele não está em nenhuma das 3 categorias bindáveis."""
    agent_ws_subpasta_errada = tmp_path / "ws" / "design" / "diagrams"
    agent_ws_subpasta_errada.mkdir(parents=True)

    tool = FunctionTool(save_artifact)
    result = _bind_tool_to_workspace(
        tool,
        agent_workspace=str(agent_ws_subpasta_errada),
        workspace_root=str(tmp_path / "ws"),
    )
    # Tool não reconhecida em nenhuma categoria -> retornada intacta.
    assert result is tool


def test_regressao_incidente_mermaid_specialist_via_create_se_agent(monkeypatch, tmp_path):
    """Reproduz o caminho real de produção: cria o agente exatamente como
    src/agents/mermaid_specialist/agent.py faz (create_se_agent com
    agent_subdir='mermaid_specialist'), chama a save_artifact resultante, e
    confirma que o arquivo cai em <design_root>/diagrams/, nunca em
    <design_root>/diagrams/diagrams/.

    Nota: shared/tools/design_filesystem.py resolve sua raiz (DESIGN_DIR) de
    forma independente de WORKSPACE_OUTPUT_DIR (usado por shared/workspace.py
    apenas para o binding legado de outros times) — por isso isolamos a raiz
    aqui via monkeypatch direto no módulo, como os demais testes de
    design_filesystem.py já fazem, em vez de setar a variável de ambiente.
    """
    from shared.tools import design_filesystem as df

    design_root = tmp_path / "design"
    monkeypatch.setattr(df, "DESIGN_DIR", design_root)
    monkeypatch.setattr(df, "ADK_DIR", tmp_path)
    # agent_subdir ainda passa por get_workspace_root()/AGENT_DIRS internamente
    # (mesmo não afetando mais save_artifact) — isolamos também para não
    # tocar no workspace_output real do projeto durante o teste.
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws_legado_nao_usado_por_save_artifact"))

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
