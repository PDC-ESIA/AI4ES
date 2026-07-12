"""Testes de validate_analysis_sections (design_filesystem.py).

Contexto: Uma run
real produziu um arquivo analise_tecnica_*.md contendo apenas a Seção 1, sem
o delimitador "<<<FIM_SECAO>>>" e sem as seções 2-8 — e o design_architect
reportou conclusão mesmo assim, porque a única checagem existente era uma
autoavaliação textual (S/N por memória) do próprio LLM, e a verificação do
pipeline_controller também dependia de "ler e achar que está completo".

validate_analysis_sections() substitui essa checagem por uma verificação
estrutural determinística, reaproveitando a mesma lógica de parsing que
read_analysis_sections() já usa para separar seções.
"""

import pytest

from shared.tools import design_filesystem as df


@pytest.fixture
def design_root(tmp_path, monkeypatch):
    root = tmp_path / "design"
    monkeypatch.setattr(df, "DESIGN_DIR", root)
    monkeypatch.setattr(df, "ADK_DIR", tmp_path)
    return root


def _write_analysis(design_root, content, filename="analise_tecnica_HU-001.md"):
    path = design_root / "analysis" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


_COMPLETE_CONTENT = "\n<<<FIM_SECAO>>>\n".join(
    f"{n}. Título da seção {n}\nConteúdo real da seção {n}." for n in range(1, 9)
)


def test_arquivo_completo_com_8_secoes_e_reportado_como_completo(design_root):
    _write_analysis(design_root, _COMPLETE_CONTENT)

    result = df.validate_analysis_sections("analise_tecnica_HU-001.md", caller="teste")

    assert result["status"] == "ok"
    assert result["complete"] is True
    assert result["found_sections"] == list(range(1, 9))
    assert result["missing_sections"] == []
    assert result["empty_sections"] == []
    assert result["section_delimiter_count"] == 7


def test_regressao_bug_b_apenas_secao_1_sem_delimitador(design_root):
    """Reproduz exatamente o cenário do incidente: só a Seção 1, sem
    <<<FIM_SECAO>>> e sem as seções 2-8."""
    _write_analysis(
        design_root,
        "1. Compreensão do lote\n\nHU-001\n- Ator principal: Usuário\n",
    )

    result = df.validate_analysis_sections("analise_tecnica_HU-001.md", caller="teste")

    assert result["status"] == "ok"
    assert result["complete"] is False
    assert result["found_sections"] == [1]
    assert result["missing_sections"] == [2, 3, 4, 5, 6, 7, 8]
    assert result["section_delimiter_count"] == 0


def test_secao_presente_mas_vazia_e_reportada_em_empty_sections(design_root):
    """Uma seção com apenas o título (sem conteúdo) não deve contar como
    presente e válida — só como 'empty'."""
    content = (
        "1. Compreensão do lote\nConteúdo real.\n"
        "<<<FIM_SECAO>>>\n"
        "2. Decisão de Arquitetura e Trade-Offs\n"  # sem conteúdo após o título
        "<<<FIM_SECAO>>>\n"
    )
    _write_analysis(design_root, content)

    result = df.validate_analysis_sections("analise_tecnica_HU-001.md", caller="teste")

    assert result["complete"] is False
    assert result["found_sections"] == [1, 2]
    assert result["empty_sections"] == [2]
    assert result["missing_sections"] == [3, 4, 5, 6, 7, 8]


def test_arquivo_inexistente_retorna_erro(design_root):
    result = df.validate_analysis_sections("analise_tecnica_inexistente.md", caller="teste")

    assert result["status"] == "error"
    assert "não encontrado" in result["error"]


def test_aceita_alias_de_pasta_explicito(design_root):
    _write_analysis(design_root, _COMPLETE_CONTENT, filename="analise_tecnica_HU-002.md")

    result = df.validate_analysis_sections("ANALYSIS/analise_tecnica_HU-002.md", caller="teste")

    assert result["status"] == "ok"
    assert result["complete"] is True
