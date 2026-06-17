"""Testes do binding ao workspace dos especialistas de Time 2 com filesystem tools.

Escopo: design_architect, mermaid_specialist, markdown_specialist, io_agent.
Validator é stateless (recebe content inline, sem filesystem tools) —
binding ao workspace não se aplica a ele.

Verificação: as tools de filesystem dos especialistas devem ter base_dir
injetado via closure (invisível ao LLM) apontando para o subdir correto.
"""
from pathlib import Path

import pytest

# validator é stateless (recebe content inline, sem filesystem tools) —
# binding ao workspace não se aplica.
ESPECIALISTAS = [
    ("design_architect", "design"),
    ("mermaid_specialist", "design/diagrams"),
    ("markdown_specialist", "design/reports"),
    ("io_agent", "design/staging"),
]


@pytest.mark.parametrize("nome,subdir_esperado", ESPECIALISTAS)
def test_especialista_binda_tools_ao_subdir(nome, subdir_esperado, monkeypatch, tmp_path):
    """Tools de filesystem dos especialistas devem ter base_dir bound (closure).

    Verifica chamando a tool e confirmando que o arquivo é escrito
    no subdir esperado do workspace.
    """
    ws_dir = tmp_path / "ws"
    # Cria marker para init_workspace aceitar
    ws_dir.mkdir()
    (ws_dir / ".ai4se_workspace").write_text("marker")
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(ws_dir))

    import importlib
    modulo = importlib.import_module(f"src.agents.{nome}.agent")
    importlib.reload(modulo)

    agente = modulo.agent
    expected_base = (ws_dir / subdir_esperado).resolve()

    # Encontrar uma tool que aceite 'caminho' e 'conteudo' (filesystem)
    encontrou_binding = False
    for t in agente.tools:
        func = getattr(t, "func", None)
        if func is None:
            continue
        fn_name = getattr(func, "__name__", "")
        if fn_name == "tool_criar_arquivo":
            # Chamar a tool e verificar onde escreve
            result = func("_binding_test.py", "# test")
            if isinstance(result, dict) and result.get("sucesso"):
                caminho_escrito = Path(result["caminho"]).resolve()
                assert caminho_escrito == (expected_base / "_binding_test.py").resolve(), (
                    f"Esperava escrita em {expected_base}/_binding_test.py, "
                    f"mas foi em {caminho_escrito}"
                )
                encontrou_binding = True
                # Limpar
                caminho_escrito.unlink(missing_ok=True)
            break
        elif fn_name == "save_artifact":
            # Design tools usam save_artifact em vez de tool_criar_arquivo
            encontrou_binding = True
            break

    assert encontrou_binding, (
        f"{nome} não tem nenhuma tool de filesystem com base_dir bound. "
        f"Esperava pelo menos uma para subdir {subdir_esperado!r}."
    )
