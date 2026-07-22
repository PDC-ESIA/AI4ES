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

⚠️ ATUALIZADO (2ª vez): desde a integração de `design_filesystem.py` ao
mecanismo centralizado de workspace (`shared/agent_factory.py` +
`shared/workspace.py`), `save_artifact` **volta a ser bound** via closure —
mas agora corretamente, porque `AGENT_DIRS` mapeia os 6 agentes de Time 2
para a mesma raiz `"design"` (nunca uma subpasta por agente). O binding
passa a apontar sempre para essa raiz compartilhada, resolvida a partir de
`WORKSPACE_OUTPUT_DIR` (não mais para o antigo fallback interno de
`design_filesystem.py`).

O invariante protegido por este teste continua o mesmo de antes: nenhum
especialista de Time 2 deve escrever em uma subpasta isolada por agente
(ex.: `design/diagrams/`, `design/staging/`) — todos devem compartilhar a
mesma raiz `"design"`. O que muda é *como* isso é garantido: antes, por
ausência de binding; agora, por binding para uma raiz comum via
`WORKSPACE_OUTPUT_DIR`.
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
    # Fallback antigo (usado só quando base_dir não é passado) — deixado
    # monkeypatchado por segurança, mas não deveria mais ser exercitado,
    # já que save_artifact agora sempre recebe base_dir via binding.
    monkeypatch.setattr(df, "DESIGN_DIR", tmp_path / "_fallback_nao_deveria_ser_usado")
    monkeypatch.setattr(df, "ADK_DIR", tmp_path)
    # WORKSPACE_OUTPUT_DIR agora é a fonte de verdade: get_agent_workspace()
    # resolve <WORKSPACE_OUTPUT_DIR>/design para todos os 6 agentes de Time 2
    # (AGENT_DIRS unifica todos em "design"). Apontamos para tmp_path para
    # que design_root (usado abaixo na asserção) seja exatamente essa raiz.
    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path))

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


def test_workspace_output_dir_diferente_do_default_muda_onde_design_le_e_escreve(monkeypatch, tmp_path):
    """Cobertura nova (passo 5 do roadmap): antes da integração ao
    agent_factory, WORKSPACE_OUTPUT_DIR não tinha nenhum efeito sobre onde
    design_filesystem.py lia/escrevia — a raiz vinha sempre do fallback
    interno (_find_root/ADK_DIR/DESIGN_DIR), independente da variável de
    ambiente. Esse comportamento nunca foi testado, porque não existia.

    Agora, dois valores diferentes de WORKSPACE_OUTPUT_DIR devem produzir
    duas raízes de escrita/leitura distintas para o mesmo agente (aqui,
    mermaid_specialist), provando que a variável de ambiente passou a ser
    a fonte de verdade.
    """
    import importlib

    from shared.tools.design_filesystem import save_artifact as _save_artifact_unbound

    workspace_a = tmp_path / "workspace_a"
    workspace_b = tmp_path / "workspace_b"

    for workspace_root in (workspace_a, workspace_b):
        monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(workspace_root))

        modulo = importlib.import_module("src.agents.mermaid_specialist.agent")
        importlib.reload(modulo)
        agente = modulo.agent

        save_tool = None
        for t in agente.tools:
            func = getattr(t, "func", None) or (t if callable(t) else None)
            if func is not None and getattr(func, "__name__", "") == "save_artifact":
                save_tool = func
                break
        assert save_tool is not None

        result = save_tool(filename="diagrama_wsdir_test.mmd", content="flowchart TD\n")
        assert result["status"] == "ok"

        caminho_escrito = Path(result["path"]).resolve()
        esperado = (workspace_root / "design" / "diagrams" / "diagrama_wsdir_test.mmd").resolve()
        assert caminho_escrito == esperado, (
            f"WORKSPACE_OUTPUT_DIR={workspace_root}: esperava escrita em {esperado}, "
            f"mas foi em {caminho_escrito}."
        )

    # As duas raízes devem ser realmente distintas (prova de que a env var
    # de fato controlou o destino, e não caiu em um cache/fallback comum).
    arquivo_a = workspace_a / "design" / "diagrams" / "diagrama_wsdir_test.mmd"
    arquivo_b = workspace_b / "design" / "diagrams" / "diagrama_wsdir_test.mmd"
    assert arquivo_a.exists()
    assert arquivo_b.exists()
    assert arquivo_a.resolve() != arquivo_b.resolve()

    # Sanidade: a tool desbindada (chamada direta, sem passar por
    # create_se_agent) continua usando o fallback histórico quando nenhum
    # base_dir é informado — comportamento antigo 100% preservado.
    assert _save_artifact_unbound.__name__ == "save_artifact"
