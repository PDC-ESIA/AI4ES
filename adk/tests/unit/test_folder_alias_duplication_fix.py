"""Testes de _resolve_path_arg / save_artifact contra duplicação de prefixo
de pasta (alias).

Contexto: uma run real salvou os diagramas .mmd do mermaid_specialist em
`design/diagrams/diagrams/` em vez de `design/diagrams/` — o nome do arquivo
chegou a save_artifact já contendo "diagrams/" embutido, e o Agente IO, por
convenção própria, prefixa novamente com o alias "DIAGRAMS/" antes de
delegar à ferramenta de persistência. O resultado: arquivo fisicamente
salvo (nada se perdeu), mas em uma subpasta que nenhuma listagem de primeiro
nível de DIAGRAMS/ enxerga — o markdown_specialist e o validator concluíram
que os diagramas não existiam e bloquearam o pipeline pedindo intervenção
humana para "mover" arquivos que, na verdade, só precisavam ser salvos no
lugar certo desde o início.

`_resolve_path_arg` (usada por save_artifact, append_artifact,
append_architect_section, patch_section, read_file, read_multiple_files e
validate_analysis_sections) agora remove prefixos de alias duplicados no
início do nome do arquivo, tornando a resolução de caminho idempotente.
"""

import pytest

from shared.tools import design_filesystem as df


@pytest.fixture
def design_root(tmp_path, monkeypatch):
    root = tmp_path / "design"
    monkeypatch.setattr(df, "DESIGN_DIR", root)
    monkeypatch.setattr(df, "ADK_DIR", tmp_path)
    return root


def test_prefixo_simples_de_diagrams_resolve_normalmente(design_root):
    result = df.save_artifact("diagrams/diagrama_HU-001_login.mmd", "flowchart TD\n", caller="teste")

    assert result["status"] == "ok"
    saved_path = design_root / "diagrams" / "diagrama_HU-001_login.mmd"
    assert saved_path.exists()
    # não pode ter criado uma subpasta "diagrams" dentro de "diagrams"
    assert not (design_root / "diagrams" / "diagrams").exists()


def test_regressao_incidente_prefixo_duplicado_diagrams_diagrams(design_root):
    """Reproduz exatamente o path relatado no incidente real:
    'diagrams/diagrams/diagrama_HU-001_login.mmd'."""
    result = df.save_artifact(
        "diagrams/diagrams/diagrama_HU-001_login.mmd", "flowchart TD\n", caller="teste"
    )

    assert result["status"] == "ok"
    saved_path = design_root / "diagrams" / "diagrama_HU-001_login.mmd"
    assert saved_path.exists(), "arquivo deveria estar em DIAGRAMS/, não em DIAGRAMS/diagrams/"
    assert not (design_root / "diagrams" / "diagrams").exists()

    # Uma listagem de primeiro nível de DIAGRAMS/ agora enxerga o arquivo —
    # exatamente a checagem que o markdown_specialist e o validator fazem.
    listing = df.list_design_files(filetype="mmd", folder="diagrams", caller="teste")
    assert listing["status"] == "ok"
    assert "diagrama_HU-001_login.mmd" in listing["files"]


def test_prefixo_duplicado_case_insensitive(design_root):
    """DIAGRAMS/diagrams/x.mmd (maiúsculo + minúsculo) também deve colapsar."""
    result = df.save_artifact("DIAGRAMS/diagrams/diagrama_HU-002.mmd", "flowchart TD\n", caller="teste")

    assert result["status"] == "ok"
    assert (design_root / "diagrams" / "diagrama_HU-002.mmd").exists()
    assert not (design_root / "diagrams" / "diagrams").exists()


def test_prefixo_triplicado_tambem_colapsa(design_root):
    result = df.save_artifact(
        "diagrams/diagrams/diagrams/diagrama_HU-003.mmd", "flowchart TD\n", caller="teste"
    )

    assert result["status"] == "ok"
    assert (design_root / "diagrams" / "diagrama_HU-003.mmd").exists()


def test_alias_diferente_nao_e_removido_por_engano(design_root):
    """Só remove segmentos que são REALMENTE aliases de pasta reconhecidos —
    um nome de arquivo que por acaso comece com algo parecido não deve ser
    truncado."""
    result = df.save_artifact("analysis/relatorio_setembro.md", "conteudo\n", caller="teste")

    assert result["status"] == "ok"
    assert (design_root / "analysis" / "relatorio_setembro.md").exists()


def test_prefixo_nao_reconhecido_continua_dando_erro(design_root):
    result = df.save_artifact("pasta_inventada/arquivo.md", "conteudo\n", caller="teste")

    assert result["status"] == "error"
    assert "não reconhecida" in result["error"]
