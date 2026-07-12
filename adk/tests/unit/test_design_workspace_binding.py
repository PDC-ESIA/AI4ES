"""Testes do binding ao workspace dos especialistas de Time 2 com filesystem tools.

Escopo: design_architect, mermaid_specialist, markdown_specialist, io_agent.
Validator é stateless (recebe content inline, sem filesystem tools) —
binding ao workspace não se aplica a ele.

⚠️ ATUALIZADO:
Este teste antes exigia que `save_artifact` tivesse `base_dir` bound por
agente (via closure, apontando para um subdir tipo "design/diagrams" ou
"design/staging"). Essa era exatamente a causa raiz de um incidente real:
`design_filesystem.py` trata `base_dir` como a RAIZ de uma árvore completa
de subpastas oficiais (analysis/, diagrams/, prototypes/, reports/,
doubts/, entrega_final/) — uma raiz COMPARTILHADA entre todos os agentes do
Time 2, nunca uma subpasta isolada por agente. Fazer bind de
"design/diagrams" como se fosse a raiz do mermaid_specialist recriava essa
árvore inteira um nível abaixo do correto (design/diagrams/diagrams/,
design/diagrams/analysis/ etc.).

O comportamento correto — verificado abaixo — é o oposto do que este teste
verificava antes: nenhum especialista de Time 2 deve ter `save_artifact`
bound a um base_dir isolado. Todos devem compartilhar a mesma raiz "design",
resolvida internamente por `shared/tools/design_filesystem.py`
independentemente de qualquer workspace por agente.
"""
from pathlib import Path

import pytest

# validator é stateless (recebe content inline, sem filesystem tools) —
# binding ao workspace não se aplica.
ESPECIALISTAS = [
    "design_architect",
    "mermaid_specialist",
    "markdown_specialist",
    "io_agent",
]


@pytest.mark.parametrize("nome", ESPECIALISTAS)
def test_especialista_nao_tem_save_artifact_isolado_por_agente(nome, monkeypatch, tmp_path):
    """save_artifact dos especialistas de Time 2 NUNCA deve ter base_dir
    isolado por agente — todos compartilham a mesma raiz "design".

    Verifica chamando a tool (com a raiz de design isolada via monkeypatch
    direto no módulo, para não tocar no workspace_output real) e confirmando
    que o arquivo cai na pasta oficial de primeiro nível esperada pela
    extensão/alias — nunca em uma subpasta extra nomeada com o subdir do
    próprio agente.
    """
    from shared.tools import design_filesystem as df

    design_root = tmp_path / "design"
    monkeypatch.setattr(df, "DESIGN_DIR", design_root)
    monkeypatch.setattr(df, "ADK_DIR", tmp_path)
    # Isola também o workspace legado (usado só por outros times) para não
    # tocar no workspace_output real do projeto durante o teste.
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "ws_legado_nao_usado_por_design"))

    import importlib
    modulo = importlib.import_module(f"src.agents.{nome}.agent")
    importlib.reload(modulo)

    agente = modulo.agent

    save_tool = None
    for t in agente.tools:
        func = getattr(t, "func", None) or (t if callable(t) else None)
        if func is not None and getattr(func, "__name__", "") == "save_artifact":
            save_tool = func
            break

    assert save_tool is not None, f"{nome} deveria ter save_artifact entre suas tools."

    result = save_tool(filename="_binding_test.md", content="# test")
    assert result["status"] == "ok"

    caminho_escrito = Path(result["path"]).resolve()
    # Sem alias e sem extensão .html/.mmd, o destino correto é a raiz
    # compartilhada design/analysis/ — nunca uma subpasta com o nome do
    # próprio agente (ex.: design/diagrams/, design/staging/, design/reports/).
    esperado = (design_root / "analysis" / "_binding_test.md").resolve()
    assert caminho_escrito == esperado, (
        f"{nome}: esperava escrita em {esperado}, mas foi em {caminho_escrito} — "
        f"indica que save_artifact voltou a ter base_dir isolado por agente."
    )
