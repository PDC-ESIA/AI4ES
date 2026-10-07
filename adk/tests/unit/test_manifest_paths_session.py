"""Paths dos manifestos de fase com o workspace isolado por sessão.

Regressão: com a pasta `<yyyyMMdd-HHmm>-<sessão>/`, o manifesto de design
passou a gravar `<sessão>/design/...` (relativizado um nível acima da raiz do
workspace), que o coder não conseguia abrir. Os paths devem ser relativos à
raiz do workspace da sessão — mesma convenção de requisitos e codificação.
"""

import json

from shared.workspace import get_workspace_root, session_workspace

_SID = "585c972b-5ed8-41aa-82df-ae16537e097a"


def _escrever(path, conteudo="conteudo"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(conteudo, encoding="utf-8")


def _arvore_design(root):
    _escrever(root / "design" / "analysis" / "analise_tecnica_HU-001.md", "# análise")
    _escrever(root / "design" / "diagrams" / "diagrama_HU-001.mmd", "graph TD")
    _escrever(root / "design" / "validation" / "veredicto.md", "✅ APROVADO")


def test_manifesto_de_design_usa_paths_relativos_a_sessao(tmp_path, monkeypatch):
    from src.agents.workflow_design_pipeline.manifest import build_design_manifest

    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "workspace_output"))
    with session_workspace(_SID):
        root = get_workspace_root()
        assert root.name.endswith(_SID)  # pasta da sessão de fato no meio
        _arvore_design(root)
        manifesto = build_design_manifest()

    paths = sorted(a.path for a in manifesto.artifacts)
    assert paths == [
        "design/analysis/analise_tecnica_HU-001.md",
        "design/diagrams/diagrama_HU-001.mmd",
        "design/validation/veredicto.md",
    ]


def test_coder_e_design_leem_artefatos_do_manifesto_de_design(tmp_path, monkeypatch):
    from shared.tools.coding_tools.context_engineer_tools import tool_ler_artefatos
    from shared.tools.design_filesystem import read_phase_artifact
    from src.agents.workflow_design_pipeline.manifest import build_design_manifest

    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "workspace_output"))
    with session_workspace(_SID):
        _arvore_design(get_workspace_root())
        manifesto = build_design_manifest()
        itens = [{"path": a.path, "tipo": a.tipo} for a in manifesto.artifacts]

        lido = tool_ler_artefatos(paths_json=json.dumps(itens), fase="design")
        assert lido["sucesso"] is True
        assert lido["total_lidos"] == len(itens) == 3
        assert lido["fallback"] is False

        for item in itens:
            assert read_phase_artifact(item["path"])["status"] == "ok"


def test_leitores_toleram_prefixos_legados(tmp_path, monkeypatch):
    """Manifestos gravados por versões anteriores ainda devem abrir."""
    from shared.tools.coding_tools.context_engineer_tools import tool_ler_artefatos
    from shared.tools.design_filesystem import read_phase_artifact

    monkeypatch.setenv("WORKSPACE_OUTPUT_DIR", str(tmp_path / "workspace_output"))
    with session_workspace(_SID):
        root = get_workspace_root()
        _arvore_design(root)
        legados = [
            "workspace_output/design/analysis/analise_tecnica_HU-001.md",
            f"{root.name}/design/analysis/analise_tecnica_HU-001.md",
        ]
        for path in legados:
            lido = tool_ler_artefatos(
                paths_json=json.dumps([{"path": path, "tipo": "analise"}]), fase="design"
            )
            assert lido["total_lidos"] == 1, path
            assert read_phase_artifact(path)["status"] == "ok", path
